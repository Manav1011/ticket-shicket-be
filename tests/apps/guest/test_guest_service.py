import pytest
from uuid import uuid4, UUID
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timedelta

from apps.guest.service import GuestService
from apps.guest.repository import GuestRepository
from apps.guest.models import GuestModel, GuestRefreshTokenModel
from apps.guest.exceptions import (
    GuestNotFoundException,
    GuestAlreadyConvertedException,
    DuplicateEmailException,
    DuplicatePhoneException,
)
from apps.user.models import UserModel
from exceptions import UnauthorizedError


class TestGuestLogin:
    """Tests for GuestService.login_guest"""

    @pytest.mark.asyncio
    async def test_login_creates_new_guest_when_device_id_not_found(self):
        """When device_id not found, creates new guest and returns tokens."""
        # Arrange
        mock_session = AsyncMock()
        mock_session.flush = AsyncMock()
        mock_session.refresh = AsyncMock()

        new_guest = GuestModel.create(device_id=uuid4())
        new_guest.id = uuid4()  # Ensure consistent ID

        mock_guest_repo = AsyncMock(spec=GuestRepository)
        mock_guest_repo.get_by_device_id.return_value = None
        mock_guest_repo.create.return_value = new_guest
        mock_guest_repo.session = mock_session
        mock_guest_repo.create_refresh_token = AsyncMock()

        mock_user_repo = AsyncMock()

        service = GuestService(mock_guest_repo, mock_user_repo)
        device_id = uuid4()

        with patch("apps.guest.service.create_tokens") as mock_create_tokens:
            mock_create_tokens.return_value = {
                "access_token": "access123",
                "refresh_token": "refresh123",
            }

            result = await service.login_guest(device_id)

            # Assert
            mock_guest_repo.create.assert_called_once()
            mock_create_tokens.assert_called_once()
            assert result["access_token"] == "access123"
            assert result["refresh_token"] == "refresh123"

    @pytest.mark.asyncio
    async def test_login_returns_existing_guest_when_device_id_found(self):
        """When device_id found, returns existing guest without creating new."""
        # Arrange
        mock_session = AsyncMock()
        mock_session.flush = AsyncMock()

        existing_guest = GuestModel.create(device_id=uuid4())
        existing_guest.id = uuid4()

        mock_guest_repo = AsyncMock(spec=GuestRepository)
        mock_guest_repo.get_by_device_id.return_value = existing_guest
        mock_guest_repo.session = mock_session
        mock_guest_repo.create_refresh_token = AsyncMock()

        mock_user_repo = AsyncMock()

        service = GuestService(mock_guest_repo, mock_user_repo)
        device_id = existing_guest.device_id

        with patch("apps.guest.service.create_tokens") as mock_create_tokens:
            mock_create_tokens.return_value = {
                "access_token": "access456",
                "refresh_token": "refresh456",
            }

            result = await service.login_guest(device_id)

            # Assert
            mock_guest_repo.create.assert_not_called()
            assert result["guest_id"] == str(existing_guest.id)

    @pytest.mark.asyncio
    async def test_login_raises_when_guest_already_converted(self):
        """When guest is already converted, raises GuestAlreadyConvertedException."""
        # Arrange
        mock_guest_repo = AsyncMock(spec=GuestRepository)
        converted_guest = GuestModel.create(device_id=uuid4())
        converted_guest.is_converted = True
        mock_guest_repo.get_by_device_id.return_value = converted_guest

        mock_user_repo = AsyncMock()

        service = GuestService(mock_guest_repo, mock_user_repo)

        with pytest.raises(GuestAlreadyConvertedException):
            await service.login_guest(uuid4())


