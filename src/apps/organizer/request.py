import re

from pydantic import field_validator, Field

from utils.schema import CamelCaseModel

from apps.organizer.enums import OrganizerVisibility

# URL regex pattern - allows http/https URLs
URL_REGEX = r"^https?://[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}(/.*)?$"


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

    @field_validator('website_url', 'instagram_url', 'facebook_url', 'youtube_url', 'logo_url', 'cover_image_url')
    @classmethod
    def validate_url(cls, v):
        if v is not None and not re.match(URL_REGEX, v):
            raise ValueError('Invalid URL format. Must start with http:// or https://')
        return v


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

    @field_validator('website_url', 'instagram_url', 'facebook_url', 'youtube_url', 'logo_url', 'cover_image_url')
    @classmethod
    def validate_url(cls, v):
        if v is not None and not re.match(URL_REGEX, v):
            raise ValueError('Invalid URL format. Must start with http:// or https://')
        return v


class CreateB2BRequestBody(CamelCaseModel):
    event_id: str
    event_day_id: str
    quantity: int = Field(gt=0)


class ConfirmB2BPaymentBody(CamelCaseModel):
    pass
