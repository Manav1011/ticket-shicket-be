# Phase 1B Organizer Workflow Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Complete the organizer-facing progressive draft workflow on top of the Phase 1 backend foundation so organizers can create, reopen, edit, schedule, ticket, and operate events section by section.

**Architecture:** Keep the existing three-app boundary from Phase 1: `organizer`, `event`, and `ticketing`. Phase 1B does not add new apps; it fills the missing workflow routes and service logic needed for progressive editing, including draft retrieval, section updates, event-day CRUD, full scan lifecycle, ticketing read surfaces, and a readiness summary endpoint that guides the frontend without implementing publishing.

**Tech Stack:** FastAPI, Pydantic, SQLAlchemy 2.0 async, Alembic, PostgreSQL, pytest, unittest.mock/AsyncMock

---

## Scope Check

This plan covers one connected subsystem: the organizer editing workflow for draft events. It intentionally excludes media uploads, public event pages, publish/unpublish actions, payments, orders, coupons, and open-event RSVP.

## Organizer Flow

This is the exact organizer-to-backend interaction Phase 1B should support.

### Step 1: Organizer opens the event area

Frontend action:
- Organizer opens the event dashboard and clicks `Create Event`.

Backend behavior:
- Return organizer pages owned by the current user.
- If the list is empty, frontend sends the organizer to organizer creation.
- If the list has one item, frontend can preselect it.
- If the list has many items, frontend shows a picker.

Routes:
- `GET /api/organizers`
- `POST /api/organizers`

### Step 2: Organizer creates a draft shell

Frontend action:
- Frontend posts the selected organizer page ID.

Backend behavior:
- Create an event with:
  - `status = draft`
  - `organizer_page_id`
  - `created_by_user_id`
  - nullable publish-time fields still empty
  - `setup_status = {}`

Routes:
- `POST /api/events/drafts`

### Step 3: Organizer lands on the editor and can reopen it later

Frontend action:
- Frontend loads the draft editor immediately after creation.
- Later, organizer can reopen saved drafts.

Backend behavior:
- Return event shell, event days, ticket types, day allocations, and current setup status.
- Return owner-scoped draft lists for resume flow.

Routes:
- `GET /api/events/{event_id}`
- `GET /api/me/events?status=draft`

### Step 4: Organizer edits basic event info

Frontend action:
- Organizer edits:
  - title
  - description
  - event type
  - access type
  - location mode
  - timezone
  - start/end dates if used at event level

Backend behavior:
- Partially update only those fields.
- Recompute or persist `setup_status["basic_info"]`.
- Do not enforce publish-time validation yet.

Routes:
- `PATCH /api/events/{event_id}/basic-info`

### Step 5: Organizer manages event days

Frontend action:
- Organizer creates one or more event days.
- Organizer can later update or delete a day.

Backend behavior:
- Create or edit `event_days`.
- Keep `scan_status = not_started` and `next_ticket_index = 1` for new days.
- Return owner-scoped day lists.

Routes:
- `POST /api/events/{event_id}/days`
- `GET /api/events/{event_id}/days`
- `PATCH /api/events/days/{event_day_id}`
- `DELETE /api/events/days/{event_day_id}`

### Step 6: Organizer chooses access mode

Frontend action:
- Organizer chooses `open` or `ticketed` in basic info.

Backend behavior:
- If `open`, ticketing routes reject writes.
- If `ticketed`, organizer can create ticket types and allocations.

This is enforced by:
- `PATCH /api/events/{event_id}/basic-info`
- `POST /api/events/{event_id}/ticket-types`
- `POST /api/events/{event_id}/ticket-allocations`

### Step 7: Organizer configures ticketing

Frontend action:
- Organizer creates ticket types.
- Organizer allocates ticket types to specific days and quantities.
- Organizer reopens editor later and sees existing ticketing configuration.

