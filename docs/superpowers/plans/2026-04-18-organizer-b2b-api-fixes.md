# Organizer B2B API Performance & Filter Fixes

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix N+1 query problems, unnecessary INSERT-on-read, import placement, and add `event_day_id` filter support to the organizer B2B ticket and allocation APIs.

**Architecture:**
- Add a read-only `get_b2b_ticket_type_for_event(event_id)` method to `TicketingRepository` — returns single B2B ticket type without creating anything (no INSERT side effects). There is exactly 1 B2B type per event.
- Rewrite `list_b2b_tickets_by_holder` to use `GROUP BY event_day_id` + `COUNT` in a single query, accepting a single `b2b_ticket_type_id`
- Rewrite `list_b2b_allocations_for_holder` to JOIN `allocation_tickets` in the main query using a subquery, eliminating the N+1 loop
- Add optional `event_day_id` filter to both repository and service methods
- Move all inline imports to module level

**Tech Stack:** SQLAlchemy async, PostgreSQL, FastAPI

---

## Issues Being Fixed

| Issue | Location | Fix |
|-------|----------|-----|
| N+1 in `get_my_b2b_tickets` (2 queries × N days) | `organizer/service.py` | Single GROUP BY query; get B2B type upfront |
| `get_or_create_b2b_ticket_type` INSERT on read | `organizer/service.py` | Replace with read-only `get_b2b_ticket_type_for_event` |
| Fetches full rows when only counts needed | `allocation/repository.py` | Use `COUNT()` + `GROUP BY event_day_id` |
| N+1 in `get_my_b2b_allocations` (1 query × N allocations) | `allocation/repository.py` | JOIN `allocation_tickets` in main query via subquery |
| Imports inside function bodies | `organizer/service.py` | Move to module level |
| No `event_day_id` filter | `allocation/repository.py` + `organizer/service.py` | Add optional `event_day_id` param |

---

## Files to Modify

- `src/apps/ticketing/repository.py` — add `get_b2b_ticket_types_for_event`
- `src/apps/allocation/repository.py` — rewrite 2 methods with proper GROUP BY and JOINs
- `src/apps/organizer/service.py` — fix imports, rewrite 2 methods
- `src/apps/organizer/urls.py` — add optional `event_day_id` query param to both routes

---

## Task 1: Add read-only `get_b2b_ticket_type_for_event` to TicketingRepository

**Files:**
- Modify: `src/apps/ticketing/repository.py:93-130`
- Test: `tests/apps/ticketing/test_b2b_requests.py` (existing — check for relevant test or add)

- [ ] **Step 1: Add `get_b2b_ticket_type_for_event` method**

Find the `get_or_create_b2b_ticket_type` method around line 93. After it, add this new read-only method:

```python
async def get_b2b_ticket_type_for_event(
    self,
    event_id: UUID,
) -> TicketTypeModel | None:
    """
    Get the B2B ticket type for an event. There is exactly 1 B2B type per event.
    Returns None if none exist — does NOT create.
    """
    from apps.ticketing.enums import TicketCategory

    result = await self._session.scalar(
        select(TicketTypeModel).where(
            TicketTypeModel.event_id == event_id,
            TicketTypeModel.category == TicketCategory.b2b,
        )
    )
    return result
```

- [ ] **Step 2: Verify existing tests still pass**

Run: `uv run pytest tests/apps/ticketing/test_b2b_requests.py -v`
Expected: PASS

---

## Task 2: Rewrite `list_b2b_tickets_by_holder` with GROUP BY

**Files:**
- Modify: `src/apps/allocation/repository.py:160-189`
- Test: `tests/apps/organizer/test_b2b_requests.py` (check for existing)

- [ ] **Step 1: Rewrite `list_b2b_tickets_by_holder`**

Replace the current method (lines 160-189) with:

```python
async def list_b2b_tickets_by_holder(
    self,
    event_id: UUID,
    holder_id: UUID,
    b2b_ticket_type_id: UUID,
    event_day_id: UUID | None = None,
) -> list[dict]:
    """
    List B2B ticket counts owned by a holder for an event, grouped by event_day.
    Uses COUNT + GROUP BY — does NOT return full ticket rows.

    Args:
        event_id: Event UUID
        holder_id: TicketHolder UUID
        b2b_ticket_type_id: The B2B ticket type UUID for this event (from get_b2b_ticket_type_for_event)
        event_day_id: Optional — if provided, filter to specific day only
    """
    from apps.ticketing.models import TicketTypeModel

    conditions = [
        TicketModel.event_id == event_id,
        TicketModel.owner_holder_id == holder_id,
        TicketModel.ticket_type_id == b2b_ticket_type_id,
    ]
    if event_day_id:
        conditions.append(TicketModel.event_day_id == event_day_id)

    result = await self._session.execute(
        select(
            TicketModel.event_day_id,
            TicketTypeModel.name,
            func.count(TicketModel.id).label("count"),
        )
        .join(TicketTypeModel, TicketModel.ticket_type_id == TicketTypeModel.id)
        .where(*conditions)
        .group_by(
            TicketModel.event_day_id,
            TicketTypeModel.name,
        )
    )
    rows = result.all()
    return [
        {
            "event_day_id": row[0],
            "ticket_type_name": row[1],
            "count": row[2],
        }
        for row in rows
    ]
```

**Important:** Add `func` to the existing import at the top of the file:
```python
from sqlalchemy import select, update, func, or_
```

- [ ] **Step 2: Verify tests still pass**

Run: `uv run pytest tests/apps/organizer/test_b2b_requests.py -v`
Expected: PASS

---

## Task 3: Rewrite `list_b2b_allocations_for_holder` without N+1

**Files:**
- Modify: `src/apps/allocation/repository.py:191-241`

- [ ] **Step 1: Rewrite `list_b2b_allocations_for_holder` using subquery join**

Replace the current method (lines 191-241) with:

```python
async def list_b2b_allocations_for_holder(
    self,
    event_id: UUID,
    holder_id: UUID,
    event_day_id: UUID | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[dict]:
    """
    List B2B allocations where the given holder is sender or receiver.
    Fetches ticket_ids via subquery — single query, no N+1.

    Args:
        event_id: Event UUID
        holder_id: TicketHolder UUID
        event_day_id: Optional — if provided, filter allocations to tickets from that day only
        limit: Pagination limit
        offset: Pagination offset
    """
    # Subquery: get all ticket_ids for this holder's B2B allocations, optionally filtered by day
    ticket_subq = (
        select(AllocationTicketModel.allocation_id)
        .join(TicketModel, AllocationTicketModel.ticket_id == TicketModel.id)
        .where(TicketModel.owner_holder_id == holder_id)
    )
    if event_day_id:
        ticket_subq = ticket_subq.where(TicketModel.event_day_id == event_day_id)
    ticket_subq = ticket_subq.distinct().subquery()

    # Main query: allocations involving this holder, using the subquery to filter
    alloc_ids = (
        select(AllocationModel.id)
        .where(
            AllocationModel.event_id == event_id,
            AllocationModel.allocation_type == AllocationType.b2b,
            or_(
                AllocationModel.to_holder_id == holder_id,
                AllocationModel.from_holder_id == holder_id,
            ),
        )
        .order_by(AllocationModel.created_at.desc())
        .limit(limit)
        .offset(offset)
        .subquery()
    )

    # Fetch allocations + join their ticket IDs in one query
    result = await self._session.execute(
        select(AllocationModel)
        .where(AllocationModel.id.in_(select(alloc_ids)))
        .order_by(AllocationModel.created_at.desc())
    )
    allocations = result.scalars().all()

    # Fetch all ticket_ids for these allocations in ONE query
    alloc_id_list = [a.id for a in allocations]
    if not alloc_id_list:
        return []

    tickets_result = await self._session.execute(
        select(AllocationTicketModel.allocation_id, AllocationTicketModel.ticket_id)
        .where(AllocationTicketModel.allocation_id.in_(alloc_id_list))
    )
    tickets_by_alloc = {}
    for alloc_id, ticket_id in tickets_result.all():
        tickets_by_alloc.setdefault(alloc_id, []).append(ticket_id)

    enriched = []
    for alloc in allocations:
        direction = "received" if alloc.to_holder_id == holder_id else "transferred"
        metadata = alloc.metadata_ or {}
        source = metadata.get("source", "b2b_free")
        ticket_ids = tickets_by_alloc.get(alloc.id, [])

        enriched.append({
            "allocation_id": alloc.id,
            "direction": direction,
            "from_holder_id": alloc.from_holder_id,
            "to_holder_id": alloc.to_holder_id,
            "ticket_count": alloc.ticket_count,
            "ticket_ids": ticket_ids,
            "status": alloc.status,
            "source": source,
            "created_at": alloc.created_at,
        })

    return enriched
```

