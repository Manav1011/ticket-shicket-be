import pytest
from uuid import uuid4
from unittest.mock import AsyncMock, MagicMock
from apps.ticketing.repository import TicketingRepository


@pytest.mark.asyncio
async def test_select_tickets_for_transfer_returns_ticket_list():
    session = AsyncMock()
    repo = TicketingRepository(session)

    owner_id = uuid4()
    event_id = uuid4()
    ticket_ids = [uuid4(), uuid4()]

    result_mock = MagicMock()
    result_mock.all.return_value = [(ticket_ids[0], 0), (ticket_ids[1], 1)]
    session.execute = AsyncMock(return_value=result_mock)

    result = await repo.select_tickets_for_transfer(
        owner_holder_id=owner_id,
        event_id=event_id,
        quantity=2,
    )

    assert len(result) == 2
    assert result[0]["ticket_id"] == ticket_ids[0]
    assert result[0]["ticket_index"] == 0


@pytest.mark.asyncio
async def test_select_tickets_for_transfer_with_event_day():
    session = AsyncMock()
    repo = TicketingRepository(session)

    result_mock = MagicMock()
    result_mock.all.return_value = []
    session.execute = AsyncMock(return_value=result_mock)

    await repo.select_tickets_for_transfer(
        owner_holder_id=uuid4(),
        event_id=uuid4(),
        quantity=5,
        event_day_id=uuid4(),
    )

    session.execute.assert_awaited_once()
