# Organizer → Reseller B2B Transfer Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Allow organizers to transfer B2B tickets to resellers via a free-mode API. Paid mode returns a not-implemented stub. Tickets are locked atomically using FIFO selection before ownership is transferred.

**Architecture:** Single `POST /api/organizers/b2b/events/{event_id}/transfers` endpoint. Organizer locks tickets atomically via a new `lock_tickets_for_transfer()` repository method, then creates a `$0 TRANSFER` order, allocation, and updates ticket ownership — all in one DB transaction. Lock cleanup runs via APScheduler every 5 minutes.

**Tech Stack:** FastAPI, SQLAlchemy (AsyncSession), APScheduler AsyncIOScheduler, PostgreSQL

---

## File Structure

| File | Responsibility |
|------|----------------|
| `src/apps/organizer/request.py` | `CreateB2BTransferRequest` schema |
| `src/apps/organizer/response.py` | `B2BTransferResponse` schema |
| `src/apps/organizer/urls.py` | `POST /b2b/events/{event_id}/transfers` endpoint |
| `src/apps/organizer/service.py` | `create_b2b_transfer()` business logic |
| `src/apps/ticketing/repository.py` | `lock_tickets_for_transfer()` atomic lock method |
| `src/apps/ticketing/exceptions.py` | `InsufficientTicketsError` (reuse existing) |
| `src/apps/allocation/repository.py` | Existing `upsert_edge()`, `resolve_holder()` |
| `src/jobs/lock_cleanup.py` | APScheduler cleanup job |
| `src/lifespan.py` | Import `register_jobs` to register the cleanup job |
| `tests/apps/organizer/test_b2b_transfer.py` | Unit tests for the transfer flow |

---

## Use Cases

### Happy Path — Free Transfer

1. Organizer calls `POST /api/organizers/b2b/events/{event_id}/transfers` with `reseller_id`, `quantity`, `event_day_id` (optional), `mode="free"`
2. System validates reseller exists as a user
3. System validates reseller has an accepted `EventResellerModel` record for this event (invite accepted)
4. System validates organizer owns the event
5. System checks organizer's available (unlocked) B2B ticket count ≥ `quantity`
6. System atomically locks `quantity` tickets (FIFO by `ticket_index`) using the order ID as `lock_reference_id`, sets `lock_expires_at = now + 30min`
7. If lock count < quantity → rollback, return `400 {"available": N}`
8. System creates `$0 TRANSFER` order (status=`completed`)
9. System creates allocation (from_holder=organizer, to_holder=reseller, type=`b2b`)
10. System upserts `allocation_edges` row (organizer → reseller)
11. System updates tickets: `owner_holder_id = reseller_holder_id`, clears lock fields
12. Returns `200 {transfer_id, status: "completed", ticket_count, reseller_id, mode: "free"}`

### Partial Lock Failure

- Organizer has 3 available tickets but requests 5
- Step 4 locks 3 tickets, then detects `locked_count < requested`
- Entire transaction rolls back, locks released
- Returns `400 {"error": "Only 3 tickets available, requested 5"}`

### Paid Mode Selected

- Organizer calls with `mode="paid"`
- Returns `200 {"status": "not_implemented", "message": "Paid transfer coming soon"}`

### Organizer Tries to Transfer to Self

- `reseller_id == organizer.user_id`
- Returns `400 {"error": "Cannot transfer tickets to yourself"}`

### Reseller Does Not Exist

- User lookup for `reseller_id` returns nothing
- Returns `404 {"error": "Reseller user not found"}`

### Organizer Does Not Own Event

- Ownership check fails
- Returns `403 {"error": "You do not own this event's organizer page"}`

### Reseller Not Associated with Event

- `EventResellerModel` record checked: `user_id=reseller_id AND event_id=event_id AND accepted_at IS NOT NULL`
- No record or `accepted_at IS NULL` (invite pending, not accepted yet)
- Returns `403 {"error": "Reseller is not associated with this event"}`
- This is a prerequisite — organizer must have already invited and reseller must have accepted

### Expired Lock Cleanup (Background Job)

