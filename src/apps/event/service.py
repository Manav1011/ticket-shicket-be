from datetime import datetime, timezone
from uuid import UUID
import json

from apps.event.enums import EventAccessType, LocationMode

from .exceptions import AlreadyExistsError, EventNotFound, InvalidScanTransition, OrganizerOwnershipError, InvalidAsset
from .models import EventModel, EventDayModel, EventMediaAssetModel
from .response import FieldErrorResponse
from sqlalchemy.exc import IntegrityError
from src.utils.s3_client import get_s3_client
from src.utils.file_validation import FileValidator, FileValidationError
from .repository import EventRepository
from apps.organizer.repository import OrganizerRepository
from apps.ticketing.repository import TicketingRepository
from apps.allocation.repository import CouponRepository, AllocationRepository
from apps.allocation.models import CouponModel, OrderModel, OrderCouponModel, ClaimLinkModel
from src.config import settings
from apps.allocation.enums import CouponType, GatewayType
from apps.ticketing.enums import OrderType, OrderStatus, TicketCategory
from apps.payment_gateway.services.factory import get_gateway
from exceptions import BadRequestError


def _serialize_for_json(obj):
    """Recursively convert UUID objects and Pydantic models to JSON-serializable format."""
    if isinstance(obj, UUID):
        return str(obj)
    elif hasattr(obj, 'model_dump'):  # Pydantic model
        return _serialize_for_json(obj.model_dump())
    elif isinstance(obj, dict):
        return {k: _serialize_for_json(v) for k, v in obj.items()}
    elif isinstance(obj, (list, tuple)):
        return [_serialize_for_json(item) for item in obj]
    else:
        return obj


