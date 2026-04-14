import uuid

from sqlalchemy import (
    CheckConstraint,
    Enum,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from db.base import Base, TimeStampMixin, UUIDPrimaryKeyMixin
from apps.ticketing.enums import OrderStatus, OrderType
from .enums import AllocationStatus, TicketHolderStatus


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


class AllocationModel(Base, UUIDPrimaryKeyMixin, TimeStampMixin):
    __tablename__ = "allocations"

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