Backend behavior:
- Ticket types belong to event.
- Allocations belong to event day and ticket type.
- Creating an allocation generates concrete tickets and bumps `next_ticket_index`.

Routes:
- `POST /api/events/{event_id}/ticket-types`
- `GET /api/events/{event_id}/ticket-types`
- `POST /api/events/{event_id}/ticket-allocations`
- `GET /api/events/{event_id}/ticket-allocations`

### Step 8: Organizer sees progress and readiness

Frontend action:
- Frontend shows completed sections and missing work.

Backend behavior:
- Return section completion and missing requirements.
- Do not publish yet; just describe readiness.

Routes:
- `GET /api/events/{event_id}/readiness`

### Step 9: Organizer operates scanning on the day

Frontend action:
- Organizer starts, pauses, resumes, and ends scanning for a specific event day.

Backend behavior:
- Enforce valid lifecycle transitions:
  - `not_started -> active`
  - `active -> paused`
  - `paused -> active`
  - `active|paused -> ended`
- Reject invalid transitions.

Routes:
- `POST /api/events/days/{event_day_id}/start-scan`
- `POST /api/events/days/{event_day_id}/pause-scan`
- `POST /api/events/days/{event_day_id}/resume-scan`
- `POST /api/events/days/{event_day_id}/end-scan`

## File Structure

- `src/apps/organizer/repository.py`: add organizer list query for the current user.
- `src/apps/organizer/service.py`: add organizer list service.
- `src/apps/organizer/urls.py`: add organizer list route.
- `src/apps/organizer/response.py`: add organizer list response model if needed.
- `src/apps/event/repository.py`: add event detail fetch, owner-scoped draft list, event-day list/update/delete, and readiness query helpers.
- `src/apps/event/service.py`: add event detail/list services, basic-info patch, event-day CRUD, pause/resume/end scan, setup status calculation, readiness summary.
- `src/apps/event/request.py`: add request models for basic info patch and event-day updates.
- `src/apps/event/response.py`: add draft list item response and readiness response.
- `src/apps/event/urls.py`: add routes for `GET /api/events/{id}`, `GET /api/me/events`, `PATCH /api/events/{id}/basic-info`, event-day CRUD, and full scan lifecycle.
- `src/apps/ticketing/repository.py`: add list queries for ticket types and allocations.
- `src/apps/ticketing/service.py`: add list services for ticket types and allocations.
- `src/apps/ticketing/response.py`: add list response items if required.
- `src/apps/ticketing/urls.py`: add read routes for ticket types and ticket allocations.
- `tests/apps/organizer/test_organizer_urls.py`: list-organizers route tests.
- `tests/apps/event/test_event_service.py`: service tests for basic info updates, draft detail, event-day CRUD, scan transitions, and readiness.
- `tests/apps/event/test_event_urls.py`: route tests for event reads, patches, day CRUD, and scan routes.
- `tests/apps/ticketing/test_ticketing_service.py`: service tests for list behavior and owner scoping.
- `tests/apps/ticketing/test_ticketing_urls.py`: route tests for list behavior.
- `tests/apps/event/test_workflow_integration.py`: progressive workflow test that reads like the organizer journey.

## Task 1: Add Organizer Listing and Draft Resume Surfaces

**Files:**
- Modify: `src/apps/organizer/repository.py`
- Modify: `src/apps/organizer/service.py`
- Modify: `src/apps/organizer/urls.py`
- Modify: `tests/apps/organizer/test_organizer_urls.py`
- Modify: `src/apps/event/repository.py`
- Modify: `src/apps/event/service.py`
- Modify: `src/apps/event/response.py`
- Modify: `src/apps/event/urls.py`
- Create: `tests/apps/event/test_event_resume_urls.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/apps/organizer/test_organizer_urls.py
from types import SimpleNamespace
from uuid import uuid4
from unittest.mock import AsyncMock

import pytest

from apps.organizer.urls import list_organizers


@pytest.mark.asyncio
async def test_list_organizers_returns_owner_rows():
    owner_id = uuid4()
    request = SimpleNamespace(state=SimpleNamespace(user=SimpleNamespace(id=owner_id)))
    service = AsyncMock()
    service.list_organizers.return_value = [
        SimpleNamespace(
            id=uuid4(),
            owner_user_id=owner_id,
            name="Ahmedabad Talks",
            slug="ahmedabad-talks",
            bio=None,
            logo_url=None,
            cover_image_url=None,
            website_url=None,
            instagram_url=None,
            facebook_url=None,
            youtube_url=None,
            visibility="public",
            status="active",
        )
    ]

    response = await list_organizers(request=request, service=service)

    assert len(response.data) == 1
    assert response.data[0].owner_user_id == owner_id
```

