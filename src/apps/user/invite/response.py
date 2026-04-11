from datetime import datetime
from uuid import UUID
from utils.schema import CamelCaseModel


class InviteResponse(CamelCaseModel):
    id: UUID
    target_user_id: UUID
    created_by_id: UUID
    status: str
    invite_type: str
    meta: dict
    expires_at: datetime | None = None
    created_at: datetime
    updated_at: datetime