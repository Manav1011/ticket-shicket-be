from datetime import date as Date, datetime
from uuid import UUID

from utils.schema import CamelCaseModel


class CreateDraftEventRequest(CamelCaseModel):
    organizer_page_id: UUID


class UpdateEventBasicInfoRequest(CamelCaseModel):
    title: str | None = None
    description: str | None = None
    event_type: str | None = None
    event_access_type: str | None = None
    location_mode: str | None = None
    timezone: str | None = None


class CreateEventDayRequest(CamelCaseModel):
    day_index: int
    date: Date
    start_time: datetime | None = None
    end_time: datetime | None = None


class UpdateEventDayRequest(CamelCaseModel):
    day_index: int | None = None
    date: Date | None = None
    start_time: datetime | None = None
    end_time: datetime | None = None
