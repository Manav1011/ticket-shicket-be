from uuid import UUID
from apps.resellers.repository import ResellerRepository
from apps.resellers.response import (
    ResellerEventsResponse,
    ResellerEventItem,
    ResellerTicketItem,
    ResellerTicketsResponse,
    ResellerAllocationItem,
    ResellerAllocationsResponse,
)
from exceptions import ForbiddenError, NotFoundError


class ResellerService:
    def __init__(self, session):
        self._repo = ResellerRepository(session)

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
