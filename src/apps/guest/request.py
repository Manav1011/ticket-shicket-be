import uuid
import re

from pydantic import field_validator

from utils.schema import CamelCaseModel

from constants.regex import EMAIL_REGEX, PHONE_REGEX
from utils.validation import strong_password


class GuestLoginRequest(CamelCaseModel):
    """Empty request - device_id extracted from header."""


class GuestConvertRequest(CamelCaseModel):
    """Request body for converting guest to user at checkout."""
    email: str
    phone: str
    password: str
    first_name: str
    last_name: str

    @field_validator('email')
    @classmethod
    def validate_email(cls, v):
        if not re.match(EMAIL_REGEX, v):
            raise ValueError('Invalid email format')
        return v

    @field_validator('phone')
    @classmethod
    def validate_phone(cls, v):
        if not re.match(PHONE_REGEX, v):
            raise ValueError('Invalid phone format')
        return v

    @field_validator('password')
    @classmethod
    def validate_password(cls, v):
        if not strong_password(v):
            raise ValueError('Password must be 8+ chars with upper, lower, digit, special char')
        return v

    @field_validator('first_name', 'last_name')
    @classmethod
    def validate_name(cls, v):
        if not v or len(v.strip()) < 2:
            raise ValueError('Name must be at least 2 characters')
        return v.strip()