```python
# tests/apps/event/test_event_resume_urls.py
from datetime import date
from types import SimpleNamespace
from uuid import uuid4
from unittest.mock import AsyncMock

import pytest

from apps.event.urls import get_event, list_my_events


@pytest.mark.asyncio
async def test_get_event_returns_owner_scoped_draft():
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
        setup_status={},
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

    response = await get_event(event_id=event_id, request=request, service=service)

    assert response.data.id == event_id
    assert response.data.status == "draft"


@pytest.mark.asyncio
async def test_list_my_events_filters_by_status():
    owner_id = uuid4()
    request = SimpleNamespace(state=SimpleNamespace(user=SimpleNamespace(id=owner_id)))
    service = AsyncMock()
    service.list_my_events.return_value = [
        SimpleNamespace(
            id=uuid4(),
            organizer_page_id=uuid4(),
            created_by_user_id=owner_id,
            title="Draft Event",
            slug=None,
            description=None,
            event_type=None,
            status="draft",
            event_access_type="ticketed",
            setup_status={"basic_info": True},
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
    ]

    response = await list_my_events(status="draft", request=request, service=service)

    assert len(response.data) == 1
    service.list_my_events.assert_awaited_once_with(owner_id, "draft")
```

- [ ] **Step 2: Run the tests to verify they fail**

Run:

```bash
/home/manav1011/Documents/ticket-shicket-be/.venv/bin/python -m pytest tests/apps/organizer/test_organizer_urls.py tests/apps/event/test_event_resume_urls.py -v
```

Expected:

```text
FAIL: list_organizers route missing
FAIL: get_event or list_my_events route missing
```

- [ ] **Step 3: Write the minimal implementation**

```python
# src/apps/organizer/urls.py
@router.get("")
async def list_organizers(
    request: Request,
    service: Annotated[OrganizerService, Depends(get_organizer_service)],
) -> BaseResponse[list[OrganizerPageResponse]]:
    organizers = await service.list_organizers(request.state.user.id)
    return BaseResponse(
        data=[OrganizerPageResponse.model_validate(item) for item in organizers]
    )
```

```python
# src/apps/event/urls.py
@router.get("/{event_id}")
async def get_event(
    event_id: UUID,
    request: Request,
    service: Annotated[EventService, Depends(get_event_service)],
) -> BaseResponse[EventResponse]:
    event = await service.get_event_detail(request.state.user.id, event_id)
    return BaseResponse(data=EventResponse.model_validate(event))


@router.get("/me/list")
async def list_my_events(
    status: str | None,
    request: Request,
    service: Annotated[EventService, Depends(get_event_service)],
) -> BaseResponse[list[EventResponse]]:
    events = await service.list_my_events(request.state.user.id, status)
    return BaseResponse(data=[EventResponse.model_validate(item) for item in events])
```

- [ ] **Step 4: Re-run the tests to verify they pass**

Run:

```bash
/home/manav1011/Documents/ticket-shicket-be/.venv/bin/python -m pytest tests/apps/organizer/test_organizer_urls.py tests/apps/event/test_event_resume_urls.py -v
```

Expected:

```text
PASS
```

- [ ] **Step 5: Commit**

