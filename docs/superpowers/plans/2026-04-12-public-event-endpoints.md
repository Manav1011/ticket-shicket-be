# Public Event Endpoints Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add public read-only endpoints at `/api/open/events` and `/api/open/organizers` for unauthenticated visitors to browse events, event details with embedded days/assets/tickets, and organizer pages.

**Architecture:** Create `PublicEventService` (receives both `EventRepository` and `TicketingRepository`) and `PublicOrganizerService` to separate public read logic from private owner-scoped logic. For events: change the existing `public_urls.py` router prefix from `/api/events` to `/api/open/events` and remove the router-level auth dependency — the router becomes fully public. Auth is added back only at the route level for `POST /api/open/events/{event_id}/interest` (requires user or guest token). For organizers: create a new `public_urls.py` at `/api/open/organizers` with no auth dependency. `GET /api/open/events/{event_id}` embeds all related data so the frontend makes one call per page.

**Tech Stack:** FastAPI, SQLAlchemy async ORM, Alembic, Pydantic response/request models, `uv` for project commands and tests.

---

### File Structure

| Action | File | Purpose |
|---|---|---|
| Create | `src/apps/event/public_service.py` | PublicEventService — list events, get event detail |
| Create | `src/apps/organizer/public_service.py` | PublicOrganizerService — list organizers, get organizer, list events by organizer |
| Create | `src/apps/organizer/public_urls.py` | Public organizer router at `/api/open/organizers` |
| Modify | `src/apps/event/public_urls.py` | Change prefix to `/api/open/events`, add `GET /` and `GET /{event_id}` |
| Modify | `src/apps/event/response.py` | Add `EventDetailResponse` with embedded collections |
| Modify | `src/apps/event/repository.py` | Add `list_published_events()` |
| Modify | `src/apps/organizer/repository.py` | Add `get_by_id()`, `list_public_organizers()`, `list_events_by_organizer_public()` |
| Modify | `src/server.py` | Register `organizer_public_router` |

---

### Task 1: Add repository method for public event listing

**Files:**
- Modify: `src/apps/event/repository.py`
- Test: `tests/apps/event/test_event_service.py`

- [ ] **Step 1: Write the failing test**

```python
@pytest.mark.asyncio
async def test_list_published_events_returns_only_published():
    session = AsyncMock()
    repo = EventRepository(session)

    mock_result = AsyncMock()
    mock_result.all.return_value = [
        SimpleNamespace(id=uuid4(), title="Published Event 1", is_published=True),
        SimpleNamespace(id=uuid4(), title="Published Event 2", is_published=True),
    ]
    session.scalars.return_value = mock_result

    events = await repo.list_published_events()

    assert len(events) == 2
    session.scalars.assert_called_once()
    call_args = session.scalars.call_args[0][0]
    assert "is_published" in str(call_args)
```

- [ ] **Step 2: Run test to verify it fails**

Run:
```bash
uv run pytest tests/apps/event/test_event_service.py -k list_published_events -v
```
Expected: FAIL with `AttributeError: 'EventRepository' object has no attribute 'list_published_events'`

- [ ] **Step 3: Add list_published_events to repository**

Add to `src/apps/event/repository.py`:

```python
async def list_published_events(self) -> list[EventModel]:
    result = await self._session.scalars(
        select(EventModel)
        .where(EventModel.is_published == True)
        .where(EventModel.status == "published")
        .order_by(EventModel.created_at.desc())
    )
    return list(result.all())
```

- [ ] **Step 4: Run test to verify it passes**

Run:
```bash
uv run pytest tests/apps/event/test_event_service.py -k list_published_events -v
```
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/apps/event/repository.py tests/apps/event/test_event_service.py
git commit -m "feat: add list_published_events repository method"
```

---

### Task 2: Add repository methods for public organizer listing

**Files:**
- Modify: `src/apps/organizer/repository.py`
- Test: `tests/apps/organizer/test_organizer_service.py`

- [ ] **Step 1: Write the failing tests**

```python
@pytest.mark.asyncio
async def test_list_public_organizers_returns_only_active():
    session = AsyncMock()
    repo = OrganizerRepository(session)

    mock_result = AsyncMock()
    mock_result.all.return_value = [
        SimpleNamespace(id=uuid4(), name="Org 1", status="active"),
        SimpleNamespace(id=uuid4(), name="Org 2", status="active"),
    ]
    session.scalars.return_value = mock_result

    organizers = await repo.list_public_organizers()

    assert len(organizers) == 2
    call_args = session.scalars.call_args[0][0]
    assert "status" in str(call_args)


