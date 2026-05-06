from uuid import UUID
import hashlib
import secrets
import uuid as uuid_lib
from datetime import datetime, timedelta, timezone

from apps.resellers.repository import ResellerRepository
from apps.resellers.response import (
    ResellerEventsResponse,
    ResellerEventItem,
    ResellerTicketItem,
    ResellerTicketsResponse,
    ResellerAllocationItem,
    ResellerAllocationsResponse,
)
from apps.allocation.enums import AllocationType, AllocationStatus, TransferMode
from apps.allocation.models import OrderModel
from apps.allocation.repository import AllocationRepository
from apps.ticketing.enums import OrderType, OrderStatus
from apps.ticketing.repository import TicketingRepository
from apps.organizer.response import CustomerTransferResponse
from apps.payment_gateway.services.factory import get_gateway
from apps.payment_gateway.services.base import BuyerInfo
from apps.payment_gateway.repositories.order import OrderPaymentRepository
from apps.allocation.enums import GatewayType
from exceptions import ForbiddenError, NotFoundError, BadRequestError


class ResellerService:
    def __init__(self, session):
        self._repo = ResellerRepository(session)
        self._allocation_repo = AllocationRepository(session)
        self._ticketing_repo = TicketingRepository(session)

    async def list_my_events(self, user_id: UUID) -> ResellerEventsResponse:
        """List events where user is an accepted reseller."""
        rows = await self._repo.list_my_events(user_id)
        events = []
        for row in rows:
            events.append(ResellerEventItem(
                event_id=row["event_id"],
                event_name=row["event_name"],
                organizer_name=row.get("organizer_name", "Unknown"),
                event_status=row["event_status"],
                my_role="reseller",
                accepted_at=row.get("accepted_at"),
            ))
        return ResellerEventsResponse(events=events, total=len(events))

    async def get_my_tickets(
        self,
        event_id: UUID,
        user_id: UUID,
        event_day_id: UUID | None = None,
    ) -> ResellerTicketsResponse:
        """Get my tickets for an event I resell."""
        # Check reseller association
        is_reseller = await self._repo.is_accepted_reseller(user_id, event_id)
        if not is_reseller:
            raise ForbiddenError("You are not a reseller for this event")

        # Get holder
        holder = await self._repo.get_my_holder_for_event(user_id)
        if not holder:
            return ResellerTicketsResponse(
                event_id=event_id,
                holder_id=None,
                tickets=[],
                total=0,
            )

        # Get B2B ticket type
        b2b_type = await self._repo.get_b2b_ticket_type_for_event(event_id)
        if not b2b_type:
            return ResellerTicketsResponse(
                event_id=event_id,
                holder_id=holder.id,
                tickets=[],
                total=0,
            )

        # Get ticket counts
        rows = await self._repo.list_b2b_tickets_by_holder(
            event_id=event_id,
            holder_id=holder.id,
            b2b_ticket_type_id=b2b_type.id,
            event_day_id=event_day_id,
        )

        tickets = [ResellerTicketItem(event_day_id=r["event_day_id"], count=r["count"]) for r in rows]
        total = sum(r["count"] for r in rows)

        return ResellerTicketsResponse(
            event_id=event_id,
            holder_id=holder.id,
            tickets=tickets,
            total=total,
        )

    async def get_my_allocations(
        self,
        event_id: UUID,
        user_id: UUID,
        limit: int = 50,
        offset: int = 0,
    ) -> ResellerAllocationsResponse:
        """Get my allocations for an event I resell."""
        # Check reseller association
        is_reseller = await self._repo.is_accepted_reseller(user_id, event_id)
        if not is_reseller:
            raise ForbiddenError("You are not a reseller for this event")

        # Get holder
        holder = await self._repo.get_my_holder_for_event(user_id)
        if not holder:
            return ResellerAllocationsResponse(
                event_id=event_id,
                allocations=[],
                total=0,
            )

        # Get allocations
        rows = await self._repo.list_b2b_allocations_for_holder(
            event_id=event_id,
            holder_id=holder.id,
            limit=limit,
            offset=offset,
        )

        allocations = [
            ResellerAllocationItem(
                allocation_id=r["allocation_id"],
                event_day_id=r["event_day_id"],
                direction=r["direction"],
                from_holder_id=r["from_holder_id"],
                to_holder_id=r["to_holder_id"],
                ticket_count=r["ticket_count"],
                status=r["status"],
                source=r["source"],
                created_at=r["created_at"],
            )
            for r in rows
        ]

        return ResellerAllocationsResponse(
            event_id=event_id,
            allocations=allocations,
            total=len(allocations),
        )

    async def create_reseller_customer_transfer(
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
        [Reseller] Transfer B2B tickets to a customer (free mode).
        Customer receives a claim link; their ticket ownership is transferred immediately.

        Flow (free mode):
        1. Validate reseller is associated with this event
        2. Validate event_day_id exists and belongs to event
        3. Resolve customer TicketHolder (phone+email match, or phone-only, or email-only)
        4. Get reseller's TicketHolder
        5. Check reseller's available ticket count ≥ quantity (scoped to event_day)
        6. Create $0 TRANSFER order (status=paid, immediate)
        7. Lock tickets (FIFO, 30-min TTL) for specific ticket_type + event_day
        8. Create Allocation + ClaimLink in one transaction
        9. Add tickets to allocation
        10. Upsert AllocationEdge (reseller → customer)
        11. Update ticket ownership to customer, clear lock fields
        12. Mark allocation as completed (free transfer is immediate)
        13. Send notifications (mock SMS/WhatsApp/Email)

        Flow (paid mode):
        1. Create PENDING order (status=pending, 30-min TTL)
        2. Lock tickets (FIFO, 30-min TTL)
        3. Create Razorpay payment link (transfer_type=reseller_to_customer)
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

        # 1. Validate reseller is associated with this event
        is_reseller = await self._repo.is_accepted_reseller(user_id, event_id)
        if not is_reseller:
            raise ForbiddenError("You are not a reseller for this event")

        # 2. Validate event_day_id exists and belongs to event
        from apps.event.repository import EventRepository
        event_repo = EventRepository(self._repo._session)
        event_day = await event_repo.get_event_day_by_id(event_day_id)
        if not event_day or event_day.event_id != event_id:
            raise NotFoundError("Event day not found or does not belong to this event")

        # Fetch event for description
        event = await event_repo.get_by_id(event_id)
        if not event:
            raise NotFoundError("Event not found")

        if mode == TransferMode.PAID:
            # Build buyer info from customer contact (customer may not have a user account)
            customer_name = phone or "Customer"
            customer_email = email
            customer_phone = phone or ""

            # Resolve customer TicketHolder first (needed for order.receiver_holder_id)
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

            # Get reseller's holder
            reseller_holder = await self._repo.get_my_holder_for_event(user_id)
            if not reseller_holder:
                raise NotFoundError("Reseller has no ticket holder account")

            # Check reseller's available ticket count ≥ quantity
            b2b_ticket_type = await self._ticketing_repo.get_b2b_ticket_type_for_event(event_id)
            if not b2b_ticket_type:
                raise NotFoundError("No B2B ticket type found for this event")

            ticket_rows = await self._allocation_repo.list_b2b_tickets_by_holder(
                event_id=event_id,
                holder_id=reseller_holder.id,
                b2b_ticket_type_id=b2b_ticket_type.id,
                event_day_id=event_day_id,
            )
            available = sum(r["count"] for r in ticket_rows)
            if available < quantity:
                raise BadRequestError(f"Only {available} B2B tickets available, requested {quantity}")

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
                sender_holder_id=reseller_holder.id,
                receiver_holder_id=customer_holder.id,
                transfer_type="reseller_to_customer",
                event_day_id=event_day_id,
            )
            self._repo._session.add(order)
            await self._repo._session.flush()
            await self._repo._session.refresh(order)

            # 2. Lock tickets (FIFO, 30-min TTL)
            locked_ticket_ids = await self._ticketing_repo.lock_tickets_for_transfer(
                owner_holder_id=reseller_holder.id,
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
                transfer_type="reseller_to_customer",
                buyer_holder_id=customer_holder.id,
            )

            # 4. Update order with gateway details
            order_payment_repo = OrderPaymentRepository(self._repo._session)
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
            print(f"[PAID RESELLER→CUSTOMER TRANSFER] Payment link: {payment_link}")
            print(f"[PAID RESELLER→CUSTOMER TRANSFER] Sending to phone={customer_phone}, email={customer_email}")

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

        # 4. Get reseller's holder
        reseller_holder = await self._repo.get_my_holder_for_event(user_id)
        if not reseller_holder:
            raise NotFoundError("Reseller has no ticket holder account")

        # 5. Check reseller's available ticket count ≥ quantity
        b2b_ticket_type = await self._ticketing_repo.get_b2b_ticket_type_for_event(event_id)
        if not b2b_ticket_type:
            raise NotFoundError("No B2B ticket type found for this event")

        ticket_rows = await self._allocation_repo.list_b2b_tickets_by_holder(
            event_id=event_id,
            holder_id=reseller_holder.id,
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
        self._repo._session.add(order)
        await self._repo._session.flush()
        await self._repo._session.refresh(order)

        # 7. Lock tickets using order.id as lock_reference_id
        locked_ticket_ids = await self._ticketing_repo.lock_tickets_for_transfer(
            owner_holder_id=reseller_holder.id,
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
            from_holder_id=reseller_holder.id,
            to_holder_id=customer_holder.id,
            order_id=order.id,
            allocation_type=AllocationType.transfer,
            ticket_count=len(locked_ticket_ids),
            token_hash=token_hash,
            created_by_holder_id=reseller_holder.id,
            jwt_jti=secrets.token_hex(8),
            metadata_={"source": "reseller_customer_free", "mode": mode},
        )

        # 9. Add tickets to allocation
        await self._allocation_repo.add_tickets_to_allocation(allocation.id, locked_ticket_ids)

        # 10. Upsert allocation edge (reseller → customer)
        await self._allocation_repo.upsert_edge(
            event_id=event_id,
            from_holder_id=reseller_holder.id,
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

        print(f"\n[RESELLER TO CUSTOMER FREE TRANSFER] Claim URL: http://0.0.0.0:8080/api/open{claim_url}\n")

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
