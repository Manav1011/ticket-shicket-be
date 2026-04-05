# Phase 1B Progressive Event Workflow Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Complete the organizer-side progressive editing workflow on top of the Phase 1 backend foundation so organizers can create, reopen, update, schedule, ticket, and operationally manage draft events without leaving gaps in the API surface.

**Architecture:** Keep the existing three-app split: `organizer`, `event`, and `ticketing`. Extend those apps with owner-scoped read/update routes, setup-status recomputation, full event-day CRUD, full scan lifecycle, and the missing ticketing read surfaces; do not introduce new apps or mix in later-phase concerns like media, publishing, orders, or RSVP.

**Tech Stack:** FastAPI, Pydantic, SQLAlchemy 2.0 async, Alembic, PostgreSQL, pytest, unittest.mock/AsyncMock

---

## Scope Check

This plan covers one connected subsystem: the organizer draft-editing workflow that sits on top of the Phase 1 foundation already implemented.

This plan intentionally does **not** include:
- media uploads
- public event page rendering
- publish/unpublish
- orders, payments, coupons
- attendee registration for open events
- live QR scan ingestion or Redis bitmap hardening

## Organizer Flow First

This is the exact organizer journey Phase 1B must support. The route list here is the user-visible contract the rest of the plan implements.

### 1. Organizer opens event tools

Frontend action:
- organizer visits the event creation area

Backend calls:
- `GET /api/organizers`

Backend behavior:
- return only organizer pages owned by the current user
- if the response is empty, frontend should route the organizer into organizer creation
- if there is one organizer, frontend can auto-select it
- if there are many, frontend shows a picker

### 2. Organizer creates an organizer page if needed

Frontend action:
- organizer enters organizer identity details

Backend calls:
- `POST /api/organizers`

Backend behavior:
- normalize slug
- enforce slug uniqueness
- store owner via `request.state.user.id`

### 3. Organizer creates a draft event shell

Frontend action:
- organizer clicks `Create Event` after choosing an organizer page

Backend calls:
- `POST /api/events/drafts`

Request:

```json
{
  "organizerPageId": "uuid"
}
```

Backend behavior:
- validate organizer ownership
- create a minimal `draft` event
- keep progressive fields nullable
- initialize `setup_status` to an empty object

Response:
- event id
- organizer page id
- `status = draft`
- `event_access_type = ticketed` by default
- empty progress state

### 4. Organizer lands on the event editor and resumes later

Frontend action:
- editor loads current event state
- organizer can reopen unfinished drafts later

Backend calls:
- `GET /api/events/{event_id}`
- `GET /api/organizers/{organizer_id}/events?status=draft`

Backend behavior:
- enforce owner scope through organizer ownership
- return the exact draft the user is editing
- return enough summary data for draft listing screens

### 5. Organizer fills basic event information

Frontend action:
- organizer edits title, description, event type, access mode, location mode, timezone

Backend calls:
- `PATCH /api/events/{event_id}/basic-info`

Request:

```json
{
  "title": "Ahmedabad Startup Meetup",
  "description": "Founders and builders meetup",
  "eventType": "meetup",
  "eventAccessType": "ticketed",
  "locationMode": "venue",
  "timezone": "Asia/Kolkata"
}
```

Backend behavior:
- partial update of the event shell
- recompute `setup_status.basic_info`
- leave publish-only validation for later phases

### 6. Organizer adds one or more event days

Frontend action:
- organizer creates event days
- organizer edits or deletes them while still in draft

Backend calls:
- `POST /api/events/{event_id}/days`
- `GET /api/events/{event_id}/days`
- `PATCH /api/events/days/{event_day_id}`
- `DELETE /api/events/days/{event_day_id}`

Backend behavior:
- enforce unique `day_index` per event
- initialize scan state to `not_started`
- recompute `setup_status.schedule`

### 7. Organizer configures ticketing only if the event is ticketed

Frontend action:
- if `event_access_type == ticketed`, organizer creates ticket types and allocates them to days
- if `event_access_type == open`, frontend skips ticket setup

Backend calls:
- `GET /api/events/{event_id}/ticket-types`
- `POST /api/events/{event_id}/ticket-types`
- `GET /api/events/{event_id}/ticket-allocations`
- `POST /api/events/{event_id}/ticket-allocations`

Backend behavior:
- hard-reject ticket routes for `open` events
- create ticket types under the event
- allocate quantities to event days
- generate concrete ticket rows
- recompute `setup_status.tickets`
- for `open` events, mark `tickets` as complete because ticketing is not required

### 8. Organizer checks draft readiness

Frontend action:
- editor shows section completion and missing parts

Backend calls:
- `GET /api/events/{event_id}/readiness`

Backend behavior:
- summarize:
  - completed sections
  - missing sections
  - blocking issues
- use the same rules as `setup_status`
- do not publish anything yet

### 9. Organizer operates event-day scanning

Frontend action:
- on the actual event day, organizer controls entry operations

Backend calls:
- `POST /api/events/days/{event_day_id}/start-scan`
- `POST /api/events/days/{event_day_id}/pause-scan`
- `POST /api/events/days/{event_day_id}/resume-scan`
- `POST /api/events/days/{event_day_id}/end-scan`

Backend behavior:
- only allow valid state transitions
- reject scans outside `active` state in later scan-ingestion work
- keep timestamps for each operational state

## Phase 1B Route Surface

This is the complete route surface Phase 1B should leave behind.

