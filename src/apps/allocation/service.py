"""
Allocation service — handles all ticket movement flows.
All allocation operations are wrapped in a single database transaction.
"""
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from .enums import AllocationStatus
from .exceptions import (
    TicketHolderInactiveError,
    TicketHolderNotFoundError,
)
from .models import TicketHolderModel
from .repository import AllocationRepository


class AllocationService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = AllocationRepository(session)

    @property
    def repo(self) -> AllocationRepository:
        return self._repo

    async def resolve_holder(
        self,
        phone: str | None = None,
        email: str | None = None,
        user_id: uuid.UUID | None = None,
        create_if_missing: bool = True,
    ) -> TicketHolderModel:
        """
        Resolve a ticket holder by contact info.
        Creates if not exists and create_if_missing=True.
        If user_id is provided but no phone/email, looks up user's contact info.
        """
        assert phone or email or user_id, "At least one identifier required"
        assert not (phone and email), "Only phone OR email allowed at v1"

        # If user_id provided, look up user to get phone/email
        if user_id and not phone and not email:
            from apps.user.repository import UserRepository
            user_repo = UserRepository(self._session)
            user = await user_repo.get_by_id(user_id)
            if user:
                phone = user.phone
                email = user.email

        if user_id:
            holder = await self._repo.get_holder_by_user_id(user_id)
            if holder:
                return holder

        if phone:
            holder = await self._repo.get_holder_by_phone(phone)
            if holder:
                if user_id and holder.user_id is None:
                    holder.user_id = user_id
                    await self._session.flush()
                return holder

        if email:
            holder = await self._repo.get_holder_by_email(email)
            if holder:
                if user_id and holder.user_id is None:
                    holder.user_id = user_id
                    await self._session.flush()
                return holder

        if not create_if_missing:
            raise TicketHolderNotFoundError(f"No holder found for {phone or email or user_id}")

        return await self._repo.create_holder(user_id=user_id, phone=phone, email=email)

    async def validate_holder_active(self, holder_id: uuid.UUID) -> bool:
        """Check that a holder exists and is active."""
        holder = await self._repo.get_holder_by_id(holder_id)
        if not holder:
            raise TicketHolderNotFoundError(f"Holder {holder_id} not found")
        if holder.status != "active":
            raise TicketHolderInactiveError(f"Holder {holder_id} is {holder.status}")
        return True
