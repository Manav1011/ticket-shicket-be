from enum import Enum


class AllocationStatus(str, Enum):
    pending = "pending"
    processing = "processing"
    completed = "completed"
    failed = "failed"


class TicketHolderStatus(str, Enum):
    active = "active"
    deleted = "deleted"


class AllocationType(str, Enum):
    b2b = "b2b"
    purchase = "purchase"
    transfer = "transfer"
    refund = "refund"
