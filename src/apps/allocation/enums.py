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


class ClaimLinkStatus(str, Enum):
    active = "active"
    inactive = "inactive"


class GatewayType(str, Enum):
    RAZORPAY_ORDER = "razorpay_order"          # Checkout flow (online purchase, V2)
    RAZORPAY_PAYMENT_LINK = "razorpay_payment_link"  # Payment link flow (B2B)
    STRIPE_CHECKOUT = "stripe_checkout"       # Future


class TransferMode(str, Enum):
    FREE = "free"
    PAID = "paid"


class CouponType(str, Enum):
    FLAT = "FLAT"
    PERCENTAGE = "PERCENTAGE"
