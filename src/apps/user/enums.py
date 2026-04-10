from enum import Enum


class UserStatus(str, Enum):
    active = "active"
    disabled = "disabled"
    deleted = "deleted"
