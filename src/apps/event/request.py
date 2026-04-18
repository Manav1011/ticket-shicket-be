from datetime import date as Date, datetime
from uuid import UUID

from apps.event.enums import EventAccessType, LocationMode
from utils.schema import CamelCaseModel


class CreateDraftEventRequest(CamelCaseModel):
    organizer_page_id: UUID
    title: str
    event_access_type: EventAccessType


class UpdateEventBasicInfoRequest(CamelCaseModel):
    title: str | None = None
    description: str | None = None
    event_type: str | None = None
    event_access_type: EventAccessType | None = None
    location_mode: LocationMode | None = None
    timezone: str | None = None
    venue_name: str | None = None
    venue_address: str | None = None
    venue_city: str | None = None
    venue_state: str | None = None
    venue_country: str | None = None
    venue_latitude: float | None = None
    venue_longitude: float | None = None
    venue_google_place_id: str | None = None
    online_event_url: str | None = None
    recorded_event_url: str | None = None


class CreateEventDayRequest(CamelCaseModel):
    date: Date
    start_time: datetime | None = None
    end_time: datetime | None = None


class UpdateEventDayRequest(CamelCaseModel):
    day_index: int | None = None
    date: Date | None = None
    start_time: datetime | None = None
    end_time: datetime | None = None


class UpdateMediaAssetMetadataRequest(CamelCaseModel):
    title: str | None = None
    caption: str | None = None
    alt_text: str | None = None
    sort_order: int | None = None
    is_primary: bool | None = None


class UpdateShowTicketsRequest(CamelCaseModel):
    show_tickets: bool | None = None


class CreateResellerInviteRequest(CamelCaseModel):
    user_ids: list[UUID]  # Required: list of user IDs to invite
    permissions: list[str] = []  # Optional permissions for each invite

    def model_post_init(self, __pydantic_self__) -> None:
        if len(self.user_ids) == 0:
            raise ValueError("At least one user_id is required")
