import pytest
from uuid import uuid4
from unittest.mock import AsyncMock, MagicMock
from apps.allocation.repository import AllocationRepository


@pytest.mark.asyncio
async def test_resolve_holder_returns_existing_by_phone():
    session = AsyncMock()
    repo = AllocationRepository(session)
    existing_holder = MagicMock()
    existing_holder.id = uuid4()

    session.scalar = AsyncMock(return_value=existing_holder)
    result = await repo.resolve_holder(phone="+919999999999")

    assert result == existing_holder
    session.scalar.assert_awaited()


@pytest.mark.asyncio
async def test_resolve_holder_creates_new_when_not_found():
    session = AsyncMock()
    repo = AllocationRepository(session)

    session.scalar = AsyncMock(return_value=None)
    session.add = MagicMock()
    session.flush = AsyncMock()
    session.refresh = AsyncMock()

    result = await repo.resolve_holder(phone="+919999999999")

    session.add.assert_called_once()
    session.flush.assert_awaited()


@pytest.mark.asyncio
async def test_resolve_holder_prefers_phone_over_email():
    """When holder exists by phone, should return it without checking email."""
    session = AsyncMock()
    repo = AllocationRepository(session)
    existing_holder = MagicMock()

    # First call (phone lookup) returns holder
    session.scalar = AsyncMock(side_effect=[existing_holder, None, None])
    result = await repo.resolve_holder(phone="+919999999999", email="test@test.com")

    assert result == existing_holder
