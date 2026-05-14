# next_ticket_index Atomic Increment Fix

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the read-modify-write race condition on `next_ticket_index` with an atomic DB-level `UPDATE ... RETURNING` in all 4 locations where B2B and regular tickets are minted.

**Architecture:** Add a single `increment_next_ticket_index(event_day_id, quantity)` method to `EventRepository` (the same class that already owns `get_event_day_by_id`) that performs an atomic `UPDATE event_days SET next_ticket_index = next_ticket_index + quantity RETURNING next_ticket_index - quantity`. Then replace all 4 Python-side read-then-increment patterns with calls to this method.

**Tech Stack:** SQLAlchemy 2.0 async, PostgreSQL, Python 3.11+

---

## How It Works: Before vs After

### Before (broken — read-modify-write race)

```
TicketingService.allocate_ticket_type_to_day()
│
├─ day = await event_day_repository.get_event_day_by_id(id)    # TX1: READ next_ticket_index = 500
├─ start_index = day.next_ticket_index                          # start_index = 500
├─ bulk_create_tickets(start_index=500, qty=100)                # creates tickets 500-599
│
│  ⚠️  At this moment, another request (TX2) can also read next_ticket_index = 500
│      and create tickets with the SAME indices → constraint violation → rollback
│
├─ day.next_ticket_index += 100                                 # Python writes 600 (but TX2 already read 500!)
└─ session.flush()                                              # ORM flushes the dirty day object
```

Multiple concurrent requests all read the same `next_ticket_index`, create tickets with overlapping indices, and the DB constraint violation causes transaction rollbacks. Under load, the identity map accumulates thousands of ORM objects from failed transactions → RAM exhaustion.

### After (correct — atomic DB-level increment)

```
TicketingService.allocate_ticket_type_to_day()
│
├─ start_index = await event_repository.increment_next_ticket_index(id, 100)
│                  └─ DB: UPDATE event_days
│                     SET next_ticket_index = next_ticket_index + 100
│                     RETURNING next_ticket_index - 100
│                  └─ Returns 500 (the value BEFORE increment)
│                  └─ DB now shows next_ticket_index = 600 (atomically)
│
│  ✅  Any concurrent request must wait for the UPDATE lock — no race possible
│
├─ bulk_create_tickets(start_index=500, qty=100)                # creates tickets 500-599
│  ✅  next_ticket_index is already 600 in the DB — no overlap
└─ (no dirty ORM object to flush — the increment happened in the DB directly)
```

The `SELECT FOR UPDATE` implicit in the `UPDATE` statement serializes concurrent access. Each request gets a unique, non-overlapping range.

---

## File Map

```
src/apps/event/repository.py         — Add atomic increment method (same class that has get_event_day_by_id)
src/apps/ticketing/service.py        — Fix 2 call sites (allocate_ticket_type_to_day, update_allocation_quantity)
src/apps/superadmin/service.py       — Fix 2 call sites (approve_b2b_request_free, process_paid_b2b_allocation)
src/apps/event/models.py             — Read EventDayModel for reference
src/apps/ticketing/repository.py      — Read bulk_create_tickets for context
tests/apps/event/test_repository.py  — Add test for atomic increment
```

---

## Task 1: Add `increment_next_ticket_index` to EventRepository

**Files:**
- Modify: `src/apps/event/repository.py:88-114`

- [ ] **Step 1: Read the current EventRepository methods**

Run: `grep -n "async def" src/apps/event/repository.py | head -20`

Expected output: list of async methods in the repository

- [ ] **Step 2: Add the atomic increment method to EventRepository**

Find the `get_event_day_by_id` method at line 88 and add the new method after it.

```python
async def increment_next_ticket_index(self, event_day_id: UUID, quantity: int) -> int:
    """
    Atomically increment next_ticket_index and return the start index (value BEFORE increment).
    This prevents the read-modify-write race condition that occurs when multiple
    ticket-creation operations run concurrently.
    """
    result = await self._session.execute(
        update(EventDayModel)
        .where(EventDayModel.id == event_day_id)
        .values(next_ticket_index=EventDayModel.next_ticket_index + quantity)
        .returning(EventDayModel.next_ticket_index)
    )
    # Return value BEFORE increment = start_index for new tickets
    return result.scalar_one() - quantity
```

The method should be added after `get_event_day_by_id` (around line 94).

- [ ] **Step 3: Verify the import for `update` is present**

Check that `from sqlalchemy import update` is at the top of the file. If not, add it alongside the existing sqlalchemy imports.

Run: `head -15 src/apps/event/repository.py`

Expected: `from sqlalchemy import select` is present. Add `update` if missing.

- [ ] **Step 4: Run a basic syntax check**

Run: `cd /home/web-h-063/Documents/ticket-shicket-be && python3 -c "from apps.event.repository import EventRepository; print('OK')"`