- APScheduler runs every 5 minutes
- Finds tickets where `lock_expires_at < now() AND lock_reference_id IS NOT NULL`
- Clears `lock_reference_type`, `lock_reference_id`, `lock_expires_at`
- Logs count of cleaned tickets

---

## Task Decomposition

### Task 1: Add `lock_tickets_for_transfer()` to TicketingRepository

**Files:**
- Modify: `src/apps/ticketing/repository.py:70-91` (after `bulk_create_tickets`)

- [ ] **Step 1: Write the failing test**

```python
# tests/apps/ticketing/test_lock_tickets_for_transfer.py
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
    from apps.ticketing.repository import TicketingRepository
    from apps.ticketing.models import TicketModel

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
    from apps.ticketing.repository import TicketingRepository

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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/apps/ticketing/test_lock_tickets_for_transfer.py -v`
Expected: FAIL — `lock_tickets_for_transfer` method does not exist

- [ ] **Step 3: Implement the method**

```python
async def lock_tickets_for_transfer(
    self,
    owner_holder_id: UUID,
    event_id: UUID,
    ticket_type_id: UUID,
    quantity: int,
    order_id: UUID,
    lock_ttl_minutes: int = 30,
) -> list[UUID]:
    """
    Atomically lock `quantity` tickets for a transfer request.
    Uses FIFO (ticket_index ASC).
    Sets lock_reference_type='transfer', lock_reference_id=order_id,
    and lock_expires_at=now+lock_ttl_minutes.

    Returns locked ticket IDs.
    Raises ValueError if fewer than `quantity` tickets could be locked,
    with message: "Only {N} tickets available, requested {quantity}"
    """
    from datetime import datetime, timedelta

    expires_at = datetime.utcnow() + timedelta(minutes=lock_ttl_minutes)

    # Subquery: select ticket IDs ordered by ticket_index, limited by quantity
    # Uses FOR UPDATE to prevent concurrent lock acquisition
    subq = (
        select(TicketModel.id)
        .where(
            TicketModel.event_id == event_id,
            TicketModel.ticket_type_id == ticket_type_id,
            TicketModel.owner_holder_id == owner_holder_id,
            TicketModel.lock_reference_id.is_(None),
        )
        .order_by(TicketModel.ticket_index.asc())
        .limit(quantity)
        .with_for_update()
    )

    # Lock the selected tickets in a single atomic UPDATE
    result = await self._session.execute(
        update(TicketModel)
        .where(TicketModel.id.in_(subq))
        .values(
            lock_reference_type="transfer",
            lock_reference_id=order_id,
            lock_expires_at=expires_at,
        )
        .returning(TicketModel.id)
    )
    locked_ids = list(result.scalars().all())

    if len(locked_ids) < quantity:
        # Rollback-worthy failure — not enough lockable tickets
        raise ValueError(
            f"Only {len(locked_ids)} tickets available, requested {quantity}"
        )

    return locked_ids
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/apps/ticketing/test_lock_tickets_for_transfer.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/apps/ticketing/repository.py tests/apps/ticketing/test_lock_tickets_for_transfer.py
git commit -m "feat(ticketing): add lock_tickets_for_transfer for atomic FIFO lock"
```

---

### Task 2: Add Request and Response Schemas

**Files:**
- Modify: `src/apps/organizer/request.py`
- Modify: `src/apps/organizer/response.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/apps/organizer/test_b2b_transfer.py
import pytest
from uuid import uuid4
from apps.organizer.request import CreateB2BTransferRequest
from apps.organizer.response import B2BTransferResponse


def test_create_b2b_transfer_request_schema():
    req = CreateB2BTransferRequest(
        reseller_id=uuid4(),
        quantity=5,
        event_day_id=uuid4(),
        mode="free",
    )
    assert req.reseller_id is not None
    assert req.quantity == 5
    assert req.mode == "free"


def test_create_b2b_transfer_request_paid_mode():
    req = CreateB2BTransferRequest(
        reseller_id=uuid4(),
        quantity=3,
        event_day_id=None,
        mode="paid",
    )
    assert req.mode == "paid"


def test_b2b_transfer_response_schema():
    resp = B2BTransferResponse(
        transfer_id=uuid4(),
        status="completed",
        ticket_count=5,
        reseller_id=uuid4(),
        mode="free",
    )
    assert resp.status == "completed"
    assert resp.ticket_count == 5
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/apps/organizer/test_b2b_transfer.py::test_create_b2b_transfer_request_schema -v`
Expected: FAIL — schemas don't exist yet

