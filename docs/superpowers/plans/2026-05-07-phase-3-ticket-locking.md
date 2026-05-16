# Phase 3: Ticket Locking — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add `lock_tickets_for_purchase()` to `TicketingRepository` — FIFO pool-based locking with TTL. Used by `create_order` in Phase 4 before creating the order.

**Architecture:** Lock from the general pool (`owner_holder_id=None`, `lock_reference_id=None`) rather than from a specific holder's tickets. Sets `lock_reference_type='order'`, `lock_reference_id=order_id`, `lock_expires_at=now+TTL`. `clear_locks_for_order(order_id)` already exists in the repo and handles cleanup — it matches on `lock_reference_type='order'` and `lock_reference_id=order_id`.

**Tech Stack:** SQLAlchemy (async), PostgreSQL `FOR UPDATE` for atomic locking.

---

## File Map

| Action | File |
|--------|------|
| Modify | `src/apps/ticketing/repository.py` — add `lock_tickets_for_purchase` |
| Create | `tests/test_ticket_locking.py` — unit tests for pool-based locking |

---

## Context: Existing `lock_tickets_for_transfer`

`lock_tickets_for_transfer` (lines 194–251 in `repository.py`) locks tickets **from a specific holder** (`owner_holder_id=owner_holder_id`). The new method locks from the **pool** (`owner_holder_id=None`).

The key difference:

| | `lock_tickets_for_transfer` | `lock_tickets_for_purchase` (new) |
|---|---|---|
| Source | Specific holder's tickets | General pool |
| Condition | `owner_holder_id == owner_holder_id` | `owner_holder_id IS NULL` |
| `lock_reference_type` | `'transfer'` | `'order'` |

Both use `FOR UPDATE` + atomic UPDATE returning ticket IDs. Both raise `ValueError` if not enough tickets available.

---

## Tasks

### Task 1: Write the Failing Test

**Files:**
- Create: `tests/test_ticket_locking.py`

- [ ] **Step 1: Write failing tests for `lock_tickets_for_purchase`**

```python
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
    holder = TicketHolderModel(id=uuid4(), name="Test Holder")
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
        category=TicketCategory.general,
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
    for ticket_id in locked_ids:
        ticket = await ticket_repo.session.get(TicketModel, ticket_id)
        assert ticket.lock_reference_type == "order"
        assert ticket.lock_reference_id == order_id


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
    locked_tickets = [await ticket_repo.session.get(TicketModel, tid) for tid in locked_ids]
    assert [t.ticket_index for t in locked_tickets] == [0, 1, 2]


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


async def test_lock_tickets_for_purchase_excludes_owned_tickets(pool_setup, ticket_repo, holder_id):
    """Tickets already owned by a holder (not pool) are not locked."""
    # Give one ticket to a holder
    ticket = pool_setup["tickets"][0]
    ticket.owner_holder_id = holder_id
    await ticket_repo.session.commit()

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
    for tid in locked_ids:
        t = await ticket_repo.session.get(TicketModel, tid)
        assert t.owner_holder_id is None  # never owned by a holder
```

Run: `pytest tests/test_ticket_locking.py -v`
Expected: FAIL — `lock_tickets_for_purchase` not defined yet.

---

### Task 2: Implement `lock_tickets_for_purchase`

**Files:**
- Modify: `src/apps/ticketing/repository.py` — add method after `lock_tickets_for_transfer`

- [ ] **Step 1: Add method to `TicketingRepository`**

Add after `lock_tickets_for_transfer` (around line 251):

```python
async def lock_tickets_for_purchase(
    self,
    event_id: UUID,
    event_day_id: UUID,
    ticket_type_id: UUID,
    quantity: int,
    order_id: UUID,
    lock_ttl_minutes: int = 30,
) -> list[UUID]:
    """
    Atomically lock `quantity` tickets from the pool for a purchase order.
    Uses FIFO (ticket_index ASC).

    Pool tickets: owner_holder_id IS NULL and lock_reference_id IS NULL.
    Sets lock_reference_type='order', lock_reference_id=order_id,
    and lock_expires_at=now+lock_ttl_minutes.

    Returns locked ticket IDs.
    Raises ValueError if fewer than `quantity` tickets could be locked,
    with message: "Only {N} tickets available, requested {quantity}"
    """
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=lock_ttl_minutes)

    # Select pool tickets ordered by ticket_index, limited by quantity
    subq = (
        select(TicketModel.id)
        .where(
            TicketModel.event_id == event_id,
            TicketModel.event_day_id == event_day_id,
            TicketModel.ticket_type_id == ticket_type_id,
            TicketModel.owner_holder_id.is_(None),
            TicketModel.lock_reference_id.is_(None),
        )
        .order_by(TicketModel.ticket_index.asc())
        .limit(quantity)
        .with_for_update()
    )

    # Lock the selected tickets atomically
    result = await self._session.execute(
        update(TicketModel)
        .where(TicketModel.id.in_(subq))
        .values(
            lock_reference_type="order",
            lock_reference_id=order_id,
            lock_expires_at=expires_at,
        )
        .returning(TicketModel.id)
    )
    locked_ids = list(result.scalars().all())

    if len(locked_ids) < quantity:
        raise ValueError(
            f"Only {len(locked_ids)} tickets available, requested {quantity}"
        )

    return locked_ids
```

- [ ] **Step 2: Verify `clear_locks_for_order` handles `'order'` type**

Check `clear_locks_for_order` (line 313–329). It already clears `lock_reference_type.in_(["order", "transfer"])` — no changes needed.

- [ ] **Step 3: Run tests**

```bash
pytest tests/test_ticket_locking.py -v
```

Expected: PASS

- [ ] **Step 4: Commit**

```bash
git add src/apps/ticketing/repository.py tests/test_ticket_locking.py
git commit -m "feat(ticketing): add lock_tickets_for_purchase for pool-based order locking"
```

---

## Verification

1. Run `pytest tests/test_ticket_locking.py -v` — all pass
2. Confirm `clear_locks_for_order(order_id)` clears tickets locked with `lock_reference_type='order'` — already verified by code review
3. `uv run main.py` — no import errors

---

## Follow-up: Integration Check for Phase 4

When `create_order` calls `lock_tickets_for_purchase` before creating the order:

1. If `lock_tickets_for_purchase` raises `ValueError` (not enough tickets) → return 400 to user, no order created
2. If order creation fails after locking → call `clear_locks_for_order(order.id)` to release locks (Phase 4 handles this)

This is pre-wired — no additional work needed in Phase 3.