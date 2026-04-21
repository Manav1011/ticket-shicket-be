import pytest
from uuid import uuid4
from unittest.mock import AsyncMock, MagicMock
from apps.allocation.repository import RevokedScanTokenRepository


@pytest.mark.asyncio
async def test_add_revoked_inserts_jti():
    session = AsyncMock()
    repo = RevokedScanTokenRepository(session)

    await repo.add_revoked(
        event_day_id=uuid4(),
        jti="test_jti_123",
        reason="split",
    )

    session.execute.assert_awaited_once()


@pytest.mark.asyncio
async def test_is_revoked_returns_true_when_revoked():
    session = AsyncMock()
    jti = "revoked_jti"
    event_day_id = uuid4()

    session.scalar = AsyncMock(return_value=jti)
    repo = RevokedScanTokenRepository(session)

    result = await repo.is_revoked(event_day_id, jti)

    assert result is True


@pytest.mark.asyncio
async def test_is_revoked_returns_false_when_not_revoked():
    session = AsyncMock()
    event_day_id = uuid4()

    session.scalar = AsyncMock(return_value=None)
    repo = RevokedScanTokenRepository(session)

    result = await repo.is_revoked(event_day_id, "unknown_jti")

    assert result is False


@pytest.mark.asyncio
async def test_get_revoked_jtis_for_event_day():
    session = AsyncMock()
    event_day_id = uuid4()
    jtis = ["jti_1", "jti_2", "jti_3"]

    mock_scalars = MagicMock()
    mock_scalars.all.return_value = jtis
    session.scalars = AsyncMock(return_value=mock_scalars)
    repo = RevokedScanTokenRepository(session)

    result = await repo.get_revoked_jtis_for_event_day(event_day_id)

    assert result == jtis
