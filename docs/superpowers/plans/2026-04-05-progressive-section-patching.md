# Progressive Section Patching Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add true field-level progressive patch support for the currently editable organizer page, event basic info, and event day sections without changing the broader Phase 1B backend architecture.

**Architecture:** Keep the current `organizer` and `event` app boundaries intact and make progressive editing work by switching update endpoints to partial-patch semantics based on `exclude_unset=True`. Persist only explicitly provided fields, preserve existing values for omitted fields, and keep `setup_status` derived from actual stored event state instead of “was this route called.”

**Tech Stack:** FastAPI, Pydantic, SQLAlchemy 2.0 async, PostgreSQL, pytest, unittest.mock/AsyncMock

---

## Scope Check

This plan covers one connected subsystem: field-level progressive editing for the three sections the organizer currently edits in the Phase 1B flow.

In scope:
- organizer page progressive updates
- event basic-info progressive updates
- event-day progressive updates
- route and service semantics for omitted vs explicitly provided fields

Out of scope:
- ticketing patch/edit endpoints
- media/content sections
- publish validation
- scan ingestion logic
- public event page rendering

## Intended Editing Semantics

This plan standardizes patch semantics for all three sections:

- omitted field: do not change stored value
- explicitly provided non-null value: replace stored value
- explicitly provided `null` value:
  - allowed for nullable text/media fields
  - ignored or rejected for fields that are operationally required and not nullable in the model

This keeps progressive UX smooth while respecting the current schema constraints.

## File Structure

- `src/apps/organizer/request.py`: keep create payload, refine update payload for patch semantics.
- `src/apps/organizer/repository.py`: add owner-scoped organizer fetch helper if needed for updates.
- `src/apps/organizer/exceptions.py`: add an organizer-not-found exception for owner-scoped patch routes.
- `src/apps/organizer/service.py`: add organizer partial-update logic and fix organizer creation so all currently modeled profile fields are persisted.
- `src/apps/organizer/urls.py`: add `PATCH /api/organizers/{organizer_id}` and pass only explicitly provided fields to the service.
- `src/apps/event/request.py`: make `UpdateEventBasicInfoRequest` and `UpdateEventDayRequest` partial-patch friendly.
- `src/apps/event/service.py`: update `update_basic_info()` and `update_event_day()` to merge only provided fields and preserve existing values for omitted ones.
- `src/apps/event/urls.py`: pass `exclude_unset=True` payloads for event basic-info and event-day patch routes.
- `tests/apps/organizer/test_organizer_service.py`: add organizer partial-update tests and organizer creation field-coverage test.
- `tests/apps/organizer/test_organizer_urls.py`: add organizer patch route tests and payload forwarding assertions.
- `tests/apps/event/test_event_service.py`: add field-level patch tests for basic info and event days.
- `tests/apps/event/test_event_urls.py`: add route tests proving only provided fields are sent through.
- `tests/apps/event/test_phase_1b_workflow.py`: add progressive editing regression coverage for reopen-and-continue behavior.
- `tests/apps/event/test_app_bootstrap.py`: add route presence coverage for the organizer patch endpoint.

## Task 1: Add Organizer Page Progressive Patching

