from types import SimpleNamespace
from uuid import uuid4
from unittest.mock import AsyncMock, patch

import pytest

from apps.user.exceptions import DuplicatePhoneException
from apps.user.models import UserModel
from apps.user.repository import UserRepository
from apps.user.service import UserService
from auth.blocklist import TokenBlocklist


@pytest.mark.asyncio
async def test_create_user_hashes_password_and_normalizes_email():
    session = AsyncMock()
    session.flush = AsyncMock()
    session.refresh = AsyncMock()
    repo = AsyncMock(spec=UserRepository)
    repo.get_by_email_or_phone.return_value = None
    repo.session = session
    blocklist = AsyncMock(spec=TokenBlocklist)
    service = UserService(repo, blocklist)

    with patch("apps.user.service.hash_password", new=AsyncMock(return_value="hashed-password")):
        user = await service.create_user(
            first_name="Jane",
            last_name="Doe",
            email=" Jane@Example.COM ",
            phone="1234567890",
            password="Secret123!",
        )

    assert user.email == "jane@example.com"
    assert user.password == "hashed-password"
    repo.add.assert_called_once()


@pytest.mark.asyncio
async def test_login_user_looks_up_normalized_email():
    session = AsyncMock()
    repo = AsyncMock(spec=UserRepository)
    repo.get_by_email.return_value = UserModel(
        id=uuid4(),
        first_name="Jane",
        last_name="Doe",
        email="jane@example.com",
        phone="1234567890",
        password="hashed-password",
    )
    repo.session = session
    blocklist = AsyncMock(spec=TokenBlocklist)
    service = UserService(repo, blocklist)

    with patch("apps.user.service.verify_password", new=AsyncMock(return_value=True)):
        with patch(
            "apps.user.service.create_tokens",
            new=AsyncMock(return_value={"access_token": "a", "refresh_token": "r"}),
        ):
            await service.login_user(" JANE@EXAMPLE.COM ", "Secret123!")

    repo.get_by_email.assert_awaited_once_with("jane@example.com")


@pytest.mark.asyncio
async def test_create_user_raises_duplicate_phone():
    session = AsyncMock()
    repo = AsyncMock(spec=UserRepository)
    repo.get_by_email_or_phone.return_value = SimpleNamespace(email=None, phone="1234567890")
    repo.session = session
    blocklist = AsyncMock(spec=TokenBlocklist)
    service = UserService(repo, blocklist)

    with pytest.raises(DuplicatePhoneException):
        await service.create_user(
            first_name="Jane",
            last_name="Doe",
            email="jane@example.com",
            phone="1234567890",
            password="Secret123!",
        )


@pytest.mark.asyncio
async def test_delete_user_revokes_tokens_and_clears_guest_links():
    session = AsyncMock()
    session.commit = AsyncMock()
    repo = AsyncMock(spec=UserRepository)
    user = UserModel(
        id=uuid4(),
        first_name="Jane",
        last_name="Doe",
        email="jane@example.com",
        phone="1234567890",
        password="hashed-password",
    )
    repo.get_by_id.return_value = user
    repo.session = session
    blocklist = AsyncMock(spec=TokenBlocklist)
    service = UserService(repo, blocklist)

    deleted = await service.delete_user_by_id(user.id)

    assert deleted == user
    repo.delete_all_user_tokens.assert_awaited_once_with(user.id)
    repo.clear_guest_conversion_links.assert_awaited_once_with(user.id)
    repo.delete.assert_awaited_once_with(user.id)
    session.commit.assert_awaited_once()
