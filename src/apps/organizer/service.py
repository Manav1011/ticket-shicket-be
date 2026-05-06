import re
import secrets
import uuid
import hashlib
from uuid import UUID
from datetime import datetime, timedelta, timezone

from .exceptions import OrganizerNotFound, OrganizerSlugAlreadyExists
from .models import OrganizerPageModel
from src.utils.s3_client import get_s3_client
from src.utils.file_validation import FileValidator, FileValidationError
from apps.superadmin.service import SuperAdminService
from apps.superadmin.enums import B2BRequestStatus


from apps.ticketing.repository import TicketingRepository
from apps.payment_gateway.services.factory import get_gateway
from apps.payment_gateway.services.base import BuyerInfo
from apps.payment_gateway.repositories.order import OrderPaymentRepository
from apps.allocation.enums import AllocationStatus, TransferMode, GatewayType
from apps.allocation.repository import AllocationRepository
from apps.allocation.service import AllocationService
from apps.event.repository import EventRepository
from exceptions import ForbiddenError
from apps.user.repository import UserRepository
from apps.ticketing.enums import OrderType, OrderStatus
from apps.allocation.enums import AllocationType
from apps.allocation.models import OrderModel
from apps.organizer.response import B2BTransferResponse, CustomerTransferResponse
from exceptions import BadRequestError, NotFoundError