**Files:**
- Modify: `src/apps/organizer/request.py`
- Modify: `src/apps/organizer/repository.py`
- Modify: `src/apps/organizer/exceptions.py`
- Modify: `src/apps/organizer/service.py`
- Modify: `src/apps/organizer/urls.py`
- Modify: `tests/apps/organizer/test_organizer_service.py`
- Modify: `tests/apps/organizer/test_organizer_urls.py`
- Modify: `tests/apps/event/test_app_bootstrap.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/apps/organizer/test_organizer_service.py
@pytest.mark.asyncio
async def test_create_organizer_persists_profile_fields():
    repo = AsyncMock()
    repo.get_by_slug.return_value = None
    repo.add = MagicMock()
    repo.session = AsyncMock()
    service = OrganizerService(repo)

    organizer = await service.create_organizer(
        owner_user_id=uuid4(),
        name="Ahmedabad Talks",
        slug=" Ahmedabad Talks ",
        bio="Meetups",
        logo_url="https://cdn/logo.png",
        cover_image_url="https://cdn/cover.png",
        website_url="https://example.com",
        instagram_url="https://instagram.com/ahmedabadtalks",
        facebook_url=None,
        youtube_url=None,
        visibility="public",
    )

    assert organizer.logo_url == "https://cdn/logo.png"
    assert organizer.cover_image_url == "https://cdn/cover.png"
    assert organizer.website_url == "https://example.com"


@pytest.mark.asyncio
async def test_update_organizer_only_changes_provided_fields():
    owner_id = uuid4()
    organizer_id = uuid4()
    organizer = SimpleNamespace(
        id=organizer_id,
        owner_user_id=owner_id,
        name="Ahmedabad Talks",
        slug="ahmedabad-talks",
        bio="Meetups",
        logo_url="https://cdn/logo.png",
        cover_image_url=None,
        website_url=None,
        instagram_url=None,
        facebook_url=None,
        youtube_url=None,
        visibility="public",
    )
    repo = AsyncMock()
    repo.get_by_id_for_owner.return_value = organizer
    repo.get_by_slug.return_value = None
    repo.session = AsyncMock()
    service = OrganizerService(repo)

    updated = await service.update_organizer(
        owner_user_id=owner_id,
        organizer_id=organizer_id,
        bio="New bio",
    )

    assert updated.bio == "New bio"
    assert updated.name == "Ahmedabad Talks"
    assert updated.logo_url == "https://cdn/logo.png"
```

```python
# tests/apps/organizer/test_organizer_urls.py
from apps.organizer.request import UpdateOrganizerPageRequest
from apps.organizer.urls import update_organizer


@pytest.mark.asyncio
async def test_update_organizer_forwards_only_set_fields():
    owner_id = uuid4()
    organizer_id = uuid4()
    request = SimpleNamespace(state=SimpleNamespace(user=SimpleNamespace(id=owner_id)))
    body = UpdateOrganizerPageRequest(bio="New bio")
    service = AsyncMock()
    service.update_organizer.return_value = SimpleNamespace(
        id=organizer_id,
        owner_user_id=owner_id,
        name="Ahmedabad Talks",
        slug="ahmedabad-talks",
        bio="New bio",
        logo_url="https://cdn/logo.png",
        cover_image_url=None,
        website_url=None,
        instagram_url=None,
        facebook_url=None,
        youtube_url=None,
        visibility="public",
        status="active",
    )

    response = await update_organizer(
        organizer_id=organizer_id,
        request=request,
        body=body,
        service=service,
    )

    assert response.data.bio == "New bio"
    service.update_organizer.assert_awaited_once_with(
        owner_id,
        organizer_id,
        bio="New bio",
    )
```

```python
# tests/apps/event/test_app_bootstrap.py
def test_phase_one_routes_are_registered():
    app = create_app()
    paths = {route.path for route in app.routes}

    assert "/api/organizers/{organizer_id}" in paths
```

- [ ] **Step 2: Run the tests to verify they fail**

Run:

```bash
/home/manav1011/Documents/ticket-shicket-be/.venv/bin/python -m pytest tests/apps/organizer/test_organizer_service.py tests/apps/organizer/test_organizer_urls.py tests/apps/event/test_app_bootstrap.py -v
```

Expected:

```text
FAIL: OrganizerService.create_organizer got unexpected keyword argument 'logo_url'
FAIL: OrganizerService has no attribute update_organizer
FAIL: cannot import name update_organizer
FAIL: "/api/organizers/{organizer_id}" not in app routes
```

- [ ] **Step 3: Write the minimal implementation**