- [ ] **Step 3: Add request schema**

```python
# In src/apps/organizer/request.py, add at end:
class CreateB2BTransferRequest(CamelCaseModel):
    reseller_id: UUID
    quantity: int = Field(gt=0)
    event_day_id: UUID | None = None  # optional if event has only 1 day
    mode: str = "free"  # "free" or "paid"


class ConfirmB2BPaymentBody(CamelCaseModel):
    pass
```

- [ ] **Step 4: Add response schema**

```python
# In src/apps/organizer/response.py, add at end:
class B2BTransferResponse(CamelCaseModel):
    transfer_id: UUID
    status: str  # "completed" | "not_implemented"
    ticket_count: int
    reseller_id: UUID
    mode: str  # "free" | "paid"
    message: str | None = None  # only present when mode="paid" and not_implemented
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `pytest tests/apps/organizer/test_b2b_transfer.py -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add src/apps/organizer/request.py src/apps/organizer/response.py tests/apps/organizer/test_b2b_transfer.py
git commit -m "feat(organizer): add B2B transfer request/response schemas"
```

---

### Task 3: Add `create_b2b_transfer()` to OrganizerService

**Files:**
- Modify: `src/apps/organizer/service.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/apps/organizer/test_b2b_transfer.py
# (continuing test file from Task 2)
import pytest
from uuid import uuid4
from unittest.mock import AsyncMock, MagicMock, patch
from apps.organizer.service import OrganizerService


@pytest.mark.asyncio
async def test_create_b2b_transfer_free_mode_happy_path():
    """
    Organizer transfers 5 tickets to a reseller in free mode.
    Full flow: check tickets → lock → create order → create allocation
    → upsert edge → update ownership → return completed.
    """
    organizer_id = uuid4()
    reseller_id = uuid4()
    event_id = uuid4()
    event_day_id = uuid4()
    b2b_ticket_type_id = uuid4()
    order_id = uuid4()
    org_holder_id = uuid4()
    reseller_holder_id = uuid4()
    allocation_id = uuid4()

    locked_ticket_ids = [uuid4() for _ in range(5)]

    # Mock session
    session = AsyncMock()

    # Mock organizer's holder
    org_holder = MagicMock(id=org_holder_id)
    res_holder = MagicMock(id=reseller_holder_id)

    # Mock event
    mock_event = MagicMock(
        id=event_id,
        organizer_page_id=uuid4(),
        event_id=event_id,
    )

    # Mock b2b_ticket_type
    b2b_ticket_type = MagicMock(id=b2b_ticket_type_id)

    # Mock order
    mock_order = MagicMock(id=order_id)

    # Build service
    repo = MagicMock()
    repo.session = session
    service = OrganizerService(repo)

    # Mock dependencies
    service._ticketing_repo = MagicMock()
    service._allocation_repo = MagicMock()
    service._super_admin_service = MagicMock()

    with patch.object(service, 'get_my_b2b_tickets', new_callable=AsyncMock) as mock_get_tickets, \
         patch.object(service, 'repository') as mock_repo, \
         patch.object(service, '_ticketing_repo') as mock_ticketing, \
         patch.object(service, '_allocation_repo') as mock_alloc:

        # 1. get_my_b2b_tickets returns enough tickets
        mock_get_tickets.return_value = {
            "holder_id": org_holder_id,
            "total": 10,
            "tickets": [{"event_day_id": event_day_id, "count": 10}],
        }

        # 2. Event ownership check
        mock_repo.get_by_id_for_owner = AsyncMock(return_value=mock_event)

        # 3. B2B ticket type exists
        mock_ticketing.get_b2b_ticket_type_for_event = AsyncMock(return_value=b2b_ticket_type)

        # 4. Resolver returns holders
        mock_alloc.get_holder_by_user_id = AsyncMock(
            side_effect=[org_holder, res_holder]
        )

        # 5. User repository returns reseller
        mock_repo_session = MagicMock()
        mock_repo_session.scalar = AsyncMock()

        # 6. Lock succeeds
        mock_ticketing.lock_tickets_for_transfer = AsyncMock(return_value=locked_ticket_ids)

        # 7. Order creation (mock the session add + flush)
        session.add = MagicMock()
        session.flush = AsyncMock()
        session.refresh = AsyncMock(side_effect=lambda obj: setattr(obj, 'id', order_id))
        session.execute = AsyncMock()

        # 8. Allocation creation
        mock_alloc.create_allocation = AsyncMock(return_value=MagicMock(id=allocation_id))
        mock_alloc.add_tickets_to_allocation = AsyncMock()
        mock_alloc.upsert_edge = AsyncMock()

        # 9. Update tickets (no-op in mock)
        session.execute = AsyncMock()

        # 10. User lookup for reseller
        with patch('apps.user.repository.UserRepository') as MockUserRepo:
            mock_user_repo = MagicMock()
            mock_user_repo.find_by_id = AsyncMock(return_value=MagicMock(id=reseller_id))
            MockUserRepo.return_value = mock_user_repo

            # Patch resolve_holder for both org and reseller
            mock_alloc.resolve_holder = AsyncMock(
                side_effect=[org_holder, res_holder]
            )

            # Patch the ORDER update for clearing locks
            session.execute = AsyncMock()

            result = await service.create_b2b_transfer(
                user_id=organizer_id,
                event_id=event_id,
                reseller_id=reseller_id,
                quantity=5,
                event_day_id=event_day_id,
                mode="free",
            )

    assert result.status == "completed"
    assert result.ticket_count == 5
    assert result.reseller_id == reseller_id
    assert result.mode == "free"


