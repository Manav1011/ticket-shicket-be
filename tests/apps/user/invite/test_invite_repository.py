import pytest
import uuid
from apps.user.invite.models import InviteModel
from apps.user.invite.repository import InviteRepository


@pytest.fixture
async def invite_repository(db_session):
    return InviteRepository(db_session)


async def test_add_invite(invite_repository):
    invite = InviteModel(
        id=uuid.uuid4(),
        target_user_id=uuid.uuid4(),
        created_by_id=uuid.uuid4(),
        status="pending",
        meta={"event_id": str(uuid.uuid4())},
    )
    invite_repository.add(invite)
    assert invite.id is not None
    assert invite.status == "pending"


async def test_get_invite_by_id(invite_repository, sample_invite):
    invite = await invite_repository.get_invite_by_id(sample_invite.id)
    assert invite is not None
    assert invite.id == sample_invite.id


async def test_list_pending_invites_for_user(invite_repository, sample_invite, another_user_id):
    invites = await invite_repository.list_pending_invites_for_user(another_user_id)
    assert len(invites) >= 1
    assert any(i.id == sample_invite.id for i in invites)