```text
GET    /api/organizers
POST   /api/organizers
GET    /api/organizers/{organizer_id}/events?status=draft

POST   /api/events/drafts
GET    /api/events/{event_id}
PATCH  /api/events/{event_id}/basic-info
GET    /api/events/{event_id}/readiness

POST   /api/events/{event_id}/days
GET    /api/events/{event_id}/days
PATCH  /api/events/days/{event_day_id}
DELETE /api/events/days/{event_day_id}

POST   /api/events/days/{event_day_id}/start-scan
POST   /api/events/days/{event_day_id}/pause-scan
POST   /api/events/days/{event_day_id}/resume-scan
POST   /api/events/days/{event_day_id}/end-scan

GET    /api/events/{event_id}/ticket-types
POST   /api/events/{event_id}/ticket-types
GET    /api/events/{event_id}/ticket-allocations
POST   /api/events/{event_id}/ticket-allocations
```

## Setup Status Rules

Phase 1B should standardize `setup_status` around these keys:

```json
{
  "basic_info": true,
  "schedule": false,
  "tickets": false
}
```

Rules:
- `basic_info = true` when `title`, `event_access_type`, `location_mode`, and `timezone` are all present
- `schedule = true` when the event has at least one `event_day`
- `tickets = true` when:
  - `event_access_type == "open"`, or
  - the event has at least one ticket type and at least one day allocation

## File Structure

- `src/apps/organizer/repository.py`: add owner-scoped organizer listing and organizer event-summary queries.
- `src/apps/organizer/response.py`: add organizer list and organizer event-summary DTOs.
- `src/apps/organizer/urls.py`: add `GET /api/organizers` and `GET /api/organizers/{organizer_id}/events`.
- `src/apps/event/repository.py`: add event detail fetch, event list-by-organizer, event-day list/update/delete, and setup-status helper queries.
- `src/apps/event/service.py`: add event detail retrieval, basic-info update, setup-status recomputation, event-day CRUD, readiness summary, and full scan lifecycle methods.
- `src/apps/event/request.py`: add `UpdateEventDayRequest`.
- `src/apps/event/response.py`: add `EventReadinessResponse`, `EventReadinessIssueResponse`, `EventSummaryResponse`, and `EventDayListResponse` if needed.
- `src/apps/event/urls.py`: add `GET /api/events/{event_id}`, `PATCH /api/events/{event_id}/basic-info`, `GET /api/events/{event_id}/readiness`, event-day CRUD routes, and pause/resume/end-scan routes.
- `src/apps/ticketing/repository.py`: add list queries for ticket types and day allocations, plus small aggregate helpers for setup-status computation.
- `src/apps/ticketing/response.py`: add list response DTOs if needed.
- `src/apps/ticketing/urls.py`: add `GET /api/events/{event_id}/ticket-types` and `GET /api/events/{event_id}/ticket-allocations`.
- `tests/apps/organizer/test_organizer_service.py`: extend for organizer listing and organizer event list behavior.
- `tests/apps/organizer/test_organizer_urls.py`: extend for organizer list and organizer event-summary routes.
- `tests/apps/event/test_event_service.py`: extend for basic-info updates, setup-status recomputation, event-day CRUD, readiness, and scan transitions.
- `tests/apps/event/test_event_urls.py`: extend for event detail, basic-info patch, readiness, event-day CRUD, and full scan lifecycle routes.
- `tests/apps/ticketing/test_ticketing_service.py`: extend for list helpers and ticket completeness rules.
- `tests/apps/ticketing/test_ticketing_urls.py`: extend for ticket type list and allocation list routes.

## Task 1: Add Organizer Listing and Draft Resume Surfaces

**Files:**
- Modify: `src/apps/organizer/repository.py`
- Modify: `src/apps/organizer/response.py`
- Modify: `src/apps/organizer/urls.py`
- Modify: `src/apps/event/repository.py`
- Modify: `tests/apps/organizer/test_organizer_service.py`
- Modify: `tests/apps/organizer/test_organizer_urls.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/apps/organizer/test_organizer_service.py
@pytest.mark.asyncio
async def test_list_organizer_events_filters_by_owner_and_status():
    owner_id = uuid4()
    organizer_id = uuid4()
    repo = AsyncMock()
    repo.list_events_for_owner.return_value = [
        SimpleNamespace(id=uuid4(), organizer_page_id=organizer_id, status="draft")
    ]
    service = OrganizerService(repo)

    events = await service.list_organizer_events(owner_id, organizer_id, "draft")

    assert len(events) == 1
    repo.list_events_for_owner.assert_awaited_once_with(owner_id, organizer_id, "draft")
```

```python
# tests/apps/organizer/test_organizer_urls.py
from apps.organizer.urls import list_organizers, list_organizer_events


@pytest.mark.asyncio
async def test_list_organizers_returns_owner_scoped_rows():
    owner_id = uuid4()
    request = SimpleNamespace(state=SimpleNamespace(user=SimpleNamespace(id=owner_id)))
    service = AsyncMock()
    service.list_organizers.return_value = [
        SimpleNamespace(
            id=uuid4(),
            owner_user_id=owner_id,
            name="Ahmedabad Talks",
            slug="ahmedabad-talks",
            bio="Meetups",
            visibility="public",
            status="active",
            logo_url=None,
            cover_image_url=None,
            website_url=None,
            instagram_url=None,
            facebook_url=None,
            youtube_url=None,
        )
    ]

    response = await list_organizers(request=request, service=service)

    assert len(response.data) == 1


@pytest.mark.asyncio
async def test_list_organizer_events_returns_draft_summaries():
    owner_id = uuid4()
    organizer_id = uuid4()
    request = SimpleNamespace(state=SimpleNamespace(user=SimpleNamespace(id=owner_id)))
    service = AsyncMock()
    service.list_organizer_events.return_value = [
        SimpleNamespace(
            id=uuid4(),
            organizer_page_id=organizer_id,
            title=None,
            status="draft",
            event_access_type="ticketed",
            setup_status={"basic_info": False, "schedule": False, "tickets": False},
            created_at="2026-04-05T10:00:00",
        )
    ]

    response = await list_organizer_events(
        organizer_id=organizer_id,
        status="draft",
        request=request,
        service=service,
    )

    assert response.data[0].status == "draft"
```