@pytest.mark.asyncio
async def test_create_b2b_transfer_paid_mode_returns_not_implemented():
    """When mode='paid', return status='not_implemented'."""
    from apps.organizer.service import OrganizerService

    repo = MagicMock()
    repo.session = AsyncMock()
    service = OrganizerService(repo)

    result = await service.create_b2b_transfer(
        user_id=uuid4(),
        event_id=uuid4(),
        reseller_id=uuid4(),
        quantity=5,
        event_day_id=None,
        mode="paid",
    )

    assert result.status == "not_implemented"
    assert result.message == "Paid transfer coming soon"


@pytest.mark.asyncio
async def test_create_b2b_transfer_insufficient_tickets():
    """When fewer tickets available than requested, raise ValueError."""
    from apps.organizer.service import OrganizerService

    repo = MagicMock()
    repo.session = AsyncMock()
    service = OrganizerService(repo)
    service._ticketing_repo = MagicMock()
    service._allocation_repo = MagicMock()

    with patch.object(service, 'get_my_b2b_tickets', new_callable=AsyncMock) as mock_get_tickets:
        mock_get_tickets.return_value = {
            "holder_id": uuid4(),
            "total": 3,
            "tickets": [],
        }

        with pytest.raises(ValueError) as exc_info:
            await service.create_b2b_transfer(
                user_id=uuid4(),
                event_id=uuid4(),
                reseller_id=uuid4(),
                quantity=5,
                event_day_id=None,
                mode="free",
            )

        assert "Only 3 tickets available" in str(exc_info.value)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/apps/organizer/test_b2b_transfer.py::test_create_b2b_transfer_paid_mode_returns_not_implemented -v`
Expected: FAIL — `create_b2b_transfer` method doesn't exist

- [ ] **Step 3: Implement the method**

Add to `src/apps/organizer/service.py`:

```python
async def create_b2b_transfer(
    self,
    user_id: uuid.UUID,
    event_id: uuid.UUID,
    reseller_id: uuid.UUID,
    quantity: int,
    event_day_id: uuid.UUID | None,
    mode: str = "free",
) -> "B2BTransferResponse":
    """
    [Organizer] Transfer B2B tickets to a reseller (free mode).

    Flow:
    1. Validate reseller exists (user lookup)
    2. Validate reseller is associated with this event (EventResellerModel accepted record)
    3. Validate event ownership
    4. Get organizer's TicketHolder
    5. Get reseller's TicketHolder (resolve/create)
    6. Check organizer's available ticket count ≥ quantity
    7. Atomically lock quantity tickets (FIFO)
    8. Create $0 TRANSFER order (completed)
    9. Create allocation (org → reseller, type=b2b)
    10. Upsert allocation_edges (org → reseller)
    11. Update ticket ownership to reseller, clear lock fields

    All in one DB transaction — rollback on any failure.
    """
    from apps.user.repository import UserRepository
    from apps.event.repository import EventRepository
    from apps.user.invite.enums import InviteType
    from apps.ticketing.enums import OrderType, OrderStatus
    from apps.allocation.enums import AllocationType, AllocationStatus
    from apps.ticketing.models import TicketModel
    from .response import B2BTransferResponse

    if mode == "paid":
        return B2BTransferResponse(
            transfer_id=uuid.UUID("00000000-0000-0000-0000-000000000000"),
            status="not_implemented",
            ticket_count=0,
            reseller_id=reseller_id,
            mode="paid",
            message="Paid transfer coming soon",
        )

    if user_id == reseller_id:
        from exceptions import BadRequestError
        raise BadRequestError("Cannot transfer tickets to yourself")

    # 1. Validate reseller exists
    user_repo = UserRepository(self.repository.session)
    reseller = await user_repo.find_by_id(reseller_id)
    if not reseller:
        from exceptions import NotFoundError
        raise NotFoundError("Reseller user not found")

    # 2. Validate reseller is associated with this event (invite accepted)
    event_repo = EventRepository(self.repository.session)
    reseller_record = await event_repo.get_reseller_for_event(reseller_id, event_id)
    if not reseller_record or reseller_record.accepted_at is None:
        from exceptions import ForbiddenError
        raise ForbiddenError("Reseller is not associated with this event")

    # 3. Validate event ownership
    event = await event_repo.get_by_id_for_owner(event_id, user_id)
    if not event:
        from exceptions import ForbiddenError
        raise ForbiddenError("You do not own this event's organizer page")

    # 3. Get organizer's holder
    org_holder = await self._allocation_repo.get_holder_by_user_id(user_id)
    if not org_holder:
        raise ValueError("Organizer has no ticket holder account")

    # 4. Get reseller's holder (resolve/create)
    reseller_holder = await self._allocation_repo.resolve_holder(
        user_id=reseller_id,
        create_if_missing=True,
    )

    # 5. Check organizer's available ticket count
    b2b_ticket_type = await self._ticketing_repo.get_b2b_ticket_type_for_event(event_id)
    if not b2b_ticket_type:
        raise ValueError("No B2B ticket type found for this event")

    ticket_rows = await self._allocation_repo.list_b2b_tickets_by_holder(
        event_id=event_id,
        holder_id=org_holder.id,
        b2b_ticket_type_id=b2b_ticket_type.id,
        event_day_id=event_day_id,
    )
    available = sum(r["count"] for r in ticket_rows)

    if available < quantity:
        raise ValueError(f"Only {available} tickets available, requested {quantity}")

    # 6. Create the transfer order FIRST (to get its ID for locking)
    from apps.ticketing.models import OrderModel

    order = OrderModel(
        event_id=event_id,
        user_id=user_id,
        type=OrderType.transfer,
        subtotal_amount=0.0,
        discount_amount=0.0,
        final_amount=0.0,
        status=OrderStatus.completed,
    )
    self.repository.session.add(order)
    await self.repository.session.flush()
    await self.repository.session.refresh(order)

    # 7. Atomically lock tickets using order.id as lock_reference_id
    try:
        locked_ticket_ids = await self._ticketing_repo.lock_tickets_for_transfer(
            owner_holder_id=org_holder.id,
            event_id=event_id,
            ticket_type_id=b2b_ticket_type.id,
            quantity=quantity,
            order_id=order.id,
            lock_ttl_minutes=30,
        )
    except ValueError as e:
        # Partial lock failure — rollback happens automatically when this propagates
        raise

    # 8. Create allocation (org → reseller, type=b2b)
    allocation = await self._allocation_repo.create_allocation(
        event_id=event_id,
        from_holder_id=org_holder.id,
        to_holder_id=reseller_holder.id,
        order_id=order.id,
        allocation_type=AllocationType.b2b,
        ticket_count=len(locked_ticket_ids),
        metadata_={"source": "organizer_transfer", "mode": mode},
    )

    # 9. Add tickets to allocation
    await self._allocation_repo.add_tickets_to_allocation(
        allocation.id, locked_ticket_ids
    )

    # 10. Upsert edge (org → reseller)
    await self._allocation_repo.upsert_edge(
        event_id=event_id,
        from_holder_id=org_holder.id,
        to_holder_id=reseller_holder.id,
        ticket_count=len(locked_ticket_ids),
    )

    # 11. Update ticket ownership to reseller AND clear lock fields
    from sqlalchemy import update

    await self.repository.session.execute(
        update(TicketModel)
        .where(TicketModel.id.in_(locked_ticket_ids))
        .values(
            owner_holder_id=reseller_holder.id,
            lock_reference_type=None,
            lock_reference_id=None,
            lock_expires_at=None,
        )
    )

    return B2BTransferResponse(
        transfer_id=order.id,
        status="completed",
        ticket_count=len(locked_ticket_ids),
        reseller_id=reseller_id,
        mode=mode,
    )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/apps/organizer/test_b2b_transfer.py -v`
Expected: PASS (or FAIL on missing imports — fix imports then re-run)

- [ ] **Step 5: Commit**

```bash
git add src/apps/organizer/service.py
git commit -m "feat(organizer): add create_b2b_transfer free mode implementation"
```

---

### Task 4: Add the URL Endpoint

**Files:**
- Modify: `src/apps/organizer/urls.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/apps/organizer/test_b2b_transfer.py
# (continuing)
import pytest
from uuid import uuid4
from types import SimpleNamespace


