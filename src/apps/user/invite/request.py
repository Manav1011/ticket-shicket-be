from uuid import UUID
from utils.schema import CamelCaseModel


class ResellerMetadata(CamelCaseModel):
    event_id: UUID | None = None  # Optional - backend will set this
    permissions: list[str] = []


class CreateInviteRequest(CamelCaseModel):
    lookup_type: str  # "email" or "phone"
    lookup_value: str
    metadata: ResellerMetadata | None = None