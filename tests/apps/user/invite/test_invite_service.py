import pytest
import uuid
from unittest.mock import MagicMock, AsyncMock
from apps.user.invite.service import InviteService


@pytest.fixture
def mock_user_repo():
    return MagicMock()


@pytest.fixture
def mock_invite_repo():
    return MagicMock()


@pytest.fixture
def invite_service(mock_user_repo, mock_invite_repo):
    return InviteService(repository=mock_invite_repo, user_repository=mock_user_repo)


async def test_list_pending_invites(invite_service, mock_invite_repo):
    mock_invite_repo.list_pending_invites_for_user = AsyncMock(return_value=[])
    result = await invite_service.list_pending_invites_for_user(uuid.uuid4())
    assert isinstance(result, list)


async def test_get_invite_by_id_not_found(invite_service, mock_invite_repo):
    from apps.user.invite.exceptions import InviteNotFound

    mock_invite_repo.get_invite_by_id = AsyncMock(return_value=None)
    with pytest.raises(InviteNotFound):
        await invite_service.get_invite_by_id(uuid.uuid4())