```python
# src/apps/organizer/service.py
from .exceptions import OrganizerNotFound, OrganizerSlugAlreadyExists


async def create_organizer(
    self,
    owner_user_id,
    name,
    slug,
    bio,
    logo_url,
    cover_image_url,
    website_url,
    instagram_url,
    facebook_url,
    youtube_url,
    visibility,
):
    normalized_slug = re.sub(r"[^a-z0-9]+", "-", slug.strip().lower()).strip("-")
    if await self.repository.get_by_slug(normalized_slug):
        raise OrganizerSlugAlreadyExists

    organizer = OrganizerPageModel(
        owner_user_id=owner_user_id,
        name=name.strip(),
        slug=normalized_slug,
        bio=bio,
        logo_url=logo_url,
        cover_image_url=cover_image_url,
        website_url=website_url,
        instagram_url=instagram_url,
        facebook_url=facebook_url,
        youtube_url=youtube_url,
        visibility=visibility,
        status="active",
    )
    self.repository.add(organizer)
    await self.repository.session.flush()
    await self.repository.session.refresh(organizer)
    return organizer


async def update_organizer(self, owner_user_id, organizer_id, **payload):
    organizer = await self.repository.get_by_id_for_owner(organizer_id, owner_user_id)
    if not organizer:
        raise OrganizerNotFound

    if "slug" in payload and payload["slug"] is not None:
        normalized_slug = re.sub(r"[^a-z0-9]+", "-", payload["slug"].strip().lower()).strip("-")
        existing = await self.repository.get_by_slug(normalized_slug)
        if existing and existing.id != organizer_id:
            raise OrganizerSlugAlreadyExists
        payload["slug"] = normalized_slug

    for field, value in payload.items():
        setattr(organizer, field, value)

    await self.repository.session.flush()
    return organizer
```

```python
# src/apps/organizer/exceptions.py
from exceptions import NotFoundError


class OrganizerNotFound(NotFoundError):
    message = "Organizer page not found."
```

```python
# src/apps/organizer/urls.py
from .request import CreateOrganizerPageRequest, UpdateOrganizerPageRequest


@router.patch("/{organizer_id}")
async def update_organizer(
    organizer_id: UUID,
    request: Request,
    body: Annotated[UpdateOrganizerPageRequest, Body()],
    service: Annotated[OrganizerService, Depends(get_organizer_service)],
) -> BaseResponse[OrganizerPageResponse]:
    organizer = await service.update_organizer(
        request.state.user.id,
        organizer_id,
        **body.model_dump(exclude_unset=True),
    )
    return BaseResponse(data=OrganizerPageResponse.model_validate(organizer))
```

- [ ] **Step 4: Run the tests to verify they pass**

Run:

```bash
/home/manav1011/Documents/ticket-shicket-be/.venv/bin/python -m pytest tests/apps/organizer/test_organizer_service.py tests/apps/organizer/test_organizer_urls.py tests/apps/event/test_app_bootstrap.py -v
```

Expected:

```text
PASS: organizer creation stores profile fields
PASS: organizer patch route forwards only explicitly provided fields
PASS: organizer patch route is registered
```

- [ ] **Step 5: Commit**

```bash
git add src/apps/organizer/request.py src/apps/organizer/repository.py src/apps/organizer/exceptions.py src/apps/organizer/service.py src/apps/organizer/urls.py tests/apps/organizer/test_organizer_service.py tests/apps/organizer/test_organizer_urls.py tests/apps/event/test_app_bootstrap.py
git commit -m "feat: add progressive organizer page patching"
```

## Task 2: Add Field-Level Progressive Patching for Event Basic Info

