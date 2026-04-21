import pytest
from uuid import uuid4
from unittest.mock import AsyncMock, MagicMock, patch
from apps.allocation.repository import AllocationRepository, ClaimLinkRepository


@pytest.mark.asyncio
async def test_create_allocation_with_claim_link_returns_both():
    session = AsyncMock()
    repo = AllocationRepository(session)

    event_id = uuid4()
    from_id = uuid4()
    to_id = uuid4()
    order_id = uuid4()
    token_hash = "abc12345"

    # Mock create_allocation to return a mock
    mock_allocation = MagicMock()
    mock_allocation.id = uuid4()

    # Mock ClaimLinkRepository create
    mock_claim_link = MagicMock()
    mock_claim_link.id = uuid4()

    with patch.object(
        repo, "create_allocation", new_callable=AsyncMock, return_value=mock_allocation
    ) as mock_alloc_create:
        with patch.object(
            ClaimLinkRepository, "create", new_callable=AsyncMock, return_value=mock_claim_link
        ) as mock_create:
            result = await repo.create_allocation_with_claim_link(
                event_id=event_id,
                from_holder_id=from_id,
                to_holder_id=to_id,
                order_id=order_id,
                allocation_type="transfer",
                ticket_count=5,
                token_hash=token_hash,
                created_by_holder_id=from_id,
            )

    allocation, claim_link = result
    assert allocation == mock_allocation
    assert claim_link == mock_claim_link
    mock_alloc_create.assert_awaited_once()
    mock_create.assert_awaited_once()
