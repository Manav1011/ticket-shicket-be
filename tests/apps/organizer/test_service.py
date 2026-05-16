import pytest
import uuid
from unittest.mock import AsyncMock, MagicMock

from apps.organizer.service import OrganizerService
from exceptions import ForbiddenError, NotFoundError


@pytest.mark.asyncio
async def test_create_b2b_request_rejects_non_organizer():
    """
    When a user who is not the event organizer calls create_b2b_request,
    the service must raise ForbiddenError.
    """
    # Setup mocks
    mock_repository = AsyncMock()
    mock_ticketing_repo = AsyncMock()
    mock_event_repo = AsyncMock()
    mock_allocation_repo = AsyncMock()
    mock_allocation_service = AsyncMock()

    svc = object.__new__(OrganizerService)
    svc.repository = mock_repository
    svc._ticketing_repo = mock_ticketing_repo
    svc._event_repo = mock_event_repo
    svc._allocation_repo = mock_allocation_repo
    svc._allocation_service = mock_allocation_service

    requesting_user_id = uuid.UUID("33333333-3333-3333-3333-333333333333")
    event_id = uuid.UUID("55555555-5555-5555-5555-555555555555")
    event_day_id = uuid.UUID("44444444-4444-4444-4444-444444444444")
    quantity = 10

    # Mock event where organizer_id is DIFFERENT from requesting_user_id
    mock_event = MagicMock()
    mock_event.id = event_id
    mock_event.organizer_id = uuid.UUID("00000000-0000-0000-0000-000000000000")  # Different user

    mock_event_repo.get_event_by_id = AsyncMock(return_value=mock_event)

    # Expect ForbiddenError
    with pytest.raises(ForbiddenError, match="not the organizer"):
        await svc.create_b2b_request(
            user_id=requesting_user_id,
            event_id=event_id,
            event_day_id=event_day_id,
            quantity=quantity,
        )


@pytest.mark.asyncio
async def test_create_b2b_request_rejects_nonexistent_event():
    """
    When the event doesn't exist, must raise NotFoundError.
    """
    mock_repository = AsyncMock()
    mock_ticketing_repo = AsyncMock()
    mock_event_repo = AsyncMock()
    mock_allocation_repo = AsyncMock()
    mock_allocation_service = AsyncMock()

    svc = object.__new__(OrganizerService)
    svc.repository = mock_repository
    svc._ticketing_repo = mock_ticketing_repo
    svc._event_repo = mock_event_repo
    svc._allocation_repo = mock_allocation_repo
    svc._allocation_service = mock_allocation_service

    requesting_user_id = uuid.UUID("33333333-3333-3333-3333-333333333333")
    event_id = uuid.UUID("55555555-5555-5555-5555-555555555555")
    event_day_id = uuid.UUID("44444444-4444-4444-4444-444444444444")
    quantity = 10

    mock_event_repo.get_event_by_id = AsyncMock(return_value=None)

    with pytest.raises(NotFoundError, match="not found"):
        await svc.create_b2b_request(
            user_id=requesting_user_id,
            event_id=event_id,
            event_day_id=event_day_id,
            quantity=quantity,
        )


@pytest.mark.asyncio
async def test_create_b2b_request_succeeds_for_owner():
    """
    When the user is the event organizer, create_b2b_request succeeds.
    """
    mock_repository = AsyncMock()
    mock_ticketing_repo = AsyncMock()
    mock_event_repo = AsyncMock()
    mock_allocation_repo = AsyncMock()
    mock_allocation_service = AsyncMock()

    svc = object.__new__(OrganizerService)
    svc.repository = mock_repository
    svc._ticketing_repo = mock_ticketing_repo
    svc._event_repo = mock_event_repo
    svc._allocation_repo = mock_allocation_repo
    svc._allocation_service = mock_allocation_service

    requesting_user_id = uuid.UUID("33333333-3333-3333-3333-333333333333")
    event_id = uuid.UUID("55555555-5555-5555-5555-555555555555")
    event_day_id = uuid.UUID("44444444-4444-4444-4444-444444444444")
    quantity = 10

    # Mock event where organizer_id matches requesting_user_id
    mock_event = MagicMock()
    mock_event.id = event_id
    mock_event.organizer_id = requesting_user_id

    mock_event_repo.get_event_by_id = AsyncMock(return_value=mock_event)

    mock_b2b_ticket_type = MagicMock()
    mock_b2b_ticket_type.id = uuid.uuid4()
    mock_ticketing_repo.get_or_create_b2b_ticket_type = AsyncMock(return_value=mock_b2b_ticket_type)

    mock_repository.create_b2b_request = AsyncMock(return_value=MagicMock())

    result = await svc.create_b2b_request(
        user_id=requesting_user_id,
        event_id=event_id,
        event_day_id=event_day_id,
        quantity=quantity,
    )

    # Should succeed and call repository.create_b2b_request
    mock_repository.create_b2b_request.assert_called_once()