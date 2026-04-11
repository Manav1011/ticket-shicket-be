from typing import Optional
from uuid import UUID

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from .models import InviteModel


class InviteRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    @property
    def session(self) -> AsyncSession:
        return self._session

    def add(self, entity) -> None:
        self._session.add(entity)

    async def get_invite_by_id(self, invite_id: UUID) -> Optional[InviteModel]:
        return await self._session.scalar(
            select(InviteModel).where(InviteModel.id == invite_id)
        )

    async def list_pending_invites_for_user(self, user_id: UUID) -> list[InviteModel]:
        result = await self._session.scalars(
            select(InviteModel)
            .where(
                and_(
                    InviteModel.target_user_id == user_id,
                    InviteModel.status == "pending",
                )
            )
            .order_by(InviteModel.created_at.desc())
        )
        return list(result.all())

    async def update_invite_status(self, invite: InviteModel, status: str) -> None:
        invite.status = status
        await self._session.flush()

    async def get_pending_invite_for_user_event(
        self, target_user_id: UUID, event_id: UUID
    ) -> Optional[InviteModel]:
        return await self._session.scalar(
            select(InviteModel).where(
                and_(
                    InviteModel.target_user_id == target_user_id,
                    InviteModel.status == "pending",
                    InviteModel.meta.contains({"event_id": str(event_id)}),
                )
            )
        )