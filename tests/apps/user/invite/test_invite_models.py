import pytest
import uuid
from datetime import datetime
from apps.user.invite.models import InviteModel


def test_invite_model_creation():
    event_uuid = uuid.uuid4()
    invite = InviteModel(
        id=uuid.uuid4(),
        target_user_id=uuid.uuid4(),
        created_by_id=uuid.uuid4(),
        status="pending",
        meta={"event_id": str(event_uuid)},
    )
    assert invite.status == "pending"
    assert isinstance(invite.meta, dict)
    assert invite.meta == {"event_id": str(event_uuid)}