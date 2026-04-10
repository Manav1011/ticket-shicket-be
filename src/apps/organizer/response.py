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