class OrganizerService:
    def __init__(self, repository) -> None:
        self.repository = repository
        self._super_admin_service = SuperAdminService(repository.session)
        self._ticketing_repo = TicketingRepository(repository.session)
        self._allocation_repo = AllocationRepository(repository.session)
        self._allocation_service = AllocationService(repository.session)

    async def list_organizers(self, owner_user_id):
        return await self.repository.list_by_owner(owner_user_id)

    async def list_organizer_events(self, owner_user_id, organizer_id, status=None):
        return await self.repository.list_events_for_owner(owner_user_id, organizer_id, status)

    async def list_my_events(
        self,
        user_id: UUID,
        status: str | None = None,
        event_access_type: str | None = None,
        date_from=None,
        date_to=None,
        search: str | None = None,
        sort_by: str = "created_at",
        order: str = "desc",
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[list, dict]:
        """
        List all events for user across all their organizer pages.
        Returns (events, pagination_meta).
        """
        from apps.event.repository import EventRepository

        event_repo = EventRepository(self.repository.session)

        events, total = await event_repo.list_events_for_user(
            owner_user_id=user_id,
            status=status,
            event_access_type=event_access_type,
            date_from=date_from,
            date_to=date_to,
            search=search,
            sort_by=sort_by,
            order=order,
            limit=limit,
            offset=offset,
        )

        pagination_meta = {
            "total": total,
            "limit": limit,
            "offset": offset,
            "has_more": offset + len(events) < total,
        }

        return events, pagination_meta

    async def create_organizer(
        self,
        owner_user_id,
        name,
        bio=None,
        logo_url=None,
        cover_image_url=None,
        website_url=None,
        instagram_url=None,
        facebook_url=None,
        youtube_url=None,
        visibility=None,
    ):
        normalized_slug = re.sub(r"[^a-z0-9]+", "-", name.strip().lower()).strip("-")
        if await self.repository.get_by_slug(normalized_slug):
            raise OrganizerSlugAlreadyExists

        organizer = OrganizerPageModel(
            owner_user_id=owner_user_id,
            name=name.strip(),
            slug=normalized_slug,
            bio=bio,
            logo_url=logo_url,
            cover_image_url=cover_image_url,
            website_url=website_url,
            instagram_url=instagram_url,
            facebook_url=facebook_url,
            youtube_url=youtube_url,
            visibility=visibility,
            status="active",
        )
        self.repository.add(organizer)
        await self.repository.session.flush()
        await self.repository.session.refresh(organizer)
        return organizer

    async def update_organizer(self, owner_user_id, organizer_id, **payload):
        organizer = await self.repository.get_by_id_for_owner(organizer_id, owner_user_id)
        if not organizer:
            raise OrganizerNotFound

        if "slug" in payload and payload["slug"] is not None:
            normalized_slug = re.sub(r"[^a-z0-9]+", "-", payload["slug"].strip().lower()).strip("-")
            existing = await self.repository.get_by_slug(normalized_slug)
            if existing and existing.id != organizer_id:
                raise OrganizerSlugAlreadyExists
            payload["slug"] = normalized_slug

        for field, value in payload.items():
            setattr(organizer, field, value)

        await self.repository.session.flush()
        await self.repository.session.refresh(organizer)
        return organizer

    async def upload_logo(
        self,
        owner_user_id: UUID,
        organizer_page_id: UUID,
        file_name: str,
        file_content: bytes,
    ) -> OrganizerPageModel:
        """
        Upload logo image for organizer page.

        Args:
            owner_user_id: Page owner
            organizer_page_id: Organizer page UUID
            file_name: Original filename
            file_content: File bytes

        Returns:
            Updated OrganizerPageModel with logo_url

        Raises:
            OrganizerNotFound: If organizer page doesn't exist or user doesn't own it
            FileValidationError: If file validation fails
        """
        # Verify ownership
        organizer = await self.repository.get_by_id_for_owner(
            organizer_page_id, owner_user_id
        )
        if not organizer:
            raise OrganizerNotFound

        # Validate logo image (required: max 5MB, jpg/png/webp, min 200x200)
        FileValidator.validate_banner_image(file_name, file_content)

        # Upload to S3: organizers/{organizer_id}/logo_{uuid}_{filename}
        s3_client = get_s3_client()
        storage_key = s3_client.upload_file(
            resource_id=organizer_page_id,
            asset_type="logo",
            file_name=file_name,
            file_content=file_content,
            path_prefix="organizers",
        )
        public_url = s3_client.generate_public_url(storage_key)

        # Update organizer page
        organizer.logo_url = public_url
        await self.repository.session.flush()
        await self.repository.session.refresh(organizer)
        return organizer

    async def upload_cover_image(
        self,
        owner_user_id: UUID,
        organizer_page_id: UUID,
        file_name: str,
        file_content: bytes,
    ) -> OrganizerPageModel:
        """
        Upload cover image for organizer page.

        Args:
            owner_user_id: Page owner
            organizer_page_id: Organizer page UUID
            file_name: Original filename
            file_content: File bytes

        Returns:
            Updated OrganizerPageModel with cover_image_url

        Raises:
            OrganizerNotFound: If organizer page doesn't exist or user doesn't own it
            FileValidationError: If file validation fails
        """
        # Verify ownership
        organizer = await self.repository.get_by_id_for_owner(
            organizer_page_id, owner_user_id
        )
        if not organizer:
            raise OrganizerNotFound

        # Validate cover image (reuse banner validation: max 5MB, jpg/png/webp, min 200x200)
        FileValidator.validate_banner_image(file_name, file_content)

        # Upload to S3: organizers/{organizer_id}/cover_{uuid}_{filename}
        s3_client = get_s3_client()
        storage_key = s3_client.upload_file(
            resource_id=organizer_page_id,
            asset_type="cover",
            file_name=file_name,
            file_content=file_content,
            path_prefix="organizers",
        )
        public_url = s3_client.generate_public_url(storage_key)

        # Update organizer page
        organizer.cover_image_url = public_url
        await self.repository.session.flush()
        await self.repository.session.refresh(organizer)
        return organizer

    # --- B2B Request Methods ---

    async def create_b2b_request(
        self,
        user_id: uuid.UUID,
        event_id: uuid.UUID,
        event_day_id: uuid.UUID,
        quantity: int,
    ):
        """[Organizer] Submit a B2B ticket request. System auto-derives B2B ticket type."""
        # Auto-derive B2B ticket type for this event day
        b2b_ticket_type = await self._ticketing_repo.get_or_create_b2b_ticket_type(
            event_day_id=event_day_id,
        )
        return await self.repository.create_b2b_request(
            requesting_user_id=user_id,
            event_id=event_id,
            event_day_id=event_day_id,
            ticket_type_id=b2b_ticket_type.id,
            quantity=quantity,
        )

    async def get_b2b_requests_for_event(
        self,
        event_id: uuid.UUID,
    ) -> list:
        """[Organizer] List B2B requests for a specific event."""
        return await self.repository.list_b2b_requests_by_event(event_id)

    async def confirm_b2b_payment(
        self,
        request_id: uuid.UUID,
        event_id: uuid.UUID,
        user_id: uuid.UUID,
    ):
        """
        [Organizer] Confirm payment for an approved paid B2B request.
        Verifies user owns the organizer page that owns this event, then triggers allocation.
        """
        # Verify the B2B request belongs to this event
        b2b_req = await self.repository.get_b2b_request_by_id(request_id)
        if not b2b_req or b2b_req.event_id != event_id:
            raise ForbiddenError("B2B request does not belong to this event")

        return await self._super_admin_service.process_paid_b2b_allocation(
            request_id=request_id,
        )

    # --- B2B My Tickets & Allocations ---

    async def get_my_b2b_tickets(
        self,
        event_id: uuid.UUID,
        user_id: uuid.UUID,
        event_day_id: uuid.UUID | None = None,
    ) -> dict:
        """
        [Organizer] Get B2B tickets owned by the organizer for an event.
        Groups tickets by event_day. Single query to get B2B type, then single query
        to get counts with GROUP BY.

        Args:
            event_id: Event UUID
            user_id: Organizer user UUID
            event_day_id: Optional -- if provided, filter to specific event day only
        """
        # 1. Verify event ownership
        event = await EventRepository(self.repository.session).get_by_id_for_owner(event_id, user_id)
        if not event:
            raise ForbiddenError("You do not own this event's organizer page")

        # 2. Get organizer's holder
        holder = await self._allocation_repo.get_holder_by_user_id(user_id)
        if not holder:
            return {
                "event_id": event_id,
                "holder_id": None,
                "tickets": [],
                "total": 0,
            }

        # 3. Get B2B ticket type for this event (read-only — no INSERT)
        b2b_type = await self._ticketing_repo.get_b2b_ticket_type_for_event(event_id)
        if not b2b_type:
            return {
                "event_id": event_id,
                "holder_id": holder.id,
                "tickets": [],
                "total": 0,
            }

        # 4. Single query with GROUP BY — get counts grouped by event_day
        rows = await self._allocation_repo.list_b2b_tickets_by_holder(
            event_id=event_id,
            holder_id=holder.id,
            b2b_ticket_type_id=b2b_type.id,
            event_day_id=event_day_id,
        )

        grand_total = sum(row["count"] for row in rows)

        return {
            "event_id": event_id,
            "holder_id": holder.id,
            "tickets": rows,
            "total": grand_total,
        }

    async def get_my_b2b_allocations(
        self,
        event_id: uuid.UUID,
        user_id: uuid.UUID,
        event_day_id: uuid.UUID | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[dict]:
        """
        [Organizer] Get B2B allocation history (received AND transferred)
        for tickets owned by the organizer. Single-query JOIN for ticket_ids.

        Args:
            event_id: Event UUID
            user_id: Organizer user UUID
            event_day_id: UUID | None -- if provided, filter to allocations from that event day
            limit: Pagination limit
            offset: Pagination offset
        """
        # 1. Verify event ownership
        event = await EventRepository(self.repository.session).get_by_id_for_owner(event_id, user_id)
        if not event:
            raise ForbiddenError("You do not own this event's organizer page")

        # 2. Get organizer's holder
        holder = await self._allocation_repo.get_holder_by_user_id(user_id)
        if not holder:
            return []

        # 3. Get allocations with single-query ticket_ids
        allocations = await self._allocation_repo.list_b2b_allocations_for_holder(
            event_id=event_id,
            holder_id=holder.id,
            event_day_id=event_day_id,
            limit=limit,
            offset=offset,
        )

        return allocations

    async def create_b2b_transfer(
        self,
        user_id: UUID,
        event_id: UUID,
        reseller_id: UUID,
        quantity: int,
        event_day_id: UUID | None = None,
        mode: TransferMode = TransferMode.FREE,
        price: float | None = None,
    ) -> B2BTransferResponse:
        """
        [Organizer] Transfer B2B tickets to a reseller (free mode).

        Flow:
        1. Validate reseller exists (user lookup)
        2. Validate reseller is associated with this event (EventResellerModel accepted record)
        3. Validate event ownership
        4. Get organizer's TicketHolder
        4.5. Validate event_day_id exists (if provided)
        5. Get reseller's TicketHolder (resolve/create)
        6. Check organizer's available ticket count ≥ quantity
        7. Atomically lock quantity tickets (FIFO)
        8. Create $0 TRANSFER order (completed)
        9. Create allocation (org → reseller, type=b2b)
        10. Upsert allocation_edges (org → reseller)
        11. Update ticket ownership to reseller, clear lock fields

        All in one DB transaction — rollback on any failure.
        """

        if user_id == reseller_id:
            from exceptions import BadRequestError
            raise BadRequestError("Cannot transfer tickets to yourself")

        # 1. Validate reseller exists
        user_repo = UserRepository(self.repository.session)
        reseller = await user_repo.find_by_id(reseller_id)
        if not reseller:
            from exceptions import NotFoundError
            raise NotFoundError("Reseller user not found")

        # 2. Validate reseller is associated with this event (invite accepted)
        event_repo = EventRepository(self.repository.session)
        reseller_record = await event_repo.get_reseller_for_event(reseller_id, event_id)
        if not reseller_record or reseller_record.accepted_at is None:
            from exceptions import ForbiddenError
            raise ForbiddenError("Reseller is not associated with this event")

        # 3. Validate event ownership
        event = await event_repo.get_by_id_for_owner(event_id, user_id)
        if not event:
            from exceptions import ForbiddenError
            raise ForbiddenError("You do not own this event's organizer page")

        # 4. Get organizer's holder
        org_holder = await self._allocation_repo.get_holder_by_user_id(user_id)
        if not org_holder:
            from exceptions import NotFoundError
            raise NotFoundError("Organizer has no ticket holder account")

        # 4.5 Validate event_day_id if provided
        if event_day_id:
            event_day = await event_repo.get_event_day_by_id(event_day_id)
            if not event_day or event_day.event_id != event_id:
                from exceptions import NotFoundError
                raise NotFoundError("Event day not found or does not belong to this event")

        # 5. Get reseller's holder (resolve/create)
        reseller_holder = await self._allocation_service.resolve_holder(
            user_id=reseller_id,
            create_if_missing=True,
        )

        # 6. Check organizer's available ticket count
        b2b_ticket_type = await self._ticketing_repo.get_b2b_ticket_type_for_event(event_id)
        if not b2b_ticket_type:
            from exceptions import NotFoundError
            raise NotFoundError("No B2B ticket type found for this event")

        ticket_rows = await self._allocation_repo.list_b2b_tickets_by_holder(
            event_id=event_id,
            holder_id=org_holder.id,
            b2b_ticket_type_id=b2b_ticket_type.id,
            event_day_id=event_day_id,
        )
        available = sum(r["count"] for r in ticket_rows)

        if available < quantity:
            from exceptions import BadRequestError
            raise BadRequestError(f"Only {available} B2B tickets available, requested {quantity}")

        if mode == TransferMode.PAID:
            total_price = price or 0.0
            # 1. Create pending order (no allocation created yet)
            order = OrderModel(
                event_id=event_id,
                user_id=user_id,
                type=OrderType.transfer,
                subtotal_amount=total_price,
                discount_amount=0.0,
                final_amount=total_price,
                status=OrderStatus.pending,
                gateway_type=GatewayType.RAZORPAY_PAYMENT_LINK,
                lock_expires_at=datetime.utcnow() + timedelta(minutes=30),
            )
            self.repository.session.add(order)
            await self.repository.session.flush()
            await self.repository.session.refresh(order)
            order.sender_holder_id = org_holder.id
            order.receiver_holder_id = reseller_holder.id
            order.transfer_type = "organizer_to_reseller"
            order.event_day_id = event_day_id

            # 2. Lock tickets (FIFO, 30-min TTL)
            locked_ticket_ids = await self._ticketing_repo.lock_tickets_for_transfer(
                owner_holder_id=org_holder.id,
                event_id=event_id,
                ticket_type_id=b2b_ticket_type.id,
                event_day_id=event_day_id,
                quantity=quantity,
                order_id=order.id,
                lock_ttl_minutes=30,
            )

            # 3. Create payment link via Razorpay
            # Determine reseller contact info for BuyerInfo
            reseller_name = getattr(reseller, 'name', None) or 'Reseller'
            reseller_email = getattr(reseller, 'email', None)
            reseller_phone = getattr(reseller, 'phone', None)

            gateway = get_gateway("razorpay")
            buyer_info = BuyerInfo(
                name=reseller_name,
                email=reseller_email,
                phone=reseller_phone or "",
            )
            payment_result = await gateway.create_payment_link(
                order_id=order.id,
                amount=int(total_price * 100),
                currency="INR",
                buyer=buyer_info,
                description=f"Ticket Transfer - {event.title}",
                event_id=event_id,
                flow_type="b2b_transfer",
                transfer_type="organizer_to_reseller",
                buyer_holder_id=reseller_holder.id,
            )

            # 4. Update order with gateway details
            order_payment_repo = OrderPaymentRepository(self.repository.session)
            await order_payment_repo.update_pending_order_on_payment_link_created(
                order_id=order.id,
                gateway_order_id=payment_result.gateway_order_id,
                gateway_response=payment_result.gateway_response,
                short_url=payment_result.short_url,
            )

            # 5. Send payment link via our notification channels
            from src.utils.notifications.sms import mock_send_sms
            from src.utils.notifications.whatsapp import mock_send_whatsapp
            from src.utils.notifications.email import mock_send_email

            payment_link = payment_result.short_url
            print(f"[PAID B2B TRANSFER] Payment link: {payment_link}")
            print(f"[PAID B2B TRANSFER] Sending to phone={reseller_phone}, email={reseller_email}")

            message = f"Complete your B2B ticket purchase: {payment_link}"
            if reseller_phone:
                mock_send_sms(reseller_phone, message, template="b2b_paid_transfer")
                mock_send_whatsapp(reseller_phone, message, template="b2b_paid_transfer")
            if reseller_email:
                mock_send_email(reseller_email, "Complete Your B2B Ticket Purchase", message)

            # NO allocation created here — webhook handles that on payment

            return B2BTransferResponse(
                transfer_id=order.id,
                status="pending_payment",
                ticket_count=len(locked_ticket_ids),
                reseller_id=reseller_id,
                mode=TransferMode.PAID,
                payment_url=payment_result.short_url,
            )

        # 7. Create the transfer order FIRST (to get its ID for locking)
        order = OrderModel(
            event_id=event_id,
            user_id=user_id,
            type=OrderType.transfer,
            subtotal_amount=0.0,
            discount_amount=0.0,
            final_amount=0.0,
            status=OrderStatus.paid,
        )
        self.repository.session.add(order)
        await self.repository.session.flush()
        await self.repository.session.refresh(order)

        # 8. Atomically lock tickets using order.id as lock_reference_id
        locked_ticket_ids = await self._ticketing_repo.lock_tickets_for_transfer(
            owner_holder_id=org_holder.id,
            event_id=event_id,
            ticket_type_id=b2b_ticket_type.id,
            event_day_id=event_day_id,
            quantity=quantity,
            order_id=order.id,
            lock_ttl_minutes=30,
        )

        # 9. Create allocation (org → reseller, type=b2b)
        allocation = await self._allocation_repo.create_allocation(
            event_id=event_id,
            from_holder_id=org_holder.id,
            to_holder_id=reseller_holder.id,
            order_id=order.id,
            allocation_type=AllocationType.b2b,
            ticket_count=len(locked_ticket_ids),
            metadata_={"source": "organizer_transfer", "mode": mode},
        )

        # 10. Add tickets to allocation
        await self._allocation_repo.add_tickets_to_allocation(
            allocation.id, locked_ticket_ids
        )

        # 11. Upsert edge (org → reseller)
        await self._allocation_repo.upsert_edge(
            event_id=event_id,
            from_holder_id=org_holder.id,
            to_holder_id=reseller_holder.id,
            ticket_count=len(locked_ticket_ids),
        )

        # 12. Update ticket ownership to reseller AND clear lock fields
        await self._ticketing_repo.update_ticket_ownership_batch(
            ticket_ids=locked_ticket_ids,
            new_owner_holder_id=reseller_holder.id,
        )

        # 13. Mark allocation as completed (free transfer is immediate)
        await self._allocation_repo.transition_allocation_status(
            allocation.id,
            AllocationStatus.pending,
            AllocationStatus.completed,
        )

        return B2BTransferResponse(
            transfer_id=order.id,
            status="completed",
            ticket_count=len(locked_ticket_ids),
            reseller_id=reseller_id,
            mode=TransferMode.FREE,
        )

    async def create_customer_transfer(
        self,
        user_id: UUID,
        event_id: UUID,
        phone: str | None,
        email: str | None,
        quantity: int,
        event_day_id: UUID,
        mode: TransferMode = TransferMode.FREE,
        price: float | None = None,
    ) -> CustomerTransferResponse:
        """
        [Organizer] Transfer B2B tickets to a customer (free mode).
        Customer receives a claim link; their ticket ownership is transferred immediately.

        Flow (free mode):
        1. Validate event ownership
        2. Validate event_day_id provided and belongs to event
        3. Resolve customer TicketHolder (phone+email match, or phone-only, or email-only)
        4. Get organizer's TicketHolder
        5. Check organizer's available ticket count ≥ quantity (scoped to event_day)
        6. Create $0 TRANSFER order (status=paid, immediate)
        7. Lock tickets (FIFO, 30-min TTL) for specific ticket_type + event_day
        8. Create Allocation + ClaimLink in one transaction (create_allocation_with_claim_link)
           - ClaimLink.event_day_id = the target event_day (claim is scoped per day)
        9. Add tickets to allocation (add_tickets_to_allocation)
        10. Upsert AllocationEdge (org → customer)
        11. Update ticket ownership to customer, clear lock fields
        12. Mark allocation as completed (free transfer is immediate)
        13. Send notifications (mock SMS/WhatsApp/Email)

        Flow (paid mode):
        1. Create PENDING order (status=pending, 30-min TTL)
        2. Lock tickets (FIFO, 30-min TTL)
        3. Create Razorpay payment link (transfer_type=organizer_to_customer)
        4. Send notification with payment link
        5. Return CustomerTransferResponse with payment_url (Allocation deferred to webhook)

        Returns:
            CustomerTransferResponse with transfer_id, status, ticket_count, mode, claim_link
        """
        from src.utils.claim_link_utils import generate_claim_link_token
        from src.utils.notifications.sms import mock_send_sms
        from src.utils.notifications.whatsapp import mock_send_whatsapp
        from src.utils.notifications.email import mock_send_email

        if not phone and not email:
            raise BadRequestError("Either phone or email must be provided")

        # 1. Validate event ownership
        from apps.event.repository import EventRepository
        event_repo = EventRepository(self.repository.session)
        event = await event_repo.get_by_id_for_owner(event_id, user_id)
        if not event:
            raise ForbiddenError("You do not own this event's organizer page")

        if mode == TransferMode.PAID:
            # Build buyer info from customer contact (customer may not have a user account)
            customer_name = phone or "Customer"
            customer_email = email
            customer_phone = phone or ""

            # Get organizer's holder first (needed for availability check)
            org_holder = await self._allocation_repo.get_holder_by_user_id(user_id)
            if not org_holder:
                raise NotFoundError("Organizer has no ticket holder account")

            # Check organizer's available ticket count ≥ quantity
            b2b_ticket_type = await self._ticketing_repo.get_b2b_ticket_type_for_event(event_id)
            if not b2b_ticket_type:
                raise NotFoundError("No B2B ticket type found for this event")

            ticket_rows = await self._allocation_repo.list_b2b_tickets_by_holder(
                event_id=event_id,
                holder_id=org_holder.id,
                b2b_ticket_type_id=b2b_ticket_type.id,
                event_day_id=event_day_id,
            )
            available = sum(r["count"] for r in ticket_rows)
            if available < quantity:
                raise BadRequestError(f"Only {available} B2B tickets available, requested {quantity}")

            # Resolve customer TicketHolder (needed for order.receiver_holder_id)
            if phone and email:
                existing = await self._allocation_repo.get_holder_by_phone_and_email(phone, email)
                if existing:
                    customer_holder = existing
                else:
                    by_phone = await self._allocation_repo.get_holder_by_phone(phone)
                    if by_phone:
                        customer_holder = by_phone
                    else:
                        by_email = await self._allocation_repo.get_holder_by_email(email)
                        if by_email:
                            customer_holder = by_email
                        else:
                            customer_holder = await self._allocation_repo.create_holder(
                                phone=phone, email=email
                            )
            elif phone:
                customer_holder = await self._allocation_repo.get_holder_by_phone(phone)
                if not customer_holder:
                    customer_holder = await self._allocation_repo.create_holder(phone=phone)
            else:
                customer_holder = await self._allocation_repo.get_holder_by_email(email)
                if not customer_holder:
                    customer_holder = await self._allocation_repo.create_holder(email=email)

            total_price = price or 0.0

            # Create pending order with all fields for webhook handler
            order = OrderModel(
                event_id=event_id,
                user_id=user_id,
                type=OrderType.transfer,
                subtotal_amount=total_price,
                discount_amount=0.0,
                final_amount=total_price,
                status=OrderStatus.pending,
                gateway_type=GatewayType.RAZORPAY_PAYMENT_LINK,
                lock_expires_at=datetime.utcnow() + timedelta(minutes=30),
                sender_holder_id=org_holder.id,
                receiver_holder_id=customer_holder.id,
                transfer_type="organizer_to_customer",
                event_day_id=event_day_id,
            )
            self.repository.session.add(order)
            await self.repository.session.flush()
            await self.repository.session.refresh(order)

            locked_ticket_ids = await self._ticketing_repo.lock_tickets_for_transfer(
                owner_holder_id=org_holder.id,
                event_id=event_id,
                ticket_type_id=b2b_ticket_type.id,
                event_day_id=event_day_id,
                quantity=quantity,
                order_id=order.id,
                lock_ttl_minutes=30,
            )

            # 3. Create payment link via Razorpay
            gateway = get_gateway("razorpay")
            buyer_info = BuyerInfo(
                name=customer_name,
                email=customer_email,
                phone=customer_phone,
            )
            payment_result = await gateway.create_payment_link(
                order_id=order.id,
                amount=int(total_price * 100),
                currency="INR",
                buyer=buyer_info,
                description=f"Ticket Transfer - {event.title}",
                event_id=event_id,
                flow_type="b2b_transfer",
                transfer_type="organizer_to_customer",
                buyer_holder_id=customer_holder.id,
            )

            # 4. Update order with gateway details
            order_payment_repo = OrderPaymentRepository(self.repository.session)
            await order_payment_repo.update_pending_order_on_payment_link_created(
                order_id=order.id,
                gateway_order_id=payment_result.gateway_order_id,
                gateway_response=payment_result.gateway_response,
                short_url=payment_result.short_url,
            )

            # 5. Send payment link via our notification channels
            from src.utils.notifications.sms import mock_send_sms
            from src.utils.notifications.whatsapp import mock_send_whatsapp
            from src.utils.notifications.email import mock_send_email

            payment_link = payment_result.short_url
            print(f"[PAID CUSTOMER TRANSFER] Payment link: {payment_link}")
            print(f"[PAID CUSTOMER TRANSFER] Sending to phone={customer_phone}, email={customer_email}")

            message = f"Complete your ticket purchase: {payment_link}"
            if customer_phone:
                mock_send_sms(customer_phone, message, template="customer_paid_transfer")
                mock_send_whatsapp(customer_phone, message, template="customer_paid_transfer")
            if customer_email:
                mock_send_email(customer_email, "Complete Your Ticket Purchase", message)

            # NO allocation created here — webhook handles that on payment

            return CustomerTransferResponse(
                transfer_id=order.id,
                status="pending_payment",
                ticket_count=len(locked_ticket_ids),
                mode=TransferMode.PAID,
                payment_url=payment_result.short_url,
            )

        # 2. Validate event_day_id exists and belongs to event
        event_day = await event_repo.get_event_day_by_id(event_day_id)
        if not event_day or event_day.event_id != event_id:
            raise NotFoundError("Event day not found or does not belong to this event")

        # 3. Resolve customer TicketHolder
        # Priority order when both phone+email provided:
        #   1. Try AND lookup
        #   2. Try phone-only lookup
        #   3. Try email-only lookup
        #   4. Create new if nothing found
        if phone and email:
            existing = await self._allocation_repo.get_holder_by_phone_and_email(phone, email)
            if existing:
                customer_holder = existing
            else:
                by_phone = await self._allocation_repo.get_holder_by_phone(phone)
                if by_phone:
                    customer_holder = by_phone
                else:
                    by_email = await self._allocation_repo.get_holder_by_email(email)
                    if by_email:
                        customer_holder = by_email
                    else:
                        customer_holder = await self._allocation_repo.create_holder(
                            phone=phone, email=email
                        )
        elif phone:
            customer_holder = await self._allocation_repo.get_holder_by_phone(phone)
            if not customer_holder:
                customer_holder = await self._allocation_repo.create_holder(phone=phone)
        else:
            customer_holder = await self._allocation_repo.get_holder_by_email(email)
            if not customer_holder:
                customer_holder = await self._allocation_repo.create_holder(email=email)        
        # 4. Get organizer's holder
        org_holder = await self._allocation_repo.get_holder_by_user_id(user_id)
        if not org_holder:
            raise NotFoundError("Organizer has no ticket holder account")

        # 5. Check organizer's available ticket count ≥ quantity
        b2b_ticket_type = await self._ticketing_repo.get_b2b_ticket_type_for_event(event_id)
        if not b2b_ticket_type:
            raise NotFoundError("No B2B ticket type found for this event")

        ticket_rows = await self._allocation_repo.list_b2b_tickets_by_holder(
            event_id=event_id,
            holder_id=org_holder.id,
            b2b_ticket_type_id=b2b_ticket_type.id,
            event_day_id=event_day_id,
        )
        available = sum(r["count"] for r in ticket_rows)
        if available < quantity:
            raise BadRequestError(f"Only {available} B2B tickets available, requested {quantity}")

        # 6. Create $0 TRANSFER order (status=paid — immediate completion)
        order = OrderModel(
            event_id=event_id,
            user_id=user_id,
            type=OrderType.transfer,
            subtotal_amount=0.0,
            discount_amount=0.0,
            final_amount=0.0,
            status=OrderStatus.paid,
        )
        self.repository.session.add(order)
        await self.repository.session.flush()
        await self.repository.session.refresh(order)

        # 7. Lock tickets using order.id as lock_reference_id
        locked_ticket_ids = await self._ticketing_repo.lock_tickets_for_transfer(
            owner_holder_id=org_holder.id,
            event_id=event_id,
            ticket_type_id=b2b_ticket_type.id,
            event_day_id=event_day_id,
            quantity=quantity,
            order_id=order.id,
            lock_ttl_minutes=30,
        )

        # 8. Create allocation + claim link in one transaction
        raw_token = generate_claim_link_token(length=8)
        token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
        allocation, claim_link = await self._allocation_repo.create_allocation_with_claim_link(
            event_id=event_id,
            event_day_id=event_day_id,
            from_holder_id=org_holder.id,
            to_holder_id=customer_holder.id,
            order_id=order.id,
            allocation_type=AllocationType.transfer,
            ticket_count=len(locked_ticket_ids),
            token_hash=token_hash,
            created_by_holder_id=org_holder.id,
            jwt_jti=secrets.token_hex(8),
            metadata_={"source": "organizer_customer_free", "mode": mode},
        )

        # 9. Add tickets to allocation
        await self._allocation_repo.add_tickets_to_allocation(allocation.id, locked_ticket_ids)

        # 10. Upsert allocation edge (org → customer)
        await self._allocation_repo.upsert_edge(
            event_id=event_id,
            from_holder_id=org_holder.id,
            to_holder_id=customer_holder.id,
            ticket_count=len(locked_ticket_ids),
        )

        # 11. Update ticket ownership to customer, clear lock fields
        await self._ticketing_repo.update_ticket_ownership_batch(
            ticket_ids=locked_ticket_ids,
            new_owner_holder_id=customer_holder.id,
            claim_link_id=claim_link.id,
        )

        # 12. Mark allocation as completed (free transfer is immediate)
        await self._allocation_repo.transition_allocation_status(
            allocation.id,
            AllocationStatus.pending,
            AllocationStatus.completed,
        )

        # 13. Send notifications (mock — real integration replaces these later)
        claim_url = f"/claim/{raw_token}"
        message = f"You received {len(locked_ticket_ids)} ticket(s). Claim at: {claim_url}"

        print(f"\n[CUSTOMER TRANSFER] Claim URL: http://0.0.0.0:8080/api/open{claim_url}\n")

        mock_send_sms(phone or "", message, template="customer_transfer")
        mock_send_whatsapp(phone or "", message, template="customer_transfer")
        if email:
            mock_send_email(email, "You received tickets!", message)

        return CustomerTransferResponse(
            transfer_id=order.id,
            status="completed",
            ticket_count=len(locked_ticket_ids),
            mode=TransferMode.FREE,
        )
