from datetime import date, datetime
from uuid import UUID

from utils.schema import BaseResponse, CamelCaseModel


class EventSummaryResponse(CamelCaseModel):
    id: UUID
    organizer_page_id: UUID
    title: str | None = None
    status: str
    event_access_type: str
    setup_status: dict
    created_at: datetime


class EventResponse(CamelCaseModel):
    id: UUID
    organizer_page_id: UUID
    created_by_user_id: UUID
    title: str | None = None
    slug: str | None = None
    description: str | None = None
    event_type: str | None = None
    status: str
    event_access_type: str
    setup_status: dict
    location_mode: str | None = None
    timezone: str | None = None
    start_date: date | None = None
    end_date: date | None = None
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
    published_at: datetime | None = None
    is_published: bool
    show_tickets: bool = False
    interested_counter: int = 0
    media_assets: list["MediaAssetResponse"] = []


class EventInterestResponse(CamelCaseModel):
    created: bool
    interested_counter: int


class EventDayResponse(CamelCaseModel):
    id: UUID
    event_id: UUID
    day_index: int
    date: date
    start_time: datetime | None = None
    end_time: datetime | None = None
    scan_status: str
    scan_started_at: datetime | None = None
    scan_paused_at: datetime | None = None
    scan_ended_at: datetime | None = None
    next_ticket_index: int


class EventReadinessResponse(CamelCaseModel):
    completed_sections: list[str]
    missing_sections: list[str]
    blocking_issues: list[str]


class ScanStatusHistoryResponse(CamelCaseModel):
    id: UUID
    event_day_id: UUID
    changed_by_user_id: UUID
    previous_status: str
    new_status: str
    changed_at: datetime
    notes: str | None = None


class FieldErrorResponse(CamelCaseModel):
    field: str
    message: str
    code: str


class SectionValidationResult(CamelCaseModel):
    complete: bool
    errors: list[FieldErrorResponse]


class PublishValidationResponse(CamelCaseModel):
    can_publish: bool
    event_id: UUID
    published_at: datetime | None = None
    sections: dict[str, SectionValidationResult]
    blocking_issues: list[str]
    redirect_hint: dict | None = None


class MediaAssetResponse(CamelCaseModel):
    id: UUID
    event_id: UUID
    asset_type: str
    storage_key: str
    public_url: str
    title: str | None = None
    caption: str | None = None
    alt_text: str | None = None
    sort_order: int
    is_primary: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class EventDayPublicResponse(CamelCaseModel):
    id: UUID
    day_index: int
    date: date
    start_time: datetime | None = None
    end_time: datetime | None = None
    scan_status: str


class MediaAssetPublicResponse(CamelCaseModel):
    id: UUID
    asset_type: str
    public_url: str
    title: str | None = None
    caption: str | None = None
    alt_text: str | None = None
    sort_order: int
    is_primary: bool


class TicketTypePublicResponse(CamelCaseModel):
    id: UUID
    name: str | None = None
    description: str | None = None
    price: str = "0.00"
    currency: str = "USD"


class EventDetailResponse(CamelCaseModel):
    id: UUID
    title: str | None = None
    slug: str | None = None
    description: str | None = None
    event_type: str | None = None
    status: str
    event_access_type: str
    location_mode: str | None = None
    timezone: str | None = None
    start_date: date | None = None
    end_date: date | None = None
    venue_name: str | None = None
    venue_address: str | None = None
    venue_city: str | None = None
    venue_state: str | None = None
    venue_country: str | None = None
    venue_latitude: float | None = None
    venue_longitude: float | None = None
    online_event_url: str | None = None
    recorded_event_url: str | None = None
    published_at: datetime | None = None
    is_published: bool
    interested_counter: int = 0
    days: list[EventDayPublicResponse] = []
    media_assets: list[MediaAssetPublicResponse] = []
    ticket_types: list[TicketTypePublicResponse] = []

    class Config:
        from_attributes = True


class EventEnvelopeResponse(BaseResponse[EventResponse]):
    pass


class ResellerResponse(CamelCaseModel):
    id: UUID
    user_id: UUID
    event_id: UUID
    invited_by_id: UUID
    permissions: dict | list[str]


class ResellerInviteResponse(CamelCaseModel):
    id: UUID
    target_user_id: UUID
    created_by_id: UUID
    status: str
    invite_type: str
    meta: dict
    created_at: datetime
    accepted_at: datetime | None = None
    created_at: datetime


class PaginationMeta(CamelCaseModel):
    total: int
    limit: int
    offset: int
    has_more: bool


class PaginatedEventResponse(CamelCaseModel):
    events: list[EventResponse]
    pagination: PaginationMeta


class ClaimRedemptionResponse(CamelCaseModel):
    ticket_count: int
    jwt: str


class SplitClaimResponse(CamelCaseModel):
    status: str
    tickets_transferred: int
    remaining_ticket_count: int
    new_jwt: str
    message: str


class CouponAppliedResponse(CamelCaseModel):
    code: str
    type: str
    value: float
    max_discount: float | None


class PreviewOrderResponse(CamelCaseModel):
    subtotal_amount: str
    discount_amount: str
    final_amount: str
    coupon_applied: CouponAppliedResponse | None = None


class CreateOrderResponse(CamelCaseModel):
    order_id: UUID
    razorpay_order_id: str | None
    razorpay_key_id: str | None
    amount: int
    currency: str
    subtotal_amount: str
    discount_amount: str
    final_amount: str
    status: str
    is_free: bool = False
    claim_token: str | None = None


class PollStatusResponse(CamelCaseModel):
    order_id: UUID
    status: str
    ticket_count: int
    jwt: str | None = None
    claim_token: str | None = None
    failure_reason: str | None = None
