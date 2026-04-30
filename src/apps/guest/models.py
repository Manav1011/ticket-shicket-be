from __future__ import annotations
import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from db.base import Base, TimeStampMixin, UUIDPrimaryKeyMixin


class GuestModel(Base, UUIDPrimaryKeyMixin, TimeStampMixin):
    """
    Guest user model for anonymous browsing.
    Identified by device_id (UUID generated on first login).
    Converted to User at checkout.
    """
    __tablename__ = "guests"

    device_id: Mapped[uuid.UUID] = mapped_column(index=True, unique=True)
    # User fields captured at conversion
    email: Mapped[str | None] = mapped_column(String(320), index=True, nullable=True)
    phone: Mapped[str | None] = mapped_column(index=True, nullable=True)
    # Conversion tracking
    is_converted: Mapped[bool] = mapped_column(default=False, nullable=False)
    converted_user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id"), nullable=True
    )

    @classmethod
    def create(cls, device_id: uuid.UUID) -> Self:
        return cls(id=uuid.uuid4(), device_id=device_id)


class GuestRefreshTokenModel(Base, UUIDPrimaryKeyMixin, TimeStampMixin):
    """
    Refresh tokens for guest users.
    Token hash is stored (never plain text).
    """
    __tablename__ = "guest_refresh_tokens"

    token_hash: Mapped[str] = mapped_column(index=True, unique=True)
    guest_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("guests.id"), index=True
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked: Mapped[bool] = mapped_column(default=False, nullable=False)

    @property
    def is_expired(self) -> bool:
        return datetime.now(timezone.utc) > self.expires_at

    @property
    def is_active(self) -> bool:
        return not self.revoked and not self.is_expired
