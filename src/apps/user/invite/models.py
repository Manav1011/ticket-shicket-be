import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from db.base import Base, TimeStampMixin, UUIDPrimaryKeyMixin


class InviteModel(Base, UUIDPrimaryKeyMixin, TimeStampMixin):
    __tablename__ = "invites"

    target_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True
    )
    created_by_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True
    )
    status: Mapped[str] = mapped_column(
        String(20), default="pending", nullable=False, index=True
    )
    meta: Mapped[dict] = mapped_column(
        JSONB, default=dict, nullable=False, server_default="{}"
    )
    expires_at: Mapped[datetime | None] = mapped_column(nullable=True)