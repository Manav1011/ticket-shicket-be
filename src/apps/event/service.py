from datetime import datetime

from .exceptions import EventNotFound, InvalidScanTransition, OrganizerOwnershipError
from .models import EventModel


class EventService:
    def __init__(self, repository, organizer_repository) -> None:
        self.repository = repository
        self.organizer_repository = organizer_repository

    async def create_draft_event(self, owner_user_id, organizer_page_id, title, event_access_type):
        organizer = await self.organizer_repository.get_by_id_for_owner(
            organizer_page_id, owner_user_id
        )
        if not organizer:
            raise OrganizerOwnershipError

        event = EventModel(
            organizer_page_id=organizer_page_id,
            created_by_user_id=owner_user_id,
            title=title,
            slug=None,
            description=None,
            event_type=None,
            status="draft",
            event_access_type=event_access_type,
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

    def _build_setup_status(self, event, day_count, ticket_type_count, allocation_count):
        basic_info_complete = all(
            [
                getattr(event, "title", None),
                getattr(event, "event_access_type", None),
                getattr(event, "location_mode", None),
                getattr(event, "timezone", None),
            ]
        )
        schedule_complete = day_count > 0
        tickets_complete = getattr(event, "event_access_type", None) == "open" or (
            ticket_type_count > 0 and allocation_count > 0
        )
        return {
            "basic_info": basic_info_complete,
            "schedule": schedule_complete,
            "tickets": tickets_complete,
        }

    async def _refresh_setup_status(self, event):
        day_count = await self.repository.count_event_days(event.id)
        ticket_type_count = await self.repository.count_ticket_types(event.id)
        allocation_count = await self.repository.count_ticket_allocations(event.id)
        event.setup_status = self._build_setup_status(
            event, day_count, ticket_type_count, allocation_count
        )
        await self.repository.session.flush()
        return event.setup_status

    async def get_event_detail(self, owner_user_id, event_id):
        event = await self.repository.get_by_id_for_owner(event_id, owner_user_id)
        if not event:
            raise EventNotFound
        return event

    async def update_basic_info(self, owner_user_id, event_id, **payload):
        event = await self.repository.get_by_id_for_owner(event_id, owner_user_id)
        if not event:
            raise EventNotFound

        for field, value in payload.items():
            setattr(event, field, value)

        await self._refresh_setup_status(event)
        return event

    async def get_readiness(self, owner_user_id, event_id):
        event = await self.get_event_detail(owner_user_id, event_id)
        status = event.setup_status or {
            "basic_info": False,
            "schedule": False,
            "tickets": False,
        }
        missing_sections = [name for name, done in status.items() if not done]
        blocking_issues = []
        if not status["basic_info"]:
            blocking_issues.append("Complete basic event information")
        if not status["schedule"]:
            blocking_issues.append("Add at least one event day")
        if not status["tickets"]:
            blocking_issues.append("Add ticket types and allocations or switch event to open")
        return {
            "completed_sections": [name for name, done in status.items() if done],
            "missing_sections": missing_sections,
            "blocking_issues": blocking_issues,
        }

    async def create_event_day(self, owner_user_id, event_id, day_index, date, start_time=None, end_time=None):
        event = await self.repository.get_by_id_for_owner(event_id, owner_user_id)
        if not event:
            raise EventNotFound
        day = await self.repository.create_event_day(
            event_id, day_index, date, start_time=start_time, end_time=end_time
        )
        await self._refresh_setup_status(event)
        return day

    async def list_event_days(self, owner_user_id, event_id):
        event = await self.repository.get_by_id_for_owner(event_id, owner_user_id)
        if not event:
            raise EventNotFound
        return await self.repository.list_event_days(event_id)

    async def update_event_day(self, owner_user_id, event_day_id, **payload):
        day = await self.repository.get_event_day_for_owner(event_day_id, owner_user_id)
        if not day:
            raise EventNotFound
        for field, value in payload.items():
            setattr(day, field, value)
        await self.repository.session.flush()
        return day

    async def delete_event_day(self, owner_user_id, event_day_id):
        day = await self.repository.get_event_day_for_owner(event_day_id, owner_user_id)
        if not day:
            raise EventNotFound
        event = await self.repository.get_by_id_for_owner(day.event_id, owner_user_id)
        await self.repository.delete_event_day(day)
        if event:
            await self._refresh_setup_status(event)

    async def start_scan(self, owner_user_id, event_day_id, notes: str | None = None):
        day = await self.repository.get_event_day_for_owner(event_day_id, owner_user_id)
        if not day:
            raise EventNotFound
        if day.scan_status == "ended":
            raise InvalidScanTransition
        previous_status = day.scan_status
        day.scan_status = "active"
        if day.scan_started_at is None:
            day.scan_started_at = datetime.utcnow()
        await self.repository.create_scan_status_history(
            event_day_id=event_day_id,
            changed_by_user_id=owner_user_id,
            previous_status=previous_status,
            new_status="active",
            notes=notes,
        )
        await self.repository.session.flush()
        return day

    async def pause_scan(self, owner_user_id, event_day_id, notes: str | None = None):
        day = await self.repository.get_event_day_for_owner(event_day_id, owner_user_id)
        if not day:
            raise EventNotFound
        if day.scan_status != "active":
            raise InvalidScanTransition
        previous_status = day.scan_status
        day.scan_status = "paused"
        day.scan_paused_at = datetime.utcnow()
        await self.repository.create_scan_status_history(
            event_day_id=event_day_id,
            changed_by_user_id=owner_user_id,
            previous_status=previous_status,
            new_status="paused",
            notes=notes,
        )
        await self.repository.session.flush()
        return day

    async def resume_scan(self, owner_user_id, event_day_id, notes: str | None = None):
        day = await self.repository.get_event_day_for_owner(event_day_id, owner_user_id)
        if not day:
            raise EventNotFound
        if day.scan_status != "paused":
            raise InvalidScanTransition
        previous_status = day.scan_status
        day.scan_status = "active"
        await self.repository.create_scan_status_history(
            event_day_id=event_day_id,
            changed_by_user_id=owner_user_id,
            previous_status=previous_status,
            new_status="active",
            notes=notes,
        )
        await self.repository.session.flush()
        return day

    async def end_scan(self, owner_user_id, event_day_id, notes: str | None = None):
        day = await self.repository.get_event_day_for_owner(event_day_id, owner_user_id)
        if not day:
            raise EventNotFound
        if day.scan_status == "ended":
            raise InvalidScanTransition
        previous_status = day.scan_status
        day.scan_status = "ended"
        day.scan_ended_at = datetime.utcnow()
        await self.repository.create_scan_status_history(
            event_day_id=event_day_id,
            changed_by_user_id=owner_user_id,
            previous_status=previous_status,
            new_status="ended",
            notes=notes,
        )
        await self.repository.session.flush()
        return day