Expected: `OK` with no errors

- [ ] **Step 5: Commit**

```bash
git add src/apps/event/repository.py
git commit -m "feat(event): add atomic increment_next_ticket_index method
"
```

---

## Task 2: Fix `allocate_ticket_type_to_day` in TicketingService

**Files:**
- Modify: `src/apps/ticketing/service.py:101-109`

- [ ] **Step 1: Read the current code around lines 101-109**

```python
await self.repository.bulk_create_tickets(
    event_id,
    event_day_id,
    ticket_type_id,
    start_index=day.next_ticket_index,
    quantity=quantity,
)
day.next_ticket_index += quantity
await self.repository.session.flush()
```

- [ ] **Step 2: Replace with atomic increment call**

Replace all 3 lines (bulk_create_tickets + day.next_ticket_index increment + flush) with:

```python
start_index = await self.repository.increment_next_ticket_index(event_day_id, quantity)
await self.repository.bulk_create_tickets(
    event_id,
    event_day_id,
    ticket_type_id,
    start_index=start_index,
    quantity=quantity,
)
```

The `session.flush()` is removed — it was flushing the ORM dirty state of `day.next_ticket_index += quantity`, which is no longer needed since the atomic method commits the increment directly in the DB.

- [ ] **Step 3: Verify the fix compiles**

Run: `cd /home/web-h-063/Documents/ticket-shicket-be && python3 -c "from apps.ticketing.service import TicketingService; print('OK')"`

Expected: `OK`

- [ ] **Step 4: Commit**

```bash
git add src/apps/ticketing/service.py
git commit -m "fix(ticketing): atomic next_ticket_index in allocate_ticket_type_to_day
"
```

---

## Task 3: Fix `update_allocation_quantity` in TicketingService

**Files:**
- Modify: `src/apps/ticketing/service.py:145-157`

- [ ] **Step 1: Read the current code around lines 145-159**

```python
quantity_increase = new_quantity - allocation.quantity
await self.repository.bulk_create_tickets(
    event_id,
    allocation.event_day_id,
    allocation.ticket_type_id,
    start_index=day.next_ticket_index,
    quantity=quantity_increase,
)

# C4: Update allocation and day state
allocation.quantity = new_quantity
day.next_ticket_index += quantity_increase
await self.repository.session.flush()
await self.repository.session.refresh(allocation)
return allocation
```

- [ ] **Step 2: Replace with atomic increment call**

Replace the bulk_create_tickets call and the `day.next_ticket_index += quantity_increase` line:

```python
quantity_increase = new_quantity - allocation.quantity
start_index = await self.repository.increment_next_ticket_index(
    allocation.event_day_id, quantity_increase
)
await self.repository.bulk_create_tickets(
    event_id,
    allocation.event_day_id,
    allocation.ticket_type_id,
    start_index=start_index,
    quantity=quantity_increase,
)

# C4: Update allocation and day state
allocation.quantity = new_quantity
```

The `day.next_ticket_index += quantity_increase` and `session.flush()` are removed — the atomic increment already happened in the DB. `session.refresh(allocation)` remains to refresh the allocation object after the quantity change.

- [ ] **Step 3: Verify the fix compiles**

Run: `cd /home/web-h-063/Documents/ticket-shicket-be && python3 -c "from apps.ticketing.service import TicketingService; print('OK')"`

Expected: `OK`

- [ ] **Step 4: Commit**

```bash
git add src/apps/ticketing/service.py
git commit -m "fix(ticketing): atomic next_ticket_index in update_allocation_quantity
"
```

---

## Task 4: Fix `approve_b2b_request_free` in SuperAdminService

**Files:**
- Modify: `src/apps/superadmin/service.py:119-137`

- [ ] **Step 1: Read the current code around lines 119-137**

```python
# Get event day to find next_ticket_index
day = await self._event_repo.get_event_day_by_id(b2b_request.event_day_id)
if not day:
    raise SuperAdminError(f"Event day {b2b_request.event_day_id} not found")

start_index = day.next_ticket_index

# Create tickets on-the-fly (B2B tickets don't exist in pool)
tickets = await self._ticketing_repo.bulk_create_tickets(
    event_id=b2b_request.event_id,
    event_day_id=b2b_request.event_day_id,
    ticket_type_id=b2b_ticket_type.id,
    start_index=start_index,
    quantity=b2b_request.quantity,
)
ticket_ids = [t.id for t in tickets]

# Update day next_ticket_index
day.next_ticket_index += b2b_request.quantity
```

- [ ] **Step 2: Replace with atomic increment call**

Replace the get_event_day_by_id call, the start_index read, and the `day.next_ticket_index +=` line:

