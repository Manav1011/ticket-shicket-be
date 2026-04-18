"""
Integration test for full reseller invite flow:
1. User lookup via API returns user_id
2. Batch reseller invites created with user_ids
3. Invites listed with status filter
4. Duplicate prevention works
"""
import pytest
from uuid import uuid4
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime

from apps.user.response import UserLookupResponse
from apps.event.request import CreateResellerInviteRequest
from apps.event.response import ResellerInviteResponse
from apps.user.invite.enums import InviteType


@pytest.mark.asyncio
async def test_full_reseller_invite_flow_with_user_ids():
    """
    Full flow:
    1. Organizer calls GET /api/users/find?email=alice@example.com → gets user_id
    2. Organizer calls POST /api/events/{event_id}/reseller-invites with user_ids=[user_id]
    3. Batch invite created in single DB call
    4. GET /api/events/{event_id}/reseller-invites shows the new invite
    """
    from apps.user.urls import find_user_endpoint
    from apps.event.urls import (
        create_reseller_invite,
        list_event_reseller_invites,
    )

    organizer_id = uuid4()
    reseller_id = uuid4()
    event_id = uuid4()
    invite_id = uuid4()

    # Step 1: User lookup returns user_id
    user_service = AsyncMock()
    user_service.find_user = AsyncMock(return_value=UserLookupResponse(
        user_id=reseller_id,
        email="alice@example.com",
        phone="9876543210",
        first_name="Alice",
        last_name="Smith",
    ))

    request = SimpleNamespace(state=SimpleNamespace(user=SimpleNamespace(id=organizer_id)))
    lookup_response = await find_user_endpoint(
        email="alice@example.com",
        phone=None,
        service=user_service,
    )

    assert lookup_response.data.user_id == reseller_id
    assert lookup_response.data.email == "alice@example.com"

    # Step 2: Create batch invites
    body = CreateResellerInviteRequest(user_ids=[reseller_id])
    event_service = AsyncMock()
    invite_service = AsyncMock()
    mock_event = SimpleNamespace(id=event_id, organizer_page_id=uuid4())
    event_service.repository.get_by_id_for_owner = AsyncMock(return_value=mock_event)
    invite_service.user_repository.find_by_id = AsyncMock(return_value=SimpleNamespace(id=reseller_id))
    invite_service.repository.get_pending_invite_for_user_event = AsyncMock(return_value=None)
    invite_service.create_invite_batch = AsyncMock(return_value=[
        SimpleNamespace(
            id=invite_id,
            target_user_id=reseller_id,
            created_by_id=organizer_id,
            status="pending",
            invite_type=InviteType.reseller.value,
            meta={"event_id": str(event_id), "permissions": []},
            created_at=datetime.utcnow(),
        )
    ])

    invite_response = await create_reseller_invite(
        event_id=event_id,
        request=request,
        body=body,
        event_service=event_service,
        invite_service=invite_service,
    )

    assert len(invite_response.data) == 1
    assert invite_response.data[0].id == invite_id
    assert invite_response.data[0].status == "pending"
    assert invite_response.data[0].target_user_id == reseller_id
    
    # Verify batch insert was called (single DB round trip)
    invite_service.create_invite_batch.assert_awaited_once_with(
        target_user_ids=[reseller_id],
        created_by_id=organizer_id,
        metadata={"event_id": str(event_id), "permissions": []},
        invite_type=InviteType.reseller.value,
    )

    # Step 3: List invites returns the created invite
    event_service.repository.list_reseller_invites_for_event = AsyncMock(return_value=[
        SimpleNamespace(
            id=invite_id,
            target_user_id=reseller_id,
            created_by_id=organizer_id,
            status="pending",
            invite_type=InviteType.reseller.value,
            meta={"event_id": str(event_id), "permissions": []},
            created_at=datetime.utcnow(),
        )
    ])

    list_response = await list_event_reseller_invites(
        event_id=event_id,
        request=request,
        event_service=event_service,
        status=None,
    )

    assert len(list_response.data) == 1
    assert list_response.data[0].id == invite_id
    assert list_response.data[0].status == "pending"


@pytest.mark.asyncio
async def test_duplicate_prevention_during_batch_invite():
    """Verify that batch invite fails fast if any user has a pending invite."""
    from apps.event.urls import create_reseller_invite
    from exceptions import AlreadyExistsError

    organizer_id = uuid4()
    reseller_id = uuid4()
    event_id = uuid4()
    request = SimpleNamespace(state=SimpleNamespace(user=SimpleNamespace(id=organizer_id)))
    body = CreateResellerInviteRequest(user_ids=[reseller_id])
    event_service = AsyncMock()
    invite_service = AsyncMock()
    mock_event = SimpleNamespace(id=event_id, organizer_page_id=uuid4())
    event_service.repository.get_by_id_for_owner = AsyncMock(return_value=mock_event)
    invite_service.user_repository.find_by_id = AsyncMock(return_value=SimpleNamespace(id=reseller_id))
    
    # Simulate existing pending invite
    invite_service.repository.get_pending_invite_for_user_event = AsyncMock(
        return_value=SimpleNamespace(id=uuid4())
    )

    with pytest.raises(AlreadyExistsError):
        await create_reseller_invite(
            event_id=event_id,
            request=request,
            body=body,
            event_service=event_service,
            invite_service=invite_service,
        )

    # Verify no batch insert was attempted (fail-fast)
    invite_service.create_invite_batch.assert_not_awaited()


@pytest.mark.asyncio
async def test_batch_reseller_invite_with_multiple_users():
    """Test batch invite creation with multiple users."""
    from apps.event.urls import create_reseller_invite

    organizer_id = uuid4()
    event_id = uuid4()
    reseller_ids = [uuid4(), uuid4(), uuid4()]
    invite_ids = [uuid4(), uuid4(), uuid4()]
    request = SimpleNamespace(state=SimpleNamespace(user=SimpleNamespace(id=organizer_id)))
    body = CreateResellerInviteRequest(user_ids=reseller_ids)
    event_service = AsyncMock()
    invite_service = AsyncMock()
    mock_event = SimpleNamespace(id=event_id, organizer_page_id=uuid4())
    event_service.repository.get_by_id_for_owner = AsyncMock(return_value=mock_event)
    invite_service.user_repository.find_by_id = AsyncMock(
        side_effect=lambda uid: SimpleNamespace(id=uid)
    )
    invite_service.repository.get_pending_invite_for_user_event = AsyncMock(return_value=None)
    
    # Mock batch create returning 3 invites
    invite_service.create_invite_batch = AsyncMock(return_value=[
        SimpleNamespace(
            id=invite_ids[i],
            target_user_id=reseller_ids[i],
            created_by_id=organizer_id,
            status="pending",
            invite_type=InviteType.reseller.value,
            meta={"event_id": str(event_id), "permissions": []},
            created_at=datetime.utcnow(),
        )
        for i in range(3)
    ])

    response = await create_reseller_invite(
        event_id=event_id,
        request=request,
        body=body,
        event_service=event_service,
        invite_service=invite_service,
    )

    assert len(response.data) == 3
    for i, invite in enumerate(response.data):
        assert invite.id == invite_ids[i]
        assert invite.target_user_id == reseller_ids[i]
        assert invite.status == "pending"
    
    # Verify all 3 users were validated before batch insert
    assert invite_service.user_repository.find_by_id.await_count == 3
    # Verify batch insert was called once with all 3 user_ids
    invite_service.create_invite_batch.assert_awaited_once()
    call_args = invite_service.create_invite_batch.call_args
    assert call_args[1]["target_user_ids"] == reseller_ids
