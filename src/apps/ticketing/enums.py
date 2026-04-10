from enum import Enum


class TicketCategory(str, Enum):
    online = "online"
    b2b = "b2b"
    public = "public"
    vip = "vip"


class TicketStatus(str, Enum):
    active = "active"
    cancelled = "cancelled"
    used = "used"


class AllocationSourceType(str, Enum):
    pool = "POOL"
    user = "USER"


class AllocationStatus(str, Enum):
    pending = "pending"
    completed = "completed"
    failed = "failed"


class OrderType(str, Enum):
    purchase = "PURCHASE"
    transfer = "TRANSFER"


class OrderStatus(str, Enum):
    pending = "pending"
    paid = "paid"
    failed = "failed"
    expired = "expired"


class CouponType(str, Enum):
    flat = "FLAT"
    percentage = "PERCENTAGE"
