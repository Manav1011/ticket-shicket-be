from typing import Optional
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.organizer.models import OrganizerPageModel
from apps.ticketing.models import DayTicketAllocationModel, TicketTypeModel

from .models import EventDayModel, EventModel


class EventRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    @property
    def session(self) -> AsyncSession:
        return self._session

    def add(self, event: EventModel) -> None:
        self._session.add(event)

    async def get_by_id_for_owner(
        self, event_id: UUID, owner_user_id: UUID
    ) -> Optional[EventModel]:
        return await self._session.scalar(
            select(EventModel)
            .join_from(EventModel, OrganizerPageModel)
            .where(
                EventModel.id == event_id,
                OrganizerPageModel.owner_user_id == owner_user_id,
            )
        )

    async def create_event_day(
        self, event_id, day_index, day_date, start_time=None, end_time=None
    ) -> EventDayModel:
        event_day = EventDayModel(
            event_id=event_id,
            day_index=day_index,
            date=day_date,
            start_time=start_time,
            end_time=end_time,
            scan_status="not_started",
            next_ticket_index=1,
        )
        self._session.add(event_day)
        await self._session.flush()
        await self._session.refresh(event_day)
        return event_day

    async def get_event_day_for_owner(
        self, event_day_id: UUID, owner_user_id: UUID
    ) -> Optional[EventDayModel]:
        return await self._session.scalar(
            select(EventDayModel)
            .join(EventModel, EventDayModel.event_id == EventModel.id)
            .join_from(EventModel, OrganizerPageModel)
            .where(
                EventDayModel.id == event_day_id,
                OrganizerPageModel.owner_user_id == owner_user_id,
            )
        )

    async def list_event_days(self, event_id: UUID) -> list[EventDayModel]:
        result = await self._session.scalars(
            select(EventDayModel)
            .where(EventDayModel.event_id == event_id)
            .order_by(EventDayModel.day_index.asc())
        )
        return list(result.all())

    async def delete_event_day(self, event_day: EventDayModel) -> None:
        await self._session.delete(event_day)
        await self._session.flush()

    async def count_event_days(self, event_id: UUID) -> int:
        return await self._session.scalar(
            select(func.count(EventDayModel.id)).where(EventDayModel.event_id == event_id)
        )

    async def count_ticket_types(self, event_id: UUID) -> int:
        return await self._session.scalar(
            select(func.count(TicketTypeModel.id)).where(TicketTypeModel.event_id == event_id)
        )

    async def count_ticket_allocations(self, event_id: UUID) -> int:
        return await self._session.scalar(
            select(func.count(DayTicketAllocationModel.id))
            .join(TicketTypeModel, DayTicketAllocationModel.ticket_type_id == TicketTypeModel.id)
            .where(TicketTypeModel.event_id == event_id)
        )
