import uuid
from utils.schema import CamelCaseModel


class GuestLoginRequest(CamelCaseModel):
    """Empty request - device_id extracted from header."""


class GuestConvertRequest(CamelCaseModel):
    """Request body for converting guest to user at checkout."""
    email: str
    phone: str
    password: str
    first_name: str
    last_name: str
