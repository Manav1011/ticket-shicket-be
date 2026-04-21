import pytest
from uuid import uuid4
from unittest.mock import AsyncMock, MagicMock
from apps.allocation.repository import ClaimLinkRepository
from apps.allocation.enums import ClaimLinkStatus


@pytest.mark.asyncio
async def test_create_claim_link():
    session = AsyncMock()
    repo = ClaimLinkRepository(session)

    result = await repo.create(
        allocation_id=uuid4(),
        token_hash="abc12345",
        event_id=uuid4(),
        from_holder_id=None,
        to_holder_id=uuid4(),
        created_by_holder_id=uuid4(),
    )

    session.add.assert_called_once()
    session.flush.assert_awaited_once()
    assert result.status == ClaimLinkStatus.active


@pytest.mark.asyncio
async def test_get_by_token_hash_returns_link():
    session = AsyncMock()
    token_hash = "test_token"
    mock_link = MagicMock()
    mock_link.token_hash = token_hash

    session.scalar = AsyncMock(return_value=mock_link)
    repo = ClaimLinkRepository(session)

    result = await repo.get_by_token_hash(token_hash)

    assert result == mock_link
    session.scalar.assert_awaited_once()


@pytest.mark.asyncio
async def test_revoke_sets_status_to_inactive():
    session = AsyncMock()
    mock_result = MagicMock()
    mock_result.rowcount = 1
    session.execute = AsyncMock(return_value=mock_result)
    repo = ClaimLinkRepository(session)

    success = await repo.revoke("abc12345")

    assert success is True
    session.execute.assert_awaited_once()
