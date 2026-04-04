from types import SimpleNamespace
from uuid import uuid4
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from apps.guest.exceptions import DuplicateEmailException
from apps.guest.models import GuestModel
from apps.guest.repository import GuestRepository
from apps.guest.service import GuestService
from auth.blocklist import TokenBlocklist


@pytest.mark.asyncio
async def test_convert_guest_hashes_password_and_normalizes_email():
    guest_repo = AsyncMock(spec=GuestRepository)
    guest_repo.get_by_id.return_value = GuestModel.create(device_id=uuid4())
    guest_repo.update_conversion = AsyncMock()
    guest_repo.revoke_all_guest_tokens = AsyncMock()
    guest_repo.session = AsyncMock()
    guest_repo.session.commit = AsyncMock()

    user_repo = AsyncMock()
    user_repo.get_by_email_or_phone = AsyncMock(return_value=None)
    user_repo.add = MagicMock()
    user_repo.session = AsyncMock()
    user_repo.session.flush = AsyncMock()
    user_repo.session.refresh = AsyncMock()

    blocklist = AsyncMock(spec=TokenBlocklist)
    service = GuestService(guest_repo, user_repo, blocklist)

    with patch("apps.guest.service.hash_password", new=AsyncMock(return_value="hashed-password")):
        with patch(
            "apps.guest.service.create_tokens",
            new=AsyncMock(return_value={"access_token": "a", "refresh_token": "r"}),
        ):
            result = await service.convert_guest(
                guest_id=guest_repo.get_by_id.return_value.id,
                email=" Guest@Example.COM ",
                phone="1234567890",
                password="Secret123!",
                first_name="Jane",
                last_name="Doe",
            )

    created_user = user_repo.add.call_args.args[0]
    assert created_user.email == "guest@example.com"
    assert created_user.password == "hashed-password"
    assert result["user_id"]


@pytest.mark.asyncio
async def test_convert_guest_raises_duplicate_email_case_insensitively():
    guest = GuestModel.create(device_id=uuid4())

    guest_repo = AsyncMock(spec=GuestRepository)
    guest_repo.get_by_id.return_value = guest
    guest_repo.update_conversion = AsyncMock()
    guest_repo.revoke_all_guest_tokens = AsyncMock()
    guest_repo.session = AsyncMock()
    guest_repo.session.commit = AsyncMock()

    user_repo = AsyncMock()
    user_repo.get_by_email_or_phone = AsyncMock(
        return_value=SimpleNamespace(email="guest@example.com", phone=None)
    )
    user_repo.add = MagicMock()
    user_repo.session = AsyncMock()
    user_repo.session.flush = AsyncMock()
    user_repo.session.refresh = AsyncMock()

    blocklist = AsyncMock(spec=TokenBlocklist)
    service = GuestService(guest_repo, user_repo, blocklist)

    with pytest.raises(DuplicateEmailException):
        await service.convert_guest(
            guest_id=guest.id,
            email="GUEST@example.com",
            phone="1234567890",
            password="Secret123!",
            first_name="Jane",
            last_name="Doe",
        )