class PurchaseService:
    """Service for online ticket purchase flow — includes coupon validation and discount calculation."""

    def __init__(self, coupon_repository: CouponRepository, repository: EventRepository) -> None:
        self._coupon_repo = coupon_repository
        self.repository = repository

    async def preview_order(
        self,
        event_id: UUID,
        event_day_id: UUID,
        ticket_type_id: UUID,
        quantity: int,
        coupon_code: str | None = None,
    ) -> dict:
        """
        Validate and return price breakdown without creating an order or locking tickets.
        Raises BadRequestError if validation fails.
        """
        from apps.ticketing.repository import TicketingRepository
        from apps.event.models import EventDayModel
        from sqlalchemy import select

        # Validate event exists and is published
        event_result = await self.repository.session.execute(
            select(EventModel).where(EventModel.id == event_id)
        )
        event = event_result.scalar_one_or_none()
        if not event:
            raise BadRequestError("Event not found")
        if not event.is_published or event.status != "published":
            raise BadRequestError("Event is not available for purchase")

        # Validate event_day belongs to event
        day_result = await self.repository.session.execute(
            select(EventDayModel).where(
                EventDayModel.id == event_day_id,
                EventDayModel.event_id == event_id,
            )
        )
        day = day_result.scalar_one_or_none()
        if not day:
            raise BadRequestError("Event day not found")

        # Validate ticket_type belongs to event
        ticket_type_repo = TicketingRepository(self.repository.session)
        ticket_type = await ticket_type_repo.get_ticket_type_for_event(ticket_type_id, event_id)
        if not ticket_type:
            raise BadRequestError("Ticket type not found")

        # Check pool availability
        available_count = await self._count_available_pool_tickets(
            event_id, event_day_id, ticket_type_id
        )
        if quantity > available_count:
            raise BadRequestError(f"Only {available_count} tickets available, requested {quantity}")

        # Calculate pricing
        subtotal = float(ticket_type.price) * quantity
        coupon_applied = None
        discount = 0.0

        if coupon_code:
            coupon = await self.validate_coupon(coupon_code, subtotal)
            discount = self.calculate_discount(coupon, subtotal)
            coupon_applied = {
                "code": coupon.code,
                "type": coupon.type.value if hasattr(coupon.type, 'value') else coupon.type,
                "value": float(coupon.value),
                "max_discount": float(coupon.max_discount) if coupon.max_discount else None,
            }

        final = subtotal - discount

        return {
            "subtotal_amount": f"{subtotal:.2f}",
            "discount_amount": f"{discount:.2f}",
            "final_amount": f"{final:.2f}",
            "coupon_applied": coupon_applied,
        }

    async def _count_available_pool_tickets(
        self,
        event_id: UUID,
        event_day_id: UUID,
        ticket_type_id: UUID,
    ) -> int:
        """Count pool tickets that are available for purchase (not owned, not locked)."""
        from apps.ticketing.models import TicketModel
        from sqlalchemy import select, func

        result = await self.repository.session.execute(
            select(func.count(TicketModel.id)).where(
                TicketModel.event_id == event_id,
                TicketModel.event_day_id == event_day_id,
                TicketModel.ticket_type_id == ticket_type_id,
                TicketModel.owner_holder_id.is_(None),
                TicketModel.lock_reference_id.is_(None),
            )
        )
        return result.scalar_one()

    async def create_order(
        self,
        user_id: UUID,
        event_id: UUID,
        event_day_id: UUID,
        ticket_type_id: UUID,
        quantity: int,
        coupon_code: str | None = None,
        order_id: UUID | None = None,
    ) -> dict:
        """
        Create a purchase order: validate → resolve buyer holder → lock tickets →
        create order → call Razorpay → return razorpay checkout details.

        If order creation fails after locking, clears locks before re-raising.

        Raises BadRequestError on validation failure.
        Raises exception on gateway/DB failure (after cleanup).
        """
        import uuid as uuid_lib
        from datetime import timedelta
        from apps.ticketing.repository import TicketingRepository
        from sqlalchemy import select

        if order_id is None:
            order_id = uuid_lib.uuid4()

        # Validate event (published)
        event_result = await self.repository.session.execute(
            select(EventModel).where(EventModel.id == event_id)
        )
        event = event_result.scalar_one_or_none()
        if not event:
            raise BadRequestError("Event not found")
        if not event.is_published or event.status != "published":
            raise BadRequestError("Event is not available for purchase")

        # Validate event_day
        day_result = await self.repository.session.execute(
            select(EventDayModel).where(
                EventDayModel.id == event_day_id,
                EventDayModel.event_id == event_id,
            )
        )
        day = day_result.scalar_one_or_none()
        if not day:
            raise BadRequestError("Event day not found")

        # Validate ticket_type (must be public/online category)
        ticketing_repo = TicketingRepository(self.repository.session)
        ticket_type = await ticketing_repo.get_ticket_type_for_event(ticket_type_id, event_id)
        if not ticket_type:
            raise BadRequestError("Ticket type not found")
        if ticket_type.category == TicketCategory.b2b:
            raise BadRequestError("Cannot purchase B2B ticket type directly")

        # Resolve buyer TicketHolder
        allocation_repo = AllocationRepository(self.repository.session)
        buyer_holder = await allocation_repo.resolve_holder(user_id=user_id)

        # Validate coupon and calculate discount (if provided)
        subtotal = float(ticket_type.price) * quantity
        discount = 0.0
        coupon_record = None

        if coupon_code:
            coupon_record = await self.validate_coupon(coupon_code, subtotal)
            discount = self.calculate_discount(coupon_record, subtotal)

        final_amount = subtotal - discount

        # Lock tickets BEFORE creating order (prevents over-selling)
        locked_ticket_ids = await ticketing_repo.lock_tickets_for_purchase(
            event_id=event_id,
            event_day_id=event_day_id,
            ticket_type_id=ticket_type_id,
            quantity=quantity,
            order_id=order_id,
            lock_ttl_minutes=30,
        )

        try:
            # Create OrderModel
            order = OrderModel(
                id=order_id,
                event_id=event_id,
                user_id=user_id,
                receiver_holder_id=buyer_holder.id,
                sender_holder_id=None,
                event_day_id=event_day_id,
                type=OrderType.purchase,
                subtotal_amount=subtotal,
                discount_amount=discount,
                final_amount=final_amount,
                status=OrderStatus.pending,
                lock_expires_at=datetime.utcnow() + timedelta(minutes=30),
                gateway_type=GatewayType.RAZORPAY_ORDER,
            )
            self.repository.session.add(order)

            # Save coupon application
            if coupon_record and discount > 0:
                order_coupon = OrderCouponModel(
                    order_id=order_id,
                    coupon_id=coupon_record.id,
                    discount_applied=discount,
                )
                self.repository.session.add(order_coupon)

            await self.repository.session.flush()

            # Call Razorpay to create checkout order
            gateway = await get_gateway("razorpay")
            razorpay_result = await gateway.create_checkout_order(
                order_id=order_id,
                amount=int(final_amount * 100),  # paise
                currency=ticket_type.currency or "INR",
                event_id=event_id,
            )

            # Update order with gateway order_id
            order.gateway_order_id = razorpay_result.gateway_order_id
            order.gateway_response = razorpay_result.gateway_response
            await self.repository.session.flush()

            return {
                "order_id": order_id,
                "razorpay_order_id": razorpay_result.gateway_order_id,
                "razorpay_key_id": razorpay_result.key_id,
                "amount": razorpay_result.amount,
                "currency": razorpay_result.currency,
                "subtotal_amount": f"{subtotal:.2f}",
                "discount_amount": f"{discount:.2f}",
                "final_amount": f"{final_amount:.2f}",
                "status": "pending",
            }

        except Exception as e:
            # Clear locks before re-raising — order creation failed
            await ticketing_repo.clear_locks_for_order(order_id)
            raise e

    async def poll_order_status(self, order_id: UUID, user_id: UUID) -> dict:
        """
        Poll status of a purchase order.
        If paid, returns claim link URL and JWT for immediate redemption.
        """
        from apps.ticketing.enums import OrderStatus
        from sqlalchemy import select

        result = await self.repository.session.execute(
            select(OrderModel).where(OrderModel.id == order_id)
        )
        order = result.scalar_one_or_none()
        if not order:
            from exceptions import NotFoundError
            raise NotFoundError(f"Order {order_id} not found")

        # Ownership check
        if order.user_id != user_id:
            from exceptions import ForbiddenError
            raise ForbiddenError("You do not have access to this order")

        response = {
            "order_id": order_id,
            "status": order.status.value if hasattr(order.status, 'value') else order.status,
            "ticket_count": 0,
            "jwt": None,
            "claim_url": None,
            "failure_reason": None,
        }

        if order.status == OrderStatus.paid:
            # Find the claim link created for this order
            from apps.allocation.models import AllocationModel
            link_result = await self.repository.session.execute(
                select(ClaimLinkModel, AllocationModel)
                .join(AllocationModel, ClaimLinkModel.allocation_id == AllocationModel.id)
                .where(AllocationModel.order_id == order_id)
            )
            row = link_result.one_or_none()
            if row:
                claim_link, allocation = row
                response["ticket_count"] = allocation.ticket_count
                # V2 Checkout: V2 FE handles claim via /claim/:token
                response["claim_url"] = f"{settings.FRONTEND_URL}/claim/{claim_link.token}"

                # Generate a temporary JWT for immediate redemption in the same browser session.
                # This is a short-lived access token for the claim flow (not a scan JWT).
                # Uses claim_link.id + order_id so frontend can call claim endpoint without
                # requiring the user to already have a session. Phase 5 (webhook) sets
                # claim_link.jwt_jti for the actual scan JWT — that replaces this after
                # the webhook fires and allocation is fully set up.
                from auth.jwt import access

                jwt_payload = {
                    "sub": "guest_purchase",
                    "claim_link_id": str(claim_link.id),
                    "order_id": str(order_id),
                }
                response["jwt"] = access.encode(
                    payload=jwt_payload,
                    expire_period=3600,
                )

        elif order.status == OrderStatus.failed:
            # Check for failure reason in allocation (purchase orders have 1 allocation)
            from apps.allocation.models import AllocationModel
            alloc_result = await self.repository.session.execute(
                select(AllocationModel).where(AllocationModel.order_id == order_id)
            )
            alloc = alloc_result.scalar_one_or_none()
            if alloc:
                response["failure_reason"] = alloc.failure_reason

        return response

    @staticmethod
    def calculate_discount(coupon: CouponModel, subtotal: float) -> float:
        """
        Apply coupon to subtotal and return discount amount.
        Returns 0 if coupon is invalid or cannot be applied.
        """
        if not coupon.is_active:
            return 0.0

        now = datetime.utcnow()
        if not (coupon.valid_from <= now <= coupon.valid_until):
            return 0.0

        if coupon.used_count >= coupon.usage_limit:
            return 0.0

        if subtotal < float(coupon.min_order_amount):
            return 0.0

        if coupon.type == CouponType.FLAT:
            discount = float(coupon.value)
        else:  # PERCENTAGE
            discount = subtotal * (float(coupon.value) / 100)
            if coupon.max_discount is not None:
                discount = min(discount, float(coupon.max_discount))

        return min(discount, subtotal)

    async def validate_coupon(
        self,
        code: str,
        subtotal: float,
    ) -> CouponModel:
        """
        Validate coupon code and return coupon if valid.
        Raises BadRequestError if invalid.
        """
        coupon = await self._coupon_repo.get_by_code(code)
        if not coupon:
            from exceptions import BadRequestError
            raise BadRequestError("Invalid coupon code")

        discount = self.calculate_discount(coupon, subtotal)
        if discount == 0.0:
            if coupon.used_count >= coupon.usage_limit:
                from exceptions import BadRequestError
                raise BadRequestError("Coupon usage limit reached")
            from exceptions import BadRequestError
            raise BadRequestError("Coupon cannot be applied to this order")

        return coupon