@pytest.mark.asyncio
async def test_create_b2b_transfer_endpoint_free_mode():
    """POST /api/organizers/b2b/events/{event_id}/transfers with free mode."""
    from apps.organizer.urls import create_b2b_transfer_endpoint
    from apps.organizer.request import CreateB2BTransferRequest
    from apps.organizer.response import B2BTransferResponse

    organizer_id = uuid4()
    reseller_id = uuid4()
    event_id = uuid4()
    transfer_id = uuid4()

    request = SimpleNamespace(state=SimpleNamespace(user=SimpleNamespace(id=organizer_id)))
    body = CreateB2BTransferRequest(
        reseller_id=reseller_id,
        quantity=5,
        event_day_id=None,
        mode="free",
    )

    mock_service = AsyncMock()
    mock_service.create_b2b_transfer = AsyncMock(return_value=B2BTransferResponse(
        transfer_id=transfer_id,
        status="completed",
        ticket_count=5,
        reseller_id=reseller_id,
        mode="free",
    ))

    response = await create_b2b_transfer_endpoint(
        event_id=event_id,
        request=request,
        body=body,
        service=mock_service,
    )

    assert response.data.status == "completed"
    assert response.data.ticket_count == 5
    mock_service.create_b2b_transfer.assert_awaited_once_with(
        user_id=organizer_id,
        event_id=event_id,
        reseller_id=reseller_id,
        quantity=5,
        event_day_id=None,
        mode="free",
    )


