from typing import Optional
from uuid import UUID

from sqlalchemy import select, and_, insert
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

    async def create_invite_batch(
        self,
        target_user_ids: list[UUID],
        created_by_id: UUID,
        metadata: dict,
        invite_type: str,
    ) -> list[InviteModel]:
        """
        Bulk insert multiple invites in a single SQL statement.
        Returns all created InviteModel objects with full data.
        """
        from sqlalchemy.dialects.postgresql import insert as pg_insert
        from .enums import InviteStatus

        values = [
            {
                "target_user_id": uid,
                "created_by_id": created_by_id,
                "status": InviteStatus.pending.value,
                "invite_type": invite_type,
                "meta": metadata,
            }
            for uid in target_user_ids
        ]

        # Single bulk INSERT ... VALUES (...), (...), (...) statement
        stmt = pg_insert(InviteModel).values(values).returning(InviteModel.id)
        result = await self._session.execute(stmt)
        created_ids = list(result.scalars().all())

        # Re-fetch to get fully populated objects for response
        invites = await self._session.scalars(
            select(InviteModel).where(InviteModel.id.in_(created_ids))
        )
        return list(invites.all())