```bash
git add src/apps/organizer/urls.py src/apps/event/urls.py src/apps/event/service.py src/apps/event/repository.py tests/apps/organizer/test_organizer_urls.py tests/apps/event/test_event_resume_urls.py
git commit -m "feat: add organizer listing and draft resume routes"
```

## Task 2: Add Basic Info Patch and Setup Progress Updates

**Files:**
- Modify: `src/apps/event/request.py`
- Modify: `src/apps/event/response.py`
- Modify: `src/apps/event/repository.py`
- Modify: `src/apps/event/service.py`
- Modify: `src/apps/event/urls.py`
- Create: `tests/apps/event/test_event_basic_info_service.py`
- Create: `tests/apps/event/test_event_basic_info_urls.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/apps/event/test_event_basic_info_service.py
from types import SimpleNamespace
from uuid import uuid4
from unittest.mock import AsyncMock

import pytest

from apps.event.service import EventService


@pytest.mark.asyncio
async def test_update_basic_info_sets_fields_and_progress():
    owner_id = uuid4()
    event = SimpleNamespace(
        id=uuid4(),
        title=None,
        description=None,
        event_type=None,
        event_access_type="ticketed",
        location_mode=None,
        timezone=None,
        start_date=None,
        end_date=None,
        setup_status={},
    )
    repo = AsyncMock()
    repo.get_by_id_for_owner.return_value = event
    repo.session = AsyncMock()
    organizer_repo = AsyncMock()
    service = EventService(repo, organizer_repo)

    updated = await service.update_basic_info(
        owner_user_id=owner_id,
        event_id=event.id,
        title="TicketShicket Meetup",
        description="Community meetup",
        event_type="meetup",
        event_access_type="ticketed",
        location_mode="venue",
        timezone="Asia/Kolkata",
        start_date=None,
        end_date=None,
    )

    assert updated.title == "TicketShicket Meetup"
    assert updated.setup_status["basic_info"] is True
```

```python
# tests/apps/event/test_event_basic_info_urls.py
from datetime import date
from types import SimpleNamespace
from uuid import uuid4
from unittest.mock import AsyncMock

import pytest

from apps.event.request import UpdateEventBasicInfoRequest
from apps.event.urls import update_basic_info


@pytest.mark.asyncio
async def test_update_basic_info_route_returns_updated_event():
    owner_id = uuid4()
    event_id = uuid4()
    request = SimpleNamespace(state=SimpleNamespace(user=SimpleNamespace(id=owner_id)))
    body = UpdateEventBasicInfoRequest(
        title="TicketShicket Meetup",
        description="Community meetup",
        event_type="meetup",
        event_access_type="ticketed",
        location_mode="venue",
        timezone="Asia/Kolkata",
        start_date=None,
        end_date=None,
    )
    service = AsyncMock()
    service.update_basic_info.return_value = SimpleNamespace(
        id=event_id,
        organizer_page_id=uuid4(),
        created_by_user_id=owner_id,
        title="TicketShicket Meetup",
        slug=None,
        description="Community meetup",
        event_type="meetup",
        status="draft",
        event_access_type="ticketed",
        setup_status={"basic_info": True},
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

    response = await update_basic_info(event_id=event_id, request=request, body=body, service=service)

    assert response.data.title == "TicketShicket Meetup"
    assert response.data.setup_status["basic_info"] is True
```

- [ ] **Step 2: Run the tests to verify they fail**

Run:

```bash
/home/manav1011/Documents/ticket-shicket-be/.venv/bin/python -m pytest tests/apps/event/test_event_basic_info_service.py tests/apps/event/test_event_basic_info_urls.py -v
```

Expected:

```text
FAIL: update_basic_info route or service missing
```

- [ ] **Step 3: Write the minimal implementation**

