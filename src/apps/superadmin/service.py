"""
Super admin service — handles B2B request lifecycle.
All B2B operations are wrapped in a single database transaction.
"""
import logging
import uuid

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from apps.allocation.enums import AllocationStatus, AllocationType, GatewayType
from apps.allocation.models import AllocationModel, OrderModel, TicketHolderModel
from apps.allocation.repository import AllocationRepository
from apps.allocation.service import AllocationService
from apps.event.repository import EventRepository
from apps.ticketing.enums import OrderStatus, OrderType
from apps.ticketing.models import TicketModel
from apps.ticketing.repository import TicketingRepository
from apps.user.repository import UserRepository
from apps.payment_gateway.repositories.order import OrderPaymentRepository
from apps.payment_gateway.services.base import BuyerInfo
from apps.payment_gateway.services.factory import get_gateway
from utils.notifications.sms import mock_send_sms
from utils.notifications.whatsapp import mock_send_whatsapp
from utils.notifications.email import mock_send_email
from datetime import datetime, timedelta

from .enums import B2BRequestStatus
from .exceptions import (
    B2BRequestNotFoundError,
    B2BRequestNotPendingError,
    InsufficientTicketsError,
    SuperAdminError,
)
from .models import B2BRequestModel, SuperAdminModel
from .repository import SuperAdminRepository

logger = logging.getLogger(__name__)


