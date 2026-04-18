from uuid import UUID

from utils.schema import CamelCaseModel


class BaseUserResponse(CamelCaseModel):
    id: UUID
    first_name: str
    last_name: str


class UserLookupResponse(CamelCaseModel):
    user_id: UUID
    email: str | None = None
    phone: str | None = None
    first_name: str | None = None
    last_name: str | None = None