```python
# Atomically get next_ticket_index and increment in one DB operation
start_index = await self._event_repo.increment_next_ticket_index(
    b2b_request.event_day_id, b2b_request.quantity
)

# Create tickets on-the-fly (B2B tickets don't exist in pool)
tickets = await self._ticketing_repo.bulk_create_tickets(
    event_id=b2b_request.event_id,
    event_day_id=b2b_request.event_day_id,
    ticket_type_id=b2b_ticket_type.id,
    start_index=start_index,
    quantity=b2b_request.quantity,
)
ticket_ids = [t.id for t in tickets]
```

The `day.next_ticket_index += b2b_request.quantity` line is removed entirely — the atomic increment already happened in the DB.

- [ ] **Step 3: Verify the fix compiles**

Run: `cd /home/web-h-063/Documents/ticket-shicket-be && python3 -c "from apps.superadmin.service import SuperAdminService; print('OK')"`

Expected: `OK`

- [ ] **Step 4: Commit**

```bash
git add src/apps/superadmin/service.py
git commit -m "fix(superadmin): atomic next_ticket_index in approve_b2b_request_free
"
```

---

## Task 5: Fix `process_paid_b2b_allocation` in SuperAdminService

**Files:**
- Modify: `src/apps/superadmin/service.py:353-371`

- [ ] **Step 1: Read the current code around lines 353-371**

```python
# Get event day to find next_ticket_index
day = await self._event_repo.get_event_day_by_id(b2b_request.event_day_id)
if not day:
    raise SuperAdminError(f"Event day {b2b_request.event_day_id} not found")

start_index = day.next_ticket_index

# Create tickets on-the-fly (B2B tickets don't exist in pool)
tickets = await self._ticketing_repo.bulk_create_tickets(
    event_id=b2b_request.event_id,
    event_day_id=b2b_request.event_day_id,
    ticket_type_id=b2b_ticket_type.id,
    start_index=start_index,
    quantity=b2b_request.quantity,
)
ticket_ids = [t.id for t in tickets]

# Update day next_ticket_index
day.next_ticket_index += b2b_request.quantity
```

- [ ] **Step 2: Replace with atomic increment call**

```python
# Atomically get next_ticket_index and increment in one DB operation
start_index = await self._event_repo.increment_next_ticket_index(
    b2b_request.event_day_id, b2b_request.quantity
)

# Create tickets on-the-fly (B2B tickets don't exist in pool)
tickets = await self._ticketing_repo.bulk_create_tickets(
    event_id=b2b_request.event_id,
    event_day_id=b2b_request.event_day_id,
    ticket_type_id=b2b_ticket_type.id,
    start_index=start_index,
    quantity=b2b_request.quantity,
)
ticket_ids = [t.id for t in tickets]
```

- [ ] **Step 3: Verify the fix compiles**

Run: `cd /home/web-h-063/Documents/ticket-shicket-be && python3 -c "from apps.superadmin.service import SuperAdminService; print('OK')"`

Expected: `OK`

- [ ] **Step 4: Commit**

```bash
git add src/apps/superadmin/service.py
git commit -m "fix(superadmin): atomic next_ticket_index in process_paid_b2b_allocation
"
```

---

## Task 6: Verify No Other Call Sites Remain

**Files:**
- Modify: None (verification only)

- [ ] **Step 1: Search for any remaining usages of `next_ticket_index` that are not atomic**

Run: `grep -rn "next_ticket_index" src/apps --include="*.py" | grep -v "__pycache__"`

Expected output: All results should be either:
- `next_ticket_index=` (assignment/initialization — OK)
- `next_ticket_index=1` (migration default — OK)
- `increment_next_ticket_index(` (new atomic method — OK)
- `.returning(EventDayModel.next_ticket_index)` (inside the atomic method — OK)

Any pattern like `day.next_ticket_index` followed by `+=` without going through `increment_next_ticket_index` is a remaining bug.

- [ ] **Step 2: Check the four fixed locations are all gone**

Run: `grep -n "day.next_ticket_index +=" src/apps/ticketing/service.py src/apps/superadmin/service.py`

Expected output: no results (the `+=` patterns should be gone)

- [ ] **Step 3: Commit verification**

```bash
git add -A
git commit -m "chore: verify no remaining next_ticket_index race conditions
"
```

---

## Self-Review Checklist

- [ ] All 4 call sites now use `increment_next_ticket_index`
- [ ] No `day.next_ticket_index +=` or `day.next_ticket_index = day.next_ticket_index +` patterns remain in ticketing/service.py or superadmin/service.py
- [ ] `EventRepository.increment_next_ticket_index` uses `UPDATE ... RETURNING` with the pre-increment value
- [ ] `bulk_create_tickets` receives the returned `start_index` (not the ORM object's `next_ticket_index`)
- [ ] The `day` ORM object is no longer used for reading `next_ticket_index` in any of the 4 locations
- [ ] All files compile with no import errors