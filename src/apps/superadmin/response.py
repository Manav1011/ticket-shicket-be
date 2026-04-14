from pydantic import BaseModel, Field


class B2BRequestResponse(BaseModel):
    id: str
    requesting_organizer_id: str
    requesting_user_id: str
    event_id: str
    event_day_id: str
    ticket_type_id: str
    quantity: int
    recipient_phone: str | None
    recipient_email: str | None
    status: str
    reviewed_by_admin_id: str | None
    admin_notes: str | None
    allocation_id: str | None
    order_id: str | None
    metadata: dict = Field(validation_alias="metadata_", serialization_alias="metadata")
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True
