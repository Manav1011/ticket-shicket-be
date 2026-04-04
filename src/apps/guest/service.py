import hashlib
import uuid
from datetime import datetime, timedelta
from typing import TYPE_CHECKING

from .exceptions import (
    GuestNotFoundException,
    GuestAlreadyConvertedException,
    DuplicateEmailException,
    DuplicatePhoneException,
)
from .models import GuestModel
from .repository import GuestRepository
from apps.user.models import UserModel
from apps.user.repository import UserRepository
from auth.jwt import create_tokens
from auth.password import hash_password
from exceptions import UnauthorizedError
from config import settings

if TYPE_CHECKING:
    from apps.user.repository import UserRepository
from auth.blocklist import TokenBlocklist


class GuestService:
    def __init__(
        self,
        repository: GuestRepository,
        user_repository: "UserRepository",
        blocklist: TokenBlocklist,
    ) -> None:
        self.repository = repository
        self.user_repository = user_repository
        self._blocklist = blocklist

    async def login_guest(self, device_id: uuid.UUID) -> dict:
        """
        Login or create guest by device_id.
        Returns tokens and guest info including device_id for client storage.
        """
        guest = await self.repository.get_by_device_id(device_id)

        if not guest:
            guest = GuestModel.create(device_id=device_id)
            await self.repository.create(guest)
            await self.repository.session.flush()
            await self.repository.session.refresh(guest)

        if guest.is_converted:
            raise GuestAlreadyConvertedException

        tokens = await create_tokens(guest_id=guest.id, type="guest")

        # Store refresh token
        token_hash = self._hash_token(tokens["refresh_token"])
        await self.repository.create_refresh_token(
            token_hash=token_hash,
            guest_id=guest.id,
            expires_at=datetime.utcnow() + timedelta(seconds=int(settings.REFRESH_TOKEN_EXP)),
        )
        await self.repository.session.flush()

        return {
            "guest_id": str(guest.id),
            "device_id": str(guest.device_id),
            "access_token": tokens["access_token"],
            "refresh_token": tokens["refresh_token"],
        }

    async def refresh_guest(self, refresh_token: str) -> dict:
        """
        Validate refresh token and rotate: revoke old, issue new pair.
        For guests only - raises UnauthorizedError for converted guests.
        """
        token_hash = self._hash_token(refresh_token)
        token_record = await self.repository.get_refresh_token(token_hash)

        if not token_record:
            raise UnauthorizedError(message="Invalid refresh token")

        if not token_record.is_active:
            raise UnauthorizedError(message="Refresh token expired or revoked")

        guest = await self.repository.get_by_id(token_record.guest_id)
        if not guest:
            raise UnauthorizedError(message="Guest not found")

        if guest.is_converted:
            raise GuestAlreadyConvertedException

        # Revoke old token
        await self.repository.revoke_refresh_token(token_hash)

        # Issue new tokens
        new_tokens = await create_tokens(guest_id=guest.id, type="guest")

        # Store new refresh token
        await self.repository.create_refresh_token(
            token_hash=self._hash_token(new_tokens["refresh_token"]),
            guest_id=guest.id,
            expires_at=datetime.utcnow() + timedelta(seconds=int(settings.REFRESH_TOKEN_EXP)),
        )
        await self.repository.session.commit()

        return new_tokens

    async def logout_guest(
        self,
        refresh_token: str,
        access_token_jti: str | None = None,
    ) -> None:
        """Revoke refresh token and optionally blocklist access token by jti."""
        token_hash = self._hash_token(refresh_token)
        await self.repository.revoke_refresh_token(token_hash)

        if access_token_jti:
            await self._blocklist.add(access_token_jti, ttl=int(settings.ACCESS_TOKEN_EXP))

        await self.repository.session.commit()

    async def convert_guest(
        self,
        guest_id: uuid.UUID,
        email: str,
        phone: str,
        password: str,
        first_name: str,
        last_name: str,
    ) -> dict:
        """
        Convert guest to user at checkout.
        Creates new User, marks Guest as converted, revokes guest tokens.
        """
        guest = await self.repository.get_by_id(guest_id)
        if not guest:
            raise GuestNotFoundException

        if guest.is_converted:
            raise GuestAlreadyConvertedException

        # Check email/phone uniqueness in User table
        normalized_email = email.strip().lower()
        existing = await self.user_repository.get_by_email_or_phone(normalized_email, phone)
        if existing:
            if existing.email and existing.email.strip().lower() == normalized_email:
                raise DuplicateEmailException
            if existing.phone == phone:
                raise DuplicatePhoneException

        # Create user
        user = UserModel.create(
            first_name=first_name,
            last_name=last_name,
            email=normalized_email,
            phone=phone,
            password=await hash_password(password),
        )
        self.user_repository.add(user)
        await self.user_repository.session.flush()
        await self.user_repository.session.refresh(user)

        # Update guest record
        await self.repository.update_conversion(
            guest_id=guest_id,
            email=normalized_email,
            phone=phone,
            converted_user_id=user.id,
        )

        # Revoke all guest tokens
        await self.repository.revoke_all_guest_tokens(guest_id)

        await self.repository.session.commit()

        # Issue new user tokens
        tokens = await create_tokens(user_id=user.id, type="user")

        return {
            "user_id": str(user.id),
            "access_token": tokens["access_token"],
            "refresh_token": tokens["refresh_token"],
        }

    async def get_guest(self, guest_id: uuid.UUID) -> GuestModel:
        guest = await self.repository.get_by_id(guest_id)
        if not guest:
            raise GuestNotFoundException
        return guest

    @staticmethod
    def _hash_token(token: str) -> str:
        return hashlib.sha256(token.encode()).hexdigest()
