from datetime import date, datetime
from uuid import UUID

from utils.schema import CamelCaseModel


class CreateDraftEventRequest(CamelCaseModel):
    organizer_page_id: UUID


class UpdateEventBasicInfoRequest(CamelCaseModel):
    title: str
    description: str | None = None
    event_type: str | None = None
    event_access_type: str
    location_mode: str
    timezone: str


class CreateEventDayRequest(CamelCaseModel):
    day_index: int
    date: date
    start_time: datetime | None = None
    end_time: datetime | None = None
