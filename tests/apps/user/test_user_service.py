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


@pytest.mark.asyncio
async def test_find_user_by_email_returns_user():
    from apps.user.response import UserLookupResponse

    repo = AsyncMock(spec=UserRepository)
    blocklist = AsyncMock(spec=TokenBlocklist)
    service = UserService(repo, blocklist)

    mock_user = SimpleNamespace(
        id=uuid4(),
        email="alice@example.com",
        phone="9876543210",
        first_name="Alice",
        last_name="Smith",
    )
    repo.find_by_email = AsyncMock(return_value=mock_user)

    result = await service.find_user(email="alice@example.com")

    assert result is not None
    assert isinstance(result, UserLookupResponse)
    assert result.user_id == mock_user.id
    assert result.email == "alice@example.com"
    repo.find_by_email.assert_awaited_once_with("alice@example.com")


@pytest.mark.asyncio
async def test_find_user_by_phone_returns_user():
    from apps.user.response import UserLookupResponse

    repo = AsyncMock(spec=UserRepository)
    blocklist = AsyncMock(spec=TokenBlocklist)
    service = UserService(repo, blocklist)

    mock_user = SimpleNamespace(
        id=uuid4(),
        email="bob@example.com",
        phone="9876543210",
        first_name="Bob",
        last_name="Jones",
    )
    repo.find_by_phone = AsyncMock(return_value=mock_user)

    result = await service.find_user(phone="9876543210")

    assert result is not None
    assert isinstance(result, UserLookupResponse)
    assert result.phone == "9876543210"
    repo.find_by_phone.assert_awaited_once_with("9876543210")


@pytest.mark.asyncio
async def test_find_user_not_found_returns_none():
    repo = AsyncMock(spec=UserRepository)
    blocklist = AsyncMock(spec=TokenBlocklist)
    service = UserService(repo, blocklist)

    repo.find_by_email = AsyncMock(return_value=None)

    result = await service.find_user(email="ghost@example.com")

    assert result is None