- [ ] **Step 2: Run the tests to verify they fail**

Run:

```bash
/home/manav1011/Documents/ticket-shicket-be/.venv/bin/python -m pytest tests/apps/organizer/test_organizer_service.py tests/apps/organizer/test_organizer_urls.py -v
```

Expected:

```text
FAIL: OrganizerService has no attribute list_organizer_events
FAIL: cannot import name list_organizers
FAIL: cannot import name list_organizer_events
```

- [ ] **Step 3: Write the minimal implementation**

```python
# src/apps/organizer/repository.py
from sqlalchemy import select

from apps.event.models import EventModel
from .models import OrganizerPageModel


async def list_by_owner(self, owner_user_id):
    result = await self._session.scalars(
        select(OrganizerPageModel)
        .where(OrganizerPageModel.owner_user_id == owner_user_id)
        .order_by(OrganizerPageModel.created_at.desc())
    )
    return list(result)


async def list_events_for_owner(self, owner_user_id, organizer_id, status=None):
    query = (
        select(EventModel)
        .join_from(EventModel, OrganizerPageModel)
        .where(
            EventModel.organizer_page_id == organizer_id,
            OrganizerPageModel.owner_user_id == owner_user_id,
        )
        .order_by(EventModel.created_at.desc())
    )
    if status is not None:
        query = query.where(EventModel.status == status)
    result = await self._session.scalars(query)
    return list(result)
```

```python
# src/apps/organizer/service.py
async def list_organizer_events(self, owner_user_id, organizer_id, status=None):
    return await self.repository.list_events_for_owner(owner_user_id, organizer_id, status)
```

```python
# src/apps/organizer/urls.py
@router.get("")
async def list_organizers(
    request: Request,
    service: Annotated[OrganizerService, Depends(get_organizer_service)],
) -> BaseResponse[list[OrganizerPageResponse]]:
    organizers = await service.list_organizers(request.state.user.id)
    return BaseResponse(data=[OrganizerPageResponse.model_validate(item) for item in organizers])


@router.get("/{organizer_id}/events")
async def list_organizer_events(
    organizer_id: UUID,
    request: Request,
    service: Annotated[OrganizerService, Depends(get_organizer_service)],
    status: str | None = None,
) -> BaseResponse[list[EventSummaryResponse]]:
    events = await service.list_organizer_events(request.state.user.id, organizer_id, status)
    return BaseResponse(data=[EventSummaryResponse.model_validate(item) for item in events])
```

- [ ] **Step 4: Run the tests to verify they pass**

Run:

```bash
/home/manav1011/Documents/ticket-shicket-be/.venv/bin/python -m pytest tests/apps/organizer/test_organizer_service.py tests/apps/organizer/test_organizer_urls.py -v
```

Expected:

```text
PASS: organizer listing and organizer event list routes return owner-scoped data
```

- [ ] **Step 5: Commit**

```bash
git add src/apps/organizer/repository.py src/apps/organizer/response.py src/apps/organizer/service.py src/apps/organizer/urls.py tests/apps/organizer/test_organizer_service.py tests/apps/organizer/test_organizer_urls.py
git commit -m "feat: add organizer listing and draft resume routes"
```

## Task 2: Add Event Detail, Basic Info Updates, and Setup Status Recalculation

**Files:**
- Modify: `src/apps/event/repository.py`
- Modify: `src/apps/event/service.py`
- Modify: `src/apps/event/response.py`
- Modify: `src/apps/event/urls.py`
- Modify: `tests/apps/event/test_event_service.py`
- Modify: `tests/apps/event/test_event_urls.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/apps/event/test_event_service.py
@pytest.mark.asyncio
async def test_update_basic_info_marks_basic_info_complete():
    owner_id = uuid4()
    event_id = uuid4()
    repo = AsyncMock()
    organizer_repo = AsyncMock()
    event = SimpleNamespace(
        id=event_id,
        title=None,
        description=None,
        event_type=None,
        event_access_type="ticketed",
        location_mode=None,
        timezone=None,
        setup_status={},
    )
    repo.get_by_id_for_owner.return_value = event
    repo.count_event_days.return_value = 0
    repo.count_ticket_types.return_value = 0
    repo.count_ticket_allocations.return_value = 0
    service = EventService(repo, organizer_repo)

    updated = await service.update_basic_info(
        owner_id,
        event_id,
        title="Ahmedabad Startup Meetup",
        description="Founders and builders meetup",
        event_type="meetup",
        event_access_type="open",
        location_mode="venue",
        timezone="Asia/Kolkata",
    )

    assert updated.setup_status["basic_info"] is True
    assert updated.setup_status["tickets"] is True
```

