import pytest
from uuid import uuid4
from unittest.mock import AsyncMock

from apps.ticketing.repository import TicketingRepository


@pytest.mark.asyncio
async def test_update_ownership_batch_sets_claim_link_id():
    """claim_link_id should be included when provided."""
    session = AsyncMock()
    repo = TicketingRepository(session)

    ticket_ids = [uuid4(), uuid4()]
    new_owner_id = uuid4()
    claim_link_id = uuid4()

    await repo.update_ticket_ownership_batch(
        ticket_ids=ticket_ids,
        new_owner_holder_id=new_owner_id,
        claim_link_id=claim_link_id,
    )

    session.execute.assert_awaited_once()
    stmt = session.execute.await_args.args[0]
    assert "claim_link_id" in str(stmt)


@pytest.mark.asyncio
async def test_update_ticket_ownership_batch_empty_list():
    session = AsyncMock()
    repo = TicketingRepository(session)

    await repo.update_ticket_ownership_batch([], uuid4())

    session.execute.assert_not_called()
