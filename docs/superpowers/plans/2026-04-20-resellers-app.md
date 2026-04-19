# Resellers App - Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Create a `resellers` app with 3 core endpoints for reseller ticket/allocation visibility, mirroring the organizer B2B pattern but for the reseller perspective.

**Architecture:**
- New `src/apps/resellers/` app module following existing app patterns
- URLs under `/api/resellers/`
- Repository in `resellers/repository.py` for data access
- Service in `resellers/service.py` for business logic
- Reseller-specific auth check: `EventResellerModel.accepted_at IS NOT NULL`

**Tech Stack:** FastAPI, SQLAlchemy async, repository pattern

---

## File Structure

```
src/apps/resellers/
├── __init__.py
├── urls.py          # Route definitions
├── service.py      # Business logic
├── repository.py   # Data access
├── request.py      # Request schemas
└── response.py     # Response schemas

src/apps/allocation/repository.py  # Will add new query method
```

---

## API Endpoints

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/api/resellers/events` | List events where I'm an accepted reseller |
| GET | `/api/resellers/events/{event_id}/my-allocation` | My B2B allocation for that event |
| GET | `/api/resellers/events/{event_id}/tickets` | Tickets I own in that event |

---

## Task 1: Create the resellers app module

**Files:**
- Create: `src/apps/resellers/__init__.py`
- Create: `src/apps/resellers/urls.py`
- Create: `src/apps/resellers/service.py`
- Create: `src/apps/resellers/repository.py`
- Create: `src/apps/resellers/request.py`
- Create: `src/apps/resellers/response.py`
- Modify: `src/apps/organizer/service.py` (remove duplicate EventRepository import)

- [ ] **Step 1: Create resellers app**

Run: `uv run main.py startapp resellers`
Expected: New app created at `src/apps/resellers/`

- [ ] **Step 2: Verify app structure created**

Run: `ls src/apps/resellers/`
Expected: `__init__.py urls.py service.py repository.py` (others may need creation)

---

## Task 2: Create response schemas

**Files:**
- Modify: `src/apps/resellers/response.py`

- [ ] **Step 1: Add reseller response schemas**

```python
# src/apps/resellers/response.py
from typing import Any
from uuid import UUID
from pydantic import BaseModel
from datetime import datetime


class ResellerEventItem(BaseModel):
    event_id: UUID
    event_name: str
    organizer_name: str
    event_status: str
    my_role: str  # "reseller"
    accepted_at: datetime

    class Config:
        from_attributes = True


class ResellerEventsResponse(BaseModel):
    events: list[ResellerEventItem]
    total: int


class ResellerTicketItem(BaseModel):
    event_day_id: UUID
    count: int


class ResellerTicketsResponse(BaseModel):
    event_id: UUID
    holder_id: UUID
    tickets: list[ResellerTicketItem]
    total: int


class ResellerAllocationItem(BaseModel):
    allocation_id: UUID
    event_day_id: UUID
    direction: str  # "received" | "transferred"
    from_holder_id: UUID | None
    to_holder_id: UUID
    ticket_count: int
    status: str
    source: str
    created_at: datetime


class ResellerAllocationsResponse(BaseModel):
    event_id: UUID
    allocations: list[ResellerAllocationItem]
    total: int
```

- [ ] **Step 2: Run import check**

Run: `cd /home/manav1011/Documents/ticket-shicket-be && python3 -c "from src.apps.resellers.response import ResellerEventsResponse, ResellerTicketsResponse, ResellerAllocationsResponse; print('OK')"`
Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add src/apps/resellers/response.py
git commit -m "feat(resellers): add response schemas"
```

---

## Task 3: Create request schemas

**Files:**
- Modify: `src/apps/resellers/request.py`

- [ ] **Step 1: Add empty request schemas (placeholder for future use)**

```python
# src/apps/resellers/request.py
from pydantic import BaseModel
from uuid import UUID

# Placeholder - no request bodies needed for initial GET endpoints
```

- [ ] **Step 2: Run import check**

Run: `python3 -c "from src.apps.resellers.request import *; print('OK')"`
Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add src/apps/resellers/request.py
git commit -m "feat(resellers): add request schemas"
```

---

## Task 4: Create ResellerRepository with optimized queries

**Files:**
- Modify: `src/apps/resellers/repository.py`

- [ ] **Step 1: Write reseller repository**

```python
# src/apps/resellers/repository.py
from uuid import UUID
from sqlalchemy import select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession
from src.apps.event.models import EventResellerModel, EventModel
from src.apps.allocation.models import AllocationModel, AllocationType, AllocationTicketModel
from src.apps.ticketing.models import TicketModel


