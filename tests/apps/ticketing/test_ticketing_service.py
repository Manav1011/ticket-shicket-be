from types import SimpleNamespace
from uuid import uuid4
from unittest.mock import AsyncMock, MagicMock

import pytest

from apps.ticketing.exceptions import OpenEventDoesNotSupportTickets
from apps.ticketing.service import TicketingService


@pytest.mark.asyncio
async def test_allocate_day_inventory_generates_ticket_rows():
    event = SimpleNamespace(id=uuid4(), event_access_type="ticketed", setup_status={})
    ticket_type = SimpleNamespace(id=uuid4(), event_id=event.id, name="General")
    event_repo = AsyncMock()
    event_repo.get_by_id_for_owner.return_value = event
    event_repo.count_ticket_types = AsyncMock(return_value=1)
    event_repo.count_ticket_allocations = AsyncMock(return_value=1)
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
            category="public",
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
            category="public",
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


@pytest.mark.asyncio
async def test_update_allocation_quantity_increases_successfully():
    """Test that we can increase quantity."""
    from apps.ticketing.exceptions import CannotDecreaseQuantity

    owner_id = uuid4()
    event_id = uuid4()
    event_day_id = uuid4()
    allocation_id = uuid4()

    event = SimpleNamespace(id=event_id, event_access_type="ticketed")
    day = SimpleNamespace(
        id=event_day_id, event_id=event_id, next_ticket_index=100
    )
    allocation = SimpleNamespace(
        id=allocation_id,
        event_day_id=event_day_id,
        ticket_type_id=uuid4(),
        quantity=50,
    )

    repo = AsyncMock()
    repo.get_allocation_by_id.return_value = allocation
    repo.bulk_create_tickets = AsyncMock()
    repo.session = AsyncMock()

    event_repo = AsyncMock()
    event_repo.get_by_id_for_owner.return_value = event
    day_repo = AsyncMock()
    day_repo.get_event_day_for_owner.return_value = day

    service = TicketingService(repo, event_repo, day_repo)

    # Update quantity from 50 to 75
    updated = await service.update_allocation_quantity(owner_id, event_id, allocation_id, 75)

    assert updated.quantity == 75
    assert day.next_ticket_index == 125  # 100 + 25
    repo.bulk_create_tickets.assert_awaited_once()


@pytest.mark.asyncio
async def test_update_allocation_quantity_no_change_is_idempotent():
    """Test that same quantity is idempotent."""
    owner_id = uuid4()
    event_id = uuid4()
    event_day_id = uuid4()
    allocation_id = uuid4()

    event = SimpleNamespace(id=event_id, event_access_type="ticketed")
    day = SimpleNamespace(
        id=event_day_id, event_id=event_id, next_ticket_index=100
    )
    allocation = SimpleNamespace(
        id=allocation_id,
        event_day_id=event_day_id,
        ticket_type_id=uuid4(),
        quantity=50,
    )

    repo = AsyncMock()
    repo.get_allocation_by_id.return_value = allocation
    repo.bulk_create_tickets = AsyncMock()
    repo.session = AsyncMock()

    event_repo = AsyncMock()
    event_repo.get_by_id_for_owner.return_value = event
    day_repo = AsyncMock()
    day_repo.get_event_day_for_owner.return_value = day

    service = TicketingService(repo, event_repo, day_repo)

    # Update with same quantity
    updated = await service.update_allocation_quantity(owner_id, event_id, allocation_id, 50)

    assert updated.quantity == 50
    repo.bulk_create_tickets.assert_not_awaited()


@pytest.mark.asyncio
async def test_update_allocation_quantity_rejects_decrease():
    """Test that decreasing quantity raises CannotDecreaseQuantity."""
    from apps.ticketing.exceptions import CannotDecreaseQuantity

    owner_id = uuid4()
    event_id = uuid4()
    event_day_id = uuid4()
    allocation_id = uuid4()

    event = SimpleNamespace(id=event_id, event_access_type="ticketed")
    day = SimpleNamespace(
        id=event_day_id, event_id=event_id, next_ticket_index=100
    )
    allocation = SimpleNamespace(
        id=allocation_id,
        event_day_id=event_day_id,
        ticket_type_id=uuid4(),
        quantity=50,
    )

    repo = AsyncMock()
    repo.get_allocation_by_id.return_value = allocation
    repo.session = AsyncMock()

    event_repo = AsyncMock()
    event_repo.get_by_id_for_owner.return_value = event
    day_repo = AsyncMock()
    day_repo.get_event_day_for_owner.return_value = day

    service = TicketingService(repo, event_repo, day_repo)

    with pytest.raises(CannotDecreaseQuantity):
        await service.update_allocation_quantity(owner_id, event_id, allocation_id, 30)


@pytest.mark.asyncio
async def test_update_allocation_quantity_rejects_zero_or_negative():
    """Test that zero or negative quantities are rejected."""
    from apps.ticketing.exceptions import InvalidQuantity

    owner_id = uuid4()
    event_id = uuid4()
    event_day_id = uuid4()
    allocation_id = uuid4()

    event = SimpleNamespace(id=event_id, event_access_type="ticketed")
    day = SimpleNamespace(
        id=event_day_id, event_id=event_id, next_ticket_index=100
    )
    allocation = SimpleNamespace(
        id=allocation_id,
        event_day_id=event_day_id,
        ticket_type_id=uuid4(),
        quantity=50,
    )

    repo = AsyncMock()
    repo.get_allocation_by_id.return_value = allocation
    repo.session = AsyncMock()

    event_repo = AsyncMock()
    event_repo.get_by_id_for_owner.return_value = event
    day_repo = AsyncMock()
    day_repo.get_event_day_for_owner.return_value = day

    service = TicketingService(repo, event_repo, day_repo)

    with pytest.raises(InvalidQuantity):
        await service.update_allocation_quantity(owner_id, event_id, allocation_id, 0)

    with pytest.raises(InvalidQuantity):
        await service.update_allocation_quantity(owner_id, event_id, allocation_id, -10)


@pytest.mark.asyncio
async def test_update_allocation_quantity_rejects_nonexistent_allocation():
    """Test that updating non-existent allocation raises InvalidAllocation."""
    from apps.ticketing.exceptions import InvalidAllocation

    owner_id = uuid4()
    event_id = uuid4()
    allocation_id = uuid4()

    event = SimpleNamespace(id=event_id, event_access_type="ticketed")

    repo = AsyncMock()
    repo.get_allocation_by_id.return_value = None
    repo.session = AsyncMock()

    event_repo = AsyncMock()
    event_repo.get_by_id_for_owner.return_value = event
    day_repo = AsyncMock()

    service = TicketingService(repo, event_repo, day_repo)

    with pytest.raises(InvalidAllocation):
        await service.update_allocation_quantity(owner_id, event_id, allocation_id, 50)


@pytest.mark.asyncio
async def test_update_allocation_quantity_requires_event_ownership():
    """Test that non-owner cannot update allocation."""
    from apps.ticketing.exceptions import InvalidAllocation

    owner_id = uuid4()
    other_user_id = uuid4()
    event_id = uuid4()
    allocation_id = uuid4()

    repo = AsyncMock()
    repo.session = AsyncMock()

    event_repo = AsyncMock()
    event_repo.get_by_id_for_owner.return_value = None
    day_repo = AsyncMock()

    service = TicketingService(repo, event_repo, day_repo)

    with pytest.raises(InvalidAllocation):
        await service.update_allocation_quantity(other_user_id, event_id, allocation_id, 50)
