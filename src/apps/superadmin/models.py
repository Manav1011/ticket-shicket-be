import uuid

from sqlalchemy import Enum, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from db.base import Base, TimeStampMixin, UUIDPrimaryKeyMixin
from .enums import B2BRequestStatus


class SuperAdminModel(Base, UUIDPrimaryKeyMixin, TimeStampMixin):
    """
    Links a User account to super admin privileges.
    """
    __tablename__ = "super_admins"

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), unique=True, index=True, nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)


class B2BRequestModel(Base, UUIDPrimaryKeyMixin, TimeStampMixin):
    """
    B2B ticket request from an organizer.
    Serves as both request queue and fulfillment record.

    Organizer is derived from event.organizer_page_id — not stored redundantly.
    User is from auth token — requesting_user_id kept for audit traceability only.
    """
    __tablename__ = "b2b_requests"

    # Who submitted this request (user_id from auth token, stored for audit)
    requesting_user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )

    # Which event/day/ticket type
    event_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("events.id", ondelete="CASCADE"), index=True, nullable=False
    )
    event_day_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("event_days.id", ondelete="CASCADE"), nullable=False
    )
    ticket_type_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("ticket_types.id", ondelete="CASCADE"), nullable=False
    )

    # How many tickets
    quantity: Mapped[int] = mapped_column(nullable=False)

    # Request status
    status: Mapped[str] = mapped_column(
        Enum(B2BRequestStatus),
        default=B2BRequestStatus.pending,
        nullable=False,
        index=True,
    )

    # Admin response
    reviewed_by_admin_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("super_admins.id", ondelete="SET NULL"), nullable=True
    )
    admin_notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Fulfillment links (filled when allocation is created)
    allocation_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("allocations.id", ondelete="SET NULL"), nullable=True
    )
    order_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("orders.id", ondelete="SET NULL"), nullable=True
    )

    # Metadata for audit
    metadata_: Mapped[dict] = mapped_column(
        JSONB, default=dict, nullable=False
    )
