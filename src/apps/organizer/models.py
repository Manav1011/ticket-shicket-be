import uuid

from sqlalchemy import ForeignKey, String, text
from sqlalchemy.orm import Mapped, mapped_column

from db.base import Base, TimeStampMixin, UUIDPrimaryKeyMixin


class OrganizerPageModel(Base, UUIDPrimaryKeyMixin, TimeStampMixin):
    __tablename__ = "organizer_pages"

    owner_user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id"), index=True, nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    slug: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    bio: Mapped[str | None] = mapped_column(nullable=True)
    logo_url: Mapped[str | None] = mapped_column(nullable=True)
    cover_image_url: Mapped[str | None] = mapped_column(nullable=True)
    website_url: Mapped[str | None] = mapped_column(nullable=True)
    instagram_url: Mapped[str | None] = mapped_column(nullable=True)
    facebook_url: Mapped[str | None] = mapped_column(nullable=True)
    youtube_url: Mapped[str | None] = mapped_column(nullable=True)
    visibility: Mapped[str] = mapped_column(
        String(32), default="private", server_default=text("'private'"), nullable=False
    )
    status: Mapped[str] = mapped_column(
        String(32), default="active", server_default=text("'active'"), nullable=False
    )
