from enum import Enum


class B2BRequestStatus(str, Enum):
    pending = "pending"           # Awaiting super admin review
    approved_free = "approved_free"   # Approved, allocation created (free transfer)
    approved_paid = "approved_paid"    # Approved, pending payment
    rejected = "rejected"         # Denied by super admin
    expired = "expired"           # Order payment timeout
