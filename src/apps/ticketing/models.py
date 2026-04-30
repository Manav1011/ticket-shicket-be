import uuid
from datetime import datetime, timezone

from sqlalchemy import CheckConstraint, DateTime, Enum, ForeignKey, Integer, Numeric, String, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from apps.ticketing.enums import TicketCategory, TicketStatus
from db.base import Base, TimeStampMixin, UUIDPrimaryKeyMixin


class TicketTypeModel(Base, UUIDPrimaryKeyMixin, TimeStampMixin):
    __tablename__ = "ticket_types"

    event_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("events.id"), index=True, nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    category: Mapped[str] = mapped_column(Enum(TicketCategory), nullable=False)
    price: Mapped[float] = mapped_column(Numeric, nullable=False)
    currency: Mapped[str] = mapped_column(
        String(8), default="INR", server_default=text("'INR'"), nullable=False
    )


class DayTicketAllocationModel(Base, UUIDPrimaryKeyMixin, TimeStampMixin):
    __tablename__ = "day_ticket_allocations"
    __table_args__ = (
        CheckConstraint("quantity > 0", name="ck_day_ticket_allocations_quantity_positive"),
        UniqueConstraint("event_day_id", "ticket_type_id", name="uq_day_ticket_allocations_event_day_ticket_type"),
    )

    event_day_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("event_days.id"), index=True, nullable=False
    )
    ticket_type_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("ticket_types.id"), index=True, nullable=False
    )
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)


class TicketModel(Base, UUIDPrimaryKeyMixin, TimeStampMixin):
    __tablename__ = "tickets"
    __table_args__ = (
        UniqueConstraint("event_day_id", "ticket_index", name="uq_tickets_event_day_ticket_index"),
    )

    event_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("events.id"), index=True, nullable=False
    )
    event_day_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("event_days.id"), index=True, nullable=False
    )
    ticket_type_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("ticket_types.id"), index=True, nullable=False
    )

    ticket_index: Mapped[int] = mapped_column(Integer, nullable=False)
    seat_label: Mapped[str | None] = mapped_column(nullable=True)
    seat_metadata: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    owner_holder_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("ticket_holders.id", ondelete="SET NULL"), nullable=True, index=True
    )
    status: Mapped[str] = mapped_column(
        Enum(TicketStatus), default=TicketStatus.active, server_default=text("'active'"), nullable=False
    )
    # All locks use lock_reference_type='order' and lock_reference_id=order_id
    # (every allocation is created via an order, even free transfers create a $0 order)
    lock_reference_type: Mapped[str | None] = mapped_column(String(32), nullable=True)
    lock_reference_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    lock_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    claim_link_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("claim_links.id", ondelete="SET NULL"), nullable=True, index=True
    )
