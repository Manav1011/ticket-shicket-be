from enum import Enum


class InviteStatus(str, Enum):
    pending = "pending"
    accepted = "accepted"
    declined = "declined"
    cancelled = "cancelled"


class InviteType(str, Enum):
    reseller = "reseller"