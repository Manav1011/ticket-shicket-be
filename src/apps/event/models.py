import uuid
from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, Enum, ForeignKey, Integer, Numeric, String, Text, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from apps.event.enums import EventAccessType, EventStatus, EventType, LocationMode, ScanStatus
from db.base import Base, TimeStampMixin, UUIDPrimaryKeyMixin


class EventModel(Base, UUIDPrimaryKeyMixin, TimeStampMixin):
    __tablename__ = "events"

    organizer_page_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizer_pages.id"), index=True, nullable=False
    )
    created_by_user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id"), index=True, nullable=False
    )

    title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    slug: Mapped[str | None] = mapped_column(String(255), unique=True, index=True, nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    event_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    status: Mapped[str] = mapped_column(
        Enum(EventStatus), default=EventStatus.draft, server_default=text("'draft'"), nullable=False
    )
    event_access_type: Mapped[str] = mapped_column(
        Enum(EventAccessType), default=EventAccessType.ticketed, server_default=text("'ticketed'"), nullable=False
    )
    setup_status: Mapped[dict] = mapped_column(
        JSONB, default=dict, server_default=text("'{}'::jsonb"), nullable=False
    )

    location_mode: Mapped[str | None] = mapped_column(Enum(LocationMode), nullable=True)

    timezone: Mapped[str | None] = mapped_column(String(64), nullable=True)
    start_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    end_date: Mapped[date | None] = mapped_column(Date, nullable=True)

    venue_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    venue_address: Mapped[str | None] = mapped_column(Text, nullable=True)
    venue_city: Mapped[str | None] = mapped_column(String(255), nullable=True)
    venue_state: Mapped[str | None] = mapped_column(String(255), nullable=True)
    venue_country: Mapped[str | None] = mapped_column(String(255), nullable=True)
    venue_latitude: Mapped[float | None] = mapped_column(Numeric, nullable=True)
    venue_longitude: Mapped[float | None] = mapped_column(Numeric, nullable=True)
    venue_google_place_id: Mapped[str | None] = mapped_column(String(255), nullable=True)

    online_event_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    recorded_event_url: Mapped[str | None] = mapped_column(Text, nullable=True)

    published_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    is_published: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default=text("false"), nullable=False
    )


class EventDayModel(Base, UUIDPrimaryKeyMixin, TimeStampMixin):
    __tablename__ = "event_days"
    __table_args__ = (UniqueConstraint("event_id", "day_index", name="uq_event_days_event_id_day_index"),)

    event_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("events.id"), index=True, nullable=False
    )
    day_index: Mapped[int] = mapped_column(Integer, nullable=False)
    date: Mapped[date] = mapped_column(Date, nullable=False)
    start_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    end_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    scan_status: Mapped[str] = mapped_column(
        Enum(ScanStatus), default=ScanStatus.not_started, server_default=text("'not_started'"), nullable=False
    )
    scan_started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    scan_paused_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    scan_ended_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    next_ticket_index: Mapped[int] = mapped_column(
        Integer, default=1, server_default=text("1"), nullable=False
    )


class ScanStatusHistoryModel(Base, UUIDPrimaryKeyMixin, TimeStampMixin):
    __tablename__ = "scan_status_history"

    event_day_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("event_days.id"), index=True, nullable=False
    )
    changed_by_user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id"), index=True, nullable=False
    )
    previous_status: Mapped[str] = mapped_column(String(32), nullable=False)
    new_status: Mapped[str] = mapped_column(String(32), nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
