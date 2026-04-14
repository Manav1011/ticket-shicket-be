from typing import Optional
from uuid import UUID

from sqlalchemy import select, update, func
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from .enums import AllocationStatus
from .models import AllocationEdgeModel, AllocationModel, AllocationTicketModel, TicketHolderModel


class AllocationRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    @property
    def session(self) -> AsyncSession:
        return self._session

    # --- TicketHolder ---

    async def get_holder_by_id(self, holder_id: UUID) -> Optional[TicketHolderModel]:
        return await self._session.scalar(
            select(TicketHolderModel).where(TicketHolderModel.id == holder_id)
        )

    async def get_holder_by_user_id(self, user_id: UUID) -> Optional[TicketHolderModel]:
        return await self._session.scalar(
            select(TicketHolderModel).where(TicketHolderModel.user_id == user_id)
        )

    async def get_holder_by_phone(self, phone: str) -> Optional[TicketHolderModel]:
        return await self._session.scalar(
            select(TicketHolderModel).where(TicketHolderModel.phone == phone)
        )

    async def get_holder_by_email(self, email: str) -> Optional[TicketHolderModel]:
        return await self._session.scalar(
            select(TicketHolderModel).where(TicketHolderModel.email == email)
        )

    async def create_holder(
        self,
        user_id: UUID | None = None,
        phone: str | None = None,
        email: str | None = None,
    ) -> TicketHolderModel:
        holder = TicketHolderModel(user_id=user_id, phone=phone, email=email)
        self._session.add(holder)
        await self._session.flush()
        await self._session.refresh(holder)
        return holder

    # --- Allocation ---

    async def get_allocation_by_id(self, allocation_id: UUID) -> Optional[AllocationModel]:
        return await self._session.scalar(
            select(AllocationModel).where(AllocationModel.id == allocation_id)
        )

    async def create_allocation(
        self,
        event_id: UUID,
        from_holder_id: UUID | None,
        to_holder_id: UUID,
        order_id: UUID,
        ticket_count: int = 0,
        metadata_: dict | None = None,
    ) -> AllocationModel:
        allocation = AllocationModel(
            event_id=event_id,
            from_holder_id=from_holder_id,
            to_holder_id=to_holder_id,
            order_id=order_id,
            ticket_count=ticket_count,
            metadata_=metadata_ or {},
        )
        self._session.add(allocation)
        await self._session.flush()
        await self._session.refresh(allocation)
        return allocation

    async def transition_allocation_status(
        self,
        allocation_id: UUID,
        expected_current: AllocationStatus,
        new_status: AllocationStatus,
        failure_reason: str | None = None,
    ) -> bool:
        """
        Atomically transition allocation status only if currently in expected state.
        Returns True if transition succeeded.
        """
        kwargs = {"status": new_status.value}
        if failure_reason is not None:
            kwargs["failure_reason"] = failure_reason

        result = await self._session.execute(
            update(AllocationModel)
            .where(
                AllocationModel.id == allocation_id,
                AllocationModel.status == expected_current.value,
            )
            .values(**kwargs)
            .returning(AllocationModel.id)
        )
        return result.scalar_one_or_none() is not None

    # --- AllocationTicket ---

    async def add_tickets_to_allocation(
        self,
        allocation_id: UUID,
        ticket_ids: list[UUID],
    ) -> list[AllocationTicketModel]:
        records = [
            AllocationTicketModel(allocation_id=allocation_id, ticket_id=tid)
            for tid in ticket_ids
        ]
        self._session.add_all(records)
        await self._session.flush()
        return records

    # --- AllocationEdge ---

    async def upsert_edge(
        self,
        event_id: UUID,
        from_holder_id: UUID | None,
        to_holder_id: UUID,
        ticket_count: int,
    ) -> None:
        """
        Upsert allocation edge with atomic increment.
        Uses ON CONFLICT DO UPDATE to increment ticket_count.
        """
        from sqlalchemy.dialects.postgresql import insert as pg_insert
        from sqlalchemy import text

        stmt = pg_insert(AllocationEdgeModel).values(
            event_id=event_id,
            from_holder_id=from_holder_id,
            to_holder_id=to_holder_id,
            ticket_count=ticket_count,
        )
        stmt = stmt.on_conflict_do_update(
            constraint="uq_allocation_edges_event_from_to",
            set_={
                "ticket_count": AllocationEdgeModel.ticket_count + stmt.excluded.ticket_count,
                "updated_at": func.now(),
            },
        )
        await self._session.execute(stmt)