```python
# tests/apps/event/test_event_urls.py
from apps.event.request import UpdateEventBasicInfoRequest
from apps.event.urls import get_event_detail, get_event_readiness, update_basic_info


@pytest.mark.asyncio
async def test_get_event_detail_returns_owner_scoped_event():
    owner_id = uuid4()
    event_id = uuid4()
    request = SimpleNamespace(state=SimpleNamespace(user=SimpleNamespace(id=owner_id)))
    service = AsyncMock()
    service.get_event_detail.return_value = SimpleNamespace(
        id=event_id,
        organizer_page_id=uuid4(),
        created_by_user_id=owner_id,
        title=None,
        slug=None,
        description=None,
        event_type=None,
        status="draft",
        event_access_type="ticketed",
        setup_status={"basic_info": False, "schedule": False, "tickets": False},
        location_mode=None,
        timezone=None,
        start_date=None,
        end_date=None,
        venue_name=None,
        venue_address=None,
        venue_city=None,
        venue_state=None,
        venue_country=None,
        venue_latitude=None,
        venue_longitude=None,
        venue_google_place_id=None,
        online_event_url=None,
        recorded_event_url=None,
        published_at=None,
    )

    response = await get_event_detail(event_id=event_id, request=request, service=service)

    assert response.data.id == event_id


@pytest.mark.asyncio
async def test_update_basic_info_returns_recomputed_setup_status():
    owner_id = uuid4()
    event_id = uuid4()
    request = SimpleNamespace(state=SimpleNamespace(user=SimpleNamespace(id=owner_id)))
    body = UpdateEventBasicInfoRequest(
        title="Ahmedabad Startup Meetup",
        description="Founders and builders meetup",
        event_type="meetup",
        event_access_type="open",
        location_mode="venue",
        timezone="Asia/Kolkata",
    )
    service = AsyncMock()
    service.update_basic_info.return_value = SimpleNamespace(
        id=event_id,
        organizer_page_id=uuid4(),
        created_by_user_id=owner_id,
        title="Ahmedabad Startup Meetup",
        slug=None,
        description="Founders and builders meetup",
        event_type="meetup",
        status="draft",
        event_access_type="open",
        setup_status={"basic_info": True, "schedule": False, "tickets": True},
        location_mode="venue",
        timezone="Asia/Kolkata",
        start_date=None,
        end_date=None,
        venue_name=None,
        venue_address=None,
        venue_city=None,
        venue_state=None,
        venue_country=None,
        venue_latitude=None,
        venue_longitude=None,
        venue_google_place_id=None,
        online_event_url=None,
        recorded_event_url=None,
        published_at=None,
    )

    response = await update_basic_info(
        event_id=event_id, request=request, body=body, service=service
    )

    assert response.data.setup_status["basic_info"] is True


@pytest.mark.asyncio
async def test_get_event_readiness_returns_missing_sections():
    owner_id = uuid4()
    event_id = uuid4()
    request = SimpleNamespace(state=SimpleNamespace(user=SimpleNamespace(id=owner_id)))
    service = AsyncMock()
    service.get_readiness.return_value = {
        "completed_sections": ["basic_info"],
        "missing_sections": ["schedule", "tickets"],
        "blocking_issues": ["Add at least one event day"],
    }

    response = await get_event_readiness(
        event_id=event_id,
        request=request,
        service=service,
    )

    assert "schedule" in response.data.missing_sections
```

- [ ] **Step 2: Run the tests to verify they fail**

Run:

```bash
/home/manav1011/Documents/ticket-shicket-be/.venv/bin/python -m pytest tests/apps/event/test_event_service.py tests/apps/event/test_event_urls.py -v
```

Expected:

```text
FAIL: EventService has no attribute update_basic_info
FAIL: cannot import name get_event_detail
FAIL: cannot import name get_event_readiness
```

- [ ] **Step 3: Write the minimal implementation**

```python
# src/apps/event/service.py
def _build_setup_status(self, event, day_count, ticket_type_count, allocation_count):
    basic_info_complete = all(
        [event.title, event.event_access_type, event.location_mode, event.timezone]
    )
    schedule_complete = day_count > 0
    tickets_complete = event.event_access_type == "open" or (
        ticket_type_count > 0 and allocation_count > 0
    )
    return {
        "basic_info": basic_info_complete,
        "schedule": schedule_complete,
        "tickets": tickets_complete,
    }


async def update_basic_info(self, owner_user_id, event_id, **payload):
    event = await self.repository.get_by_id_for_owner(event_id, owner_user_id)
    if not event:
        raise EventNotFound
    for field, value in payload.items():
        setattr(event, field, value)
    day_count = await self.repository.count_event_days(event_id)
    ticket_type_count = await self.repository.count_ticket_types(event_id)
    allocation_count = await self.repository.count_ticket_allocations(event_id)
    event.setup_status = self._build_setup_status(
        event, day_count, ticket_type_count, allocation_count
    )
    await self.repository.session.flush()
    return event


async def get_event_detail(self, owner_user_id, event_id):
    event = await self.repository.get_by_id_for_owner(event_id, owner_user_id)
    if not event:
        raise EventNotFound
    return event


async def get_readiness(self, owner_user_id, event_id):
    event = await self.get_event_detail(owner_user_id, event_id)
    status = event.setup_status or {"basic_info": False, "schedule": False, "tickets": False}
    missing_sections = [name for name, done in status.items() if not done]
    blocking_issues = []
    if not status["schedule"]:
        blocking_issues.append("Add at least one event day")
    if not status["basic_info"]:
        blocking_issues.append("Complete basic event information")
    if not status["tickets"]:
        blocking_issues.append("Add ticket types and allocations or switch event to open")
    return {
        "completed_sections": [name for name, done in status.items() if done],
        "missing_sections": missing_sections,
        "blocking_issues": blocking_issues,
    }
```