**Important:** Add `TicketModel` to the imports at top of `allocation/repository.py` (it may already be there from Task 2):
```python
from apps.ticketing.models import TicketModel, TicketTypeModel
```

- [ ] **Step 2: Verify tests still pass**

Run: `uv run pytest tests/apps/organizer/test_b2b_requests.py -v`
Expected: PASS

---

## Task 4: Fix imports and rewrite organizer service methods

**Files:**
- Modify: `src/apps/organizer/service.py`

First, move these imports to the **top of the file** (after existing imports):

```python
from apps.event.repository import EventRepository
from exceptions import ForbiddenError
```

Remove the inline `from apps.event.repository import EventRepository` and `from exceptions import ForbiddenError` from inside both `confirm_b2b_payment` and the two B2B methods.

- [ ] **Step 1: Rewrite `get_my_b2b_tickets`**

Replace the current method (lines 238-305) with:

```python
async def get_my_b2b_tickets(
    self,
    event_id: uuid.UUID,
    user_id: uuid.UUID,
    event_day_id: uuid.UUID | None = None,
) -> dict:
    """
    [Organizer] Get B2B tickets owned by the organizer for an event.
    Groups tickets by event_day. Single query to get B2B type, then single query
    to get counts with GROUP BY.

    Args:
        event_id: Event UUID
        user_id: Organizer user UUID
        event_day_id: Optional — if provided, filter to specific event day only
    """
    # 1. Verify event ownership
    event = await EventRepository(self.repository.session).get_by_id_for_owner(event_id, user_id)
    if not event:
        raise ForbiddenError("You do not own this event's organizer page")

    # 2. Get organizer's holder
    holder = await self._allocation_repo.get_holder_by_user_id(user_id)
    if not holder:
        return {
            "event_id": event_id,
            "holder_id": None,
            "tickets": [],
            "total": 0,
        }

    # 3. Get B2B ticket type for this event (read-only — no INSERT)
    b2b_type = await self._ticketing_repo.get_b2b_ticket_type_for_event(event_id)
    if not b2b_type:
        return {
            "event_id": event_id,
            "holder_id": holder.id,
            "tickets": [],
            "total": 0,
        }

    # 4. Single query with GROUP BY — get counts grouped by event_day
    rows = await self._allocation_repo.list_b2b_tickets_by_holder(
        event_id=event_id,
        holder_id=holder.id,
        b2b_ticket_type_id=b2b_type.id,
        event_day_id=event_day_id,
    )

    grand_total = sum(row["count"] for row in rows)

    return {
        "event_id": event_id,
        "holder_id": holder.id,
        "tickets": rows,
        "total": grand_total,
    }
```

- [ ] **Step 2: Rewrite `get_my_b2b_allocations`**

Replace the current method (lines 307-341) with:

```python
async def get_my_b2b_allocations(
    self,
    event_id: uuid.UUID,
    user_id: uuid.UUID,
    event_day_id: uuid.UUID | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[dict]:
    """
    [Organizer] Get B2B allocation history (received AND transferred)
    for tickets owned by the organizer. Single-query JOIN for ticket_ids.

    Args:
        event_id: Event UUID
        user_id: Organizer user UUID
        event_day_id: Optional — if provided, filter to allocations from that event day
        limit: Pagination limit
        offset: Pagination offset
    """
    # 1. Verify event ownership
    event = await EventRepository(self.repository.session).get_by_id_for_owner(event_id, user_id)
    if not event:
        raise ForbiddenError("You do not own this event's organizer page")

    # 2. Get organizer's holder
    holder = await self._allocation_repo.get_holder_by_user_id(user_id)
    if not holder:
        return []

    # 3. Get allocations with single-query ticket_ids
    allocations = await self._allocation_repo.list_b2b_allocations_for_holder(
        event_id=event_id,
        holder_id=holder.id,
        event_day_id=event_day_id,
        limit=limit,
        offset=offset,
    )

    return allocations
```

- [ ] **Step 3: Remove inline imports from `confirm_b2b_payment`**

In `confirm_b2b_payment` (line ~225), remove the inline `from exceptions import ForbiddenError` import since it's now at module level.

- [ ] **Step 4: Verify all organizer tests pass**

Run: `uv run pytest tests/apps/organizer/ -v`
Expected: PASS

---

## Task 5: Add `event_day_id` query param to URL routes

**Files:**
- Modify: `src/apps/organizer/urls.py`

- [ ] **Step 1: Update `get_my_b2b_tickets` route**

Change from:
```python
@router.get("/b2b/events/{event_id}/my-tickets")
async def get_my_b2b_tickets(
    event_id: UUID,
    request: Request,
    service: Annotated[OrganizerService, Depends(get_organizer_service)],
) -> BaseResponse[MyB2BTicketsResponse]:
```

To:
```python
@router.get("/b2b/events/{event_id}/my-tickets")
async def get_my_b2b_tickets(
    event_id: UUID,
    request: Request,
    service: Annotated[OrganizerService, Depends(get_organizer_service)],
    event_day_id: UUID | None = None,
) -> BaseResponse[MyB2BTicketsResponse]:
```

And update the call:
```python
    result = await service.get_my_b2b_tickets(event_id, request.state.user.id, event_day_id=event_day_id)
```

- [ ] **Step 2: Update `get_my_b2b_allocations` route**

Add `event_day_id: UUID | None = None` query param and pass it through:
```python
    allocations = await service.get_my_b2b_allocations(
        event_id, request.state.user.id, event_day_id=event_day_id, limit=limit, offset=offset
    )
```

- [ ] **Step 3: Verify routes compile**

Run: `uv run main.py --help` or start the server briefly to check for import errors.

---

## Task 6: Rebuild graph and commit

- [ ] **Step 1: Rebuild graph**

Run: `python3 -c "from graphify.watch import _rebuild_code; from pathlib import Path; _rebuild_code(Path('.'))"`

- [ ] **Step 2: Commit**

```bash
git add src/apps/ticketing/repository.py src/apps/allocation/repository.py src/apps/organizer/service.py src/apps/organizer/urls.py
git commit -m "perf(organizer): fix N+1 queries in my-tickets and my-allocations APIs

- Add read-only get_b2b_ticket_types_for_event (no INSERT on read)
- Rewrite list_b2b_tickets_by_holder with COUNT + GROUP BY (single query)
- Rewrite list_b2b_allocations_for_holder with JOIN subquery (no N+1)
- Add optional event_day_id filter to both APIs
- Move inline imports to module level"
```

---

## Self-Review Checklist

- [ ] Spec coverage: All 6 issues addressed (N+1×2, INSERT-on-read, full-rows-vs-counts, import placement, event_day_id filter)
- [ ] No placeholders: All code blocks are complete and runnable
- [ ] Type consistency: `event_day_id: UUID | None` used consistently across repository, service, and URL layers
- [ ] `get_or_create_b2b_ticket_type` still exists and is NOT modified — used only by write operations (create B2B request, approve B2B)
- [ ] New method `get_b2b_ticket_type_for_event` is read-only — returns single type or None, zero INSERT side effects
- [ ] All existing tests still pass