class EventService:
    def __init__(self, repository: EventRepository, organizer_repository: OrganizerRepository, ticketing_repository: TicketingRepository | None = None) -> None:
        self.repository = repository
        self.organizer_repository = organizer_repository
        self._ticketing_repo = ticketing_repository

    async def create_draft_event(self, owner_user_id, organizer_page_id, title, event_access_type):
        if not title or not title.strip():
            from .exceptions import ValidationError
            raise ValidationError("Title is required")

        organizer = await self.organizer_repository.get_by_id_for_owner(
            organizer_page_id, owner_user_id
        )
        if not organizer:
            raise OrganizerOwnershipError

        event = EventModel(
            organizer_page_id=organizer_page_id,
            created_by_user_id=owner_user_id,
            title=title,
            slug=None,
            description=None,
            event_type=None,
            status="draft",
            event_access_type=event_access_type,
            setup_status={},
            location_mode=None,
            timezone=None,
            start_date=None,
            end_date=None,
        )
        self.repository.add(event)
        await self.repository.session.flush()
        await self.repository.session.refresh(event)
        # Auto-create B2B ticket type for this event so B2B transfers work out of the box
        if self._ticketing_repo is not None:
            await self._ticketing_repo.get_or_create_b2b_ticket_type_for_event(event.id)
        return event

    async def _build_setup_status(self, event, day_count, ticket_type_count, allocation_count):
        basic_info_complete = all(
            [
                getattr(event, "title", None),
                getattr(event, "event_access_type", None),
                getattr(event, "location_mode", None),
                getattr(event, "timezone", None),
            ]
        )
        schedule_complete = day_count > 0
        tickets_complete = getattr(event, "event_access_type", None) == EventAccessType.open or (
            ticket_type_count > 0 and allocation_count > 0 and getattr(event, "show_tickets", False)
        )

        # Check if banner asset exists
        banner_assets = await self.repository.list_media_assets(event.id, asset_type="banner")
        assets_complete = len(banner_assets) > 0

        return {
            "basic_info": basic_info_complete,
            "schedule": schedule_complete,
            "tickets": tickets_complete,
            "assets": assets_complete,
        }

    async def _refresh_setup_status(self, event):
        day_count = await self.repository.count_event_days(event.id)
        ticket_type_count = await self.repository.count_ticket_types(event.id)
        allocation_count = await self.repository.count_ticket_allocations(event.id)
        event.setup_status = await self._build_setup_status(
            event, day_count, ticket_type_count, allocation_count
        )
        await self.repository.session.flush()
        return event.setup_status

    def _validate_basic_info(self, event) -> list[FieldErrorResponse]:
        """Validate basic_info section based on location_mode and event_access_type."""
        errors = []

        # Required for all events
        if not getattr(event, 'title', None):
            errors.append(FieldErrorResponse(field="title", message="Title is required", code="MISSING_REQUIRED_FIELD"))
        if not getattr(event, 'event_access_type', None):
            errors.append(FieldErrorResponse(field="event_access_type", message="Event access type is required", code="MISSING_REQUIRED_FIELD"))
        if not getattr(event, 'location_mode', None):
            errors.append(FieldErrorResponse(field="location_mode", message="Location mode is required", code="MISSING_REQUIRED_FIELD"))
        if not getattr(event, 'timezone', None):
            errors.append(FieldErrorResponse(field="timezone", message="Timezone is required", code="MISSING_REQUIRED_FIELD"))

        # Location-specific validation
        lm = getattr(event, 'location_mode', None)

        # I3: Validate location_mode is a known value
        if lm is not None and lm not in (LocationMode.venue, LocationMode.online, LocationMode.recorded, LocationMode.hybrid):
            errors.append(FieldErrorResponse(field="location_mode", message=f"Invalid location_mode: {lm}", code="INVALID_FIELD_VALUE"))

        if lm in (LocationMode.venue, LocationMode.hybrid):
            venue_fields = [
                ('venue_name', 'Venue name is required for venue events'),
                ('venue_address', 'Venue address is required for venue events'),
                ('venue_city', 'Venue city is required for venue events'),
                ('venue_country', 'Venue country is required for venue events'),
            ]
            for field, msg in venue_fields:
                if not getattr(event, field, None):
                    errors.append(FieldErrorResponse(field=field, message=msg, code="MISSING_REQUIRED_FIELD"))

        if lm in (LocationMode.online, LocationMode.hybrid):
            if not getattr(event, 'online_event_url', None):
                errors.append(FieldErrorResponse(field="online_event_url", message="Online event URL is required for online events", code="MISSING_REQUIRED_FIELD"))

        if lm == LocationMode.recorded:
            if not getattr(event, 'recorded_event_url', None):
                errors.append(FieldErrorResponse(field="recorded_event_url", message="Recorded event URL is required for recorded events", code="MISSING_REQUIRED_FIELD"))

        return errors

    def _validate_schedule(self, event, days: list) -> list[FieldErrorResponse]:
        """Validate schedule section - day count and day-level requirements."""
        errors = []

        if len(days) == 0:
            errors.append(FieldErrorResponse(field="days", message="At least 1 event day is required", code="MISSING_REQUIRED_FIELD"))
            return errors

        for day in days:
            if not getattr(day, 'date', None):
                errors.append(FieldErrorResponse(field=f"day_{day.day_index}.date", message=f"Day {day.day_index}: date is required", code="MISSING_REQUIRED_FIELD"))

            # start_time required for ticketed events
            if getattr(event, 'event_access_type', None) == EventAccessType.ticketed:
                if not getattr(day, 'start_time', None):
                    errors.append(FieldErrorResponse(field=f"day_{day.day_index}.start_time", message=f"Day {day.day_index}: start time is required for ticketed events", code="MISSING_REQUIRED_FIELD"))

        return errors

    def _validate_tickets(self, event, ticket_types: list, allocations: list) -> list[FieldErrorResponse]:
        errors = []
        if getattr(event, 'event_access_type', None) == EventAccessType.open:
            return errors
        if len(ticket_types) == 0 or len(allocations) == 0:
            return errors
        for alloc in allocations:
            if getattr(alloc, 'quantity', 0) <= 0:
                errors.append(FieldErrorResponse(field=f"allocation_{getattr(alloc, 'id', 'unknown')}.quantity", message="Allocation quantity must be greater than 0", code="INVALID_FIELD_VALUE"))
        return errors

    async def _validate_assets(self, event) -> list[FieldErrorResponse]:
        """Validate assets section - requires at least one banner image."""
        errors = []
        banner_assets = await self.repository.list_media_assets(event.id, asset_type="banner")
        if len(banner_assets) == 0:
            errors.append(FieldErrorResponse(field="banner", message="At least 1 banner image is required", code="MISSING_REQUIRED_FIELD"))
        return errors

    async def validate_for_publish(self, owner_user_id: UUID, event_id: UUID):
        """Run all validations and return structured response for publish readiness."""
        event = await self.repository.get_by_id_for_owner(event_id, owner_user_id)
        if not event:
            raise EventNotFound

        days = await self.repository.list_event_days(event_id)
        ticket_types = await self.repository.list_ticket_types(event_id)
        allocations = await self.repository.list_allocations(event_id)

        basic_info_errors = self._validate_basic_info(event)
        schedule_errors = self._validate_schedule(event, days)
        ticket_errors = self._validate_tickets(event, ticket_types, allocations)
        assets_errors = await self._validate_assets(event)

        basic_info_complete = len(basic_info_errors) == 0
        schedule_complete = len(schedule_errors) == 0
        # tickets_complete requires both real tickets AND show_tickets enabled
        tickets_present = len(ticket_types) > 0 and len(allocations) > 0
        tickets_complete = (event.event_access_type == EventAccessType.open) or (tickets_present and getattr(event, 'show_tickets', False))
        assets_complete = len(assets_errors) == 0

        # Build blocking issues (tickets no longer blocks publish - tickets_pending handles that)
        blocking_issues = []
        if not basic_info_complete:
            blocking_issues.append("Complete basic_info section")
        if not schedule_complete:
            blocking_issues.append("Complete schedule section")
        if not assets_complete:
            blocking_issues.append("Upload a banner image")

        # Determine redirect hint (first incomplete section with errors)
        redirect_hint = None
        if not basic_info_complete and basic_info_errors:
            redirect_hint = {"section": "basic_info", "fields": [e.field for e in basic_info_errors]}
        elif not schedule_complete and schedule_errors:
            redirect_hint = {"section": "schedule", "fields": [e.field for e in schedule_errors]}
        elif not tickets_complete and ticket_errors:
            redirect_hint = {"section": "tickets", "fields": [e.field for e in ticket_errors]}
        elif not assets_complete and assets_errors:
            redirect_hint = {"section": "assets", "fields": [e.field for e in assets_errors]}

        return {
            "can_publish": basic_info_complete and schedule_complete and assets_complete,
            "event_id": event_id,
            "published_at": None,
            "sections": {
                "basic_info": {"complete": basic_info_complete, "errors": basic_info_errors},
                "schedule": {"complete": schedule_complete, "errors": schedule_errors},
                "tickets": {"complete": tickets_complete, "errors": ticket_errors},
                "assets": {"complete": assets_complete, "errors": assets_errors},
            },
            "blocking_issues": blocking_issues,
            "redirect_hint": redirect_hint,
        }

    async def publish_event(self, owner_user_id: UUID, event_id: UUID):
        """Publish event if all validations pass. Returns updated event."""
        validation = await self.validate_for_publish(owner_user_id, event_id)

        if not validation["can_publish"]:
            from .exceptions import CannotPublishEvent
            # Convert UUID objects to strings for JSON serialization
            validation_serializable = _serialize_for_json(validation)
            raise CannotPublishEvent(validation_serializable)

        event = await self.repository.get_by_id_for_owner(event_id, owner_user_id)
        event.status = "published"
        event.is_published = True
        event.published_at = datetime.utcnow()
        await self.repository.session.flush()
        await self.repository.session.refresh(event)
        return event

    async def get_event_detail(self, owner_user_id, event_id):
        event = await self.repository.get_by_id_for_owner(event_id, owner_user_id)
        if not event:
            raise EventNotFound
        return event

    async def interest_event(self, actor_kind, actor_id, event_id, ip_address, user_agent):
        event = await self.repository.get_by_id_for_update(event_id)
        if not event:
            raise EventNotFound

        existing = await self.repository.get_interest_for_actor(
            event_id=event_id,
            user_id=actor_id if actor_kind == "user" else None,
            guest_id=actor_id if actor_kind == "guest" else None,
        )
        if existing:
            return {"created": False, "interested_counter": event.interested_counter}

        try:
            async with self.repository.session.begin_nested():
                await self.repository.create_event_interest(
                    event_id=event_id,
                    user_id=actor_id if actor_kind == "user" else None,
                    guest_id=actor_id if actor_kind == "guest" else None,
                    ip_address=ip_address,
                    user_agent=user_agent,
                )
                await self.repository.increment_event_interest_counter(event_id)
        except IntegrityError:
            current = await self.repository.get_by_id(event_id)
            return {"created": False, "interested_counter": current.interested_counter}

        return {"created": True, "interested_counter": event.interested_counter}

    async def update_basic_info(self, owner_user_id, event_id, **payload):
        event = await self.repository.get_by_id_for_owner(event_id, owner_user_id)
        if not event:
            raise EventNotFound

        for field, value in payload.items():
            setattr(event, field, value)

        await self.repository.session.flush()
        await self._refresh_setup_status(event)
        return event

    async def update_show_tickets(self, owner_user_id, event_id, **payload):
        event = await self.repository.get_by_id_for_owner(event_id, owner_user_id)
        if not event:
            raise EventNotFound
        for field, value in payload.items():
            setattr(event, field, value)
        await self.repository.session.flush()
        await self._refresh_setup_status(event)
        return event

    async def get_readiness(self, owner_user_id, event_id):
        event = await self.get_event_detail(owner_user_id, event_id)
        day_count = await self.repository.count_event_days(event.id)
        ticket_type_count = await self.repository.count_ticket_types(event.id)
        allocation_count = await self.repository.count_ticket_allocations(event.id)
        status = await self._build_setup_status(event, day_count, ticket_type_count, allocation_count)
        missing_sections = [name for name, done in status.items() if not done]
        blocking_issues = []
        if not status["basic_info"]:
            blocking_issues.append("Complete basic event information")
        if not status["schedule"]:
            blocking_issues.append("Add at least one event day")
        if not status["tickets"]:
            blocking_issues.append("Add ticket types and allocations or switch event to open")
        if not status["assets"]:
            blocking_issues.append("Upload a banner image")
        return {
            "completed_sections": [name for name, done in status.items() if done],
            "missing_sections": missing_sections,
            "blocking_issues": blocking_issues,
        }

    async def create_event_day(self, owner_user_id, event_id, date, start_time=None, end_time=None):
        event = await self.repository.get_by_id_for_owner(event_id, owner_user_id)
        if not event:
            raise EventNotFound
        existing_days = await self.repository.list_event_days(event_id)
        if any(d.date == date for d in existing_days):
            raise AlreadyExistsError("An event day with this date already exists.")
        day = await self.repository.create_event_day(
            event_id, date, start_time=start_time, end_time=end_time
        )
        await self._refresh_setup_status(event)
        return day

    async def list_event_days(self, owner_user_id, event_id):
        event = await self.repository.get_by_id_for_owner(event_id, owner_user_id)
        if not event:
            raise EventNotFound
        return await self.repository.list_event_days(event_id)

    async def update_event_day(self, owner_user_id, event_day_id, **payload):
        day = await self.repository.get_event_day_for_owner(event_day_id, owner_user_id)
        if not day:
            raise EventNotFound
        allowed_fields = {"start_time", "end_time"}
        safe_payload = {k: v for k, v in payload.items() if k in allowed_fields}
        for field, value in safe_payload.items():
            setattr(day, field, value)
        await self.repository.session.flush()
        return day

    async def delete_event_day(self, owner_user_id, event_day_id):
        day = await self.repository.get_event_day_for_owner(event_day_id, owner_user_id)
        if not day:
            raise EventNotFound
        event = await self.repository.get_by_id_for_owner(day.event_id, owner_user_id)
        await self.repository.delete_event_day(day)
        if event:
            await self._refresh_setup_status(event)

    async def start_scan(self, owner_user_id, event_day_id, notes: str | None = None):
        day = await self.repository.get_event_day_for_owner(event_day_id, owner_user_id)
        if not day:
            raise EventNotFound
        if day.scan_status == "ended":
            raise InvalidScanTransition
        previous_status = day.scan_status
        day.scan_status = "active"
        if day.scan_started_at is None:
            day.scan_started_at = datetime.utcnow()
        await self.repository.create_scan_status_history(
            event_day_id=event_day_id,
            changed_by_user_id=owner_user_id,
            previous_status=previous_status,
            new_status="active",
            notes=notes,
        )
        await self.repository.session.flush()
        return day

    async def pause_scan(self, owner_user_id, event_day_id, notes: str | None = None):
        day = await self.repository.get_event_day_for_owner(event_day_id, owner_user_id)
        if not day:
            raise EventNotFound
        if day.scan_status != "active":
            raise InvalidScanTransition
        previous_status = day.scan_status
        day.scan_status = "paused"
        day.scan_paused_at = datetime.utcnow()
        await self.repository.create_scan_status_history(
            event_day_id=event_day_id,
            changed_by_user_id=owner_user_id,
            previous_status=previous_status,
            new_status="paused",
            notes=notes,
        )
        await self.repository.session.flush()
        return day

    async def resume_scan(self, owner_user_id, event_day_id, notes: str | None = None):
        day = await self.repository.get_event_day_for_owner(event_day_id, owner_user_id)
        if not day:
            raise EventNotFound
        if day.scan_status != "paused":
            raise InvalidScanTransition
        previous_status = day.scan_status
        day.scan_status = "active"
        await self.repository.create_scan_status_history(
            event_day_id=event_day_id,
            changed_by_user_id=owner_user_id,
            previous_status=previous_status,
            new_status="active",
            notes=notes,
        )
        await self.repository.session.flush()
        return day

    async def end_scan(self, owner_user_id, event_day_id, notes: str | None = None):
        day = await self.repository.get_event_day_for_owner(event_day_id, owner_user_id)
        if not day:
            raise EventNotFound
        if day.scan_status == "ended":
            raise InvalidScanTransition
        previous_status = day.scan_status
        day.scan_status = "ended"
        day.scan_ended_at = datetime.utcnow()
        await self.repository.create_scan_status_history(
            event_day_id=event_day_id,
            changed_by_user_id=owner_user_id,
            previous_status=previous_status,
            new_status="ended",
            notes=notes,
        )
        await self.repository.session.flush()
        return day

    async def upload_media_asset(
        self,
        owner_user_id: UUID,
        event_id: UUID,
        asset_type: str,
        file_name: str,
        file_content: bytes,
        title: str | None = None,
        caption: str | None = None,
        alt_text: str | None = None,
    ) -> EventMediaAssetModel:
        """Upload media asset to S3 and store metadata."""
        event = await self.repository.get_by_id_for_owner(event_id, owner_user_id)
        if not event:
            raise EventNotFound

        # Validate file based on asset type
        if asset_type == "banner":
            FileValidator.validate_banner_image(file_name, file_content)
        elif asset_type == "gallery_image":
            FileValidator.validate_gallery_image(file_name, file_content)
        elif asset_type == "gallery_video":
            FileValidator.validate_gallery_video(file_name, file_content)
        else:
            raise InvalidAsset(f"Invalid asset_type: {asset_type}")

        # Upload to S3
        s3_client = get_s3_client()
        storage_key = s3_client.upload_file(event_id, asset_type, file_name, file_content)
        public_url = s3_client.generate_public_url(storage_key)

        # Store metadata
        asset = EventMediaAssetModel(
            event_id=event_id,
            asset_type=asset_type,
            storage_key=storage_key,
            public_url=public_url,
            title=title,
            caption=caption,
            alt_text=alt_text,
            sort_order=0,
            is_primary=False,
        )
        self.repository.add(asset)
        await self.repository.session.flush()
        await self.repository.session.refresh(asset)

        # Update readiness status if banner
        if asset_type == "banner":
            await self._refresh_setup_status(event)

        return asset

    async def list_media_assets(
        self, owner_user_id: UUID, event_id: UUID, asset_type: str | None = None
    ) -> list[EventMediaAssetModel]:
        """List media assets for an event."""
        event = await self.repository.get_by_id_for_owner(event_id, owner_user_id)
        if not event:
            raise EventNotFound

        return await self.repository.list_media_assets(event_id, asset_type)

    async def delete_media_asset(
        self, owner_user_id: UUID, event_id: UUID, asset_id: UUID
    ) -> None:
        """Delete media asset from S3 and database."""
        event = await self.repository.get_by_id_for_owner(event_id, owner_user_id)
        if not event:
            raise EventNotFound

        asset = await self.repository.get_media_asset_by_id(asset_id)
        if not asset or asset.event_id != event_id:
            raise InvalidAsset("Asset not found or does not belong to this event")

        # Delete from S3
        s3_client = get_s3_client()
        s3_client.delete_file(asset.storage_key)

        # Delete from database
        await self.repository.delete_media_asset(asset)

        # Update readiness if was banner
        if asset.asset_type == "banner":
            await self._refresh_setup_status(event)

    async def update_media_asset_metadata(
        self,
        owner_user_id: UUID,
        event_id: UUID,
        asset_id: UUID,
        title: str | None = None,
        caption: str | None = None,
        alt_text: str | None = None,
        sort_order: int | None = None,
        is_primary: bool | None = None,
    ) -> EventMediaAssetModel:
        """Update media asset metadata."""
        event = await self.repository.get_by_id_for_owner(event_id, owner_user_id)
        if not event:
            raise EventNotFound

        asset = await self.repository.get_media_asset_by_id(asset_id)
        if not asset or asset.event_id != event_id:
            raise InvalidAsset("Asset not found or does not belong to this event")

        if title is not None:
            asset.title = title
        if caption is not None:
            asset.caption = caption
        if alt_text is not None:
            asset.alt_text = alt_text
        if sort_order is not None:
            asset.sort_order = sort_order
        if is_primary is not None:
            asset.is_primary = is_primary

        await self.repository.session.flush()
        await self.repository.session.refresh(asset)
        return asset