```python
# src/apps/event/urls.py
@router.get("/{event_id}")
async def get_event_detail(
    event_id: UUID,
    request: Request,
    service: Annotated[EventService, Depends(get_event_service)],
) -> BaseResponse[EventResponse]:
    event = await service.get_event_detail(request.state.user.id, event_id)
    return BaseResponse(data=EventResponse.model_validate(event))


@router.patch("/{event_id}/basic-info")
async def update_basic_info(
    event_id: UUID,
    request: Request,
    body: Annotated[UpdateEventBasicInfoRequest, Body()],
    service: Annotated[EventService, Depends(get_event_service)],
) -> BaseResponse[EventResponse]:
    event = await service.update_basic_info(
        request.state.user.id,
        event_id,
        **body.model_dump(),
    )
    return BaseResponse(data=EventResponse.model_validate(event))


@router.get("/{event_id}/readiness")
async def get_event_readiness(
    event_id: UUID,
    request: Request,
    service: Annotated[EventService, Depends(get_event_service)],
) -> BaseResponse[EventReadinessResponse]:
    readiness = await service.get_readiness(request.state.user.id, event_id)
    return BaseResponse(data=EventReadinessResponse.model_validate(readiness))
```

- [ ] **Step 4: Run the tests to verify they pass**

Run:

```bash
/home/manav1011/Documents/ticket-shicket-be/.venv/bin/python -m pytest tests/apps/event/test_event_service.py tests/apps/event/test_event_urls.py -v
```

Expected:

```text
PASS: event detail, basic-info patch, and readiness routes return recomputed draft state
```

- [ ] **Step 5: Commit**

```bash
git add src/apps/event/repository.py src/apps/event/service.py src/apps/event/response.py src/apps/event/urls.py tests/apps/event/test_event_service.py tests/apps/event/test_event_urls.py
git commit -m "feat: add event detail and progressive basic info updates"
```

## Task 3: Add Event-Day CRUD and Full Scan Lifecycle

**Files:**
- Modify: `src/apps/event/request.py`
- Modify: `src/apps/event/repository.py`
- Modify: `src/apps/event/service.py`
- Modify: `src/apps/event/urls.py`
- Modify: `tests/apps/event/test_event_service.py`
- Modify: `tests/apps/event/test_event_urls.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/apps/event/test_event_service.py
@pytest.mark.asyncio
async def test_pause_resume_end_scan_enforces_valid_transitions():
    owner_id = uuid4()
    repo = AsyncMock()
    organizer_repo = AsyncMock()
    day = SimpleNamespace(
        id=uuid4(),
        event_id=uuid4(),
        scan_status="active",
        scan_started_at=None,
        scan_paused_at=None,
        scan_ended_at=None,
        next_ticket_index=1,
    )
    repo.get_event_day_for_owner.return_value = day
    service = EventService(repo, organizer_repo)

    paused = await service.pause_scan(owner_id, day.id)
    assert paused.scan_status == "paused"

    resumed = await service.resume_scan(owner_id, day.id)
    assert resumed.scan_status == "active"

    ended = await service.end_scan(owner_id, day.id)
    assert ended.scan_status == "ended"
```

```python
# tests/apps/event/test_event_urls.py
from apps.event.request import CreateEventDayRequest, UpdateEventDayRequest
from apps.event.urls import (
    create_event_day,
    delete_event_day,
    end_scan,
    list_event_days,
    pause_scan,
    resume_scan,
    update_event_day,
)


@pytest.mark.asyncio
async def test_create_event_day_returns_day_payload():
    owner_id = uuid4()
    event_id = uuid4()
    request = SimpleNamespace(state=SimpleNamespace(user=SimpleNamespace(id=owner_id)))
    body = CreateEventDayRequest(day_index=1, date="2026-04-15")
    service = AsyncMock()
    service.create_event_day.return_value = SimpleNamespace(
        id=uuid4(),
        event_id=event_id,
        day_index=1,
        date="2026-04-15",
        start_time=None,
        end_time=None,
        scan_status="not_started",
        scan_started_at=None,
        scan_paused_at=None,
        scan_ended_at=None,
        next_ticket_index=1,
    )

    response = await create_event_day(event_id=event_id, request=request, body=body, service=service)

    assert response.data.day_index == 1


@pytest.mark.asyncio
async def test_pause_resume_end_scan_routes_return_latest_day_state():
    owner_id = uuid4()
    event_day_id = uuid4()
    request = SimpleNamespace(state=SimpleNamespace(user=SimpleNamespace(id=owner_id)))
    service = AsyncMock()
    service.pause_scan.return_value = SimpleNamespace(
        id=event_day_id,
        event_id=uuid4(),
        day_index=1,
        date="2026-04-15",
        start_time=None,
        end_time=None,
        scan_status="paused",
        scan_started_at="2026-04-15T09:00:00",
        scan_paused_at="2026-04-15T09:30:00",
        scan_ended_at=None,
        next_ticket_index=1,
    )

    response = await pause_scan(event_day_id=event_day_id, request=request, service=service)

    assert response.data.scan_status == "paused"
```

- [ ] **Step 2: Run the tests to verify they fail**

Run:

```bash
/home/manav1011/Documents/ticket-shicket-be/.venv/bin/python -m pytest tests/apps/event/test_event_service.py tests/apps/event/test_event_urls.py -v
```

Expected:

```text
FAIL: EventService has no attribute pause_scan
FAIL: cannot import name create_event_day
FAIL: cannot import name pause_scan
```

- [ ] **Step 3: Write the minimal implementation**

```python
# src/apps/event/request.py
class UpdateEventDayRequest(CamelCaseModel):
    day_index: int
    date: date
    start_time: datetime | None = None
    end_time: datetime | None = None
```