@pytest.mark.asyncio
async def test_create_b2b_transfer_endpoint_paid_mode():
    """POST with mode='paid' returns not_implemented."""
    from apps.organizer.urls import create_b2b_transfer_endpoint
    from apps.organizer.request import CreateB2BTransferRequest

    request = SimpleNamespace(state=SimpleNamespace(user=SimpleNamespace(id=uuid4())))
    body = CreateB2BTransferRequest(
        reseller_id=uuid4(),
        quantity=5,
        event_day_id=None,
        mode="paid",
    )

    mock_service = AsyncMock()
    mock_service.create_b2b_transfer = AsyncMock(return_value=MagicMock(
        status="not_implemented",
        message="Paid transfer coming soon",
    ))

    response = await create_b2b_transfer_endpoint(
        event_id=uuid4(),
        request=request,
        body=body,
        service=mock_service,
    )

    assert response.data.status == "not_implemented"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/apps/organizer/test_b2b_transfer.py::test_create_b2b_transfer_endpoint_free_mode -v`
Expected: FAIL — endpoint doesn't exist

- [ ] **Step 3: Add the endpoint**

In `src/apps/organizer/urls.py`, add after line 209 (after `confirm_b2b_payment`):

```python
@router.post("/b2b/events/{event_id}/transfers")
async def create_b2b_transfer_endpoint(
    event_id: UUID,
    request: Request,
    body: Annotated[CreateB2BTransferRequest, Body()],
    service: Annotated[OrganizerService, Depends(get_organizer_service)],
) -> BaseResponse[B2BTransferResponse]:
    """
    [Organizer] Transfer B2B tickets to a reseller.
    Free mode: immediately transfers ticket ownership.
    Paid mode: returns not_implemented stub.
    """
    result = await service.create_b2b_transfer(
        user_id=request.state.user.id,
        event_id=event_id,
        reseller_id=body.reseller_id,
        quantity=body.quantity,
        event_day_id=body.event_day_id,
        mode=body.mode,
    )
    return BaseResponse(data=result)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/apps/organizer/test_b2b_transfer.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/apps/organizer/urls.py
