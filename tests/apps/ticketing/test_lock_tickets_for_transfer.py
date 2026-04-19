import pytest
from uuid import uuid4
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock


@pytest.mark.asyncio
async def test_lock_tickets_for_transfer_partial_lock():
    """
    When fewer tickets are lockable than requested, raise ValueError
    with the actual lockable count.
    """
    from src.apps.ticketing.repository import TicketingRepository
    from src.apps.ticketing.models import TicketModel

    session = AsyncMock()
    org_holder_id = uuid4()
    event_id = uuid4()
    ticket_type_id = uuid4()
    order_id = uuid4()

    repo = TicketingRepository(session)

    # Mock: only 3 tickets are lockable, request is for 5
    result_mock = MagicMock()
    result_mock.scalars.return_value.all.return_value = [uuid4() for _ in range(3)]
    session.execute.return_value = result_mock

    with pytest.raises(ValueError) as exc_info:
        await repo.lock_tickets_for_transfer(
            owner_holder_id=org_holder_id,
            event_id=event_id,
            ticket_type_id=ticket_type_id,
            quantity=5,
            order_id=order_id,
        )

    assert "Only 3 tickets available, requested 5" in str(exc_info.value)


@pytest.mark.asyncio
async def test_lock_tickets_for_transfer_success():
    """
    When enough tickets are lockable, returns list of locked ticket IDs.
    """
    from src.apps.ticketing.repository import TicketingRepository

    session = AsyncMock()
    org_holder_id = uuid4()
    event_id = uuid4()
    ticket_type_id = uuid4()
    order_id = uuid4()

    repo = TicketingRepository(session)

    locked_ids = [uuid4() for _ in range(5)]
    result_mock = MagicMock()
    result_mock.scalars.return_value.all.return_value = locked_ids
    session.execute.return_value = result_mock

    result = await repo.lock_tickets_for_transfer(
        owner_holder_id=org_holder_id,
        event_id=event_id,
        ticket_type_id=ticket_type_id,
        quantity=5,
        order_id=order_id,
    )

    assert result == locked_ids
    assert session.execute.called
