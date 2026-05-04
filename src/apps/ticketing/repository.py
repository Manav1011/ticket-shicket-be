from typing import Optional
from uuid import UUID
from datetime import datetime, timedelta, timezone

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from .models import DayTicketAllocationModel, TicketModel, TicketTypeModel
from .enums import TicketCategory


class TicketingRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    @property
    def session(self) -> AsyncSession:
        return self._session

    def add(self, ticket_type: TicketTypeModel) -> None:
        self._session.add(ticket_type)

    async def list_ticket_types_for_event(self, event_id: UUID) -> list[TicketTypeModel]:
        result = await self._session.scalars(
            select(TicketTypeModel)
            .where(TicketTypeModel.event_id == event_id)
            .where(TicketTypeModel.category != TicketCategory.b2b)
            .order_by(TicketTypeModel.created_at.asc())
        )
        return list(result.all())

    async def list_allocations_for_event(self, event_id: UUID) -> list[DayTicketAllocationModel]:
        result = await self._session.scalars(
            select(DayTicketAllocationModel)
            .join(TicketTypeModel, DayTicketAllocationModel.ticket_type_id == TicketTypeModel.id)
            .where(TicketTypeModel.event_id == event_id)
            .order_by(DayTicketAllocationModel.created_at.asc())
        )
        return list(result.all())

    async def get_allocation_by_id(
        self, allocation_id: UUID
    ) -> Optional[DayTicketAllocationModel]:
        return await self._session.scalar(
            select(DayTicketAllocationModel).where(
                DayTicketAllocationModel.id == allocation_id
            )
        )

    async def get_ticket_type_for_event(
        self, ticket_type_id: UUID, event_id: UUID
    ) -> Optional[TicketTypeModel]:
        return await self._session.scalar(
            select(TicketTypeModel).where(
                TicketTypeModel.id == ticket_type_id,
                TicketTypeModel.event_id == event_id,
            )
        )

    async def create_day_allocation(
        self, event_day_id: UUID, ticket_type_id: UUID, quantity: int
    ) -> DayTicketAllocationModel:
        allocation = DayTicketAllocationModel(
            event_day_id=event_day_id,
            ticket_type_id=ticket_type_id,
            quantity=quantity,
        )
        self._session.add(allocation)
        await self._session.flush()
        await self._session.refresh(allocation)
        return allocation

    async def bulk_create_tickets(
        self,
        event_id: UUID,
        event_day_id: UUID,
        ticket_type_id: UUID,
        start_index: int,
        quantity: int,
    ) -> list[TicketModel]:
        tickets = [
            TicketModel(
                event_id=event_id,
                event_day_id=event_day_id,
                ticket_type_id=ticket_type_id,
                ticket_index=start_index + offset,
                owner_holder_id=None,  # Tickets start unallocated in pool
                status="active",
            )
            for offset in range(quantity)
        ]
        self._session.add_all(tickets)
        await self._session.flush()
        return tickets

    async def get_or_create_b2b_ticket_type(
        self,
        event_day_id: UUID,
        name: str = "B2B",
        price: float = 0.0,
        currency: str = "INR",
    ) -> TicketTypeModel:
        """
        Get or create a B2B ticket type for a given event day.
        If a B2B ticket type already exists for this event (via any day), returns it.
        Otherwise creates a new B2B ticket type linked to the event that owns this day.
        """
        from apps.ticketing.enums import TicketCategory
        from apps.event.models import EventDayModel

        # Get the event_day to find the event_id
        event_day = await self._session.scalar(
            select(EventDayModel).where(EventDayModel.id == event_day_id)
        )
        if not event_day:
            raise ValueError(f"EventDay {event_day_id} not found")

        # Look for an existing B2B ticket type for this event
        existing = await self._session.scalar(
            select(TicketTypeModel).where(
                TicketTypeModel.event_id == event_day.event_id,
                TicketTypeModel.category == TicketCategory.b2b,
            )
        )
        if existing:
            return existing

        # Create new B2B ticket type
        ticket_type = TicketTypeModel(
            event_id=event_day.event_id,
            name=name,
            category=TicketCategory.b2b,
            price=price,
            currency=currency,
        )
        self._session.add(ticket_type)
        await self._session.flush()
        await self._session.refresh(ticket_type)
        return ticket_type

    async def get_b2b_ticket_type_for_event(
        self,
        event_id: UUID,
    ) -> TicketTypeModel | None:
        """
        Get the B2B ticket type for an event. There is exactly 1 B2B type per event.
        Returns None if none exist — does NOT create.
        """
        from apps.ticketing.enums import TicketCategory

        result = await self._session.scalar(
            select(TicketTypeModel).where(
                TicketTypeModel.event_id == event_id,
                TicketTypeModel.category == TicketCategory.b2b,
            )
        )
        return result

    async def get_or_create_b2b_ticket_type_for_event(
        self,
        event_id: UUID,
        name: str = "B2B",
        price: float = 0.0,
        currency: str = "INR",
    ) -> TicketTypeModel:
        """
        Get or create a B2B ticket type for a given event.
        If a B2B ticket type already exists for this event, returns it.
        Otherwise creates a new B2B ticket type linked to this event.
        """
        from apps.ticketing.enums import TicketCategory

        existing = await self._session.scalar(
            select(TicketTypeModel).where(
                TicketTypeModel.event_id == event_id,
                TicketTypeModel.category == TicketCategory.b2b,
            )
        )
        if existing:
            return existing

        ticket_type = TicketTypeModel(
            event_id=event_id,
            name=name,
            category=TicketCategory.b2b,
            price=price,
            currency=currency,
        )
        self._session.add(ticket_type)
        await self._session.flush()
        await self._session.refresh(ticket_type)
        return ticket_type

    async def lock_tickets_for_transfer(
        self,
        owner_holder_id: UUID,
        event_id: UUID,
        ticket_type_id: UUID,
        event_day_id: UUID,
        quantity: int,
        order_id: UUID,
        lock_ttl_minutes: int = 30,
    ) -> list[UUID]:
        """
        Atomically lock `quantity` tickets for a transfer request.
        Uses FIFO (ticket_index ASC).
        Sets lock_reference_type='transfer', lock_reference_id=order_id,
        and lock_expires_at=now+lock_ttl_minutes.

        Returns locked ticket IDs.
        Raises ValueError if fewer than `quantity` tickets could be locked,
        with message: "Only {N} tickets available, requested {quantity}"
        """
        expires_at = datetime.now(timezone.utc) + timedelta(minutes=lock_ttl_minutes)

        # Subquery: select ticket IDs ordered by ticket_index, limited by quantity
        # Uses FOR UPDATE to prevent concurrent lock acquisition
        subq = (
            select(TicketModel.id)
            .where(
                TicketModel.event_id == event_id,
                TicketModel.event_day_id == event_day_id,
                TicketModel.ticket_type_id == ticket_type_id,
                TicketModel.owner_holder_id == owner_holder_id,
                TicketModel.lock_reference_id.is_(None),
            )
            .order_by(TicketModel.ticket_index.asc())
            .limit(quantity)
            .with_for_update()
        )

        # Lock the selected tickets in a single atomic UPDATE
        result = await self._session.execute(
            update(TicketModel)
            .where(TicketModel.id.in_(subq))
            .values(
                lock_reference_type="transfer",
                lock_reference_id=order_id,
                lock_expires_at=expires_at,
            )
            .returning(TicketModel.id)
        )
        locked_ids = list(result.scalars().all())

        if len(locked_ids) < quantity:
            # Rollback-worthy failure — not enough lockable tickets
            raise ValueError(
                f"Only {len(locked_ids)} tickets available, requested {quantity}"
            )

        return locked_ids

    async def select_tickets_for_transfer(
        self,
        owner_holder_id: UUID,
        event_id: UUID,
        quantity: int,
        event_day_id: UUID | None = None,
    ) -> list[dict]:
        """
        Select tickets for transfer from a holder's pool.
        Returns list of dicts with ticket id and ticket_index.
        Uses FIFO ordering (ticket_index ASC).

        Does NOT lock or update — caller decides what to do with selected tickets.
        """
        conditions = [
            TicketModel.event_id == event_id,
            TicketModel.owner_holder_id == owner_holder_id,
            TicketModel.status == "active",
            TicketModel.lock_reference_id.is_(None),
        ]
        if event_day_id:
            conditions.append(TicketModel.event_day_id == event_day_id)

        result = await self._session.execute(
            select(TicketModel.id, TicketModel.ticket_index)
            .where(*conditions)
            .order_by(TicketModel.ticket_index.asc())
            .limit(quantity)
        )
        rows = result.all()
        return [{"ticket_id": row[0], "ticket_index": row[1]} for row in rows]

    async def update_ticket_ownership_batch(
        self,
        ticket_ids: list[UUID],
        new_owner_holder_id: UUID,
        claim_link_id: UUID | None = None,
    ) -> None:
        """
        Update owner_holder_id for a batch of tickets.
        Clears lock fields as part of ownership transfer.
        """
        if not ticket_ids:
            return

        values = {
            "owner_holder_id": new_owner_holder_id,
            "lock_reference_type": None,
            "lock_reference_id": None,
            "lock_expires_at": None,
        }
        if claim_link_id is not None:
            values["claim_link_id"] = claim_link_id

        await self._session.execute(
            update(TicketModel)
            .where(TicketModel.id.in_(ticket_ids))
            .values(**values)
        )

    async def clear_locks_for_order(self, order_id: UUID) -> None:
        """
        Clear all ticket locks associated with an order.
        Used when payment webhook processing is complete or failed.
        """
        await self._session.execute(
            update(TicketModel)
            .where(
                TicketModel.lock_reference_type.in_(["order", "transfer"]),
                TicketModel.lock_reference_id == order_id,
            )
            .values(
                lock_reference_type=None,
                lock_reference_id=None,
                lock_expires_at=None,
            )
        )
