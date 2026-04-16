from datetime import datetime
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
