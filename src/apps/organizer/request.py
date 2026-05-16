import re
from uuid import UUID

from pydantic import field_validator, model_validator, Field

from utils.schema import CamelCaseModel

from apps.organizer.enums import OrganizerVisibility
from apps.allocation.enums import TransferMode
from constants.regex import PHONE_REGEX

# URL regex pattern - allows http/https URLs
URL_REGEX = r"^https?://[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}(/.*)?$"


class CreateOrganizerPageRequest(CamelCaseModel):
    name: str
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


class CreateB2BTransferRequest(CamelCaseModel):
    reseller_id: UUID
    quantity: int = Field(gt=0)
    event_day_id: UUID | None = None  # optional if event has only 1 day
    mode: TransferMode = TransferMode.FREE
    price: float | None = None  # Flat order price in rupees. Required when mode=PAID.

    @model_validator(mode='after')
    def validate_paid_mode_price(self):
        if self.mode == TransferMode.PAID:
            if self.price is None:
                raise ValueError('price is required when mode=PAID')
            if self.price <= 0:
                raise ValueError('price must be greater than 0 when mode=PAID')
        return self


class CreateCustomerTransferRequest(CamelCaseModel):
    phone: str | None = None
    email: str | None = None
    quantity: int = Field(gt=0)
    event_day_id: UUID  # required for customer transfers (claim link is per-day)
    mode: TransferMode = TransferMode.FREE
    price: float | None = None  # Flat order price in rupees. Required when mode=PAID.

    @model_validator(mode='after')
    def must_have_phone_or_email(self):
        if not self.phone and not self.email:
            raise ValueError('Either phone or email must be provided')
        return self

    @model_validator(mode='after')
    def validate_paid_mode_price(self):
        if self.mode == TransferMode.PAID:
            if self.price is None:
                raise ValueError('price is required when mode=PAID')
            if self.price <= 0:
                raise ValueError('price must be greater than 0 when mode=PAID')
        return self

    @field_validator('phone')
    @classmethod
    def validate_phone(cls, v):
        if v and not re.match(PHONE_REGEX, v):
            raise ValueError('Invalid phone format. Must be a valid Indian mobile number.')
        return v
