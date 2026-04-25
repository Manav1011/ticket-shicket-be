import pytest
from uuid import uuid4
from unittest.mock import AsyncMock, MagicMock
from src.apps.allocation.repository import AllocationRepository


@pytest.mark.asyncio
async def test_get_holder_by_phone_and_email_returns_holder():
    """Returns holder when phone and email both match."""
    session = AsyncMock()
    repo = AllocationRepository(session)
    mock_holder = MagicMock()
    mock_holder.phone = "+919999999999"
    mock_holder.email = "test@example.com"
    session.scalar = AsyncMock(return_value=mock_holder)

    result = await repo.get_holder_by_phone_and_email("+919999999999", "test@example.com")

    assert result == mock_holder
    session.scalar.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_holder_by_phone_and_email_returns_none():
    """Returns None when no holder matches both."""
    session = AsyncMock()
    repo = AllocationRepository(session)
    session.scalar = AsyncMock(return_value=None)

    result = await repo.get_holder_by_phone_and_email("+919999999999", "test@example.com")

    assert result is None