```python
# src/apps/event/service.py
async def list_event_days(self, owner_user_id, event_id):
    event = await self.repository.get_by_id_for_owner(event_id, owner_user_id)
    if not event:
        raise EventNotFound
    return await self.repository.list_event_days(event_id)


async def update_event_day(self, owner_user_id, event_day_id, **payload):
    day = await self.repository.get_event_day_for_owner(event_day_id, owner_user_id)
    if not day:
        raise EventNotFound
    for field, value in payload.items():
        setattr(day, field, value)
    await self.repository.session.flush()
    return day


async def delete_event_day(self, owner_user_id, event_day_id):
    day = await self.repository.get_event_day_for_owner(event_day_id, owner_user_id)
    if not day:
        raise EventNotFound
    await self.repository.delete_event_day(day)


async def pause_scan(self, owner_user_id, event_day_id):
    day = await self.repository.get_event_day_for_owner(event_day_id, owner_user_id)
    if not day or day.scan_status != "active":
        raise InvalidScanTransition
    day.scan_status = "paused"
    day.scan_paused_at = datetime.utcnow()
    await self.repository.session.flush()
    return day


async def resume_scan(self, owner_user_id, event_day_id):
    day = await self.repository.get_event_day_for_owner(event_day_id, owner_user_id)
    if not day or day.scan_status != "paused":
        raise InvalidScanTransition
    day.scan_status = "active"
    await self.repository.session.flush()
    return day


async def end_scan(self, owner_user_id, event_day_id):
    day = await self.repository.get_event_day_for_owner(event_day_id, owner_user_id)
    if not day or day.scan_status == "ended":
        raise InvalidScanTransition
    day.scan_status = "ended"
    day.scan_ended_at = datetime.utcnow()
    await self.repository.session.flush()
    return day
```

```python
# src/apps/event/urls.py
@router.post("/{event_id}/days")
async def create_event_day(
    event_id: UUID,
    request: Request,
    body: Annotated[CreateEventDayRequest, Body()],
    service: Annotated[EventService, Depends(get_event_service)],
) -> BaseResponse[EventDayResponse]:
    day = await service.create_event_day(request.state.user.id, event_id, **body.model_dump())
    return BaseResponse(data=EventDayResponse.model_validate(day))


@router.get("/{event_id}/days")
async def list_event_days(
    event_id: UUID,
    request: Request,
    service: Annotated[EventService, Depends(get_event_service)],
) -> BaseResponse[list[EventDayResponse]]:
    days = await service.list_event_days(request.state.user.id, event_id)
    return BaseResponse(data=[EventDayResponse.model_validate(item) for item in days])


@router.patch("/days/{event_day_id}")
async def update_event_day(
    event_day_id: UUID,
    request: Request,
    body: Annotated[UpdateEventDayRequest, Body()],
    service: Annotated[EventService, Depends(get_event_service)],
) -> BaseResponse[EventDayResponse]:
    day = await service.update_event_day(
        request.state.user.id,
        event_day_id,
        **body.model_dump(),
    )
    return BaseResponse(data=EventDayResponse.model_validate(day))


@router.delete("/days/{event_day_id}")
async def delete_event_day(
    event_day_id: UUID,
    request: Request,
    service: Annotated[EventService, Depends(get_event_service)],
) -> BaseResponse[dict]:
    await service.delete_event_day(request.state.user.id, event_day_id)
    return BaseResponse(data={"deleted": True})


@router.post("/days/{event_day_id}/pause-scan")
async def pause_scan(
    event_day_id: UUID,
    request: Request,
    service: Annotated[EventService, Depends(get_event_service)],
) -> BaseResponse[EventDayResponse]:
    day = await service.pause_scan(request.state.user.id, event_day_id)
    return BaseResponse(data=EventDayResponse.model_validate(day))


@router.post("/days/{event_day_id}/resume-scan")
async def resume_scan(
    event_day_id: UUID,
    request: Request,
    service: Annotated[EventService, Depends(get_event_service)],
) -> BaseResponse[EventDayResponse]:
    day = await service.resume_scan(request.state.user.id, event_day_id)
    return BaseResponse(data=EventDayResponse.model_validate(day))


@router.post("/days/{event_day_id}/end-scan")
async def end_scan(
    event_day_id: UUID,
    request: Request,
    service: Annotated[EventService, Depends(get_event_service)],
) -> BaseResponse[EventDayResponse]:
    day = await service.end_scan(request.state.user.id, event_day_id)
    return BaseResponse(data=EventDayResponse.model_validate(day))
```

- [ ] **Step 4: Run the tests to verify they pass**

Run:

```bash
/home/manav1011/Documents/ticket-shicket-be/.venv/bin/python -m pytest tests/apps/event/test_event_service.py tests/apps/event/test_event_urls.py -v
```

Expected:

```text
PASS: event-day CRUD and full scan lifecycle routes are owner-scoped and transition safely
```

- [ ] **Step 5: Commit**

```bash
git add src/apps/event/request.py src/apps/event/repository.py src/apps/event/service.py src/apps/event/urls.py tests/apps/event/test_event_service.py tests/apps/event/test_event_urls.py
git commit -m "feat: add event day crud and full scan lifecycle"
```

## Task 4: Add Ticketing Read Surfaces and Ticket Setup Completeness

