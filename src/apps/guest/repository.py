from datetime import datetime
from typing import Optional
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import load_only

from .models import GuestModel, GuestRefreshTokenModel


class GuestRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    @property
    def session(self) -> AsyncSession:
        return self._session

    async def get_by_id(self, guest_id: UUID) -> Optional[GuestModel]:
        return await self._session.scalar(
            select(GuestModel).where(GuestModel.id == guest_id)
        )

    async def get_by_device_id(self, device_id: UUID) -> Optional[GuestModel]:
        return await self._session.scalar(
            select(GuestModel).where(GuestModel.device_id == device_id)
        )

    async def get_by_email(self, email: str) -> Optional[GuestModel]:
        return await self._session.scalar(
            select(GuestModel).where(GuestModel.email == email)
        )

    async def get_by_phone(self, phone: str) -> Optional[GuestModel]:
        return await self._session.scalar(
            select(GuestModel).where(GuestModel.phone == phone)
        )

    async def create(self, guest: GuestModel) -> GuestModel:
        self._session.add(guest)
        await self._session.flush()
        return guest

    async def update_conversion(
        self,
        guest_id: UUID,
        email: str,
        phone: str,
        converted_user_id: UUID,
    ) -> None:
        await self._session.execute(
            update(GuestModel)
            .where(GuestModel.id == guest_id)
            .values(
                email=email,
                phone=phone,
                is_converted=True,
                converted_user_id=converted_user_id,
            )
        )
        await self._session.flush()

    async def create_refresh_token(
        self, token_hash: str, guest_id: UUID, expires_at: datetime
    ) -> GuestRefreshTokenModel:
        token = GuestRefreshTokenModel(
            token_hash=token_hash,
            guest_id=guest_id,
            expires_at=expires_at,
        )
        self._session.add(token)
        await self._session.flush()
        return token

    async def get_refresh_token(self, token_hash: str) -> Optional[GuestRefreshTokenModel]:
        return await self._session.scalar(
            select(GuestRefreshTokenModel).where(
                GuestRefreshTokenModel.token_hash == token_hash,
                GuestRefreshTokenModel.revoked == False,
            )
        )

    async def revoke_refresh_token(self, token_hash: str) -> None:
        token = await self._session.scalar(
            select(GuestRefreshTokenModel).where(
                GuestRefreshTokenModel.token_hash == token_hash
            )
        )
        if token:
            token.revoked = True
            await self._session.flush()

    async def revoke_all_guest_tokens(self, guest_id: UUID) -> None:
        await self._session.execute(
            update(GuestRefreshTokenModel)
            .where(GuestRefreshTokenModel.guest_id == guest_id)
            .values(revoked=True)
        )
        await self._session.flush()
