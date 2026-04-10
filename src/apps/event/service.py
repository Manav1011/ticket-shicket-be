from datetime import datetime
from uuid import UUID
import json

from apps.event.enums import EventAccessType, LocationMode

from .exceptions import EventNotFound, InvalidScanTransition, OrganizerOwnershipError
from .models import EventModel
from .response import FieldErrorResponse


def _serialize_for_json(obj):
    """Recursively convert UUID objects to strings for JSON serialization."""
    if isinstance(obj, UUID):
        return str(obj)
    elif isinstance(obj, dict):
        return {k: _serialize_for_json(v) for k, v in obj.items()}
    elif isinstance(obj, (list, tuple)):
        return [_serialize_for_json(item) for item in obj]
    else:
        return obj


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
        tickets_complete = getattr(event, "event_access_type", None) == EventAccessType.open or (
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

    def _validate_basic_info(self, event) -> list[FieldErrorResponse]:
        """Validate basic_info section based on location_mode and event_access_type."""
        errors = []

        # Required for all events
        if not getattr(event, 'title', None):
            errors.append(FieldErrorResponse(field="title", message="Title is required", code="MISSING_REQUIRED_FIELD"))
        if not getattr(event, 'event_access_type', None):
            errors.append(FieldErrorResponse(field="event_access_type", message="Event access type is required", code="MISSING_REQUIRED_FIELD"))
        if not getattr(event, 'location_mode', None):
            errors.append(FieldErrorResponse(field="location_mode", message="Location mode is required", code="MISSING_REQUIRED_FIELD"))
        if not getattr(event, 'timezone', None):
            errors.append(FieldErrorResponse(field="timezone", message="Timezone is required", code="MISSING_REQUIRED_FIELD"))

        # Location-specific validation
        lm = getattr(event, 'location_mode', None)

        # I3: Validate location_mode is a known value
        if lm is not None and lm not in (LocationMode.venue, LocationMode.online, LocationMode.recorded, LocationMode.hybrid):
            errors.append(FieldErrorResponse(field="location_mode", message=f"Invalid location_mode: {lm}", code="INVALID_FIELD_VALUE"))

        if lm in (LocationMode.venue, LocationMode.hybrid):
            venue_fields = [
                ('venue_name', 'Venue name is required for venue events'),
                ('venue_address', 'Venue address is required for venue events'),
                ('venue_city', 'Venue city is required for venue events'),
                ('venue_country', 'Venue country is required for venue events'),
            ]
            for field, msg in venue_fields:
                if not getattr(event, field, None):
                    errors.append(FieldErrorResponse(field=field, message=msg, code="MISSING_REQUIRED_FIELD"))

        if lm in (LocationMode.online, LocationMode.hybrid):
            if not getattr(event, 'online_event_url', None):
                errors.append(FieldErrorResponse(field="online_event_url", message="Online event URL is required for online events", code="MISSING_REQUIRED_FIELD"))

        if lm == LocationMode.recorded:
            if not getattr(event, 'recorded_event_url', None):
                errors.append(FieldErrorResponse(field="recorded_event_url", message="Recorded event URL is required for recorded events", code="MISSING_REQUIRED_FIELD"))

        return errors

    def _validate_schedule(self, event, days: list) -> list[FieldErrorResponse]:
        """Validate schedule section - day count and day-level requirements."""
        errors = []

        if len(days) == 0:
            errors.append(FieldErrorResponse(field="days", message="At least 1 event day is required", code="MISSING_REQUIRED_FIELD"))
            return errors

        for day in days:
            if not getattr(day, 'date', None):
                errors.append(FieldErrorResponse(field=f"day_{day.day_index}.date", message=f"Day {day.day_index}: date is required", code="MISSING_REQUIRED_FIELD"))

            # start_time required for ticketed events
            if getattr(event, 'event_access_type', None) == EventAccessType.ticketed:
                if not getattr(day, 'start_time', None):
                    errors.append(FieldErrorResponse(field=f"day_{day.day_index}.start_time", message=f"Day {day.day_index}: start time is required for ticketed events", code="MISSING_REQUIRED_FIELD"))

        return errors

    def _validate_tickets(self, event, ticket_types: list, allocations: list) -> list[FieldErrorResponse]:
        """Validate tickets section - requires ticket types and allocations for ticketed events."""
        errors = []

        if getattr(event, 'event_access_type', None) == EventAccessType.open:
            return errors

        if len(ticket_types) == 0:
            errors.append(FieldErrorResponse(field="ticket_types", message="At least 1 ticket type is required", code="MISSING_REQUIRED_FIELD"))

        if len(allocations) == 0:
            errors.append(FieldErrorResponse(field="allocations", message="At least 1 ticket allocation is required", code="MISSING_REQUIRED_FIELD"))
            return errors

        for alloc in allocations:
            if getattr(alloc, 'quantity', 0) <= 0:
                errors.append(FieldErrorResponse(field=f"allocation_{getattr(alloc, 'id', 'unknown')}.quantity", message="Allocation quantity must be greater than 0", code="INVALID_FIELD_VALUE"))

        return errors

    async def validate_for_publish(self, owner_user_id: UUID, event_id: UUID):
        """Run all validations and return structured response for publish readiness."""
        event = await self.repository.get_by_id_for_owner(event_id, owner_user_id)
        if not event:
            raise EventNotFound

        days = await self.repository.list_event_days(event_id)
        ticket_types = await self.repository.list_ticket_types(event_id)
        allocations = await self.repository.list_allocations(event_id)

        basic_info_errors = self._validate_basic_info(event)
        schedule_errors = self._validate_schedule(event, days)
        ticket_errors = self._validate_tickets(event, ticket_types, allocations)

        basic_info_complete = len(basic_info_errors) == 0
        schedule_complete = len(schedule_errors) == 0
        tickets_complete = len(ticket_errors) == 0

        # Build blocking issues
        blocking_issues = []
        if not basic_info_complete:
            blocking_issues.append("Complete basic_info section")
        if not schedule_complete:
            blocking_issues.append("Complete schedule section")
        if not tickets_complete:
            blocking_issues.append("Complete tickets section")

        # Determine redirect hint (first incomplete section with errors)
        redirect_hint = None
        if not basic_info_complete and basic_info_errors:
            redirect_hint = {"section": "basic_info", "fields": [e.field for e in basic_info_errors]}
        elif not schedule_complete and schedule_errors:
            redirect_hint = {"section": "schedule", "fields": [e.field for e in schedule_errors]}
        elif not tickets_complete and ticket_errors:
            redirect_hint = {"section": "tickets", "fields": [e.field for e in ticket_errors]}

        return {
            "can_publish": basic_info_complete and schedule_complete and tickets_complete,
            "event_id": event_id,
            "published_at": None,
            "sections": {
                "basic_info": {"complete": basic_info_complete, "errors": basic_info_errors},
                "schedule": {"complete": schedule_complete, "errors": schedule_errors},
                "tickets": {"complete": tickets_complete, "errors": ticket_errors},
            },
            "blocking_issues": blocking_issues,
            "redirect_hint": redirect_hint,
        }

    async def publish_event(self, owner_user_id: UUID, event_id: UUID):
        """Publish event if all validations pass. Returns updated event."""
        validation = await self.validate_for_publish(owner_user_id, event_id)

        if not validation["can_publish"]:
            from .exceptions import CannotPublishEvent
            # Convert UUID objects to strings for JSON serialization
            validation_serializable = _serialize_for_json(validation)
            raise CannotPublishEvent(validation_serializable)

        event = await self.repository.get_by_id_for_owner(event_id, owner_user_id)
        event.status = "published"
        event.is_published = True
        event.published_at = datetime.utcnow()
        await self.repository.session.flush()
        await self.repository.session.refresh(event)
        return event

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