class SuperAdminService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = SuperAdminRepository(session)
        self._allocation_repo = AllocationRepository(session)
        self._ticketing_repo = TicketingRepository(session)
        self._event_repo = EventRepository(session)

    @property
    def repo(self) -> SuperAdminRepository:
        return self._repo

    async def get_b2b_request(self, request_id: uuid.UUID) -> B2BRequestModel:
        request = await self._repo.get_b2b_request_by_id(request_id)
        if not request:
            raise B2BRequestNotFoundError(f"B2B request {request_id} not found")
        return request

    async def get_b2b_request_detail(self, request_id: uuid.UUID) -> dict:
        """Get B2B request with enriched event/user/ticket type info."""
        enriched = await self._repo.get_b2b_request_enriched(request_id)
        if not enriched:
            raise B2BRequestNotFoundError(f"B2B request {request_id} not found")
        return enriched

    async def list_pending_b2b_requests(
        self, limit: int = 50, offset: int = 0
    ) -> list[B2BRequestModel]:
        return await self._repo.list_b2b_requests(
            status=B2BRequestStatus.pending, limit=limit, offset=offset
        )

    async def list_all_b2b_requests(
        self,
        status: B2BRequestStatus | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[B2BRequestModel]:
        return await self._repo.list_b2b_requests(status=status, limit=limit, offset=offset)

    async def approve_b2b_request_free(
        self,
        admin_id: uuid.UUID,
        request_id: uuid.UUID,
        admin_notes: str | None = None,
    ) -> B2BRequestModel:
        """
        Approve a B2B request with free transfer (no payment).
        Creates allocation directly with a $0 TRANSFER order.
        """
        b2b_request = await self.get_b2b_request(request_id)
        if b2b_request.status != B2BRequestStatus.pending:
            raise B2BRequestNotPendingError(
                f"B2B request is {b2b_request.status}, expected pending"
            )

        # Resolve recipient holder
        allocation_service = AllocationService(self._session)
        to_holder = await allocation_service.resolve_holder(
            user_id=b2b_request.requesting_user_id,
            create_if_missing=True,
        )

        # Create $0 TRANSFER order (free = immediately paid)
        order = OrderModel(
            event_id=b2b_request.event_id,
            user_id=b2b_request.requesting_user_id,
            type=OrderType.transfer,
            subtotal_amount=0.0,
            discount_amount=0.0,
            final_amount=0.0,
            status=OrderStatus.paid,
        )
        self._session.add(order)
        await self._session.flush()

        # Get or create B2B ticket type for this event day
        b2b_ticket_type = await self._ticketing_repo.get_or_create_b2b_ticket_type(
            event_day_id=b2b_request.event_day_id,
        )

        # Atomically get next_ticket_index and increment in one DB operation
        start_index = await self._event_repo.increment_next_ticket_index(
            b2b_request.event_day_id, b2b_request.quantity
        )

        # Create tickets on-the-fly (B2B tickets don't exist in pool)
        tickets = await self._ticketing_repo.bulk_create_tickets(
            event_id=b2b_request.event_id,
            event_day_id=b2b_request.event_day_id,
            ticket_type_id=b2b_ticket_type.id,
            start_index=start_index,
            quantity=b2b_request.quantity,
        )
        ticket_ids = [t.id for t in tickets]

        # Create allocation (from_holder_id=NULL means pool)
        allocation = await self._allocation_repo.create_allocation(
            event_id=b2b_request.event_id,
            from_holder_id=None,
            to_holder_id=to_holder.id,
            order_id=order.id,
            allocation_type=AllocationType.b2b,
            ticket_count=len(ticket_ids),
            metadata_={
                "b2b_request_id": str(b2b_request.id),
                "approved_by_admin_id": str(admin_id),
                "source": "b2b_free",
            },
        )

        # Add tickets to allocation
        await self._allocation_repo.add_tickets_to_allocation(allocation.id, ticket_ids)

        # Update ticket ownership
        await self._update_ticket_ownership(ticket_ids, to_holder.id)

        # Upsert edge (pool → holder)
        await self._allocation_repo.upsert_edge(
            event_id=b2b_request.event_id,
            from_holder_id=None,
            to_holder_id=to_holder.id,
            ticket_count=len(ticket_ids),
        )

        # Mark allocation completed
        await self._allocation_repo.transition_allocation_status(
            allocation.id,
            AllocationStatus.pending,
            AllocationStatus.completed,
        )

        # Update B2B request
        updated = await self._repo.update_b2b_request_status(
            request_id=b2b_request.id,
            new_status=B2BRequestStatus.approved_free,
            admin_id=admin_id,
            admin_notes=admin_notes,
            allocation_id=allocation.id,
            order_id=order.id,
        )
        if not updated:
            raise SuperAdminError(f"Failed to update B2B request {b2b_request.id} status")

        await self._session.refresh(b2b_request)
        return b2b_request

    async def   approve_b2b_request_paid(
        self,
        admin_id: uuid.UUID,
        request_id: uuid.UUID,
        amount: float,
        admin_notes: str | None = None,
    ) -> B2BRequestModel:
        """
        Approve a B2B request as paid.
        Creates a pending PURCHASE order + Razorpay payment link, sends link to organizer.
        Allocation is created when webhook fires after payment.
        """
        b2b_request = await self.get_b2b_request(request_id)
        if b2b_request.status != B2BRequestStatus.pending:
            raise B2BRequestNotPendingError(
                f"B2B request is {b2b_request.status}, expected pending"
            )

        # Resolve organizer user to get contact info for payment link
        user_repo = UserRepository(self._session)
        user = await user_repo.get_by_id(b2b_request.requesting_user_id)
        if not user:
            raise SuperAdminError(f"User {b2b_request.requesting_user_id} not found")

        organizer_name = f"{user.first_name} {user.last_name}" if user.first_name else user.email.split("@")[0]
        organizer_email = user.email or ""
        organizer_phone = user.phone or ""

        # Create pending PURCHASE order
        order = OrderModel(
            event_id=b2b_request.event_id,
            user_id=b2b_request.requesting_user_id,
            type=OrderType.purchase,
            subtotal_amount=amount,
            discount_amount=0.0,
            final_amount=amount,
            status=OrderStatus.pending,
            gateway_type=GatewayType.RAZORPAY_PAYMENT_LINK,
            gateway_flow_type="b2b_request",
            event_day_id=b2b_request.event_day_id,
            lock_expires_at=datetime.utcnow() + timedelta(minutes=30),
        )
        self._session.add(order)
        await self._session.flush()

        # Create Razorpay payment link
        gateway = get_gateway("razorpay")
        buyer_info = BuyerInfo(
            name=organizer_name,
            email=organizer_email,
            phone=organizer_phone,
        )
        description = f"B2B Ticket Request — {b2b_request.quantity} tickets"
        payment_result = await gateway.create_payment_link(
            order_id=order.id,
            amount=int(amount * 100),  # Razorpay uses paise
            currency="INR",
            buyer=buyer_info,
            description=description,
            event_id=b2b_request.event_id,
            flow_type="b2b_request",
            transfer_type=None,
            buyer_holder_id=None,
        )

        # Update order with gateway details
        order_payment_repo = OrderPaymentRepository(self._session)
        await order_payment_repo.update_pending_order_on_payment_link_created(
            order_id=order.id,
            gateway_order_id=payment_result.gateway_order_id,
            gateway_response=payment_result.gateway_response,
            short_url=payment_result.short_url,
            gateway_flow_type="b2b_request",
        )

        # Update B2B request — no allocation_id yet (comes after payment)
        updated = await self._repo.update_b2b_request_status(
            request_id=b2b_request.id,
            new_status=B2BRequestStatus.approved_paid,
            admin_id=admin_id,
            admin_notes=admin_notes,
            order_id=order.id,
        )
        if not updated:
            raise SuperAdminError(f"Failed to update B2B request {b2b_request.id} status")

        # Send payment link via notification channels
        payment_link = payment_result.short_url
        message = f"Complete your B2B ticket purchase: {payment_link}"
        print(f"Mock sending payment link to organizer {organizer_name} ({organizer_email}, {organizer_phone}): {message}")
        mock_send_sms(organizer_phone, message, template="b2b_paid_request")
        mock_send_whatsapp(organizer_phone, message, template="b2b_paid_request")
        mock_send_email(organizer_email, "Complete Your B2B Ticket Purchase", message)

        await self._session.refresh(b2b_request)
        return b2b_request

    async def reject_b2b_request(
        self,
        admin_id: uuid.UUID,
        request_id: uuid.UUID,
        reason: str | None = None,
    ) -> B2BRequestModel:
        """Reject a B2B request."""
        b2b_request = await self.get_b2b_request(request_id)
        if b2b_request.status != B2BRequestStatus.pending:
            raise B2BRequestNotPendingError(
                f"B2B request is {b2b_request.status}, expected pending"
            )

        updated = await self._repo.update_b2b_request_status(
            request_id=b2b_request.id,
            new_status=B2BRequestStatus.rejected,
            admin_id=admin_id,
            admin_notes=reason,
        )
        if not updated:
            raise SuperAdminError(f"Failed to update B2B request {b2b_request.id} status")

        await self._session.refresh(b2b_request)
        return b2b_request

    async def process_paid_b2b_allocation(
        self,
        request_id: uuid.UUID,
    ) -> B2BRequestModel:
        """
        Called after payment succeeds. Creates the actual allocation using the existing paid order.
        This method is called from the organizer's confirm-payment endpoint.
        admin_id is pulled from b2b_request.reviewed_by_admin_id (the super admin who approved it).
        """
        b2b_request = await self.get_b2b_request(request_id)
        if b2b_request.status != B2BRequestStatus.approved_paid:
            raise B2BRequestNotPendingError(
                f"B2B request is {b2b_request.status}, expected approved_paid"
            )
        if not b2b_request.order_id:
            raise SuperAdminError(f"No order_id found for B2B request {request_id}")

        admin_id = b2b_request.reviewed_by_admin_id

        # Get the existing pending order
        order = await self._session.scalar(
            select(OrderModel).where(OrderModel.id == b2b_request.order_id)
        )
        if not order:
            raise SuperAdminError(f"Order {b2b_request.order_id} not found")

        # Guard: ensure the order found actually belongs to this B2B request
        if order.id != b2b_request.order_id:
            raise SuperAdminError(
                f"Order mismatch: webhook order {order.id} != b2b_request.order_id {b2b_request.order_id}"
            )

        # Mark order as paid
        order.status = OrderStatus.paid

        # Resolve recipient holder
        allocation_service = AllocationService(self._session)
        to_holder = await allocation_service.resolve_holder(
            user_id=b2b_request.requesting_user_id,
            create_if_missing=True,
        )

        # Get or create B2B ticket type for this event day
        b2b_ticket_type = await self._ticketing_repo.get_or_create_b2b_ticket_type(
            event_day_id=b2b_request.event_day_id,
        )

        # Atomically get next_ticket_index and increment in one DB operation
        start_index = await self._event_repo.increment_next_ticket_index(
            b2b_request.event_day_id, b2b_request.quantity
        )

        # Create tickets on-the-fly (B2B tickets don't exist in pool)
        tickets = await self._ticketing_repo.bulk_create_tickets(
            event_id=b2b_request.event_id,
            event_day_id=b2b_request.event_day_id,
            ticket_type_id=b2b_ticket_type.id,
            start_index=start_index,
            quantity=b2b_request.quantity,
        )
        ticket_ids = [t.id for t in tickets]

        # Create allocation (from_holder_id=NULL means pool)
        allocation = await self._allocation_repo.create_allocation(
            event_id=b2b_request.event_id,
            from_holder_id=None,
            to_holder_id=to_holder.id,
            order_id=order.id,
            allocation_type=AllocationType.b2b,
            ticket_count=len(ticket_ids),
            metadata_={
                "b2b_request_id": str(b2b_request.id),
                "approved_by_admin_id": str(admin_id),
                "source": "b2b_paid",
            },
        )

        # Add tickets to allocation
        await self._allocation_repo.add_tickets_to_allocation(allocation.id, ticket_ids)

        # Update ticket ownership
        await self._update_ticket_ownership(ticket_ids, to_holder.id)

        # Upsert edge
        await self._allocation_repo.upsert_edge(
            event_id=b2b_request.event_id,
            from_holder_id=None,
            to_holder_id=to_holder.id,
            ticket_count=len(ticket_ids),
        )

        # Mark allocation completed
        await self._allocation_repo.transition_allocation_status(
            allocation.id,
            AllocationStatus.pending,
            AllocationStatus.completed,
        )

        # Update B2B request with allocation_id
        updated = await self._repo.update_b2b_request_status(
            request_id=b2b_request.id,
            new_status=B2BRequestStatus.payment_done,
            admin_id=admin_id,
            allocation_id=allocation.id,
        )
        if not updated:
            raise SuperAdminError(f"Failed to update B2B request {b2b_request.id} status")

        # Notify organizer that their B2B tickets have been issued
        try:
            holder_result = await self._session.execute(
                select(TicketHolderModel).where(TicketHolderModel.user_id == b2b_request.requesting_user_id)
            )
            org_holder = holder_result.scalar_one_or_none()
            if org_holder:
                ticket_msg = f"Your B2B request for {b2b_request.quantity} ticket(s) has been fulfilled and tickets are now active."
                if org_holder.email:
                    mock_send_email(org_holder.email, "B2B Tickets Issued", ticket_msg)
                if org_holder.phone:
                    mock_send_sms(org_holder.phone, ticket_msg)
                    mock_send_whatsapp(org_holder.phone, ticket_msg)
        except Exception as e:
            # Notification failures must not rollback the allocation
            logger.warning(f"Failed to send B2B fulfillment notification: {e}")

        await self._session.refresh(b2b_request)
        return b2b_request

    async def _select_and_lock_tickets_fifo(
        self,
        event_day_id: uuid.UUID,
        ticket_type_id: uuid.UUID,
        quantity: int,
        order_id: uuid.UUID,
    ) -> list[uuid.UUID]:
        """
        Select the oldest unallocated tickets (FIFO by ticket_index) and lock them.
        Uses SELECT + UPDATE in a single atomic operation.
        """
        from sqlalchemy import select as sa_select

        # Subquery: select ticket IDs ordered by ticket_index (FIFO), limited by quantity
        subq = (
            sa_select(TicketModel.id)
            .where(
                TicketModel.event_day_id == event_day_id,
                TicketModel.ticket_type_id == ticket_type_id,
                TicketModel.owner_holder_id.is_(None),
                TicketModel.lock_reference_id.is_(None),
                TicketModel.status == "active",
            )
            .order_by(TicketModel.ticket_index.asc())
            .limit(quantity)
            .with_for_update()
        )

        # Update selected tickets with lock
        result = await self._session.execute(
            update(TicketModel)
            .where(TicketModel.id.in_(subq.scalar_subquery()))
            .values(
                lock_reference_type="order",
                lock_reference_id=order_id,
            )
            .returning(TicketModel.id)
        )
        return list(result.scalars().all())

    async def _update_ticket_ownership(
        self, ticket_ids: list[uuid.UUID], to_holder_id: uuid.UUID
    ) -> None:
        """Update ticket ownership and clear locks."""
        await self._session.execute(
            update(TicketModel)
            .where(TicketModel.id.in_(ticket_ids))
            .values(
                owner_holder_id=to_holder_id,
                lock_reference_type=None,
                lock_reference_id=None,
            )
        )
