from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.organizer.models import OrganizerPageModel

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
