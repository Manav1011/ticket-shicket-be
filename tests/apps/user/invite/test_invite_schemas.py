import pytest
from uuid import uuid4
from apps.user.invite.request import CreateInviteRequest, ResellerMetadata
from apps.user.invite.response import InviteResponse


def test_create_invite_request():
    request = CreateInviteRequest(
        lookup_type="email",
        lookup_value="test@example.com",
        metadata=ResellerMetadata(event_id=uuid4()),
    )
    assert request.lookup_type == "email"


def test_invite_response():
    response = InviteResponse(
        id=uuid4(),
        target_user_id=uuid4(),
        created_by_id=uuid4(),
        status="pending",
        invite_type="reseller",
        meta={},
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    assert response.status == "pending"


from datetime import datetime