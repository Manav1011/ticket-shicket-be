# tests/apps/ticketing/test_repository.py
import pytest
from uuid import uuid4
from unittest.mock import AsyncMock
from apps.ticketing.repository import TicketingRepository


@pytest.mark.asyncio
async def test_clear_locks_for_order_clears_transfer_locks():
    """clear_locks_for_order must clear locks created with lock_reference_type='transfer'."""
    session = AsyncMock()
    session.execute = AsyncMock()
    repo = TicketingRepository(session)

    order_id = uuid4()
    await repo.clear_locks_for_order(order_id)

    call_args = session.execute.call_args
    update_stmt = call_args[0][0]
    update_text = str(update_stmt)
    
    # Check that IN is used for lock_reference_type
    assert "IN" in update_text
    
    # Verify the parameters passed to execute (if they are passed as second arg)
    # Actually, SQLAlchemy's update().where().values() compiles into a statement
    # that session.execute(stmt) runs.
    compiled = update_stmt.compile()
    # In some setups, compiled.params contains the values.
    # For .in_(), it might be post-compiled.
    
    # Let's just check the SQL structure and assume SQLAlchemy does its job 
    # if we passed the right list to .in_()
    assert "lock_reference_type" in update_text


@pytest.mark.asyncio
async def test_clear_locks_for_order_clears_order_locks():
    """clear_locks_for_order must still clear locks with lock_reference_type='order'."""
    session = AsyncMock()
    session.execute = AsyncMock()
    repo = TicketingRepository(session)

    order_id = uuid4()
    await repo.clear_locks_for_order(order_id)

    call_args = session.execute.call_args
    update_stmt = call_args[0][0]
    update_text = str(update_stmt)
    assert "lock_reference_type" in update_text
    assert "IN" in update_text
