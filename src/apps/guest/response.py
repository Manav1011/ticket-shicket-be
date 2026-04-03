import uuid
from utils.schema import CamelCaseModel


class GuestLoginResponse(CamelCaseModel):
    guest_id: uuid.UUID
    device_id: uuid.UUID
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class GuestResponse(CamelCaseModel):
    id: uuid.UUID
    device_id: uuid.UUID
    is_converted: bool
    converted_user_id: uuid.UUID | None = None
