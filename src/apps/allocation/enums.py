from enum import Enum


class AllocationStatus(str, Enum):
    pending = "pending"
    processing = "processing"
    completed = "completed"
    failed = "failed"


class LockReferenceType(str, Enum):
    order = "order"
    allocation = "allocation"


class TicketHolderStatus(str, Enum):
    active = "active"
    deleted = "deleted"