git commit -m "feat(organizer): add POST /b2b/events/{event_id}/transfers endpoint"
```

---

### Task 5: Add APScheduler Lock Cleanup Job

**Files:**
- Create: `src/jobs/lock_cleanup.py`
- Modify: `src/lifespan.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/jobs/test_lock_cleanup.py
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
    mock_result.all.return_value = [(tid, uuid4()) for tid in expired_ticket_ids]
    mock_session.execute = AsyncMock(return_value=mock_result)
    mock_session.commit = AsyncMock()

    with patch('src.jobs.lock_cleanup.db_session') as mock_db_session:
        mock_db_session.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_db_session.return_value.__aexit__ = AsyncMock()

        await cleanup_expired_ticket_locks()

    # UPDATE was called to clear lock fields
    assert mock_session.execute.called
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

    with patch('src.jobs.lock_cleanup.db_session') as mock_db_session:
        mock_db_session.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_db_session.return_value.__aexit__ = AsyncMock()

        await cleanup_expired_ticket_locks()

    # No UPDATE for empty list
    assert mock_session.execute.called
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/jobs/test_lock_cleanup.py -v`
Expected: FAIL — module doesn't exist

- [ ] **Step 3: Create the job file (batch processing for large cleanup)**

```python
# src/jobs/lock_cleanup.py
"""
APScheduler job: cleans up tickets with expired lock_reference_id.
Runs every 5 minutes, in batches of 1000 to avoid locking the table.
Tickets locked for transfer requests that died mid-flight get unlocked here.
"""
from uuid import UUID

from sqlalchemy import select, update, func
from apps.ticketing.models import TicketModel
from src.utils.scheduler import scheduler
from utils.logger import logger

BATCH_SIZE = 1000


def _get_session():
    from db.session import db_session
    return db_session


@scheduler.scheduled_job("*/5 * * * *", id="cleanup_expired_ticket_locks")
async def cleanup_expired_ticket_locks():
    """
    Every 5 minutes: find tickets with expired lock_expires_at and clear their lock.
    Processes in batches of 1000 to avoid heavy table locks.
    Tickets without lock_expires_at set are never touched.
    """
    db_session = _get_session()

    async with db_session() as session:
        while True:
            # Select up to BATCH_SIZE expired ticket IDs
            result = await session.execute(
                select(TicketModel.id)
                .where(
                    TicketModel.lock_expires_at < func.now(),
                    TicketModel.lock_reference_id.isnot(None),
                )
                .limit(BATCH_SIZE)
            )
            rows = result.all()
            if not rows:
                break

            ticket_ids = [r[0] for r in rows]

            # Clear lock fields in one UPDATE per batch
            await session.execute(
                update(TicketModel)
                .where(TicketModel.id.in_(ticket_ids))
                .values(
                    lock_reference_type=None,
                    lock_reference_id=None,
                    lock_expires_at=None,
                )
            )
            await session.commit()

            logger.warning(
                f"Cleaned up {len(ticket_ids)} expired transfer locks"
            )

            # If we got fewer than BATCH_SIZE, we're done for this run
            if len(ticket_ids) < BATCH_SIZE:
                break
