"""
Super admin service — handles B2B request lifecycle.
All B2B operations are wrapped in a single database transaction.
"""
import uuid

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from apps.allocation.enums import AllocationStatus
from apps.allocation.models import AllocationModel, OrderModel
from apps.allocation.repository import AllocationRepository
from apps.allocation.service import AllocationService
from apps.ticketing.enums import OrderStatus, OrderType
from apps.ticketing.models import TicketModel

from .enums import B2BRequestStatus
from .exceptions import (
    B2BRequestNotFoundError,
    B2BRequestNotPendingError,
    InsufficientTicketsError,
    SuperAdminError,
)
from .models import B2BRequestModel, SuperAdminModel
from .repository import SuperAdminRepository


class SuperAdminService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = SuperAdminRepository(session)
        self._allocation_repo = AllocationRepository(session)

    @property
    def repo(self) -> SuperAdminRepository:
        return self._repo

    async def get_b2b_request(self, request_id: uuid.UUID) -> B2BRequestModel:
        request = await self._repo.get_b2b_request_by_id(request_id)
        if not request:
            raise B2BRequestNotFoundError(f"B2B request {request_id} not found")
        return request

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
            phone=b2b_request.recipient_phone,
            email=b2b_request.recipient_email,
            create_if_missing=True,
        )

        async with self._session.begin():
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

            # Select + lock + allocate tickets (FIFO from pool)
            ticket_ids = await self._select_and_lock_tickets_fifo(
                event_day_id=b2b_request.event_day_id,
                ticket_type_id=b2b_request.ticket_type_id,
                quantity=b2b_request.quantity,
                order_id=order.id,
            )

            if len(ticket_ids) < b2b_request.quantity:
                raise InsufficientTicketsError(
                    requested=b2b_request.quantity,
                    available=len(ticket_ids),
                )

            # Create allocation (from_holder_id=NULL means pool)
            allocation = await self._allocation_repo.create_allocation(
                event_id=b2b_request.event_id,
                from_holder_id=None,
                to_holder_id=to_holder.id,
                order_id=order.id,
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
            await self._repo.update_b2b_request_status(
                request_id=b2b_request.id,
                new_status=B2BRequestStatus.approved_free,
                admin_id=admin_id,
                admin_notes=admin_notes,
                allocation_id=allocation.id,
                order_id=order.id,
            )

        await self._session.refresh(b2b_request)
        return b2b_request

    async def approve_b2b_request_paid(
        self,
        admin_id: uuid.UUID,
        request_id: uuid.UUID,
        amount: float,
        admin_notes: str | None = None,
    ) -> B2BRequestModel:
        """
        Approve a B2B request with paid order.
        Creates a pending PURCHASE order. Organizer pays via payment gateway.
        Allocation is created later when organizer confirms payment.
        """
        b2b_request = await self.get_b2b_request(request_id)
        if b2b_request.status != B2BRequestStatus.pending:
            raise B2BRequestNotPendingError(
                f"B2B request is {b2b_request.status}, expected pending"
            )

        async with self._session.begin():
            # Create PURCHASE order with pending status
            order = OrderModel(
                event_id=b2b_request.event_id,
                user_id=b2b_request.requesting_user_id,
                type=OrderType.purchase,
                subtotal_amount=amount,
                discount_amount=0.0,
                final_amount=amount,
                status=OrderStatus.pending,
            )
            self._session.add(order)
            await self._session.flush()

            # Update B2B request — no allocation_id yet (allocation comes after payment)
            await self._repo.update_b2b_request_status(
                request_id=b2b_request.id,
                new_status=B2BRequestStatus.approved_paid,
                admin_id=admin_id,
                admin_notes=admin_notes,
                order_id=order.id,
            )

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

        await self._repo.update_b2b_request_status(
            request_id=b2b_request.id,
            new_status=B2BRequestStatus.rejected,
            admin_id=admin_id,
            admin_notes=reason,
        )
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

        # Mark order as paid
        order.status = OrderStatus.paid

        # Resolve recipient holder
        allocation_service = AllocationService(self._session)
        to_holder = await allocation_service.resolve_holder(
            phone=b2b_request.recipient_phone,
            email=b2b_request.recipient_email,
            create_if_missing=True,
        )

        # Select + lock + allocate tickets
        ticket_ids = await self._select_and_lock_tickets_fifo(
            event_day_id=b2b_request.event_day_id,
            ticket_type_id=b2b_request.ticket_type_id,
            quantity=b2b_request.quantity,
            order_id=order.id,
        )

        if len(ticket_ids) < b2b_request.quantity:
            raise InsufficientTicketsError(
                requested=b2b_request.quantity,
                available=len(ticket_ids),
            )

        # Create allocation (from_holder_id=NULL means pool)
        allocation = await self._allocation_repo.create_allocation(
            event_id=b2b_request.event_id,
            from_holder_id=None,
            to_holder_id=to_holder.id,
            order_id=order.id,
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
        await self._repo.update_b2b_request_status(
            request_id=b2b_request.id,
            new_status=B2BRequestStatus.approved_paid,
            admin_id=admin_id,
            allocation_id=allocation.id,
        )

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