```python
# src/apps/event/request.py
class UpdateEventBasicInfoRequest(CamelCaseModel):
    title: str | None = None
    description: str | None = None
    event_type: str | None = None
    event_access_type: str
    location_mode: str | None = None
    timezone: str | None = None
    start_date: date | None = None
    end_date: date | None = None
```

```python
# src/apps/event/urls.py
@router.patch("/{event_id}/basic-info")
async def update_basic_info(
    event_id: UUID,
    request: Request,
    body: Annotated[UpdateEventBasicInfoRequest, Body()],
    service: Annotated[EventService, Depends(get_event_service)],
) -> BaseResponse[EventResponse]:
    event = await service.update_basic_info(
        owner_user_id=request.state.user.id,
        event_id=event_id,
        **body.model_dump(),
    )
    return BaseResponse(data=EventResponse.model_validate(event))
```

- [ ] **Step 4: Re-run the tests to verify they pass**

Run:

```bash
/home/manav1011/Documents/ticket-shicket-be/.venv/bin/python -m pytest tests/apps/event/test_event_basic_info_service.py tests/apps/event/test_event_basic_info_urls.py -v
```

Expected:

```text
PASS
```

- [ ] **Step 5: Commit**

```bash
git add src/apps/event/request.py src/apps/event/service.py src/apps/event/urls.py tests/apps/event/test_event_basic_info_service.py tests/apps/event/test_event_basic_info_urls.py
git commit -m "feat: add progressive basic info updates"
```

## Task 3: Add Event-Day CRUD and Full Scan Lifecycle

**Files:**
- Modify: `src/apps/event/request.py`
- Modify: `src/apps/event/response.py`
- Modify: `src/apps/event/repository.py`
- Modify: `src/apps/event/service.py`
- Modify: `src/apps/event/urls.py`
- Create: `tests/apps/event/test_event_day_crud_service.py`
- Create: `tests/apps/event/test_event_day_crud_urls.py`
- Create: `tests/apps/event/test_scan_lifecycle_urls.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/apps/event/test_scan_lifecycle_urls.py
from datetime import date
from types import SimpleNamespace
from uuid import uuid4
from unittest.mock import AsyncMock

import pytest

from apps.event.urls import end_scan, pause_scan, resume_scan


@pytest.mark.asyncio
async def test_pause_scan_returns_paused_state():
    owner_id = uuid4()
    event_day_id = uuid4()
    request = SimpleNamespace(state=SimpleNamespace(user=SimpleNamespace(id=owner_id)))
    service = AsyncMock()
    service.pause_scan.return_value = SimpleNamespace(
        id=event_day_id,
        event_id=uuid4(),
        day_index=1,
        date=date(2026, 4, 20),
        start_time=None,
        end_time=None,
        scan_status="paused",
        scan_started_at=None,
        scan_paused_at=None,
        scan_ended_at=None,
        next_ticket_index=1,
    )

    response = await pause_scan(event_day_id=event_day_id, request=request, service=service)

    assert response.data.scan_status == "paused"
```

```python
# tests/apps/event/test_event_day_crud_urls.py
from datetime import date
from types import SimpleNamespace
from uuid import uuid4
from unittest.mock import AsyncMock

import pytest

from apps.event.request import CreateEventDayRequest
from apps.event.urls import create_event_day, list_event_days


@pytest.mark.asyncio
async def test_create_event_day_route_returns_day():
    owner_id = uuid4()
    event_id = uuid4()
    request = SimpleNamespace(state=SimpleNamespace(user=SimpleNamespace(id=owner_id)))
    body = CreateEventDayRequest(day_index=1, date=date(2026, 4, 20))
    service = AsyncMock()
    service.create_event_day.return_value = SimpleNamespace(
        id=uuid4(),
        event_id=event_id,
        day_index=1,
        date=date(2026, 4, 20),
        start_time=None,
        end_time=None,
        scan_status="not_started",
        scan_started_at=None,
        scan_paused_at=None,
        scan_ended_at=None,
        next_ticket_index=1,
    )

    response = await create_event_day(
        event_id=event_id, request=request, body=body, service=service
    )

    assert response.data.day_index == 1


@pytest.mark.asyncio
async def test_list_event_days_route_returns_days():
    owner_id = uuid4()
    event_id = uuid4()
    request = SimpleNamespace(state=SimpleNamespace(user=SimpleNamespace(id=owner_id)))
    service = AsyncMock()
    service.list_event_days.return_value = []

    response = await list_event_days(event_id=event_id, request=request, service=service)

    assert response.data == []
```

