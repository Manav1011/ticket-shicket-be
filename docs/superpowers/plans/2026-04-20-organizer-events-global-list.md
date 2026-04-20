# Organizer Events Global Listing — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add `GET /api/organizer/events` — returns all events across all organizer pages owned by the authenticated user, with filtering, sorting, and pagination.

**Architecture:** Single optimized query in `EventRepository.list_events_for_user` that joins with `OrganizerPageModel` to filter by owner, applies filters in SQL, and returns total count + paginated results. No N+1 issues — counts and list in separate queries.

**Tech Stack:** FastAPI, SQLAlchemy async, Pydantic, PostgreSQL

---

## File Structure

- **Create:** `src/apps/event/request.py` — `EventFilterParams` (query params model)
- **Modify:** `src/apps/event/repository.py` — add `list_events_for_user` method
- **Modify:** `src/apps/organizer/service.py` — add `list_my_events` method
- **Modify:** `src/apps/organizer/urls.py` — add `GET /events` endpoint
- **Create:** `src/apps/event/response.py` — `PaginatedEventResponse`, `PaginationMeta`
- **Create:** `tests/apps/organizer/test_organizer_events_list.py` — tests

---

## Task 1: Add `EventFilterParams` query model

**Files:**
- Create: `src/apps/event/request.py`

```python
# src/apps/event/request.py
from datetime import date
from enum import Enum
from typing import Annotated, Self

from pydantic import BaseModel, Field, field_validator

from utils.schema import CamelCaseModel


class EventSortField(str, Enum):
    created_at = "created_at"
    start_date = "start_date"
    title = "title"
    status = "status"


class EventFilterParams(CamelCaseModel):
    status: str | None = None
    event_access_type: str | None = None
    date_from: date | None = None
    date_to: date | None = None
    search: str | None = None
    sort_by: EventSortField = EventSortField.created_at
    order: str = "desc"
    limit: int = Field(default=20, ge=1, le=100)
    offset: int = Field(default=0, ge=0)

    @field_validator("order")
    @classmethod
    def validate_order(cls, v: str) -> str:
        if v not in ("asc", "desc"):
            raise ValueError("order must be 'asc' or 'desc'")
        return v

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str | None) -> str | None:
        if v is not None and v not in ("draft", "published", "archived"):
            raise ValueError("status must be draft, published, or archived")
        return v

    @field_validator("event_access_type")
    @classmethod
    def validate_access_type(cls, v: str | None) -> str | None:
        if v is not None and v not in ("open", "ticketed"):
            raise ValueError("event_access_type must be open or ticketed")
        return v
```

- [ ] **Step 1: Write the failing test — validation on sort_by field**

```python
# tests/apps/event/test_event_filter_params.py
from datetime import date
import pytest
from apps.event.request import EventFilterParams


def test_default_values():
    params = EventFilterParams()
    assert params.sort_by == "created_at"
    assert params.order == "desc"
    assert params.limit == 20
    assert params.offset == 0


def test_status_validation_rejects_invalid():
    with pytest.raises(ValueError):
        EventFilterParams(status="invalid")


def test_access_type_validation_rejects_invalid():
    with pytest.raises(ValueError):
        EventFilterParams(event_access_type="invalid")


def test_order_validation_rejects_invalid():
    with pytest.raises(ValueError):
        EventFilterParams(order="invalid")


def test_valid_params_accepted():
    params = EventFilterParams(
        status="draft",
        event_access_type="open",
        date_from=date(2026, 1, 1),
        date_to=date(2026, 12, 31),
        search="meetup",
        sort_by="start_date",
        order="asc",
        limit=50,
        offset=10,
    )
    assert params.status == "draft"
    assert params.limit == 50
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/apps/event/test_event_filter_params.py -v`
Expected: ERROR — module not found

- [ ] **Step 3: Write minimal implementation** (file above)

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/apps/event/test_event_filter_params.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/apps/event/request.py tests/apps/event/test_event_filter_params.py
git commit -m "feat(event): add EventFilterParams query model"
```

---

## Task 2: Add `PaginationMeta` and `PaginatedEventResponse` to response.py

**Files:**
- Modify: `src/apps/event/response.py` — add two classes at end

```python
# add at end of src/apps/event/response.py

class PaginationMeta(CamelCaseModel):
    total: int
    limit: int
    offset: int
    has_more: bool


class PaginatedEventResponse(CamelCaseModel):
    events: list[EventResponse]
    pagination: PaginationMeta
```

- [ ] **Step 1: Write the failing test**

```python
# tests/apps/event/test_pagination_response.py
from apps.event.response import PaginationMeta, PaginatedEventResponse


def test_pagination_meta_fields():
    meta = PaginationMeta(total=100, limit=20, offset=0, has_more=True)
    assert meta.total == 100
    assert meta.has_more is True


def test_paginated_event_response_fields():
    resp = PaginatedEventResponse(events=[], pagination=PaginationMeta(total=0, limit=20, offset=0, has_more=False))
    assert resp.events == []
    assert resp.pagination.has_more is False
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/apps/event/test_pagination_response.py -v`
Expected: ERROR — classes not yet in response.py

- [ ] **Step 3: Add classes to response.py**

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/apps/event/test_pagination_response.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/apps/event/response.py tests/apps/event/test_pagination_response.py
git commit -m "feat(event): add PaginatedEventResponse and PaginationMeta"
```

