from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .models import OrganizerPageModel


class OrganizerRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    @property
    def session(self) -> AsyncSession:
        return self._session

    async def get_by_slug(self, slug: str) -> Optional[OrganizerPageModel]:
        return await self._session.scalar(
            select(OrganizerPageModel).where(OrganizerPageModel.slug == slug)
        )

    async def list_by_owner(self, owner_user_id: UUID) -> list[OrganizerPageModel]:
        result = await self._session.scalars(
            select(OrganizerPageModel).where(
                OrganizerPageModel.owner_user_id == owner_user_id
            )
        )
        return list(result.all())

    async def get_by_id_for_owner(
        self, organizer_id: UUID, owner_user_id: UUID
    ) -> Optional[OrganizerPageModel]:
        return await self._session.scalar(
            select(OrganizerPageModel).where(
                OrganizerPageModel.id == organizer_id,
                OrganizerPageModel.owner_user_id == owner_user_id,
            )
        )

    def add(self, organizer: OrganizerPageModel) -> None:
        self._session.add(organizer)