**Files:**
- Modify: `src/apps/ticketing/repository.py`
- Modify: `src/apps/ticketing/service.py`
- Modify: `src/apps/ticketing/response.py`
- Modify: `src/apps/ticketing/urls.py`
- Modify: `tests/apps/ticketing/test_ticketing_service.py`
- Modify: `tests/apps/ticketing/test_ticketing_urls.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/apps/ticketing/test_ticketing_service.py
@pytest.mark.asyncio
async def test_list_ticket_setup_returns_ticket_types_and_allocations_for_owner_event():
    owner_id = uuid4()
    event_id = uuid4()
    repo = AsyncMock()
    event_repo = AsyncMock()
    event_repo.get_by_id_for_owner.return_value = SimpleNamespace(id=event_id, event_access_type="ticketed")
    repo.list_ticket_types_for_event.return_value = [SimpleNamespace(id=uuid4(), event_id=event_id, name="General", category="PUBLIC", price=0, currency="INR")]
    repo.list_allocations_for_event.return_value = [SimpleNamespace(id=uuid4(), event_day_id=uuid4(), ticket_type_id=uuid4(), quantity=25)]
    service = TicketingService(repo, event_repo, event_repo)

    ticket_types = await service.list_ticket_types(owner_id, event_id)
    allocations = await service.list_allocations(owner_id, event_id)

    assert len(ticket_types) == 1
    assert len(allocations) == 1
```

```python
# tests/apps/ticketing/test_ticketing_urls.py
from apps.ticketing.urls import list_ticket_allocations, list_ticket_types


@pytest.mark.asyncio
async def test_list_ticket_types_returns_event_ticket_types():
    owner_id = uuid4()
    event_id = uuid4()
    request = SimpleNamespace(state=SimpleNamespace(user=SimpleNamespace(id=owner_id)))
    service = AsyncMock()
    service.list_ticket_types.return_value = [
        SimpleNamespace(
            id=uuid4(),
            event_id=event_id,
            name="General",
            category="PUBLIC",
            price=0,
            currency="INR",
        )
    ]

    response = await list_ticket_types(event_id=event_id, request=request, service=service)

    assert response.data[0].name == "General"


@pytest.mark.asyncio
async def test_list_ticket_allocations_returns_day_allocations():
    owner_id = uuid4()
    event_id = uuid4()
    request = SimpleNamespace(state=SimpleNamespace(user=SimpleNamespace(id=owner_id)))
    service = AsyncMock()
    service.list_allocations.return_value = [
        SimpleNamespace(
            id=uuid4(),
            event_day_id=uuid4(),
            ticket_type_id=uuid4(),
            quantity=25,
        )
    ]

    response = await list_ticket_allocations(event_id=event_id, request=request, service=service)

    assert response.data[0].quantity == 25
```

- [ ] **Step 2: Run the tests to verify they fail**

Run:

```bash
/home/manav1011/Documents/ticket-shicket-be/.venv/bin/python -m pytest tests/apps/ticketing/test_ticketing_service.py tests/apps/ticketing/test_ticketing_urls.py -v
```

Expected:

```text
FAIL: TicketingService has no attribute list_ticket_types
FAIL: cannot import name list_ticket_types
FAIL: cannot import name list_ticket_allocations
```

- [ ] **Step 3: Write the minimal implementation**

```python
# src/apps/ticketing/service.py
async def list_ticket_types(self, owner_user_id, event_id):
    await self.event_repository.get_by_id_for_owner(event_id, owner_user_id)
    return await self.repository.list_ticket_types_for_event(event_id)


async def list_allocations(self, owner_user_id, event_id):
    await self.event_repository.get_by_id_for_owner(event_id, owner_user_id)
    return await self.repository.list_allocations_for_event(event_id)
```

```python
# src/apps/ticketing/repository.py
async def list_ticket_types_for_event(self, event_id: UUID) -> list[TicketTypeModel]:
    result = await self._session.scalars(
        select(TicketTypeModel)
        .where(TicketTypeModel.event_id == event_id)
        .order_by(TicketTypeModel.created_at.asc())
    )
    return list(result)


async def list_allocations_for_event(self, event_id: UUID) -> list[DayTicketAllocationModel]:
    result = await self._session.scalars(
        select(DayTicketAllocationModel)
        .join(TicketTypeModel, DayTicketAllocationModel.ticket_type_id == TicketTypeModel.id)
        .where(TicketTypeModel.event_id == event_id)
        .order_by(DayTicketAllocationModel.created_at.asc())
    )
    return list(result)
```

```python
# src/apps/ticketing/urls.py
@router.get("/{event_id}/ticket-types")
async def list_ticket_types(
    event_id: UUID,
    request: Request,
    service: Annotated[TicketingService, Depends(get_ticketing_service)],
) -> BaseResponse[list[TicketTypeResponse]]:
    ticket_types = await service.list_ticket_types(request.state.user.id, event_id)
    return BaseResponse(data=[TicketTypeResponse.model_validate(item) for item in ticket_types])


@router.get("/{event_id}/ticket-allocations")
async def list_ticket_allocations(
    event_id: UUID,
    request: Request,
    service: Annotated[TicketingService, Depends(get_ticketing_service)],
) -> BaseResponse[list[DayTicketAllocationResponse]]:
    allocations = await service.list_allocations(request.state.user.id, event_id)
    return BaseResponse(data=[DayTicketAllocationResponse.model_validate(item) for item in allocations])
```

- [ ] **Step 4: Run the tests to verify they pass**

Run:

```bash
/home/manav1011/Documents/ticket-shicket-be/.venv/bin/python -m pytest tests/apps/ticketing/test_ticketing_service.py tests/apps/ticketing/test_ticketing_urls.py -v
```

Expected:

```text
PASS: ticketing list routes expose ticket setup for progressive editors
```

- [ ] **Step 5: Commit**