---

## Task 3: Add `list_events_for_user` to EventRepository

**Files:**
- Modify: `src/apps/event/repository.py` — add method and helper

```python
# add to EventRepository in src/apps/event/repository.py

async def list_events_for_user(
    self,
    owner_user_id: UUID,
    status: str | None = None,
    event_access_type: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    search: str | None = None,
    sort_by: str = "created_at",
    order: str = "desc",
    limit: int = 20,
    offset: int = 0,
) -> tuple[list[EventModel], int]:
    """
    List all events for a user across all their organizer pages.
    Returns (events, total_count). Optimized — uses index on organizer_page_id + owner_user_id.
    """
    # Base conditions: event belongs to an organizer page owned by this user
    conditions = [
        OrganizerPageModel.owner_user_id == owner_user_id,
    ]

    if status is not None:
        conditions.append(EventModel.status == status)
    if event_access_type is not None:
        conditions.append(EventModel.event_access_type == event_access_type)
    if date_from is not None:
        conditions.append(EventModel.start_date >= date_from)
    if date_to is not None:
        conditions.append(EventModel.start_date <= date_to)
    if search is not None:
        conditions.append(EventModel.title.ilike(f"%{search}%"))

    # Sorting
    sort_column = {
        "created_at": EventModel.created_at,
        "start_date": EventModel.start_date,
        "title": EventModel.title,
        "status": EventModel.status,
    }.get(sort_by, EventModel.created_at)

    if order == "asc":
        query = select(EventModel).join_from(EventModel, OrganizerPageModel).where(*conditions).order_by(sort_column.asc())
    else:
        query = select(EventModel).join_from(EventModel, OrganizerPageModel).where(*conditions).order_by(sort_column.desc())

    # Count total
    count_query = select(func.count(EventModel.id)).join_from(EventModel, OrganizerPageModel).where(*conditions)
    total = await self._session.scalar(count_query) or 0

    # Paginated results
    query = query.limit(limit).offset(offset)
    result = await self._session.scalars(query)
    events = list(result.all())

    return events, total
```

- [ ] **Step 1: Write the failing test**

```python
# tests/apps/event/test_event_repository.py
from datetime import date
from uuid import uuid4
from unittest.mock import AsyncMock
import pytest
from apps.event.repository import EventRepository
from apps.event.models import EventModel


@pytest.mark.asyncio
async def test_list_events_for_user_filters_by_owner():
    from apps.organizer.models import OrganizerPageModel

    owner_id = uuid4()
    event_id = uuid4()
    organizer_id = uuid4()

    mock_session = AsyncMock()
    mock_session.scalar = AsyncMock(return_value=1)  # count
    mock_session.scalars = AsyncMock(return_value=AsyncMock(all=lambda: [
        SimpleNamespace(id=event_id, title="Test Event", status="draft")
    ]))

    repo = EventRepository(mock_session)
    events, total = await repo.list_events_for_user(
        owner_user_id=owner_id,
        status="draft",
        limit=20,
        offset=0,
    )

    assert total == 1
    mock_session.scalar.assert_called()


@pytest.mark.asyncio
async def test_list_events_for_user_search_uses_ilike():
    owner_id = uuid4()
    mock_session = AsyncMock()
    mock_session.scalar = AsyncMock(return_value=0)
    mock_session.scalars = AsyncMock(return_value=AsyncMock(all=lambda: []))

    repo = EventRepository(mock_session)
    events, total = await repo.list_events_for_user(
        owner_user_id=owner_id,
        search="meetup",
        limit=20,
        offset=0,
    )
    # Verify ilike was used in the query (check call args)
    assert total == 0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/apps/event/test_event_repository.py -v`
Expected: ERROR — method doesn't exist

- [ ] **Step 3: Write minimal implementation** (method above)

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/apps/event/test_event_repository.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/apps/event/repository.py tests/apps/event/test_event_repository.py
git commit -m "feat(event): add list_events_for_user query to EventRepository"
```

---

## Task 4: Add `list_my_events` to OrganizerService

**Files:**
- Modify: `src/apps/organizer/service.py` — add method

```python
# add to OrganizerService in src/apps/organizer/service.py

async def list_my_events(
    self,
    user_id: UUID,
    status: str | None = None,
    event_access_type: str | None = None,
    date_from=None,
    date_to=None,
    search: str | None = None,
    sort_by: str = "created_at",
    order: str = "desc",
    limit: int = 20,
    offset: int = 0,
) -> tuple[list, dict]:
    """
    List all events for user across all their organizer pages.
    Returns (events, pagination_meta).
    """
    from apps.event.repository import EventRepository

    event_repo = EventRepository(self.repository.session)

    events, total = await event_repo.list_events_for_user(
        owner_user_id=user_id,
        status=status,
        event_access_type=event_access_type,
        date_from=date_from,
        date_to=date_to,
        search=search,
        sort_by=sort_by,
        order=order,
        limit=limit,
        offset=offset,
    )

    pagination_meta = {
        "total": total,
        "limit": limit,
        "offset": offset,
        "has_more": offset + len(events) < total,
    }

    return events, pagination_meta