@pytest.mark.asyncio
async def test_get_organizer_by_id_returns_organizer():
    org_id = uuid4()
    session = AsyncMock()
    repo = OrganizerRepository(session)

    session.scalar.return_value = SimpleNamespace(id=org_id, name="Test Org")

    result = await repo.get_by_id(org_id)

    assert result is not None
    assert result.id == org_id
```

- [ ] **Step 2: Run tests to verify they fail**

Run:
```bash
uv run pytest tests/apps/organizer/test_organizer_service.py -k "list_public_organizers or get_organizer_by_id" -v
```
Expected: FAIL with missing method errors

- [ ] **Step 3: Add repository methods**

Add to `src/apps/organizer/repository.py`:

```python
async def get_by_id(self, organizer_id: UUID) -> Optional[OrganizerPageModel]:
    return await self._session.scalar(
        select(OrganizerPageModel).where(OrganizerPageModel.id == organizer_id)
    )

async def list_public_organizers(self) -> list[OrganizerPageModel]:
    result = await self._session.scalars(
        select(OrganizerPageModel)
        .where(OrganizerPageModel.status == "active")
        .order_by(OrganizerPageModel.created_at.desc())
    )
    return list(result.all())

async def list_events_by_organizer_public(
    self, organizer_id: UUID
) -> list[EventModel]:
    result = await self._session.scalars(
        select(EventModel)
        .where(
            EventModel.organizer_page_id == organizer_id,
            EventModel.is_published == True,
            EventModel.status == "published",
        )
        .order_by(EventModel.created_at.desc())
    )
    return list(result.all())
```

- [ ] **Step 4: Run tests to verify they pass**

Run:
```bash
uv run pytest tests/apps/organizer/test_organizer_service.py -k "list_public_organizers or get_organizer_by_id" -v
```
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/apps/organizer/repository.py tests/apps/organizer/test_organizer_service.py
git commit -m "feat: add public organizer repository methods"
```

---

### Task 3: Create PublicOrganizerService

**Files:**
- Create: `src/apps/organizer/public_service.py`
- Test: `tests/apps/organizer/test_organizer_service.py`

- [ ] **Step 1: Write the failing tests**

```python
@pytest.mark.asyncio
async def test_list_public_organizers_service():
    repo = AsyncMock()
    repo.list_public_organizers.return_value = [
        SimpleNamespace(id=uuid4(), name="Org 1"),
        SimpleNamespace(id=uuid4(), name="Org 2"),
    ]
    service = PublicOrganizerService(repo)

    result = await service.list_organizers()

    assert len(result) == 2
    repo.list_public_organizers.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_organizer_returns_organizer():
    org_id = uuid4()
    repo = AsyncMock()
    repo.get_by_id.return_value = SimpleNamespace(id=org_id, name="Test Org")
    service = PublicOrganizerService(repo)

    result = await service.get_organizer(org_id)

    assert result is not None
    assert result.id == org_id


@pytest.mark.asyncio
async def test_get_organizer_raises_not_found():
    org_id = uuid4()
    repo = AsyncMock()
    repo.get_by_id.return_value = None
    service = PublicOrganizerService(repo)

    with pytest.raises(NotFoundError):
        await service.get_organizer(org_id)


@pytest.mark.asyncio
async def test_list_events_by_organizer_returns_only_published():
    org_id = uuid4()
    repo = AsyncMock()
    repo.list_events_by_organizer_public.return_value = [
        SimpleNamespace(id=uuid4(), title="Event 1", is_published=True),
    ]
    service = PublicOrganizerService(repo)

    result = await service.list_events_by_organizer(org_id)

    assert len(result) == 1
```

