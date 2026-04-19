import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4


@pytest.mark.asyncio
async def test_cleanup_job_clears_expired_locks():
    """Job finds tickets with expired lock_expires_at and clears lock fields."""
    from src.jobs.lock_cleanup import cleanup_expired_ticket_locks

    expired_ticket_ids = [uuid4(), uuid4()]

    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.all.return_value = [(tid,) for tid in expired_ticket_ids]
    mock_session.execute = AsyncMock(return_value=mock_result)
    mock_session.commit = AsyncMock()

    with patch('db.session.db_session') as mock_db_session:
        mock_db_session.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_db_session.return_value.__aexit__ = AsyncMock(return_value=None)

        await cleanup_expired_ticket_locks()

    # UPDATE was called to clear lock fields
    assert mock_session.execute.call_count >= 1
    mock_session.commit.assert_called()


@pytest.mark.asyncio
async def test_cleanup_job_handles_no_expired_locks():
    """Job runs without error when no locks are expired."""
    from src.jobs.lock_cleanup import cleanup_expired_ticket_locks

    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.all.return_value = []
    mock_session.execute = AsyncMock(return_value=mock_result)
    mock_session.commit = AsyncMock()

    with patch('db.session.db_session') as mock_db_session:
        mock_db_session.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_db_session.return_value.__aexit__ = AsyncMock(return_value=None)

        await cleanup_expired_ticket_locks()

    # execute was called at least once (to query)
    assert mock_session.execute.call_count >= 1


@pytest.mark.asyncio
async def test_cleanup_job_batches_large_lock_sets():
    """Job processes large number of locks in batches of 1000."""
    from src.jobs.lock_cleanup import cleanup_expired_ticket_locks, BATCH_SIZE

    # Create 2500 expired tickets (will need 3 batches)
    batch1_ids = [uuid4() for _ in range(BATCH_SIZE)]
    batch2_ids = [uuid4() for _ in range(BATCH_SIZE)]
    batch3_ids = [uuid4() for _ in range(500)]

    mock_session = AsyncMock()

    # Return tickets in batches of BATCH_SIZE
    call_count = [0]
    async def mock_execute(query):
        call_count[0] += 1
        result_mock = MagicMock()
        
        # First call: SELECT batch 1
        # Second call: UPDATE batch 1
        # Third call: SELECT batch 2
        # Fourth call: UPDATE batch 2
        # Fifth call: SELECT batch 3
        # Sixth call: UPDATE batch 3
        # Seventh call: SELECT empty
        
        if call_count[0] % 2 == 1:  # SELECT query
            batch_num = (call_count[0] - 1) // 2
            if batch_num == 0:
                result_mock.all.return_value = [(tid,) for tid in batch1_ids]
            elif batch_num == 1:
                result_mock.all.return_value = [(tid,) for tid in batch2_ids]
            elif batch_num == 2:
                result_mock.all.return_value = [(tid,) for tid in batch3_ids]
            else:
                result_mock.all.return_value = []
        
        return result_mock

    mock_session.execute = AsyncMock(side_effect=mock_execute)
    mock_session.commit = AsyncMock()

    with patch('db.session.db_session') as mock_db_session:
        mock_db_session.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_db_session.return_value.__aexit__ = AsyncMock(return_value=None)

        await cleanup_expired_ticket_locks()

    # Should have called execute multiple times (SELECTs and UPDATEs)
    # At least 6 times: SELECT, UPDATE, SELECT, UPDATE, SELECT, UPDATE
    assert mock_session.execute.call_count >= 6