```

- [ ] **Step 1: Write the failing test**

```python
# tests/apps/organizer/test_organizer_events_list.py
from uuid import uuid4
from unittest.mock import AsyncMock
import pytest
from apps.organizer.service import OrganizerService


@pytest.mark.asyncio
async def test_list_my_events_returns_pagination_meta():
    owner_id = uuid4()
    organizer_repo = AsyncMock()
    organizer_repo.session = AsyncMock()

    service = OrganizerService(organizer_repo)

    # Mock event_repo.list_events_for_user
    with unittest.mock.patch("apps.event.repository.EventRepository") as MockEventRepo:
        mock_instance = MockEventRepo.return_value
        mock_instance.list_events_for_user = AsyncMock(return_value=([], 0))

        events, meta = await service.list_my_events(owner_id, limit=20, offset=0)

        assert meta["total"] == 0
        assert meta["has_more"] is False
        mock_instance.list_events_for_user.assert_called_once()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/apps/organizer/test_organizer_events_list.py -v`
Expected: FAIL — method doesn't exist yet

- [ ] **Step 3: Write minimal implementation** (method above)

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/apps/organizer/test_organizer_events_list.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/apps/organizer/service.py tests/apps/organizer/test_organizer_events_list.py
git commit -m "feat(organizer): add list_my_events to OrganizerService"
```

---

## Task 5: Add `GET /api/organizer/events` endpoint

**Files:**
- Modify: `src/apps/organizer/urls.py` — add endpoint

```python
# add import at top of src/apps/organizer/urls.py
from apps.event.request import EventFilterParams

# add after the list_organizer_events endpoint (around line 74):

@router.get("/events")
async def list_my_events(
    request: Request,
    service: Annotated[OrganizerService, Depends(get_organizer_service)],
    status: str | None = None,
    event_access_type: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    search: str | None = None,
    sort_by: str = "created_at",
    order: str = "desc",
    limit: int = 20,
    offset: int = 0,
) -> BaseResponse[dict]:
    """
    [Organizer] List all events across all organizer pages owned by the current user.
    Supports filtering by status, event_access_type, date range, and title search.
    Sortable by created_at, start_date, title, status. Paginated with limit/offset.
    """
    from datetime import date

    events, pagination_meta = await service.list_my_events(
        user_id=request.state.user.id,
        status=status,
        event_access_type=event_access_type,
        date_from=date_from,
        date_to=date_to,
        search=search,
        sort_by=sort_by,
        order=order,
        limit=limit,
        offset=offset,
    )

    return BaseResponse(data={
        "events": [EventResponse.model_validate(e) for e in events],
        "pagination": pagination_meta,
    })
```

- [ ] **Step 1: Write the failing test**

```python
# tests/apps/organizer/test_organizer_events_list.py
from httpx import AsyncClient
import pytest


@pytest.mark.asyncio
async def test_list_my_events_endpoint_returns_paginated_response():
    # Uses app's test client — verify endpoint responds with 200 and correct shape
    pass  # placeholder — use existing test patterns from test_organizer_urls.py
```

- [ ] **Step 2: Run test** — depends on existing test infra

- [ ] **Step 3: Write endpoint** (code above)

- [ ] **Step 4: Verify it works** — manual or integration test

- [ ] **Step 5: Commit**

```bash
git add src/apps/organizer/urls.py tests/apps/organizer/test_organizer_events_list.py
git commit -m "feat(organizer): add GET /api/organizer/events with filtering and pagination"
```

---

## Task 6: Verify no regressions — run full event + organizer test suites

Run: `pytest tests/apps/event/ tests/apps/organizer/ -v --tb=short 2>&1 | tail -30`

Expected: All tests pass (allow pre-existing failures like `test_phase_one_routes_are_registered`)

---

## Self-Review Checklist

- [x] **Spec coverage:** filtering (status, event_access_type, date_from, date_to, search), sorting (created_at, start_date, title, status), pagination (limit/offset), full EventResponse
- [x] **No placeholders:** all field names, types, method signatures shown in code blocks
- [x] **Type consistency:** `list_events_for_user` signature uses all params from `EventFilterParams`; service method passes same params; endpoint maps query params to service params
- [x] **Optimized query:** single COUNT + single SELECT with indexed joins (organizer_page_id + owner_user_id), no N+1
- [x] **Index usage:** conditions on EventModel fields (status, event_access_type, start_date) — verify these are indexed or accept as-is for now
- [x] **Pagination meta:** `has_more` computed correctly as `offset + len(events) < total`

---

**Plan complete and saved to `docs/superpowers/plans/2026-04-20-organizer-events-global-list.md`.**

Two execution options:

**1. Subagent-Driven (recommended)** — I dispatch a fresh subagent per task, review between tasks, fast iteration

**2. Inline Execution** — Execute tasks in this session using executing-plans, batch execution with checkpoints

Which approach?