class TestGuestConvert:
    """Tests for GuestService.convert_guest"""

    @pytest.mark.asyncio
    async def test_convert_raises_when_guest_not_found(self):
        """Raises GuestNotFoundException when guest doesn't exist."""
        # Arrange
        mock_guest_repo = AsyncMock(spec=GuestRepository)
        mock_guest_repo.get_by_id.return_value = None

        mock_user_repo = AsyncMock()

        service = GuestService(mock_guest_repo, mock_user_repo)

        with pytest.raises(GuestNotFoundException):
            await service.convert_guest(
                guest_id=uuid4(),
                email="test@example.com",
                phone="1234567890",
                password="password",
                first_name="John",
                last_name="Doe",
            )

    @pytest.mark.asyncio
    async def test_convert_raises_when_guest_already_converted(self):
        """Raises GuestAlreadyConvertedException when guest already converted."""
        # Arrange
        guest = GuestModel.create(device_id=uuid4())
        guest.is_converted = True

        mock_guest_repo = AsyncMock(spec=GuestRepository)
        mock_guest_repo.get_by_id.return_value = guest

        mock_user_repo = AsyncMock()

        service = GuestService(mock_guest_repo, mock_user_repo)

        with pytest.raises(GuestAlreadyConvertedException):
            await service.convert_guest(
                guest_id=guest.id,
                email="test@example.com",
                phone="1234567890",
                password="password",
                first_name="John",
                last_name="Doe",
            )

    @pytest.mark.asyncio
    async def test_convert_raises_on_duplicate_email(self):
        """Raises DuplicateEmailException when email already registered."""
        # Arrange
        guest = GuestModel.create(device_id=uuid4())

        mock_guest_repo = AsyncMock(spec=GuestRepository)
        mock_guest_repo.get_by_id.return_value = guest

        existing_user = UserModel()
        existing_user.email = "test@example.com"

        mock_user_repo = AsyncMock()
        mock_user_repo.get_by_email_or_phone.return_value = existing_user

        service = GuestService(mock_guest_repo, mock_user_repo)

        with pytest.raises(DuplicateEmailException):
            await service.convert_guest(
                guest_id=guest.id,
                email="test@example.com",
                phone="1234567890",
                password="password",
                first_name="John",
                last_name="Doe",
            )


class TestGuestRefresh:
    """Tests for GuestService.refresh_guest"""

    @pytest.mark.asyncio
    async def test_refresh_raises_on_invalid_token(self):
        """Raises UnauthorizedError when token not found."""
        # Arrange
        mock_guest_repo = AsyncMock(spec=GuestRepository)
        mock_guest_repo.get_refresh_token.return_value = None

        mock_user_repo = AsyncMock()

        service = GuestService(mock_guest_repo, mock_user_repo)

        with pytest.raises(UnauthorizedError):
            await service.refresh_guest("invalid_token")

    @pytest.mark.asyncio
    async def test_refresh_raises_on_converted_guest(self):
        """Raises GuestAlreadyConvertedException when guest was converted."""
        # Arrange
        guest = GuestModel.create(device_id=uuid4())
        guest.is_converted = True

        token_record = MagicMock()
        token_record.is_active = True

        mock_guest_repo = AsyncMock(spec=GuestRepository)
        mock_guest_repo.get_refresh_token.return_value = token_record
        mock_guest_repo.get_by_id.return_value = guest

        mock_user_repo = AsyncMock()

        service = GuestService(mock_guest_repo, mock_user_repo)

        with pytest.raises(GuestAlreadyConvertedException):
            await service.refresh_guest("refresh_token")


class TestGuestLogout:
    """Tests for GuestService.logout_guest"""

    @pytest.mark.asyncio
    async def test_logout_revokes_token(self):
        """Logout revokes the refresh token."""
        # Arrange
        mock_session = AsyncMock()
        mock_session.commit = AsyncMock()

        mock_guest_repo = AsyncMock(spec=GuestRepository)
        mock_guest_repo.session = mock_session
        mock_guest_repo.revoke_refresh_token = AsyncMock()

        mock_user_repo = AsyncMock()

        service = GuestService(mock_guest_repo, mock_user_repo)

        await service.logout_guest("refresh_token")

        mock_guest_repo.revoke_refresh_token.assert_called_once()
        mock_session.commit.assert_called_once()
