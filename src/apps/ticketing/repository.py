from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .models import DayTicketAllocationModel, TicketModel, TicketTypeModel


class TicketingRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    @property
    def session(self) -> AsyncSession:
        return self._session

    def add(self, ticket_type: TicketTypeModel) -> None:
        self._session.add(ticket_type)

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
                status="active",
            )
            for offset in range(quantity)
        ]
        self._session.add_all(tickets)
        await self._session.flush()
        return tickets