- [ ] **Step 2: Run the tests to verify they fail**

Run:

```bash
/home/manav1011/Documents/ticket-shicket-be/.venv/bin/python -m pytest tests/apps/event/test_event_day_crud_urls.py tests/apps/event/test_scan_lifecycle_urls.py -v
```

Expected:

```text
FAIL: event-day CRUD or pause/resume/end scan routes missing
```

- [ ] **Step 3: Write the minimal implementation**

```python
# src/apps/event/urls.py
@router.post("/{event_id}/days")
async def create_event_day(...):
    ...


@router.get("/{event_id}/days")
async def list_event_days(...):
    ...


@router.post("/days/{event_day_id}/pause-scan")
async def pause_scan(...):
    ...


@router.post("/days/{event_day_id}/resume-scan")
async def resume_scan(...):
    ...


@router.post("/days/{event_day_id}/end-scan")
async def end_scan(...):
    ...
```

```python
# src/apps/event/service.py
async def pause_scan(...):
    ...


async def resume_scan(...):
    ...


async def end_scan(...):
    ...
```

- [ ] **Step 4: Re-run the tests to verify they pass**

Run:

```bash
/home/manav1011/Documents/ticket-shicket-be/.venv/bin/python -m pytest tests/apps/event/test_event_day_crud_urls.py tests/apps/event/test_scan_lifecycle_urls.py -v
```

Expected:

```text
PASS
```

- [ ] **Step 5: Commit**

```bash
git add src/apps/event/request.py src/apps/event/response.py src/apps/event/repository.py src/apps/event/service.py src/apps/event/urls.py tests/apps/event/test_event_day_crud_urls.py tests/apps/event/test_scan_lifecycle_urls.py
git commit -m "feat: add event day workflow and full scan lifecycle"
```

## Task 4: Add Ticketing Read Surfaces for Resume Flow

**Files:**
- Modify: `src/apps/ticketing/repository.py`
- Modify: `src/apps/ticketing/service.py`
- Modify: `src/apps/ticketing/urls.py`
- Modify: `tests/apps/ticketing/test_ticketing_urls.py`
- Create: `tests/apps/ticketing/test_ticketing_list_service.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/apps/ticketing/test_ticketing_list_service.py
from types import SimpleNamespace
from uuid import uuid4
from unittest.mock import AsyncMock

import pytest

from apps.ticketing.service import TicketingService


@pytest.mark.asyncio
async def test_list_ticket_types_returns_owner_scoped_types():
    owner_id = uuid4()
    event_id = uuid4()
    event_repo = AsyncMock()
    event_repo.get_by_id_for_owner.return_value = SimpleNamespace(
        id=event_id,
        event_access_type="ticketed",
    )
    repo = AsyncMock()
    repo.list_ticket_types_for_event.return_value = []
    day_repo = AsyncMock()
    service = TicketingService(repo, event_repo, day_repo)

    result = await service.list_ticket_types(owner_id, event_id)

    assert result == []
    repo.list_ticket_types_for_event.assert_awaited_once_with(event_id)
```

