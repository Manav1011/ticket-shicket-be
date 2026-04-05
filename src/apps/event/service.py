from datetime import datetime

from .exceptions import EventNotFound, InvalidScanTransition, OrganizerOwnershipError
from .models import EventModel


class EventService:
    def __init__(self, repository, organizer_repository) -> None:
        self.repository = repository
        self.organizer_repository = organizer_repository

    async def create_draft_event(self, owner_user_id, organizer_page_id):
        organizer = await self.organizer_repository.get_by_id_for_owner(
            organizer_page_id, owner_user_id
        )
        if not organizer:
            raise OrganizerOwnershipError

        event = EventModel(
            organizer_page_id=organizer_page_id,
            created_by_user_id=owner_user_id,
            title=None,
            slug=None,
            description=None,
            event_type=None,
            status="draft",
            event_access_type="ticketed",
            setup_status={},
            location_mode=None,
            timezone=None,
            start_date=None,
            end_date=None,
        )
        self.repository.add(event)
        await self.repository.session.flush()
        await self.repository.session.refresh(event)
        return event

    async def create_event_day(
        self, owner_user_id, event_id, day_index, day_date, start_time=None, end_time=None
    ):
        event = await self.repository.get_by_id_for_owner(event_id, owner_user_id)
        if not event:
            raise EventNotFound
        return await self.repository.create_event_day(
            event_id, day_index, day_date, start_time=start_time, end_time=end_time
        )

    async def start_scan(self, owner_user_id, event_day_id):
        day = await self.repository.get_event_day_for_owner(event_day_id, owner_user_id)
        if not day:
            raise EventNotFound
        if day.scan_status == "ended":
            raise InvalidScanTransition
        day.scan_status = "active"
        if day.scan_started_at is None:
            day.scan_started_at = datetime.utcnow()
        await self.repository.session.flush()
        return day