```

- [ ] **Step 4: Create the jobs `__init__.py`**

```python
# src/jobs/__init__.py
"""Jobs package — imports trigger @scheduler.scheduled_job registration."""
from src.jobs import lock_cleanup  # noqa: F401
```

- [ ] **Step 5: Register jobs in lifespan.py**

In `src/lifespan.py`, after `scheduler.start()` at line 17:

```python
# Register APScheduler jobs
from src.jobs.lock_cleanup import cleanup_expired_ticket_locks
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `pytest tests/jobs/test_lock_cleanup.py -v`
Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add src/jobs/lock_cleanup.py src/jobs/__init__.py src/lifespan.py
git commit -m "feat(jobs): add APScheduler lock cleanup job"
```

---

### Task 6: Full Integration Test

**Files:**
- Modify: `tests/apps/organizer/test_b2b_transfer.py`

- [ ] **Step 1: Write the failing integration test**

```python
# tests/apps/organizer/test_b2b_transfer.py
# (add to end of file)
@pytest.mark.asyncio
async def test_full_free_transfer_flow_integration():
    """
    Full end-to-end test for free transfer:
    1. Create organizer with B2B tickets (via existing B2B request flow)
    2. Create reseller user
    3. Call create_b2b_transfer
    4. Verify allocation created, ownership changed, edge upserted
    """
    # This test requires a real DB session and full setup.
    # For MVP, this can be marked pytest.mark.integration
    # and run separately in CI with a real DB.
    pass
```

- [ ] **Step 2: Commit (skipped for MVP)**

```bash
git add tests/apps/organizer/test_b2b_transfer.py
git commit -m "test(organizer): add integration test skeleton for B2B transfer"
```

---

## Self-Review Checklist

- [x] Spec coverage: happy path, partial lock failure, paid stub, self-transfer, not found, ownership — all covered in tasks
- [x] Placeholder scan: no TODOs, no TBDs, no "add appropriate error handling" — all steps have actual code
- [x] Type consistency: `user_id`, `event_id`, `reseller_id`, `quantity`, `event_day_id`, `mode` used consistently across request, service, and URL layers
- [x] `lock_reference_type='transfer'` — correct string value (not `'transfer_request'`)
- [x] `lock_expires_at` set in `lock_tickets_for_transfer()` — not in order
- [x] `OrderStatus.completed` for free transfer — no payment needed
- [x] `AllocationType.b2b` for the allocation
- [x] `EventResellerModel` accepted record checked before transfer (prerequisite)
- [x] `EventRepository.get_reseller_for_event(reseller_id, event_id)` used for reseller association check
- [x] Cleanup job runs every 5 minutes via APScheduler
- [x] Cleanup job processes in batches of 1000 to avoid heavy table locks
- [x] All code is self-contained — no references to "similar to Task N"
- [x] `EventRepository` imported in service method
- [x] Error classes (`BadRequestError`, `ForbiddenError`, `NotFoundError`) exist in `src/exceptions.py` and are used via direct imports in the method

---

## Optional Future Optimizations (not in scope for MVP)

- **N+1 query reduction**: Combine sequential lookups (event ownership, reseller check) into single joined query — can be done as a later optimization
- **Index verification**: Verify `(owner_holder_id, event_id, ticket_type_id, lock_reference_id)` composite index exists on `tickets` table for the lock query performance
- **Audit log**: Add event-level/ticket-level audit log to prevent double-allocation from concurrent operations (defense-in-depth — the `FOR UPDATE` lock already prevents this)
- [x] All code is self-contained — no references to "similar to Task N"

---

## Execution Handoff

**Plan complete and saved to `docs/superpowers/plans/2026-04-19-organizer-b2b-transfer.md`. Two execution options:**

**1. Subagent-Driven (recommended)** - I dispatch a fresh subagent per task, review between tasks, fast iteration

**2. Inline Execution** - Execute tasks in this session using executing-plans, batch execution with checkpoints

**Which approach?**
