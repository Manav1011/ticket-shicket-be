from types import SimpleNamespace
from uuid import uuid4
from unittest.mock import AsyncMock, MagicMock

import pytest

from apps.ticketing.exceptions import OpenEventDoesNotSupportTickets
from apps.ticketing.service import TicketingService


@pytest.mark.asyncio
async def test_allocate_day_inventory_generates_ticket_rows():
    event = SimpleNamespace(id=uuid4(), event_access_type="ticketed")
    ticket_type = SimpleNamespace(id=uuid4(), event_id=event.id, name="General")
    event_repo = AsyncMock()
    event_repo.get_by_id_for_owner.return_value = event
    day_repo = AsyncMock()
    day_repo.get_event_day_for_owner.return_value = SimpleNamespace(
        id=uuid4(), event_id=event.id, next_ticket_index=1
    )
    repo = AsyncMock()
    repo.add = MagicMock()
    repo.create_ticket_type.return_value = ticket_type
    repo.session = AsyncMock()
    service = TicketingService(repo, event_repo, day_repo)

    await service.allocate_ticket_type_to_day(
        owner_user_id=uuid4(),
        event_id=event.id,
        event_day_id=day_repo.get_event_day_for_owner.return_value.id,
        ticket_type_id=ticket_type.id,
        quantity=3,
    )

    repo.bulk_create_tickets.assert_awaited_once()


@pytest.mark.asyncio
async def test_open_event_rejects_ticket_type_creation():
    event = SimpleNamespace(id=uuid4(), event_access_type="open")
    repo = AsyncMock()
    repo.add = MagicMock()
    repo.session = AsyncMock()
    event_repo = AsyncMock()
    event_repo.get_by_id_for_owner.return_value = event
    day_repo = AsyncMock()
    service = TicketingService(repo, event_repo, day_repo)

    with pytest.raises(OpenEventDoesNotSupportTickets):
        await service.create_ticket_type(
            owner_user_id=uuid4(),
            event_id=event.id,
            name="General",
            category="PUBLIC",
            price=0,
            currency="INR",
        )


@pytest.mark.asyncio
async def test_list_ticket_setup_returns_ticket_types_and_allocations_for_owner_event():
    owner_id = uuid4()
    event_id = uuid4()
    repo = AsyncMock()
    event_repo = AsyncMock()
    event_repo.get_by_id_for_owner.return_value = SimpleNamespace(
        id=event_id, event_access_type="ticketed"
    )
    repo.list_ticket_types_for_event.return_value = [
        SimpleNamespace(
            id=uuid4(),
            event_id=event_id,
            name="General",
            category="PUBLIC",
            price=0,
            currency="INR",
        )
    ]
    repo.list_allocations_for_event.return_value = [
        SimpleNamespace(id=uuid4(), event_day_id=uuid4(), ticket_type_id=uuid4(), quantity=25)
    ]
    service = TicketingService(repo, event_repo, event_repo)

    ticket_types = await service.list_ticket_types(owner_id, event_id)
    allocations = await service.list_allocations(owner_id, event_id)

    assert len(ticket_types) == 1
    assert len(allocations) == 1
