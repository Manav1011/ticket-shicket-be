import pytest
from uuid import uuid4
from unittest.mock import AsyncMock
from apps.ticketing.repository import TicketingRepository


@pytest.mark.asyncio
async def test_update_ticket_ownership_batch_calls_execute():
    session = AsyncMock()
    repo = TicketingRepository(session)

    ticket_ids = [uuid4(), uuid4()]
    new_owner = uuid4()

    await repo.update_ticket_ownership_batch(ticket_ids, new_owner)

    session.execute.assert_awaited_once()


@pytest.mark.asyncio
async def test_update_ticket_ownership_batch_empty_list():
    session = AsyncMock()
    repo = TicketingRepository(session)

    await repo.update_ticket_ownership_batch([], uuid4())

    session.execute.assert_not_called()
