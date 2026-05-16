import pytest
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

from apps.superadmin.service import SuperAdminService
from apps.superadmin.enums import B2BRequestStatus
from apps.superadmin.exceptions import SuperAdminError


@pytest.mark.asyncio
async def test_process_paid_b2b_allocation_rejects_mismatched_order():
    """
    When b2b_request.order_id points to a different order than the one
    fetched via b2b_request.order_id, the service must reject with SuperAdminError.
    """
    # Create mock session and repos
    session = AsyncMock()
    mock_repo = AsyncMock()
    mock_allocation_repo = AsyncMock()
    mock_ticketing_repo = AsyncMock()
    mock_event_repo = AsyncMock()

    # Manually construct SuperAdminService with mocked dependencies
    svc = object.__new__(SuperAdminService)
    svc._session = session
    svc._repo = mock_repo
    svc._allocation_repo = mock_allocation_repo
    svc._ticketing_repo = mock_ticketing_repo
    svc._event_repo = mock_event_repo

    # Create a b2b_request where order_id = UUID("11111111-1111-1111-1111-111111111111")
    b2b_request = MagicMock()
    b2b_request.id = uuid.UUID("22222222-2222-2222-2222-222222222222")
    b2b_request.order_id = uuid.UUID("11111111-1111-1111-1111-111111111111")
    b2b_request.status = B2BRequestStatus.approved_paid
    b2b_request.requesting_user_id = uuid.UUID("33333333-3333-3333-3333-333333333333")
    b2b_request.event_day_id = uuid.UUID("44444444-4444-4444-4444-444444444444")
    b2b_request.event_id = uuid.UUID("55555555-5555-5555-5555-555555555555")
    b2b_request.quantity = 10
    b2b_request.reviewed_by_admin_id = uuid.UUID("66666666-6666-6666-6666-666666666666")

    # Mock get_b2b_request to return the b2b_request
    mock_repo.get_b2b_request_by_id = AsyncMock(return_value=b2b_request)

    # Mock order lookup — returns order with DIFFERENT id
    mock_order = MagicMock()
    mock_order.id = uuid.UUID("99999999-9999-9999-9999-999999999999")  # Different from b2b_request.order_id

    # Mock session.scalar to return the mismatched order
    session.scalar = AsyncMock(return_value=mock_order)

    # Expect SuperAdminError due to order mismatch
    with pytest.raises(SuperAdminError, match="Order mismatch"):
        await svc.process_paid_b2b_allocation(b2b_request.id)