from datetime import date as Date, datetime
from enum import Enum
from typing import Annotated
from uuid import UUID

from pydantic import Field, field_validator, ConfigDict

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


class SplitClaimRequest(CamelCaseModel):
    to_email: str
    ticket_count: int


class EventSortField(str, Enum):
    created_at = "created_at"
    start_date = "start_date"
    title = "title"
    status = "status"


class EventFilterParams(CamelCaseModel):
    model_config = ConfigDict(validate_default=True)

    status: str | None = None
    event_access_type: str | None = None
    date_from: Date | None = None
    date_to: Date | None = None
    search: str | None = None
    sort_by: EventSortField = EventSortField.created_at
    order: str = "desc"
    limit: int = Field(default=20, ge=1, le=100)
    offset: int = Field(default=0, ge=0)

    @field_validator("order")
    @classmethod
    def validate_order(cls, v: str) -> str:
        if v not in ("asc", "desc"):
            raise ValueError("order must be 'asc' or 'desc'")
        return v

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str | None) -> str | None:
        if v is not None and v not in ("draft", "published", "archived"):
            raise ValueError("status must be draft, published, or archived")
        return v

    @field_validator("event_access_type")
    @classmethod
    def validate_access_type(cls, v: str | None) -> str | None:
        if v is not None and v not in ("open", "ticketed"):
            raise ValueError("event_access_type must be open or ticketed")
        return v


class PreviewOrderRequest(CamelCaseModel):
    event_id: UUID
    event_day_id: UUID
    ticket_type_id: UUID
    quantity: int = Field(ge=1)
    coupon_code: str | None = None


class CreateOrderRequest(CamelCaseModel):
    event_id: UUID
    event_day_id: UUID
    ticket_type_id: UUID
    quantity: int = Field(ge=1)
    coupon_code: str | None = None
