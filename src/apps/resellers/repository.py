from uuid import UUID
from sqlalchemy import select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession
from apps.event.models import EventResellerModel, EventModel
from apps.allocation.models import AllocationModel, AllocationType, AllocationTicketModel
from apps.ticketing.models import TicketModel


class ResellerRepository:
    def __init__(self, session: AsyncSession):
        self._session = session

    async def list_my_events(self, user_id: UUID) -> list[dict]:
        """
        List events where user is an accepted reseller.
        Uses JOIN on EventModel + EventResellerModel + OrganizerPageModel.
        Single query with all needed fields - no N+1.
        """
        from apps.organizer.models import OrganizerPageModel
        result = await self._session.execute(
            select(
                EventModel.id,
                EventModel.name,
                EventModel.status,
                OrganizerPageModel.name.label("organizer_name"),
                EventResellerModel.accepted_at,
            )
            .join(EventResellerModel, EventResellerModel.event_id == EventModel.id)
            .join(OrganizerPageModel, OrganizerPageModel.id == EventModel.organizer_id)
            .where(
                EventResellerModel.user_id == user_id,
                EventResellerModel.accepted_at.isnot(None),
            )
            .order_by(EventResellerModel.accepted_at.desc())
        )
        rows = result.all()
        return [
            {
                "event_id": row[0],
                "event_name": row[1],
                "event_status": row[2],
                "organizer_name": row[3],
                "accepted_at": row[4],
            }
            for row in rows
        ]

    async def is_accepted_reseller(self, user_id: UUID, event_id: UUID) -> bool:
        """
        Check if user is an accepted reseller for the event.
        Uses composite index-friendly query.
        """
        result = await self._session.scalar(
            select(EventResellerModel.accepted_at).where(
                EventResellerModel.user_id == user_id,
                EventResellerModel.event_id == event_id,
                EventResellerModel.accepted_at.isnot(None),
            )
        )
        return result is not None

    async def get_my_holder_for_event(self, user_id: UUID):
        """
        Get TicketHolder for a user.
        Returns None if user has no holder yet.
        """
        from apps.allocation.repository import AllocationRepository
        allocation_repo = AllocationRepository(self._session)
        return await allocation_repo.get_holder_by_user_id(user_id)

    async def get_b2b_ticket_type_for_event(self, event_id: UUID):
        """
        Get B2B ticket type for event.
        """
        from apps.ticketing.repository import TicketingRepository
        ticketing_repo = TicketingRepository(self._session)
        return await ticketing_repo.get_b2b_ticket_type_for_event(event_id)

    async def list_b2b_tickets_by_holder(
        self,
        event_id: UUID,
        holder_id: UUID,
        b2b_ticket_type_id: UUID,
    ) -> list[dict]:
        """
        List B2B ticket counts owned by holder, grouped by event_day.
        Optimized: COUNT + GROUP BY, no lock filtering (reseller owns these).
        """
        result = await self._session.execute(
            select(
                TicketModel.event_day_id,
                func.count(TicketModel.id).label("count"),
            )
            .where(
                TicketModel.event_id == event_id,
                TicketModel.owner_holder_id == holder_id,
                TicketModel.ticket_type_id == b2b_ticket_type_id,
            )
            .group_by(TicketModel.event_day_id)
        )
        return [
            {"event_day_id": row[0], "count": row[1]}
            for row in result.all()
        ]

    async def list_b2b_allocations_for_holder(
        self,
        event_id: UUID,
        holder_id: UUID,
        limit: int = 50,
        offset: int = 0,
    ) -> list[dict]:
        """
        List B2B allocations where holder is sender OR receiver.
        Direction determined by: to_holder_id == holder_id -> "received" else "transferred".
        Optimized: single query with ticket event_day resolution via subquery.
        """
        # Subquery: filter allocations to those involving this holder (either direction)
        alloc_filter = (
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

        # Subquery: get event_day_id from first ticket in each allocation
        day_subq = (
            select(
                AllocationTicketModel.allocation_id,
                TicketModel.event_day_id,
            )
            .join(TicketModel, AllocationTicketModel.ticket_id == TicketModel.id)
            .where(AllocationTicketModel.allocation_id.in_(select(alloc_filter)))
            .distinct(AllocationTicketModel.allocation_id)
            .subquery()
        )

        # Main query with JOIN for event_day_id
        result = await self._session.execute(
            select(AllocationModel, day_subq.c.event_day_id)
            .join(day_subq, AllocationModel.id == day_subq.c.allocation_id)
            .order_by(AllocationModel.created_at.desc())
        )

        allocations = []
        for row in result.all():
            alloc = row[0]
            event_day_id = row[1]
            direction = "received" if alloc.to_holder_id == holder_id else "transferred"
            source = alloc.metadata_.get("source", "b2b_free") if alloc.metadata_ else "b2b_free"
            allocations.append({
                "allocation_id": alloc.id,
                "event_day_id": event_day_id,
                "direction": direction,
                "from_holder_id": alloc.from_holder_id,
                "to_holder_id": alloc.to_holder_id,
                "ticket_count": alloc.ticket_count,
                "status": alloc.status.value if hasattr(alloc.status, 'value') else alloc.status,
                "source": source,
                "created_at": alloc.created_at,
            })
        return allocations
