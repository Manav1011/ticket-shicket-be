import pytest
from uuid import uuid4
from datetime import datetime, timezone, timedelta
from apps.ticketing.repository import TicketingRepository
from apps.ticketing.models import TicketModel, TicketTypeModel, DayTicketAllocationModel
from apps.ticketing.enums import TicketCategory


@pytest.fixture
async def ticket_repo(db_session):
    return TicketingRepository(db_session)


@pytest.fixture
async def holder_id(db_session):
    """Create a ticket holder to use in tests."""
    from apps.allocation.models import TicketHolderModel
    holder = TicketHolderModel(id=uuid4(), email="test@example.com")
    db_session.add(holder)
    await db_session.flush()
    return holder.id


@pytest.fixture
async def event_day_id(db_session, test_event):
    """Create an event day linked to test_event."""
    from apps.event.models import EventDayModel
    day = EventDayModel(
        id=uuid4(),
        event_id=test_event.id,
        day_index=1,
        date=datetime(2026, 6, 15).date(),
    )
    db_session.add(day)
    await db_session.flush()
    return day.id


@pytest.fixture
async def pool_setup(db_session, test_event, event_day_id):
    """Create ticket type + allocation + 5 pool tickets (owner_holder_id=None)."""
    ticket_type = TicketTypeModel(
        id=uuid4(),
        event_id=test_event.id,
        name="General Admission",
        category=TicketCategory.public,
        price=499.0,
        currency="INR",
    )
    db_session.add(ticket_type)

    allocation = DayTicketAllocationModel(
        id=uuid4(),
        event_day_id=event_day_id,
        ticket_type_id=ticket_type.id,
        quantity=5,
    )
    db_session.add(allocation)

    tickets = [
        TicketModel(
            id=uuid4(),
            event_id=test_event.id,
            event_day_id=event_day_id,
            ticket_type_id=ticket_type.id,
            ticket_index=i,
            owner_holder_id=None,  # pool ticket
            status="active",
        )
        for i in range(5)
    ]
    db_session.add_all(tickets)
    await db_session.flush()
    return {"ticket_type": ticket_type, "tickets": tickets, "event_id": test_event.id, "event_day_id": event_day_id}


@pytest.mark.asyncio
async def test_lock_tickets_for_purchase_locks_from_pool(pool_setup, ticket_repo):
    """Pool tickets (owner_holder_id=None) can be locked for a purchase."""
    ticket_type_id = pool_setup["ticket_type"].id
    order_id = uuid4()

    locked_ids = await ticket_repo.lock_tickets_for_purchase(
        event_id=pool_setup["event_id"],
        event_day_id=pool_setup["event_day_id"],
        ticket_type_id=ticket_type_id,
        quantity=2,
        order_id=order_id,
        lock_ttl_minutes=30,
    )

    assert len(locked_ids) == 2
    # Verify tickets are locked
    ticket_repo.session.expire_all()
    for ticket_id in locked_ids:
        ticket = await ticket_repo.session.get(TicketModel, ticket_id)
        assert ticket.lock_reference_type == "order"
        assert ticket.lock_reference_id == order_id


@pytest.mark.asyncio
async def test_lock_tickets_for_purchase_fifo_order(pool_setup, ticket_repo):
    """Tickets are locked in ticket_index FIFO order."""
    ticket_type_id = pool_setup["ticket_type"].id
    order_id = uuid4()

    locked_ids = await ticket_repo.lock_tickets_for_purchase(
        event_id=pool_setup["event_id"],
        event_day_id=pool_setup["event_day_id"],
        ticket_type_id=ticket_type_id,
        quantity=3,
        order_id=order_id,
    )

    # First 3 tickets (index 0, 1, 2) should be locked
    assert len(locked_ids) == 3
    ticket_repo.session.expire_all()
    locked_tickets = [await ticket_repo.session.get(TicketModel, tid) for tid in locked_ids]
    assert [t.ticket_index for t in locked_tickets] == [0, 1, 2]


@pytest.mark.asyncio
async def test_lock_tickets_for_purchase_respects_quantity(pool_setup, ticket_repo):
    """Cannot lock more tickets than available in pool."""
    ticket_type_id = pool_setup["ticket_type"].id
    order_id = uuid4()

    with pytest.raises(ValueError) as exc_info:
        await ticket_repo.lock_tickets_for_purchase(
            event_id=pool_setup["event_id"],
            event_day_id=pool_setup["event_day_id"],
            ticket_type_id=ticket_type_id,
            quantity=10,  # only 5 in pool
            order_id=order_id,
        )
    assert "Only 5 tickets available" in str(exc_info.value)


@pytest.mark.asyncio
async def test_lock_tickets_for_purchase_excludes_already_locked(pool_setup, ticket_repo):
    """Tickets already locked by another order are skipped."""
    ticket_type_id = pool_setup["ticket_type"].id
    first_order_id = uuid4()
    second_order_id = uuid4()

    # Lock 3 tickets for first order
    await ticket_repo.lock_tickets_for_purchase(
        event_id=pool_setup["event_id"],
        event_day_id=pool_setup["event_day_id"],
        ticket_type_id=ticket_type_id,
        quantity=3,
        order_id=first_order_id,
    )

    # Try to lock 3 more — only 2 remaining
    with pytest.raises(ValueError) as exc_info:
        await ticket_repo.lock_tickets_for_purchase(
            event_id=pool_setup["event_id"],
            event_day_id=pool_setup["event_day_id"],
            ticket_type_id=ticket_type_id,
            quantity=3,
            order_id=second_order_id,
        )
    assert "Only 2 tickets available" in str(exc_info.value)


@pytest.mark.asyncio
async def test_lock_tickets_for_purchase_excludes_owned_tickets(pool_setup, ticket_repo, holder_id):
    """Tickets already owned by a holder (not pool) are not locked."""
    # Give one ticket to a holder
    ticket = pool_setup["tickets"][0]
    ticket.owner_holder_id = holder_id
    await ticket_repo.session.flush()

    ticket_type_id = pool_setup["ticket_type"].id
    order_id = uuid4()

    # Lock 2 tickets — should skip the owned one and get 2 from pool
    locked_ids = await ticket_repo.lock_tickets_for_purchase(
        event_id=pool_setup["event_id"],
        event_day_id=pool_setup["event_day_id"],
        ticket_type_id=ticket_type_id,
        quantity=2,
        order_id=order_id,
    )

    assert len(locked_ids) == 2
    ticket_repo.session.expire_all()
    for tid in locked_ids:
        t = await ticket_repo.session.get(TicketModel, tid)
        assert t.owner_holder_id is None  # never owned by a holder