```bash
git add src/apps/ticketing/repository.py src/apps/ticketing/service.py src/apps/ticketing/response.py src/apps/ticketing/urls.py tests/apps/ticketing/test_ticketing_service.py tests/apps/ticketing/test_ticketing_urls.py
git commit -m "feat: add ticketing read routes for draft editors"
```

## Task 5: Add Readiness Integration and End-to-End Draft Workflow Tests

**Files:**
- Modify: `src/apps/event/service.py`
- Modify: `src/apps/event/urls.py`
- Modify: `src/apps/ticketing/service.py`
- Modify: `tests/apps/event/test_app_bootstrap.py`
- Create: `tests/apps/event/test_phase_1b_workflow.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/apps/event/test_phase_1b_workflow.py
from types import SimpleNamespace
from uuid import uuid4
from unittest.mock import AsyncMock

import pytest

from apps.event.service import EventService


@pytest.mark.asyncio
async def test_readiness_marks_open_event_complete_without_ticket_setup():
    owner_id = uuid4()
    event_id = uuid4()
    repo = AsyncMock()
    organizer_repo = AsyncMock()
    event = SimpleNamespace(
        id=event_id,
        title="Open Community Meetup",
        event_access_type="open",
        location_mode="venue",
        timezone="Asia/Kolkata",
        setup_status={},
    )
    repo.get_by_id_for_owner.return_value = event
    repo.count_event_days.return_value = 1
    repo.count_ticket_types.return_value = 0
    repo.count_ticket_allocations.return_value = 0
    service = EventService(repo, organizer_repo)

    readiness = await service.get_readiness(owner_id, event_id)

    assert readiness["missing_sections"] == []
    assert readiness["blocking_issues"] == []
```

```python
# tests/apps/event/test_app_bootstrap.py
def test_app_includes_phase_1b_routes(client):
    openapi = client.get("/openapi.json").json()
    assert "/api/organizers" in openapi["paths"]
    assert "/api/events/{event_id}" in openapi["paths"]
    assert "/api/events/{event_id}/readiness" in openapi["paths"]
    assert "/api/events/{event_id}/days" in openapi["paths"]
    assert "/api/events/days/{event_day_id}/pause-scan" in openapi["paths"]
    assert "/api/events/{event_id}/ticket-types" in openapi["paths"]
    assert "/api/events/{event_id}/ticket-allocations" in openapi["paths"]
```

- [ ] **Step 2: Run the tests to verify they fail**

Run:

```bash
/home/manav1011/Documents/ticket-shicket-be/.venv/bin/python -m pytest tests/apps/event/test_phase_1b_workflow.py tests/apps/event/test_app_bootstrap.py -v
```

Expected:

```text
FAIL: missing readiness edge-case coverage
FAIL: new Phase 1B routes absent from OpenAPI
```

- [ ] **Step 3: Write the minimal implementation**

```python
# src/apps/event/service.py
async def refresh_setup_status(self, event):
    day_count = await self.repository.count_event_days(event.id)
    ticket_type_count = await self.repository.count_ticket_types(event.id)
    allocation_count = await self.repository.count_ticket_allocations(event.id)
    event.setup_status = self._build_setup_status(
        event, day_count, ticket_type_count, allocation_count
    )
    await self.repository.session.flush()
    return event.setup_status
```

```python
# src/apps/ticketing/service.py
async def create_ticket_type(self, owner_user_id, event_id, name, category, price, currency):
    event = await self.event_repository.get_by_id_for_owner(event_id, owner_user_id)
    if event.event_access_type != "ticketed":
        raise OpenEventDoesNotSupportTickets
    ticket_type = TicketTypeModel(
        event_id=event_id,
        name=name,
        category=category,
        price=price,
        currency=currency,
    )
    self.repository.add(ticket_type)
    await self.repository.session.flush()
    await self.repository.session.refresh(ticket_type)
    return ticket_type
```

- [ ] **Step 4: Run the focused Phase 1B suite**

Run:

```bash
/home/manav1011/Documents/ticket-shicket-be/.venv/bin/python -m pytest tests/apps/organizer/test_organizer_service.py tests/apps/organizer/test_organizer_urls.py tests/apps/event/test_event_service.py tests/apps/event/test_event_urls.py tests/apps/event/test_app_bootstrap.py tests/apps/event/test_phase_1b_workflow.py tests/apps/ticketing/test_ticketing_service.py tests/apps/ticketing/test_ticketing_urls.py -v
```

Expected:

```text
PASS: all Phase 1B organizer workflow tests pass
```

- [ ] **Step 5: Commit**

```bash
git add src/apps/event/service.py src/apps/event/urls.py src/apps/ticketing/service.py tests/apps/event/test_app_bootstrap.py tests/apps/event/test_phase_1b_workflow.py
git commit -m "test: cover progressive draft workflow end to end"
```

## Self-Review

Spec coverage check:
- organizer-first entry flow: covered by Task 1
- draft resume and event detail: covered by Task 1 and Task 2
- progressive section updates: covered by Task 2
- event-day management: covered by Task 3
- ticketed vs open behavior in the editor: covered by Task 2, Task 4, and Task 5
- full scan lifecycle: covered by Task 3
- readiness guidance for frontend UX: covered by Task 2 and Task 5

Placeholder scan:
- no `TODO`, `TBD`, or “similar to above” placeholders remain
- each task has exact files, tests, commands, and implementation sketches

Type consistency:
- `event_access_type`, `location_mode`, `setup_status`, `EventResponse`, `EventDayResponse`, `TicketTypeResponse`, and `DayTicketAllocationResponse` match the current app naming
- the route prefix stays `/api/events` and `/api/organizers`, matching the existing FastAPI modules
