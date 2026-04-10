from utils.schema import CamelCaseModel

from apps.organizer.enums import OrganizerVisibility


class CreateOrganizerPageRequest(CamelCaseModel):
    name: str
    slug: str
    bio: str | None = None
    logo_url: str | None = None
    cover_image_url: str | None = None
    website_url: str | None = None
    instagram_url: str | None = None
    facebook_url: str | None = None
    youtube_url: str | None = None
    visibility: OrganizerVisibility = OrganizerVisibility.private


class UpdateOrganizerPageRequest(CamelCaseModel):
    name: str | None = None
    slug: str | None = None
    bio: str | None = None
    logo_url: str | None = None
    cover_image_url: str | None = None
    website_url: str | None = None
    instagram_url: str | None = None
    facebook_url: str | None = None
    youtube_url: str | None = None
    visibility: OrganizerVisibility | None = None
