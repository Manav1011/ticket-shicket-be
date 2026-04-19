from datetime import datetime
from uuid import UUID

from utils.schema import BaseResponse, CamelCaseModel


class OrganizerPageResponse(CamelCaseModel):
    id: UUID
    owner_user_id: UUID
    name: str
    slug: str
    bio: str | None = None
    logo_url: str | None = None
    cover_image_url: str | None = None
    website_url: str | None = None
    instagram_url: str | None = None
    facebook_url: str | None = None
    youtube_url: str | None = None
    visibility: str
    status: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class OrganizerPageListResponse(BaseResponse[OrganizerPageResponse]):
    pass


# --- B2B Ticket & Allocation Response Schemas ---


class MyB2BTicketItem(CamelCaseModel):
    event_day_id: UUID
    count: int


class MyB2BTicketsResponse(CamelCaseModel):
    event_id: UUID
    holder_id: UUID
    tickets: list[MyB2BTicketItem]
    total: int


class MyB2BAllocationItem(CamelCaseModel):
    allocation_id: UUID
    event_day_id: UUID
    direction: str  # "received" | "transferred"
    from_holder_id: UUID | None
    to_holder_id: UUID
    ticket_count: int
    status: str
    source: str  # from metadata_: "b2b_free" or "b2b_paid"
    created_at: datetime


class B2BTransferResponse(CamelCaseModel):
    transfer_id: UUID
    status: str  # "completed" | "not_implemented"
    ticket_count: int
    reseller_id: UUID
    mode: str  # "free" | "paid"
    message: str | None = None  # only present when mode="paid" and not_implemented
