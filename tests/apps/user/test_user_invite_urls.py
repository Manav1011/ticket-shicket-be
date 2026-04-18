from types import SimpleNamespace
from uuid import uuid4
from unittest.mock import AsyncMock, MagicMock
import pytest


@pytest.mark.asyncio
async def test_accept_invite_under_user_endpoint():
    """
    POST /api/user/invites/{invite_id}/accept
    1. Calls invite_service.accept_invite(user_id, invite_id)
    2. Validates event exists via event_service
    3. Creates EventReseller via event_service.repository
    """
    from apps.user.urls import accept_user_invite
    from utils.schema import BaseResponse

    user_id = uuid4()
    invite_id = uuid4()
    event_id = uuid4()
    reseller_id = uuid4()
    invited_by_id = uuid4()

    request = SimpleNamespace(state=SimpleNamespace(user=SimpleNamespace(id=user_id)))

    # Mock invite_service.accept_invite
    mock_invite = MagicMock()
    mock_invite.created_by_id = invited_by_id
    mock_invite.meta = {"event_id": str(event_id), "permissions": []}

    mock_invite_service = AsyncMock()
    mock_invite_service.accept_invite = AsyncMock(return_value={
        "invite": mock_invite,
        "event_id": str(event_id),
        "permissions": [],
    })

    # Mock event_service with proper UUID fields - use SimpleNamespace for proper attribute access
    mock_event = SimpleNamespace(id=event_id)
    mock_reseller = SimpleNamespace(
        id=reseller_id,
        user_id=user_id,
        event_id=event_id,
        invited_by_id=invited_by_id,
        permissions=[]
    )

    mock_event_service = AsyncMock()
    mock_event_service.repository.get_by_id = AsyncMock(return_value=mock_event)
    mock_event_service.repository.get_reseller_for_event = AsyncMock(return_value=None)
    mock_event_service.repository.create_event_reseller = AsyncMock(return_value=mock_reseller)

    response = await accept_user_invite(
        invite_id=invite_id,
        request=request,
        invite_service=mock_invite_service,
        event_service=mock_event_service,
    )

    assert response.data is not None
    mock_invite_service.accept_invite.assert_awaited_once_with(user_id, invite_id)
    mock_event_service.repository.create_event_reseller.assert_awaited_once()


@pytest.mark.asyncio
async def test_decline_invite_under_user_endpoint():
    """
    POST /api/user/invites/{invite_id}/decline
    Just calls invite_service.decline_invite(user_id, invite_id)
    """
    from apps.user.urls import decline_user_invite
    from utils.schema import BaseResponse

    user_id = uuid4()
    invite_id = uuid4()
    request = SimpleNamespace(state=SimpleNamespace(user=SimpleNamespace(id=user_id)))

    mock_invite_service = AsyncMock()
    mock_invite_service.decline_invite = AsyncMock()

    response = await decline_user_invite(
        invite_id=invite_id,
        request=request,
        invite_service=mock_invite_service,
    )

    assert response.data["declined"] is True
    mock_invite_service.decline_invite.assert_awaited_once_with(user_id, invite_id)


@pytest.mark.asyncio
async def test_cancel_invite_under_user_endpoint():
    """
    DELETE /api/user/invites/{invite_id}
    Just calls invite_service.cancel_invite(user_id, invite_id)
    """
    from apps.user.urls import cancel_user_invite
    from utils.schema import BaseResponse

    user_id = uuid4()
    invite_id = uuid4()
    request = SimpleNamespace(state=SimpleNamespace(user=SimpleNamespace(id=user_id)))

    mock_invite_service = AsyncMock()
    mock_invite_service.cancel_invite = AsyncMock()

    response = await cancel_user_invite(
        invite_id=invite_id,
        request=request,
        invite_service=mock_invite_service,
    )

    assert response.data["cancelled"] is True
    mock_invite_service.cancel_invite.assert_awaited_once_with(user_id, invite_id)