**Files:**
- Modify: `src/apps/event/request.py`
- Modify: `src/apps/event/service.py`
- Modify: `src/apps/event/urls.py`
- Modify: `tests/apps/event/test_event_service.py`
- Modify: `tests/apps/event/test_event_urls.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/apps/event/test_event_service.py
@pytest.mark.asyncio
async def test_update_basic_info_preserves_omitted_fields():
    owner_id = uuid4()
    event_id = uuid4()
    organizer_repo = AsyncMock()
    event_repo = AsyncMock()
    event_repo.session = AsyncMock()
    event = SimpleNamespace(
        id=event_id,
        title="Existing title",
        description="Existing description",
        event_type="meetup",
        event_access_type="ticketed",
        location_mode="venue",
        timezone="Asia/Kolkata",
        setup_status={},
    )
    event_repo.get_by_id_for_owner.return_value = event
    event_repo.count_event_days.return_value = 0
    event_repo.count_ticket_types.return_value = 0
    event_repo.count_ticket_allocations.return_value = 0
    service = EventService(event_repo, organizer_repo)

    updated = await service.update_basic_info(owner_id, event_id, title="Updated title")

    assert updated.title == "Updated title"
    assert updated.description == "Existing description"
    assert updated.event_access_type == "ticketed"
    assert updated.location_mode == "venue"
```

```python
# tests/apps/event/test_event_urls.py
@pytest.mark.asyncio
async def test_update_basic_info_forwards_only_set_fields():
    owner_id = uuid4()
    event_id = uuid4()
    request = SimpleNamespace(state=SimpleNamespace(user=SimpleNamespace(id=owner_id)))
    body = UpdateEventBasicInfoRequest(title="Updated title")
    service = AsyncMock()
    service.update_basic_info.return_value = SimpleNamespace(
        id=event_id,
        organizer_page_id=uuid4(),
        created_by_user_id=owner_id,
        title="Updated title",
        slug=None,
        description="Existing description",
        event_type="meetup",
        status="draft",
        event_access_type="ticketed",
        setup_status={"basic_info": True, "schedule": False, "tickets": False},
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
        event_id=event_id,
        request=request,
        body=body,
        service=service,
    )

    assert response.data.title == "Updated title"
    service.update_basic_info.assert_awaited_once_with(
        owner_id,
        event_id,
        title="Updated title",
    )
```

- [ ] **Step 2: Run the tests to verify they fail**

Run:

```bash
/home/manav1011/Documents/ticket-shicket-be/.venv/bin/python -m pytest tests/apps/event/test_event_service.py tests/apps/event/test_event_urls.py -v
```

Expected:

```text
FAIL: validation error because UpdateEventBasicInfoRequest still requires full section fields
FAIL: route forwards None values for omitted fields
```

- [ ] **Step 3: Write the minimal implementation**

```python
# src/apps/event/request.py
class UpdateEventBasicInfoRequest(CamelCaseModel):
    title: str | None = None
    description: str | None = None
    event_type: str | None = None
    event_access_type: str | None = None
    location_mode: str | None = None
    timezone: str | None = None
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
        request.state.user.id,
        event_id,
        **body.model_dump(exclude_unset=True),
    )
    return BaseResponse(data=EventResponse.model_validate(event))
```

```python
# src/apps/event/service.py
async def update_basic_info(self, owner_user_id, event_id, **payload):
    event = await self.repository.get_by_id_for_owner(event_id, owner_user_id)
    if not event:
        raise EventNotFound

    for field, value in payload.items():
        setattr(event, field, value)

    await self._refresh_setup_status(event)
    return event
```

- [ ] **Step 4: Run the tests to verify they pass**

Run:

```bash
/home/manav1011/Documents/ticket-shicket-be/.venv/bin/python -m pytest tests/apps/event/test_event_service.py tests/apps/event/test_event_urls.py -v
```

Expected:

```text
PASS: basic-info patch route accepts partial payloads
PASS: omitted fields keep their stored values
```

- [ ] **Step 5: Commit**

```bash
git add src/apps/event/request.py src/apps/event/service.py src/apps/event/urls.py tests/apps/event/test_event_service.py tests/apps/event/test_event_urls.py
git commit -m "feat: add field-level progressive patching for event basic info"
```

## Task 3: Add Field-Level Progressive Patching for Event Days