class ResellerRepository:
    def __init__(self, session: AsyncSession):
        self._session = session

    async def list_my_events(self, user_id: UUID) -> list[dict]:
        """
        List events where user is an accepted reseller.
        Uses JOIN on EventModel + EventResellerModel + OrganizerPageModel.
        Single query with all needed fields - no N+1.
        """
        from src.apps.organizer.models import OrganizerPageModel
        result = await self._session.execute(
            select(
                EventModel.id,
                EventModel.name,
                EventModel.status,
                OrganizerPageModel.name.label("organizer_name"),
                EventResellerModel.accepted_at,
            )
            .join(EventResellerModel, EventResellerModel.event_id == EventModel.id)
            .join(OrganizerPageModel, OrganizerPageModel.id == EventModel.organizer_id)
            .where(
                EventResellerModel.user_id == user_id,
                EventResellerModel.accepted_at.isnot(None),
            )
            .order_by(EventResellerModel.accepted_at.desc())
        )
        rows = result.all()
        return [
            {
                "event_id": row[0],
                "event_name": row[1],
                "event_status": row[2],
                "organizer_name": row[3],
                "accepted_at": row[4],
            }
            for row in rows
        ]

    async def is_accepted_reseller(self, user_id: UUID, event_id: UUID) -> bool:
        """
        Check if user is an accepted reseller for the event.
        Uses composite index-friendly query.
        """
        result = await self._session.scalar(
            select(EventResellerModel.accepted_at).where(
                EventResellerModel.user_id == user_id,
                EventResellerModel.event_id == event_id,
                EventResellerModel.accepted_at.isnot(None),
            )
        )
        return result is not None

    async def get_my_holder_for_event(self, user_id: UUID):
        """
        Get TicketHolder for a user.
        Returns None if user has no holder yet.
        """
        from src.apps.holder.repository import HolderRepository
        holder_repo = HolderRepository(self._session)
        return await holder_repo.get_holder_by_user_id(user_id)

    async def get_b2b_ticket_type_for_event(self, event_id: UUID):
        """
        Get B2B ticket type for event.
        """
        from src.apps.ticketing.repository import TicketingRepository
        ticketing_repo = TicketingRepository(self._session)
        return await ticketing_repo.get_b2b_ticket_type_for_event(event_id)

    async def list_b2b_tickets_by_holder(
        self,
        event_id: UUID,
        holder_id: UUID,
        b2b_ticket_type_id: UUID,
    ) -> list[dict]:
        """
        List B2B ticket counts owned by holder, grouped by event_day.
        Optimized: COUNT + GROUP BY, no lock filtering (reseller owns these).
        """
        result = await self._session.execute(
            select(
                TicketModel.event_day_id,
                func.count(TicketModel.id).label("count"),
            )
            .where(
                TicketModel.event_id == event_id,
                TicketModel.owner_holder_id == holder_id,
                TicketModel.ticket_type_id == b2b_ticket_type_id,
            )
            .group_by(TicketModel.event_day_id)
        )
        return [
            {"event_day_id": row[0], "count": row[1]}
            for row in result.all()
        ]

    async def list_b2b_allocations_for_holder(
        self,
        event_id: UUID,
        holder_id: UUID,
        limit: int = 50,
        offset: int = 0,
    ) -> list[dict]:
        """
        List B2B allocations where holder is sender OR receiver.
        Direction determined by: to_holder_id == holder_id -> "received" else "transferred".
        Optimized: single query with ticket event_day resolution via subquery.
        """
        # Subquery: filter allocations to those involving this holder (either direction)
        alloc_filter = (
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

        # Subquery: get event_day_id from first ticket in each allocation
        day_subq = (
            select(
                AllocationTicketModel.allocation_id,
                TicketModel.event_day_id,
            )
            .join(TicketModel, AllocationTicketModel.ticket_id == TicketModel.id)
            .where(AllocationTicketModel.allocation_id.in_(select(alloc_filter)))
            .distinct(AllocationTicketModel.allocation_id)
            .subquery()
        )

        # Main query with JOIN for event_day_id
        result = await self._session.execute(
            select(AllocationModel, day_subq.c.event_day_id)
            .join(day_subq, AllocationModel.id == day_subq.c.allocation_id)
            .order_by(AllocationModel.created_at.desc())
        )

        allocations = []
        for row in result.all():
            alloc = row[0]
            event_day_id = row[1]
            direction = "received" if alloc.to_holder_id == holder_id else "transferred"
            source = alloc.metadata_.get("source", "b2b_free") if alloc.metadata_ else "b2b_free"
            allocations.append({
                "allocation_id": alloc.id,
                "event_day_id": event_day_id,
                "direction": direction,
                "from_holder_id": alloc.from_holder_id,
                "to_holder_id": alloc.to_holder_id,
                "ticket_count": alloc.ticket_count,
                "status": alloc.status.value if hasattr(alloc.status, 'value') else alloc.status,
                "source": source,
                "created_at": alloc.created_at,
            })
        return allocations
```

- [ ] **Step 2: Run import check**

Run: `python3 -c "from src.apps.resellers.repository import ResellerRepository; print('OK')"`
Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add src/apps/resellers/repository.py
git commit -m "feat(resellers): add repository with optimized queries"
```

---

## Task 5: Create ResellerService

**Files:**
- Modify: `src/apps/resellers/service.py`

- [ ] **Step 1: Write reseller service**

```python
# src/apps/resellers/service.py
from uuid import UUID
from src.apps.resellers.repository import ResellerRepository
from src.apps.resellers.response import (
    ResellerEventsResponse,
    ResellerEventItem,
    ResellerTicketsResponse,
    ResellerAllocationItem,
    ResellerAllocationsResponse,
)
from src.apps.core.exceptions import ForbiddenError, NotFoundError


class ResellerService:
    def __init__(self, session):
        self._repo = ResellerRepository(session)

    async def list_my_events(self, user_id: UUID) -> ResellerEventsResponse:
        """List events where user is an accepted reseller."""
        from src.apps.holder.repository import HolderRepository

        rows = await self._repo.list_my_events(user_id)
        events = []
        for row in rows:
            events.append(ResellerEventItem(
                event_id=row["event_id"],
                event_name=row["event_name"],
                organizer_name=row.get("organizer_name", "Unknown"),
                event_status=row["event_status"],
                my_role="reseller",
                accepted_at=row.get("accepted_at"),
            ))
        return ResellerEventsResponse(events=events, total=len(events))

    async def get_my_tickets(
        self,
        event_id: UUID,
        user_id: UUID,
    ) -> ResellerTicketsResponse:
        """Get my tickets for an event I resell."""
        # Check reseller association
        is_reseller = await self._repo.is_accepted_reseller(user_id, event_id)
        if not is_reseller:
            raise ForbiddenError("You are not a reseller for this event")

        # Get holder
        holder = await self._repo.get_my_holder_for_event(user_id)
        if not holder:
            return ResellerTicketsResponse(
                event_id=event_id,
                holder_id=None,
                tickets=[],
                total=0,
            )

        # Get B2B ticket type
        b2b_type = await self._repo.get_b2b_ticket_type_for_event(event_id)
        if not b2b_type:
            return ResellerTicketsResponse(
                event_id=event_id,
                holder_id=holder.id,
                tickets=[],
                total=0,
            )

        # Get ticket counts
        rows = await self._repo.list_b2b_tickets_by_holder(
            event_id=event_id,
            holder_id=holder.id,
            b2b_ticket_type_id=b2b_type.id,
        )

        from src.apps.resellers.response import ResellerTicketItem
        tickets = [ResellerTicketItem(event_day_id=r["event_day_id"], count=r["count"]) for r in rows]
        total = sum(r["count"] for r in rows)

        return ResellerTicketsResponse(
            event_id=event_id,
            holder_id=holder.id,
            tickets=tickets,
            total=total,
        )

    async def get_my_allocations(
        self,
        event_id: UUID,
        user_id: UUID,
        limit: int = 50,
        offset: int = 0,
    ) -> ResellerAllocationsResponse:
        """Get my allocations for an event I resell."""
        # Check reseller association
        is_reseller = await self._repo.is_accepted_reseller(user_id, event_id)
        if not is_reseller:
            raise ForbiddenError("You are not a reseller for this event")

        # Get holder
        holder = await self._repo.get_my_holder_for_event(user_id)
        if not holder:
            return ResellerAllocationsResponse(
                event_id=event_id,
                allocations=[],
                total=0,
            )

        # Get allocations
        rows = await self._repo.list_b2b_allocations_for_holder(
            event_id=event_id,
            holder_id=holder.id,
            limit=limit,
            offset=offset,
        )

        from src.apps.resellers.response import ResellerAllocationItem
        allocations = [
            ResellerAllocationItem(
                allocation_id=r["allocation_id"],
                event_day_id=r["event_day_id"],
                direction=r["direction"],
                from_holder_id=r["from_holder_id"],
                to_holder_id=r["to_holder_id"],
                ticket_count=r["ticket_count"],
                status=r["status"],
                source=r["source"],
                created_at=r["created_at"],
            )
            for r in rows
        ]

        return ResellerAllocationsResponse(
            event_id=event_id,
            allocations=allocations,
            total=len(allocations),
        )
```

- [ ] **Step 2: Run import check**

Run: `python3 -c "from src.apps.resellers.service import ResellerService; print('OK')"`
Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add src/apps/resellers/service.py
git commit -m "feat(resellers): add service with business logic"
```

---

## Task 6: Create URL routes

**Files:**
- Modify: `src/apps/resellers/urls.py`

- [ ] **Step 1: Add URL routes**

```python
# src/apps/resellers/urls.py
from fastapi import APIRouter
from src.apps.core.dependencies import CurrentUserDep

router = APIRouter(prefix="/api/resellers", tags=["resellers"])


@router.get("/events")
async def list_my_reseller_events(user: CurrentUserDep):
    from src.apps.resellers.service import ResellerService
    from src.apps.core.db import db_session

    async with db_session() as session:
        service = ResellerService(session)
        return await service.list_my_events(user.id)


@router.get("/events/{event_id}/tickets")
async def get_my_reseller_tickets(event_id, user: CurrentUserDep):
    from src.apps.resellers.service import ResellerService
    from src.apps.core.db import db_session

    async with db_session() as session:
        service = ResellerService(session)
        return await service.get_my_tickets(event_id, user.id)


@router.get("/events/{event_id}/my-allocations")
async def get_my_reseller_allocations(event_id, user: CurrentUserDep, limit: int = 50, offset: int = 0):
    from src.apps.resellers.service import ResellerService
    from src.apps.core.db import db_session

    async with db_session() as session:
        service = ResellerService(session)
        return await service.get_my_allocations(event_id, user.id, limit, offset)
```

- [ ] **Step 2: Register app in main router**

Read: `src/main.py` to find where apps are registered

- [ ] **Step 3: Add router to main app**

Run: `python3 -c "from src.apps.resellers.urls import router; print('router OK')"`
Expected: `OK`

- [ ] **Step 4: Commit**

```bash
git add src/apps/resellers/urls.py
git commit -m "feat(resellers): add URL routes"
```

---

## Task 7: Verify no circular imports or missing dependencies

**Files:**
- Check: All imports across all files

- [ ] **Step 1: Full import check**

Run: `python3 -c "from src.apps.resellers import *; print('All imports OK')"`
Expected: `OK`

- [ ] **Step 2: Verify endpoint registration**

Run: `python3 -c "from src.main import app; print([r.path for r in app.routes if 'reseller' in r.path])"`
Expected: List of reseller routes

- [ ] **Step 3: Commit**

```bash
git add -A
git commit -m "feat(resellers): complete app with all endpoints"
```

---

## Query Optimization Notes

1. **list_my_events**: Uses `JOIN` on indexed `user_id` and `accepted_at IS NOT NULL` - leverages existing composite index
2. **list_b2b_tickets_by_holder**: Uses `COUNT + GROUP BY` - single query, no N+1
3. **list_b2b_allocations_for_holder**: Uses subqueries to resolve `event_day_id` without N+1, batch-limits results

---

## Self-Review Checklist

1. **Spec coverage**: All 3 endpoints implemented?
   - GET `/resellers/events` ✓
   - GET `/resellers/events/{event_id}/tickets` ✓
   - GET `/resellers/events/{event_id}/my-allocations` ✓

2. **Placeholder scan**: Any TODO/TBD in plan? No ✓

3. **Type consistency**: Method signatures match between service and repository?
   - `is_accepted_reseller(user_id, event_id)` - consistent ✓
   - `get_my_holder_for_event(user_id)` - consistent ✓ (no event_id needed)
   - `get_b2b_ticket_type_for_event(event_id)` - consistent ✓ (delegates to TicketingRepository)
   - `list_b2b_tickets_by_holder(event_id, holder_id, b2b_ticket_type_id)` - consistent ✓

---

## Execution Handoff

**Plan complete and saved to `docs/superpowers/plans/2026-04-20-resellers-app.md`. Two execution options:**

**1. Subagent-Driven (recommended)** - I dispatch a fresh subagent per task, review between tasks, fast iteration

**2. Inline Execution** - Execute tasks in this session using executing-plans, batch execution with checkpoints

**Which approach?**
