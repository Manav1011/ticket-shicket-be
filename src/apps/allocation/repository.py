from typing import Optional
from uuid import UUID

from sqlalchemy import select, update, func, or_
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from apps.ticketing.models import TicketModel, TicketTypeModel
from .enums import AllocationStatus, AllocationType
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
        allocation_type: "AllocationType",
        ticket_count: int = 0,
        metadata_: dict | None = None,
    ) -> AllocationModel:
        allocation = AllocationModel(
            event_id=event_id,
            from_holder_id=from_holder_id,
            to_holder_id=to_holder_id,
            order_id=order_id,
            allocation_type=allocation_type,
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

    # --- B2B Organizer Queries ---

    async def list_b2b_tickets_by_holder(
        self,
        event_id: UUID,
        holder_id: UUID,
        b2b_ticket_type_id: UUID,
        event_day_id: UUID | None = None,
    ) -> list[dict]:
        """
        List B2B ticket counts owned by a holder for an event, grouped by event_day.
        Uses COUNT + GROUP BY — does NOT return full ticket rows.

        Args:
            event_id: Event UUID
            holder_id: TicketHolder UUID
            b2b_ticket_type_id: The B2B ticket type UUID for this event
            event_day_id: Optional -- if provided, filter to specific day only
        """
        conditions = [
            TicketModel.event_id == event_id,
            TicketModel.owner_holder_id == holder_id,
            TicketModel.ticket_type_id == b2b_ticket_type_id,
        ]
        if event_day_id:
            conditions.append(TicketModel.event_day_id == event_day_id)

        result = await self._session.execute(
            select(
                TicketModel.event_day_id,
                func.count(TicketModel.id).label("count"),
            )
            .where(*conditions)
            .group_by(
                TicketModel.event_day_id,
            )
        )
        rows = result.all()
        return [
            {
                "event_day_id": row[0],
                "count": row[1],
            }
            for row in rows
        ]

    async def list_b2b_allocations_for_holder(
        self,
        event_id: UUID,
        holder_id: UUID,
        event_day_id: UUID | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[dict]:
        """
        List B2B allocations where the given holder is sender or receiver.
        Fetches ticket_ids via subquery — single query, no N+1.

        Args:
            event_id: Event UUID
            holder_id: TicketHolder UUID
            event_day_id: Optional — if provided, filter allocations to tickets from that day only
            limit: Pagination limit
            offset: Pagination offset
        """
        from apps.ticketing.models import TicketModel

        # Subquery: get all ticket_ids for this holder's B2B allocations, optionally filtered by day
        ticket_subq = (
            select(AllocationTicketModel.allocation_id)
            .join(TicketModel, AllocationTicketModel.ticket_id == TicketModel.id)
            .where(TicketModel.owner_holder_id == holder_id)
        )
        if event_day_id:
            ticket_subq = ticket_subq.where(TicketModel.event_day_id == event_day_id)
        ticket_subq = ticket_subq.distinct().subquery()

        # Main query: allocations involving this holder, using the subquery to filter
        alloc_ids = (
            select(AllocationModel.id)
            .where(
                AllocationModel.event_id == event_id,
                AllocationModel.allocation_type == AllocationType.b2b,
                or_(
                    AllocationModel.to_holder_id == holder_id,
                    AllocationModel.from_holder_id == holder_id,
                ),
            )
            .order_by(AllocationModel.created_at.desc())
            .limit(limit)
            .offset(offset)
            .subquery()
        )

        # Fetch allocations + join their ticket IDs in one query
        result = await self._session.execute(
            select(AllocationModel)
            .where(AllocationModel.id.in_(select(alloc_ids)))
            .order_by(AllocationModel.created_at.desc())
        )
        allocations = result.scalars().all()

        # Fetch all ticket_ids for these allocations in ONE query
        alloc_id_list = [a.id for a in allocations]
        if not alloc_id_list:
            return []

        tickets_result = await self._session.execute(
            select(AllocationTicketModel.allocation_id, AllocationTicketModel.ticket_id)
            .where(AllocationTicketModel.allocation_id.in_(alloc_id_list))
        )
        tickets_by_alloc = {}
        for alloc_id, ticket_id in tickets_result.all():
            tickets_by_alloc.setdefault(alloc_id, []).append(ticket_id)

        enriched = []
        for alloc in allocations:
            direction = "received" if alloc.to_holder_id == holder_id else "transferred"
            metadata = alloc.metadata_ or {}
            source = metadata.get("source", "b2b_free")
            ticket_ids = tickets_by_alloc.get(alloc.id, [])

            enriched.append({
                "allocation_id": alloc.id,
                "direction": direction,
                "from_holder_id": alloc.from_holder_id,
                "to_holder_id": alloc.to_holder_id,
                "ticket_count": alloc.ticket_count,
                "ticket_ids": ticket_ids,
                "status": alloc.status,
                "source": source,
                "created_at": alloc.created_at,
            })

        return enriched