- [ ] **Step 2: Run tests to verify they fail**

Run:
```bash
uv run pytest tests/apps/organizer/test_organizer_service.py -k "PublicOrganizer" -v
```
Expected: FAIL with `ImportError` (class doesn't exist)

- [ ] **Step 3: Create PublicOrganizerService**

Create `src/apps/organizer/public_service.py`:

```python
from uuid import UUID

from exceptions import NotFoundError

from .models import OrganizerPageModel


class PublicOrganizerService:
    def __init__(self, repository) -> None:
        self.repository = repository

    async def list_organizers(self) -> list[OrganizerPageModel]:
        return await self.repository.list_public_organizers()

    async def get_organizer(self, organizer_id: UUID) -> OrganizerPageModel:
        organizer = await self.repository.get_by_id(organizer_id)
        if not organizer:
            raise NotFoundError("Organizer not found")
        return organizer

    async def list_events_by_organizer(self, organizer_id: UUID) -> list:
        return await self.repository.list_events_by_organizer_public(organizer_id)
```

- [ ] **Step 4: Run tests to verify they pass**

Run:
```bash
uv run pytest tests/apps/organizer/test_organizer_service.py -k "PublicOrganizer" -v
```
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/apps/organizer/public_service.py tests/apps/organizer/test_organizer_service.py
git commit -m "feat: add PublicOrganizerService"
```

---

### Task 4: Create PublicEventService

**Files:**
- Create: `src/apps/event/public_service.py`
- Test: `tests/apps/event/test_event_service.py`

**Important:** `PublicEventService` receives BOTH `event_repo` AND `ticketing_repo`. Ticket data lives in `TicketingRepository`, not `EventRepository`.

- [ ] **Step 1: Write the failing tests**

```python
@pytest.mark.asyncio
async def test_list_public_events_returns_only_published():
    event_repo = AsyncMock()
    event_repo.list_published_events.return_value = [
        SimpleNamespace(id=uuid4(), title="Event 1", is_published=True),
        SimpleNamespace(id=uuid4(), title="Event 2", is_published=True),
    ]
    ticketing_repo = AsyncMock()
    service = PublicEventService(event_repo, ticketing_repo)

    result = await service.list_public_events()

    assert len(result) == 2
    event_repo.list_published_events.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_public_event_returns_event_with_embedded_data():
    event_id = uuid4()
    event_repo = AsyncMock()
    event_repo.get_by_id.return_value = SimpleNamespace(
        id=event_id,
        title="Test Event",
        is_published=True,
        interested_counter=5,
        organizer_page_id=uuid4(),
    )
    event_repo.list_event_days.return_value = [SimpleNamespace(id=uuid4(), day_index=0)]
    event_repo.list_media_assets.return_value = []
    ticketing_repo = AsyncMock()
    ticketing_repo.list_ticket_types_for_event.return_value = []
    ticketing_repo.list_allocations_for_event.return_value = []
    service = PublicEventService(event_repo, ticketing_repo)

    result = await service.get_public_event(event_id)

    assert result["id"] == event_id
    assert result["interested_counter"] == 5
    assert "days" in result
    assert "ticket_types" in result
    assert "media_assets" in result
    assert "ticket_allocations" in result
```

- [ ] **Step 2: Run tests to verify they fail**

Run:
```bash
uv run pytest tests/apps/event/test_event_service.py -k "PublicEventService" -v
```
Expected: FAIL with `ImportError` (class doesn't exist)

- [ ] **Step 3: Create PublicEventService**

Create `src/apps/event/public_service.py`:

```python
from uuid import UUID

from exceptions import NotFoundError


class PublicEventService:
    def __init__(self, event_repository, ticketing_repository) -> None:
        self.event_repo = event_repository
        self.ticketing_repo = ticketing_repository

    async def list_public_events(self) -> list:
        return await self.event_repo.list_published_events()

    async def get_public_event(self, event_id: UUID) -> dict:
        event = await self.event_repo.get_by_id(event_id)
        if not event:
            raise NotFoundError("Event not found")

        if not getattr(event, "is_published", False):
            raise NotFoundError("Event not found")

        days = await self.event_repo.list_event_days(event_id)
        assets = await self.event_repo.list_media_assets(event_id)
        ticket_types = await self.ticketing_repo.list_ticket_types_for_event(event_id)
        allocations = await self.ticketing_repo.list_allocations_for_event(event_id)

        return {
            "id": event.id,
            "title": event.title,
            "slug": getattr(event, "slug", None),
            "description": getattr(event, "description", None),
            "event_type": getattr(event, "event_type", None),
            "status": event.status,
            "event_access_type": getattr(event, "event_access_type", None),
            "location_mode": getattr(event, "location_mode", None),
            "timezone": getattr(event, "timezone", None),
            "start_date": getattr(event, "start_date", None),
            "end_date": getattr(event, "end_date", None),
            "venue_name": getattr(event, "venue_name", None),
            "venue_address": getattr(event, "venue_address", None),
            "venue_city": getattr(event, "venue_city", None),
            "venue_state": getattr(event, "venue_state", None),
            "venue_country": getattr(event, "venue_country", None),
            "venue_latitude": getattr(event, "venue_latitude", None),
            "venue_longitude": getattr(event, "venue_longitude", None),
            "online_event_url": getattr(event, "online_event_url", None),
            "recorded_event_url": getattr(event, "recorded_event_url", None),
            "published_at": getattr(event, "published_at", None),
            "is_published": getattr(event, "is_published", False),
            "interested_counter": getattr(event, "interested_counter", 0),
            "days": [
                {
                    "id": str(d.id),
                    "day_index": d.day_index,
                    "date": str(d.date),
                    "start_time": str(d.start_time) if d.start_time else None,
                    "end_time": str(d.end_time) if d.end_time else None,
                    "scan_status": d.scan_status,
                }
                for d in days
            ],
            "media_assets": [
                {
                    "id": str(a.id),
                    "asset_type": a.asset_type,
                    "public_url": a.public_url,
                    "title": getattr(a, "title", None),
                    "caption": getattr(a, "caption", None),
                    "alt_text": getattr(a, "alt_text", None),
                    "sort_order": a.sort_order,
                    "is_primary": a.is_primary,
                }
                for a in assets
            ],
            "ticket_types": [
                {
                    "id": str(t.id),
                    "name": getattr(t, "name", None),
                    "description": getattr(t, "description", None),
                    "price": str(getattr(t, "price", "0.00")),
                    "currency": getattr(t, "currency", "USD"),
                }
                for t in ticket_types
            ],
            "ticket_allocations": [
                {
                    "id": str(a.id),
                    "ticket_type_id": str(a.ticket_type_id),
                    "event_day_id": str(a.event_day_id),
                    "quantity": a.quantity,
                    "price": str(getattr(a, "price", "0.00")),
                }
                for a in allocations
            ],
        }
```

- [ ] **Step 4: Run tests to verify they pass**

Run:
```bash
uv run pytest tests/apps/event/test_event_service.py -k "PublicEventService" -v
```
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/apps/event/public_service.py tests/apps/event/test_event_service.py
git commit -m "feat: add PublicEventService with ticketing repo"
```

---

### Task 5: Add EventDetailResponse model and update public_urls.py

**Files:**
- Modify: `src/apps/event/response.py`
- Modify: `src/apps/event/public_urls.py`
- Test: `tests/apps/event/test_event_urls.py`

- [ ] **Step 1: Write the failing tests**

```python
def test_public_events_list_endpoint_exists():
    from apps.event.public_urls import router

    route = next(
        (r for r in router.routes if getattr(r, "path", "") == "/api/open/events"),
        None,
    )
    assert route is not None


def test_public_event_detail_endpoint_exists():
    from apps.event.public_urls import router

    route = next(
        (r for r in router.routes if getattr(r, "path", "") == "/api/open/events/{event_id}"),
        None,
    )
    assert route is not None


def test_public_list_uses_public_service():
    from apps.event.public_urls import get_public_event_service

    # Verify get_public_event_service injects PublicEventService
    # which needs two repos (event + ticketing)
    assert "PublicEventService" in str(get_public_event_service)
```

- [ ] **Step 2: Run tests to verify they fail**

Run:
```bash
uv run pytest tests/apps/event/test_event_urls.py -k "public_events_list or public_event_detail" -v
```
Expected: FAIL because routes don't exist yet

- [ ] **Step 3: Add EventDetailResponse to response.py**

Add to `src/apps/event/response.py`:

```python
class EventDayPublicResponse(CamelCaseModel):
    id: UUID
    day_index: int
    date: date
    start_time: datetime | None = None
    end_time: datetime | None = None
    scan_status: str


class MediaAssetPublicResponse(CamelCaseModel):
    id: UUID
    asset_type: str
    public_url: str
    title: str | None = None
    caption: str | None = None
    alt_text: str | None = None
    sort_order: int
    is_primary: bool


class TicketTypePublicResponse(CamelCaseModel):
    id: UUID
    name: str | None = None
    description: str | None = None
    price: str = "0.00"
    currency: str = "USD"


class TicketAllocationPublicResponse(CamelCaseModel):
    id: UUID
    ticket_type_id: UUID
    event_day_id: UUID
    quantity: int
    price: str = "0.00"


class EventDetailResponse(CamelCaseModel):
    id: UUID
    title: str | None = None
    slug: str | None = None
    description: str | None = None
    event_type: str | None = None
    status: str
    event_access_type: str
    location_mode: str | None = None
    timezone: str | None = None
    start_date: date | None = None
    end_date: date | None = None
    venue_name: str | None = None
    venue_address: str | None = None
    venue_city: str | None = None
    venue_state: str | None = None
    venue_country: str | None = None
    venue_latitude: float | None = None
    venue_longitude: float | None = None
    online_event_url: str | None = None
    recorded_event_url: str | None = None
    published_at: datetime | None = None
    is_published: bool
    interested_counter: int = 0
    days: list[EventDayPublicResponse] = []
    media_assets: list[MediaAssetPublicResponse] = []
    ticket_types: list[TicketTypePublicResponse] = []
    ticket_allocations: list[TicketAllocationPublicResponse] = []

    class Config:
        from_attributes = True
```

- [ ] **Step 4: Change router prefix, remove router-level auth, add route-level auth only for interest**

In `src/apps/event/public_urls.py`:

```python
# BEFORE — router had auth dependency at router level
router = APIRouter(
    prefix="/api/events",
    dependencies=[Depends(get_current_user_or_guest)],  # applied to ALL routes
)

# AFTER — no router-level auth; auth only on the interest route
router = APIRouter(prefix="/api/open/events")  # fully public router
```

Then update the interest route to include its own auth dependency (this was previously at the router level):

```python
# ── Interest (auth required — user or guest) ──────────────────────────────

@router.post(
    "/{event_id}/interest",
    dependencies=[
        Depends(get_current_user_or_guest),  # auth only on this route
        Depends(
            RateLimiter(
                times=rate_limiter_config["request_limit"],
                seconds=rate_limiter_config["time"],
            )
        ),
    ],
)
async def mark_event_interest(
    event_id: UUID,
    request: Request,
    service: Annotated[EventService, Depends(get_event_service)],
) -> BaseResponse[EventInterestResponse]:
    actor = request.state.actor
    result = await service.interest_event(
        actor_kind=actor.kind,
        actor_id=actor.id,
        event_id=event_id,
        ip_address=request.client.host if request.client else "unknown",
        user_agent=request.headers.get("user-agent"),
    )
    return BaseResponse(data=EventInterestResponse.model_validate(result))
```

Also add the two public GET routes to `src/apps/event/public_urls.py`:

```python
# ── Event List (public — no auth) ────────────────────────────────────────

@router.get("")
async def list_public_events(
    service: Annotated[PublicEventService, Depends(get_public_event_service)],
) -> BaseResponse[list[EventSummaryResponse]]:
    events = await service.list_public_events()
    return BaseResponse(data=[EventSummaryResponse.model_validate(e) for e in events])


# ── Event Detail (public — no auth) ─────────────────────────────────────

@router.get("/{event_id}")
async def get_public_event(
    event_id: UUID,
    service: Annotated[PublicEventService, Depends(get_public_event_service)],
) -> BaseResponse[EventDetailResponse]:
    event = await service.get_public_event(event_id)
    return BaseResponse(data=EventDetailResponse.model_validate(event))
```

Also update `get_public_event_service` to inject both repos:

```python
def get_public_event_service(session: Annotated[AsyncSession, Depends(db_session)]) -> PublicEventService:
    return PublicEventService(
        event_repository=EventRepository(session),
        ticketing_repository=TicketingRepository(session),
    )
```

And add the new imports:
```python
from apps.ticketing.repository import TicketingRepository
from .public_service import PublicEventService
```

**Authorization matrix after this change:**

| Route | Auth Required |
|---|---|
| `GET /api/open/events` | No |
| `GET /api/open/events/{event_id}` | No |
| `POST /api/open/events/{event_id}/interest` | Yes (user or guest) |
| `GET /api/open/organizers/*` | No |

- [ ] **Step 5: Run tests to verify they pass**

Run:
```bash
uv run pytest tests/apps/event/test_event_urls.py -k "public_events_list or public_event_detail" -v
```
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add src/apps/event/response.py src/apps/event/public_urls.py tests/apps/event/test_event_urls.py
git commit -m "feat: update public event router with list and detail endpoints"
```

---

### Task 6: Create organizer public router

**Files:**
- Create: `src/apps/organizer/public_urls.py`
- Modify: `src/server.py`
- Test: `tests/apps/organizer/test_organizer_urls.py`

- [ ] **Step 1: Write the failing tests**

```python
def test_public_list_organizers_endpoint_exists():
    with pytest.raises(ImportError):
        from apps.organizer.public_urls import router


def test_public_get_organizer_endpoint_exists():
    with pytest.raises(ImportError):
        from apps.organizer.public_urls import router
```

- [ ] **Step 2: Run tests to verify they fail**

Run:
```bash
uv run pytest tests/apps/organizer/test_organizer_urls.py -k "public_list or public_get_organizer" -v
```
Expected: FAIL with `ImportError` (file doesn't exist)

- [ ] **Step 3: Create organizer public_urls.py**

Create `src/apps/organizer/public_urls.py`:

```python
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from apps.event.response import EventSummaryResponse
from db.session import db_session
from utils.schema import BaseResponse

from .public_service import PublicOrganizerService
from .repository import OrganizerRepository
from .response import OrganizerPageResponse


router = APIRouter(prefix="/api/open/organizers", tags=["Public Organizers"])


def get_public_organizer_service(
    session: Annotated[AsyncSession, Depends(db_session)],
) -> PublicOrganizerService:
    return PublicOrganizerService(OrganizerRepository(session))


@router.get("")
async def list_public_organizers(
    service: Annotated[PublicOrganizerService, Depends(get_public_organizer_service)],
) -> BaseResponse[list[OrganizerPageResponse]]:
    organizers = await service.list_organizers()
    return BaseResponse(
        data=[OrganizerPageResponse.model_validate(o) for o in organizers]
    )


@router.get("/{organizer_page_id}")
async def get_public_organizer(
    organizer_page_id: UUID,
    service: Annotated[PublicOrganizerService, Depends(get_public_organizer_service)],
) -> BaseResponse[OrganizerPageResponse]:
    organizer = await service.get_organizer(organizer_page_id)
    return BaseResponse(data=OrganizerPageResponse.model_validate(organizer))


@router.get("/{organizer_page_id}/events")
async def list_organizer_public_events(
    organizer_page_id: UUID,
    service: Annotated[PublicOrganizerService, Depends(get_public_organizer_service)],
) -> BaseResponse[list[EventSummaryResponse]]:
    events = await service.list_events_by_organizer(organizer_page_id)
    return BaseResponse(data=[EventSummaryResponse.model_validate(e) for e in events])
```

- [ ] **Step 4: Register the public organizer router in server.py**

Add to `src/server.py`:

```python
from apps.organizer.public_urls import router as organizer_public_router
```

And in the `base_router.include_router` block:

```python
base_router.include_router(organizer_public_router)
```

- [ ] **Step 5: Run the organizer URL tests**

Run:
```bash
uv run pytest tests/apps/organizer/test_organizer_urls.py -v
```
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add src/apps/organizer/public_urls.py src/server.py tests/apps/organizer/test_organizer_urls.py
git commit -m "feat: add public organizer endpoints at /api/open/organizers"
```

---

### Task 7: Full integration verification

**Files:**
- Test: `tests/apps/event/test_event_urls.py`
- Test: `tests/apps/organizer/test_organizer_urls.py`

- [ ] **Step 1: Run the full event and organizer test suites**

Run:
```bash
uv run pytest tests/apps/event/test_event_urls.py tests/apps/organizer/test_organizer_urls.py -v
```
Expected: all tests pass

- [ ] **Step 2: Verify API shapes with curl**

```bash
# List events (requires user-or-guest token)
curl -s "http://localhost:8080/api/open/events" \
  -H "Authorization: Bearer <user_token>" | python3 -c "import sys,json; d=json.load(sys.stdin); print(f'Total events: {len(d[\"data\"])}')"

# Event detail with embedded data
curl -s "http://localhost:8080/api/open/events/71a97107-6382-49c3-ba2d-87143850361e" \
  -H "Authorization: Bearer <user_token>" | python3 -c "import sys,json; d=json.load(sys.stdin); print(json.dumps(d['data'], indent=2, default=str)[:800])"

# List organizers
curl -s "http://localhost:8080/api/open/organizers" \
  -H "Authorization: Bearer <user_token>" | python3 -c "import sys,json; d=json.load(sys.stdin); print(f'Total organizers: {len(d[\"data\"])}')"

# Organizer events
curl -s "http://localhost:8080/api/open/organizers/<organizer_page_id>/events" \
  -H "Authorization: Bearer <user_token>" | python3 -c "import sys,json; d=json.load(sys.stdin); print(f'Total events: {len(d[\"data\"])}')"
```

- [ ] **Step 3: Rebuild the graph**

Run:
```bash
python3 -c "from graphify.watch import _rebuild_code; from pathlib import Path; _rebuild_code(Path('.'))"
```

- [ ] **Step 4: Commit**

```bash
git add .
git commit -m "feat: complete public event and organizer endpoints"
```

---

## Self-Review

1. **Spec coverage:**
   - `GET /api/open/events` — list published events ✅ (Task 5)
   - `GET /api/open/events/{event_id}` — full event with embedded days/assets/tickets ✅ (Task 5)
   - `GET /api/open/organizers` — list organizers ✅ (Task 6)
   - `GET /api/open/organizers/{id}` — single organizer ✅ (Task 6)
   - `GET /api/open/organizers/{id}/events` — events by organizer ✅ (Task 6)
   - Interest endpoint stays at `/api/open/events/{event_id}/interest` ✅ (Task 5)

2. **Placeholder scan:**
   - No `TBD`, `TODO`, or vague instructions
   - All code is complete and shown inline

3. **Type consistency:**
   - `PublicEventService(event_repository, ticketing_repository)` — two args, matches `TicketingRepository.list_ticket_types_for_event()` and `list_allocations_for_event()` in Task 4
   - `PublicOrganizerService(repository)` — single arg, matches OrganizerRepository methods
   - `get_public_event_service()` injects both repos into `PublicEventService`
   - `EventDetailResponse`, `OrganizerPageResponse`, `EventSummaryResponse` used consistently
   - Router prefixes are `/api/open/events` and `/api/open/organizers` — no path conflicts with private routers

Plan complete and saved to `docs/superpowers/plans/2026-04-12-public-event-endpoints.md`. Two execution options:

1. **Subagent-Driven (recommended)** - I dispatch a fresh subagent per task, review between tasks, fast iteration
2. **Inline Execution** - Execute tasks in this session using executing-plans, batch execution with checkpoints

Which approach?