**Files:**
- Modify: `src/apps/event/request.py`
- Modify: `src/apps/event/service.py`
- Modify: `src/apps/event/urls.py`
- Modify: `tests/apps/event/test_event_service.py`
- Modify: `tests/apps/event/test_event_urls.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/apps/event/test_event_service.py
@pytest.mark.asyncio
async def test_update_event_day_preserves_omitted_fields():
    owner_id = uuid4()
    day_id = uuid4()
    organizer_repo = AsyncMock()
    event_repo = AsyncMock()
    event_repo.session = AsyncMock()
    day = SimpleNamespace(
        id=day_id,
        event_id=uuid4(),
        day_index=1,
        date=datetime(2026, 4, 15).date(),
        start_time=datetime(2026, 4, 15, 10, 0, 0),
        end_time=datetime(2026, 4, 15, 12, 0, 0),
        scan_status="not_started",
        scan_started_at=None,
        scan_paused_at=None,
        scan_ended_at=None,
        next_ticket_index=1,
    )
    event_repo.get_event_day_for_owner.return_value = day
    service = EventService(event_repo, organizer_repo)

    updated = await service.update_event_day(
        owner_id,
        day_id,
        start_time=datetime(2026, 4, 15, 11, 0, 0),
    )

    assert updated.start_time == datetime(2026, 4, 15, 11, 0, 0)
    assert updated.end_time == datetime(2026, 4, 15, 12, 0, 0)
    assert updated.day_index == 1
```

```python
# tests/apps/event/test_event_urls.py
@pytest.mark.asyncio
async def test_update_event_day_forwards_only_set_fields():
    owner_id = uuid4()
    event_day_id = uuid4()
    request = SimpleNamespace(state=SimpleNamespace(user=SimpleNamespace(id=owner_id)))
    body = UpdateEventDayRequest(start_time="2026-04-16T18:00:00")
    service = AsyncMock()
    service.update_event_day.return_value = SimpleNamespace(
        id=event_day_id,
        event_id=uuid4(),
        day_index=1,
        date="2026-04-16",
        start_time="2026-04-16T18:00:00",
        end_time="2026-04-16T20:00:00",
        scan_status="not_started",
        scan_started_at=None,
        scan_paused_at=None,
        scan_ended_at=None,
        next_ticket_index=1,
    )

    response = await update_event_day(
        event_day_id=event_day_id,
        request=request,
        body=body,
        service=service,
    )

    assert response.data.start_time == "2026-04-16T18:00:00"
    service.update_event_day.assert_awaited_once_with(
        owner_id,
        event_day_id,
        start_time="2026-04-16T18:00:00",
    )
```

- [ ] **Step 2: Run the tests to verify they fail**

Run:

```bash
/home/manav1011/Documents/ticket-shicket-be/.venv/bin/python -m pytest tests/apps/event/test_event_service.py tests/apps/event/test_event_urls.py -v
```

Expected:

```text
FAIL: validation error because UpdateEventDayRequest still requires full day payload
FAIL: route forwards None values for omitted day fields
```

- [ ] **Step 3: Write the minimal implementation**

```python
# src/apps/event/request.py
class UpdateEventDayRequest(CamelCaseModel):
    day_index: int | None = None
    date: date | None = None
    start_time: datetime | None = None
    end_time: datetime | None = None
```

```python
# src/apps/event/urls.py
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
        **body.model_dump(exclude_unset=True),
    )
    return BaseResponse(data=EventDayResponse.model_validate(day))
```

```python
# src/apps/event/service.py
async def update_event_day(self, owner_user_id, event_day_id, **payload):
    day = await self.repository.get_event_day_for_owner(event_day_id, owner_user_id)
    if not day:
        raise EventNotFound
    for field, value in payload.items():
        setattr(day, field, value)
    await self.repository.session.flush()
    return day
```

- [ ] **Step 4: Run the tests to verify they pass**

Run:

```bash
/home/manav1011/Documents/ticket-shicket-be/.venv/bin/python -m pytest tests/apps/event/test_event_service.py tests/apps/event/test_event_urls.py -v
```

Expected:

```text
PASS: event-day patch route accepts partial payloads
PASS: omitted day fields keep their stored values
```

- [ ] **Step 5: Commit**

