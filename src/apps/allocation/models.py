import uuid
from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from db.base import Base, TimeStampMixin, UUIDPrimaryKeyMixin
from apps.ticketing.enums import OrderStatus, OrderType
from .enums import AllocationStatus, AllocationType, ClaimLinkStatus, GatewayType, TicketHolderStatus


class TicketHolderModel(Base, UUIDPrimaryKeyMixin, TimeStampMixin):
    __tablename__ = "ticket_holders"

    user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    phone: Mapped[str | None] = mapped_column(String(32), unique=True, nullable=True)
    email: Mapped[str | None] = mapped_column(String(255), unique=True, nullable=True)
    status: Mapped[str] = mapped_column(
        Enum(TicketHolderStatus),
        default=TicketHolderStatus.active,
        server_default=text("'active'"),
        nullable=False,
    )

    __table_args__ = (
        CheckConstraint(
            "phone IS NOT NULL OR email IS NOT NULL",
            name="ck_ticket_holders_has_contact",
        ),
    )


class ClaimLinkModel(Base, UUIDPrimaryKeyMixin, TimeStampMixin):
    __tablename__ = "claim_links"

    allocation_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("allocations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    token_hash: Mapped[str] = mapped_column(
        String(64), unique=True, nullable=False, index=True
    )
    event_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("events.id", ondelete="CASCADE"), nullable=False, index=True
    )
    event_day_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("event_days.id", ondelete="CASCADE"), nullable=False, index=True
    )
    from_holder_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("ticket_holders.id", ondelete="CASCADE"), nullable=True
    )
    to_holder_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("ticket_holders.id", ondelete="CASCADE"), nullable=False, index=True
    )
    status: Mapped[str] = mapped_column(
        Enum(ClaimLinkStatus),
        default=ClaimLinkStatus.active,
        server_default=text("'active'"),
        nullable=False,
        index=True,
    )
    jwt_jti: Mapped[str | None] = mapped_column(String(32), nullable=True)
    claimed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_by_holder_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("ticket_holders.id", ondelete="CASCADE"), nullable=False
    )


class RevokedScanTokenModel(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "revoked_scan_tokens"

    event_day_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("event_days.id", ondelete="CASCADE"), nullable=False, index=True
    )
    jti: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    reason: Mapped[str] = mapped_column(String(32), nullable=False)
    revoked_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )

    __table_args__ = (
        UniqueConstraint("event_day_id", "jti", name="uq_revoked_scan_tokens_event_day_jti"),
    )


class AllocationModel(Base, UUIDPrimaryKeyMixin, TimeStampMixin):
    __tablename__ = "allocations"
    __table_args__ = (
        UniqueConstraint("order_id", name="uq_allocations_order_id"),
    )

    event_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("events.id", ondelete="CASCADE"), index=True, nullable=False
    )
    from_holder_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("ticket_holders.id", ondelete="SET NULL"), nullable=True, index=True
    )
    to_holder_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("ticket_holders.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    order_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("orders.id", ondelete="RESTRICT"), nullable=False
    )  # Every allocation is created via an order (free transfers create $0 order)
    allocation_type: Mapped[str] = mapped_column(
        Enum(AllocationType), nullable=False
    )
    status: Mapped[str] = mapped_column(
        Enum(AllocationStatus),
        default=AllocationStatus.pending,
        server_default=text("'pending'"),
        nullable=False,
        index=True,
    )
    failure_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    ticket_count: Mapped[int] = mapped_column(
        Integer, default=0, server_default=text("0"), nullable=False
    )
    metadata_: Mapped[dict] = mapped_column(
        JSONB, default=dict, server_default=text("'{}'::jsonb"), nullable=False
    )


class AllocationTicketModel(Base, TimeStampMixin):
    __tablename__ = "allocation_tickets"

    allocation_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("allocations.id", ondelete="CASCADE"), primary_key=True
    )
    ticket_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("tickets.id", ondelete="CASCADE"), primary_key=True, index=True
    )


class AllocationEdgeModel(Base, UUIDPrimaryKeyMixin, TimeStampMixin):
    __tablename__ = "allocation_edges"
    __table_args__ = (
        UniqueConstraint(
            "event_id", "from_holder_id", "to_holder_id",
            name="uq_allocation_edges_event_from_to",
        ),
    )

    event_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("events.id", ondelete="CASCADE"), nullable=False, index=True
    )
    from_holder_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("ticket_holders.id", ondelete="CASCADE"), nullable=True
    )
    to_holder_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("ticket_holders.id", ondelete="CASCADE"), nullable=False, index=True
    )
    ticket_count: Mapped[int] = mapped_column(
        Integer, default=0, server_default=text("0"), nullable=False
    )


class OrderModel(Base, UUIDPrimaryKeyMixin, TimeStampMixin):
    """
    Order model — created for every allocation (PURCHASE or TRANSFER).
    Free transfers (B2B, U2U) create a $0 TRANSFER order.
    """
    __tablename__ = "orders"

    event_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("events.id", ondelete="CASCADE"), index=True, nullable=False
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    type: Mapped[str] = mapped_column(
        Enum(OrderType), nullable=False
    )  # PURCHASE / TRANSFER
    subtotal_amount: Mapped[float] = mapped_column(
        Numeric, nullable=False
    )
    discount_amount: Mapped[float] = mapped_column(
        Numeric, default=0, server_default=text("0"), nullable=False
    )
    final_amount: Mapped[float] = mapped_column(
        Numeric, nullable=False
    )
    status: Mapped[str] = mapped_column(
        Enum(OrderStatus),
        default=OrderStatus.pending,
        server_default=text("'pending'"),
        nullable=False,
    )
    lock_expires_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, index=True)
    gateway_type: Mapped[str | None] = mapped_column(Enum(GatewayType), nullable=True)
    gateway_order_id: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    gateway_response: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    short_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    gateway_payment_id: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    captured_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    expired_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    __table_args__ = (
        Index(
            "ix_orders_pending_lock_expiry",
            "status",
            "lock_expires_at",
            postgresql_where=text("status = 'pending'"),
        ),
    )
