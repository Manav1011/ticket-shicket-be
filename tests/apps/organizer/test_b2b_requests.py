import pytest
from uuid import uuid4
from pydantic import ValidationError
from unittest.mock import AsyncMock, MagicMock


def test_create_b2b_request_body_has_no_ticket_type_id():
    """Organizer should NOT provide ticket_type_id — system auto-derives B2B ticket type."""
    from apps.organizer.request import CreateB2BRequestBody

    # Should accept event_id, event_day_id, quantity — NO ticket_type_id
    # If I try to pass extra fields, it might fail if extra="forbid" (not the case here)
    # But it should definitely NOT be in model_fields
    assert 'ticket_type_id' not in CreateB2BRequestBody.model_fields


def test_create_b2b_request_body_has_no_recipient_fields():
    """B2B request body should NOT accept recipient_phone or recipient_email."""
    from apps.organizer.request import CreateB2BRequestBody

    # Should NOT have recipient fields in model_fields
    assert 'recipient_phone' not in CreateB2BRequestBody.model_fields
    assert 'recipient_email' not in CreateB2BRequestBody.model_fields


def test_b2b_response_has_no_recipient_fields():
    """B2BRequestResponse should NOT have recipient_phone or recipient_email."""
    from apps.superadmin.response import B2BRequestResponse

    assert 'recipient_phone' not in B2BRequestResponse.model_fields
    assert 'recipient_email' not in B2BRequestResponse.model_fields


async def test_get_or_create_b2b_ticket_type_creates_new():
    """When no B2B ticket type exists for a day, create one."""
    from apps.ticketing.repository import TicketingRepository
    from apps.ticketing.models import TicketTypeModel
    from apps.ticketing.enums import TicketCategory

    mock_session = AsyncMock()
    mock_session.scalar = AsyncMock(return_value=None)
    mock_session.add = MagicMock()
    mock_session.flush = AsyncMock()
    mock_session.refresh = AsyncMock()

    # Mock event_day lookup
    mock_event_day = MagicMock()
    mock_event_day.event_id = uuid4()
    mock_session.scalar.side_effect = [mock_event_day, None] # 1st for event_day, 2nd for ticket_type

    repo = TicketingRepository(mock_session)
    event_day_id = uuid4()

    result = await repo.get_or_create_b2b_ticket_type(event_day_id=event_day_id)

    assert result is not None
    mock_session.add.assert_called_once()
    call_arg = mock_session.add.call_args[0][0]
    assert call_arg.category == TicketCategory.b2b


async def test_get_or_create_b2b_ticket_type_returns_existing():
    """When B2B ticket type exists for a day, return it."""
    from apps.ticketing.repository import TicketingRepository
    from apps.ticketing.models import TicketTypeModel

    existing = MagicMock(spec=TicketTypeModel)
    existing.id = uuid4()

    mock_session = AsyncMock()
    
    # Mock event_day lookup
    mock_event_day = MagicMock()
    mock_event_day.event_id = uuid4()
    mock_session.scalar.side_effect = [mock_event_day, existing] # 1st for event_day, 2nd for ticket_type

    repo = TicketingRepository(mock_session)
    event_day_id = uuid4()

    result = await repo.get_or_create_b2b_ticket_type(event_day_id=event_day_id)

    assert result == existing
    assert mock_session.scalar.call_count == 2


async def test_create_b2b_request_auto_derives_ticket_type():
    """Organizer create_b2b_request should auto-derive B2B ticket type."""
    from apps.organizer.service import OrganizerService

    mock_repo = MagicMock()
    mock_session = AsyncMock()
    mock_repo.session = mock_session
    mock_repo.create_b2b_request = AsyncMock(return_value=MagicMock(id=uuid4()))

    service = OrganizerService(mock_repo)
    
    # Mock ticketing repo
    mock_ticket_type = MagicMock()
    mock_ticket_type.id = uuid4()
    service._ticketing_repo = MagicMock()
    service._ticketing_repo.get_or_create_b2b_ticket_type = AsyncMock(return_value=mock_ticket_type)

    organizer_id = uuid4()
    user_id = uuid4()
    event_id = uuid4()
    event_day_id = uuid4()

    await service.create_b2b_request(
        organizer_id=organizer_id,
        user_id=user_id,
        event_id=event_id,
        event_day_id=event_day_id,
        quantity=5,
    )

    # Verify create_b2b_request was called with derived ticket_type_id
    mock_repo.create_b2b_request.assert_called_once_with(
        requesting_organizer_id=organizer_id,
        requesting_user_id=user_id,
        event_id=event_id,
        event_day_id=event_day_id,
        ticket_type_id=mock_ticket_type.id,
        quantity=5,
    )


async def test_approve_free_uses_organizer_holder(monkeypatch):
    """Approve free should resolve to_holder via requesting_user_id, not recipient info."""
    from apps.superadmin.service import SuperAdminService
    from apps.superadmin.enums import B2BRequestStatus

    mock_session = AsyncMock()
    mock_session.begin = MagicMock(return_value=MagicMock(__aenter__=AsyncMock(), __aexit__=AsyncMock()))
    
    # Mock b2b_request lookup
    b2b_req = MagicMock()
    b2b_req.id = uuid4()
    b2b_req.requesting_user_id = uuid4()
    b2b_req.quantity = 1
    b2b_req.status = B2BRequestStatus.pending
    
    mock_session.scalar = AsyncMock(return_value=b2b_req)
    mock_session.refresh = AsyncMock()

    service = SuperAdminService(mock_session)

    # Mock AllocationService
    mock_resolve_holder = AsyncMock(return_value=MagicMock(id=uuid4()))
    class MockAllocationService:
        def __init__(self, session):
            pass
        resolve_holder = mock_resolve_holder

    monkeypatch.setattr("apps.superadmin.service.AllocationService", MockAllocationService)
    
    service._select_and_lock_tickets_fifo = AsyncMock(return_value=[uuid4()])
    service._update_ticket_ownership = AsyncMock()

    admin_id = uuid4()
    request_id = uuid4()

    await service.approve_b2b_request_free(
        admin_id=admin_id,
        request_id=request_id,
    )

    # Verify resolve_holder was called with user_id, NOT phone/email
    mock_resolve_holder.assert_called_once()
    kwargs = mock_resolve_holder.call_args.kwargs
    assert 'user_id' in kwargs
    assert kwargs['user_id'] == b2b_req.requesting_user_id
    assert 'phone' not in kwargs
    assert 'email' not in kwargs


async def test_confirm_b2b_payment_rejects_wrong_organizer():
    """confirm_b2b_payment should reject if user doesn't own the organizer page."""
    from apps.organizer.service import OrganizerService
    from exceptions import ForbiddenError

    # Setup: user does NOT own organizer_id
    mock_repo = MagicMock()
    mock_session = AsyncMock()
    mock_repo.session = mock_session

    # B2B request exists but belongs to different organizer
    b2b_req = MagicMock()
    b2b_req.requesting_organizer_id = uuid4()  # Different from organizer_id below

    mock_repo.get_b2b_request_by_id = AsyncMock(return_value=b2b_req)
    mock_repo.get_by_id_for_owner = AsyncMock(return_value=None)  # User doesn't own this organizer

    service = OrganizerService(mock_repo)

    wrong_organizer_id = uuid4()
    correct_user_id = uuid4()
    b2b_request_id = uuid4()

    with pytest.raises(ForbiddenError):
        await service.confirm_b2b_payment(
            request_id=b2b_request_id,
            organizer_id=wrong_organizer_id,
            user_id=correct_user_id,
        )