```bash
git add src/apps/event/request.py src/apps/event/service.py src/apps/event/urls.py tests/apps/event/test_event_service.py tests/apps/event/test_event_urls.py
git commit -m "feat: add field-level progressive patching for event days"
```

## Task 4: Add Workflow Regression Coverage for Progressive Reopen-and-Continue Editing

**Files:**
- Modify: `tests/apps/event/test_phase_1b_workflow.py`
- Modify: `tests/apps/event/test_app_bootstrap.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/apps/event/test_phase_1b_workflow.py
@pytest.mark.asyncio
async def test_progressive_basic_info_patch_can_update_only_title_then_only_timezone():
    owner_id = uuid4()
    event_id = uuid4()
    repo = AsyncMock()
    organizer_repo = AsyncMock()
    repo.session = AsyncMock()
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

    await service.update_basic_info(owner_id, event_id, title="Partial title")
    await service.update_basic_info(owner_id, event_id, timezone="Asia/Kolkata")

    assert event.title == "Partial title"
    assert event.timezone == "Asia/Kolkata"


@pytest.mark.asyncio
async def test_progressive_event_day_patch_can_update_only_start_time():
    owner_id = uuid4()
    day_id = uuid4()
    repo = AsyncMock()
    organizer_repo = AsyncMock()
    repo.session = AsyncMock()
    day = SimpleNamespace(
        id=day_id,
        event_id=uuid4(),
        day_index=1,
        date=datetime(2026, 4, 16).date(),
        start_time=None,
        end_time=datetime(2026, 4, 16, 20, 0, 0),
        scan_status="not_started",
        scan_started_at=None,
        scan_paused_at=None,
        scan_ended_at=None,
        next_ticket_index=1,
    )
    repo.get_event_day_for_owner.return_value = day
    service = EventService(repo, organizer_repo)

    await service.update_event_day(owner_id, day_id, start_time=datetime(2026, 4, 16, 18, 0, 0))

    assert day.start_time == datetime(2026, 4, 16, 18, 0, 0)
    assert day.end_time == datetime(2026, 4, 16, 20, 0, 0)
```

- [ ] **Step 2: Run the tests to verify they fail**

Run:

```bash
/home/manav1011/Documents/ticket-shicket-be/.venv/bin/python -m pytest tests/apps/event/test_phase_1b_workflow.py -v
```

Expected:

```text
FAIL: validation error or overwritten stored values due to non-partial patch semantics
```

- [ ] **Step 3: Write the minimal implementation**

This task should not require any new production code if Tasks 1-3 were implemented correctly. Its purpose is to prove that the earlier patch semantics support reopen-and-continue editing across multiple calls.

- [ ] **Step 4: Run the focused workflow regression suite**

Run:

```bash
/home/manav1011/Documents/ticket-shicket-be/.venv/bin/python -m pytest tests/apps/organizer/test_organizer_service.py tests/apps/organizer/test_organizer_urls.py tests/apps/event/test_event_service.py tests/apps/event/test_event_urls.py tests/apps/event/test_app_bootstrap.py tests/apps/event/test_phase_1b_workflow.py -v
```

Expected:

```text
PASS: organizer page, basic info, and event day progressive patch flows work end to end
```

- [ ] **Step 5: Commit**

```bash
git add tests/apps/event/test_phase_1b_workflow.py tests/apps/event/test_app_bootstrap.py
git commit -m "test: cover progressive patching for current editable sections"
```

## Self-Review

Spec coverage:
- organizer page progressive editing: covered by Task 1
- basic info field-level progressive editing: covered by Task 2
- event-day field-level progressive editing: covered by Task 3
- reopen-and-continue regression coverage: covered by Task 4

Placeholder scan:
- no `TODO`, `TBD`, `implement later`, or “similar to Task N” markers remain
- every task includes exact file paths, tests, commands, and code snippets

Type consistency:
- `UpdateOrganizerPageRequest`, `UpdateEventBasicInfoRequest`, and `UpdateEventDayRequest` are used consistently across request, route, and test steps
- patch routes consistently use `body.model_dump(exclude_unset=True)` so omitted fields are preserved
