import pytest
import uuid
from datetime import datetime
from apps.user.invite.models import InviteModel


@pytest.fixture
async def another_user_id():
    return uuid.uuid4()


@pytest.fixture
async def sample_invite(db_session, another_user_id, test_user):
    invite = InviteModel(
        id=uuid.uuid4(),
        target_user_id=another_user_id,
        created_by_id=test_user.id,
        status="pending",
        meta={"event_id": str(uuid.uuid4())},
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    db_session.add(invite)
    await db_session.flush()
    return invite