from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, Field


class B2BRequestResponse(BaseModel):
    id: UUID
    requesting_user_id: UUID
    event_id: UUID
    event_day_id: UUID
    ticket_type_id: UUID
    quantity: int
    status: str
    reviewed_by_admin_id: UUID | None
    admin_notes: str | None
    allocation_id: UUID | None
    order_id: UUID | None
    metadata: dict = Field(validation_alias="metadata_", serialization_alias="metadata")
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class B2BRequestDetailResponse(BaseModel):
    id: UUID
    quantity: int
    status: str
    admin_notes: str | None
    created_at: datetime
    updated_at: datetime
    # Enriched fields
    event_name: str | None = None
    event_day_date: date | None = None
    ticket_type_name: str | None = None
    requesting_user_email: str | None = None

    class Config:
        from_attributes = True
