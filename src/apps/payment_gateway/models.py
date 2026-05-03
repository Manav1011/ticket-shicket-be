"""Payment gateway event audit log model."""
import uuid
from sqlalchemy import (
    ForeignKey,
    Index,
    String,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from db.base import Base, TimeStampMixin, UUIDPrimaryKeyMixin


class PaymentGatewayEventModel(Base, UUIDPrimaryKeyMixin, TimeStampMixin):
    """
    Append-only audit log for all payment gateway events.
    Unique constraint on (order_id, event_type, gateway_event_id) prevents duplicate processing.
    Unique constraint on gateway_payment_id prevents duplicate payment processing.
    """
    __tablename__ = "payment_gateway_events"
    __table_args__ = (
        UniqueConstraint(
            "order_id", "event_type", "gateway_event_id",
            name="uq_payment_gateway_events_dedup",
        ),
        UniqueConstraint(
            "gateway_payment_id",
            name="uq_payment_gateway_events_payment_id",
        ),
        Index("ix_payment_gateway_events_order_id", "order_id"),
        Index("ix_payment_gateway_events_gateway_event_id", "gateway_event_id"),
        Index("ix_payment_gateway_events_gateway_payment_id", "gateway_payment_id"),
    )

    order_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("orders.id", ondelete="CASCADE"), nullable=False, index=True
    )
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    gateway_event_id: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    payload: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    gateway_payment_id: Mapped[str | None] = mapped_column(
        String(128), nullable=True, unique=True, index=True
    )