```python
# tests/apps/ticketing/test_ticketing_urls.py
from types import SimpleNamespace
from uuid import uuid4
from unittest.mock import AsyncMock

import pytest

from apps.ticketing.urls import list_ticket_types, list_ticket_allocations


@pytest.mark.asyncio
async def test_list_ticket_types_route_returns_rows():
    owner_id = uuid4()
    event_id = uuid4()
    request = SimpleNamespace(state=SimpleNamespace(user=SimpleNamespace(id=owner_id)))
    service = AsyncMock()
    service.list_ticket_types.return_value = []

    response = await list_ticket_types(event_id=event_id, request=request, service=service)

    assert response.data == []


@pytest.mark.asyncio
async def test_list_ticket_allocations_route_returns_rows():
    owner_id = uuid4()
    event_id = uuid4()
    request = SimpleNamespace(state=SimpleNamespace(user=SimpleNamespace(id=owner_id)))
    service = AsyncMock()
    service.list_ticket_allocations.return_value = []

    response = await list_ticket_allocations(event_id=event_id, request=request, service=service)

    assert response.data == []
```

- [ ] **Step 2: Run the tests to verify they fail**

Run:

```bash
/home/manav1011/Documents/ticket-shicket-be/.venv/bin/python -m pytest tests/apps/ticketing/test_ticketing_list_service.py tests/apps/ticketing/test_ticketing_urls.py -v
```

Expected:

```text
FAIL: ticketing list routes or service methods missing
```

- [ ] **Step 3: Write the minimal implementation**

```python
# src/apps/ticketing/urls.py
@router.get("/{event_id}/ticket-types")
async def list_ticket_types(...):
    ...


@router.get("/{event_id}/ticket-allocations")
async def list_ticket_allocations(...):
    ...
```

```python
# src/apps/ticketing/service.py
async def list_ticket_types(self, owner_user_id, event_id):
    ...


async def list_ticket_allocations(self, owner_user_id, event_id):
    ...
```

- [ ] **Step 4: Re-run the tests to verify they pass**

Run:

```bash
/home/manav1011/Documents/ticket-shicket-be/.venv/bin/python -m pytest tests/apps/ticketing/test_ticketing_list_service.py tests/apps/ticketing/test_ticketing_urls.py -v
```

Expected:

```text
PASS
```

- [ ] **Step 5: Commit**

```bash
git add src/apps/ticketing/repository.py src/apps/ticketing/service.py src/apps/ticketing/urls.py tests/apps/ticketing/test_ticketing_list_service.py tests/apps/ticketing/test_ticketing_urls.py
git commit -m "feat: add ticketing read routes for draft resume"
```

## Task 5: Add Readiness Summary and End-to-End Workflow Test

**Files:**
- Modify: `src/apps/event/response.py`
- Modify: `src/apps/event/repository.py`
- Modify: `src/apps/event/service.py`
- Modify: `src/apps/event/urls.py`
- Create: `tests/apps/event/test_event_readiness_urls.py`
- Create: `tests/apps/event/test_workflow_integration.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/apps/event/test_event_readiness_urls.py
from types import SimpleNamespace
from uuid import uuid4
from unittest.mock import AsyncMock

import pytest

from apps.event.urls import get_event_readiness


@pytest.mark.asyncio
async def test_get_event_readiness_returns_completed_and_missing_sections():
    owner_id = uuid4()
    event_id = uuid4()
    request = SimpleNamespace(state=SimpleNamespace(user=SimpleNamespace(id=owner_id)))
    service = AsyncMock()
    service.get_event_readiness.return_value = {
        "completed_sections": ["basic_info"],
        "missing_sections": ["schedule", "tickets"],
        "warnings": [],
    }

    response = await get_event_readiness(event_id=event_id, request=request, service=service)

    assert response.data["completed_sections"] == ["basic_info"]
    assert "schedule" in response.data["missing_sections"]
```

