from enum import Enum


class GuestStatus(str, Enum):
    active = "active"
    converted = "converted"