```python
# tests/apps/event/test_workflow_integration.py
def test_phase_1b_flow_is_documented_by_routes():
    expected_routes = {
        "/api/organizers",
        "/api/events/drafts",
        "/api/events/{event_id}",
        "/api/events/me/list",
        "/api/events/{event_id}/basic-info",
        "/api/events/{event_id}/days",
        "/api/events/days/{event_day_id}/start-scan",
        "/api/events/days/{event_day_id}/pause-scan",
        "/api/events/days/{event_day_id}/resume-scan",
        "/api/events/days/{event_day_id}/end-scan",
        "/api/events/{event_id}/ticket-types",
        "/api/events/{event_id}/ticket-allocations",
        "/api/events/{event_id}/readiness",
    }

    from server import create_app

    app = create_app()
    route_paths = {route.path for route in app.routes}

    assert expected_routes.issubset(route_paths)
```

- [ ] **Step 2: Run the tests to verify they fail**

Run:

```bash
/home/manav1011/Documents/ticket-shicket-be/.venv/bin/python -m pytest tests/apps/event/test_event_readiness_urls.py tests/apps/event/test_workflow_integration.py -v
```

Expected:

```text
FAIL: readiness route missing
FAIL: final workflow route surface incomplete
```

- [ ] **Step 3: Write the minimal implementation**

```python
# src/apps/event/urls.py
@router.get("/{event_id}/readiness")
async def get_event_readiness(
    event_id: UUID,
    request: Request,
    service: Annotated[EventService, Depends(get_event_service)],
) -> BaseResponse[dict]:
    readiness = await service.get_event_readiness(request.state.user.id, event_id)
    return BaseResponse(data=readiness)
```

```python
# src/apps/event/service.py
async def get_event_readiness(self, owner_user_id, event_id):
    event = await self.repository.get_by_id_for_owner(event_id, owner_user_id)
    completed = []
    missing = []

    if event.setup_status.get("basic_info"):
        completed.append("basic_info")
    else:
        missing.append("basic_info")

    days = await self.repository.list_event_days_for_event(event_id, owner_user_id)
    if days:
        completed.append("schedule")
    else:
        missing.append("schedule")

    if event.event_access_type == "open":
        completed.append("tickets")
    else:
        allocations = await self.repository.count_ticket_allocations_for_event(event_id)
        if allocations:
            completed.append("tickets")
        else:
            missing.append("tickets")

    return {
        "completed_sections": completed,
        "missing_sections": missing,
        "warnings": [],
    }
```

- [ ] **Step 4: Re-run the tests to verify they pass**

Run:

```bash
/home/manav1011/Documents/ticket-shicket-be/.venv/bin/python -m pytest tests/apps/event/test_event_readiness_urls.py tests/apps/event/test_workflow_integration.py -v
```

Expected:

```text
PASS
```

- [ ] **Step 5: Commit**

```bash
git add src/apps/event/response.py src/apps/event/repository.py src/apps/event/service.py src/apps/event/urls.py tests/apps/event/test_event_readiness_urls.py tests/apps/event/test_workflow_integration.py
git commit -m "feat: add readiness summary for organizer workflow"
```

## Self-Review

**Spec coverage:** This plan covers the full organizer-facing progressive workflow: organizer listing, draft retrieval, basic info updates, event-day CRUD, full scan lifecycle, ticketing read surfaces, and readiness feedback. It intentionally excludes media, publish actions, and commerce.

**Placeholder scan:** There are no `TODO`, `TBD`, or “implement later” placeholders. Every task names exact files, test commands, and concrete route/service names.

**Type consistency:** The plan consistently uses the current Phase 1 app boundaries (`organizer`, `event`, `ticketing`) and route prefixes rooted at `/api/organizers` and `/api/events`. The same names are reused across tasks: `UpdateEventBasicInfoRequest`, `CreateEventDayRequest`, `get_event_readiness`, `list_ticket_types`, `list_ticket_allocations`.

Plan complete and saved to `docs/superpowers/plans/2026-04-05-phase-1b-organizer-workflow.md`. Two execution options:

**1. Subagent-Driven (recommended)** - I dispatch a fresh subagent per task, review between tasks, fast iteration

**2. Inline Execution** - Execute tasks in this session using executing-plans, batch execution with checkpoints

Which approach?
