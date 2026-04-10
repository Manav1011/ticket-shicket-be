# Publish Event API with Validation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add `is_published` field to EventModel and implement `POST /api/events/{event_id}/publish` with comprehensive section-based validation and detailed error responses.

**Architecture:** Validation is split into three sections (basic_info, schedule, tickets) with location-mode-aware field requirements and ticketed vs open event rules. Publish endpoint returns structured validation response grouped by section with field-level errors and redirect hints.

**Tech Stack:** FastAPI, SQLAlchemy async, Pydantic, Alembic migrations

---

## File Structure

- **Modify:** `src/apps/event/models.py` — Add `is_published` field to EventModel
- **Modify:** `src/apps/event/repository.py` — Add method to fetch event with days, ticket_types, allocations for validation
- **Modify:** `src/apps/event/service.py` — Add publish validation methods
- **Modify:** `src/apps/event/request.py` — (none needed for this feature)
- **Create:** `src/apps/event/response.py` — Add `PublishValidationResponse`, `SectionErrorResponse`, `FieldErrorResponse`
- **Modify:** `src/apps/event/urls.py` — Add `POST /{event_id}/publish` endpoint
- **Create:** `src/migrations/versions/xxxxxxxx_add_is_published_to_events.py` — Alembic migration
- **Modify:** `tests/apps/event/test_event_urls.py` — Add publish endpoint tests
- **Modify:** `tests/apps/event/test_event_service.py` — Add publish validation tests
- **Modify:** `docs/schemas/base.md` — Document `is_published` field

---

## Task 1: Add `is_published` Field to EventModel

**Files:**
- Modify: `src/apps/event/models.py:26-28`

- [ ] **Step 1: Add field to EventModel**

```python
# After line 28 (status field), add:
is_published: Mapped[bool] = mapped_column(
    Boolean, default=False, server_default=text("false"), nullable=False
)
```

- [ ] **Step 2: Create migration**

Run: `.venv/bin/python main.py makemigrations --message "Add is_published field to events table"`

- [ ] **Step 3: Apply migration**

Run: `.venv/bin/python main.py migrate`

- [ ] **Step 4: Commit**

```bash
git add src/apps/event/models.py src/migrations/versions/xxxxxxxx_add_is_published.py
git commit -m "feat(event): add is_published field to events table"
```

---

## Task 2: Add Publish Validation Response Schema

**Files:**
- Modify: `src/apps/event/response.py:59-68` (add new classes before `EventEnvelopeResponse`)

- [ ] **Step 1: Add response schema classes**

```python
class FieldErrorResponse(CamelCaseModel):
    field: str
    message: str
    code: str  # e.g., "MISSING_REQUIRED_FIELD", "INVALID_FORMAT"


class SectionValidationResult(CamelCaseModel):
    complete: bool
    errors: list[FieldErrorResponse]


class PublishValidationResponse(CamelCaseModel):
    can_publish: bool
    event_id: UUID
    published_at: datetime | None = None
    sections: dict[str, SectionValidationResult]
    blocking_issues: list[str]
    redirect_hint: dict | None = None  # {"section": "basic_info", "fields": ["venue_name"]}
```

- [ ] **Step 2: Update imports in urls.py**

Add `PublishValidationResponse` to the import from `.response`

- [ ] **Step 3: Commit**

```bash
git add src/apps/event/response.py
git commit -m "feat(event): add publish validation response schemas"
```

---

## Task 3: Add Publish Validation Logic to Service

**Files:**
- Modify: `src/apps/event/service.py`

- [ ] **Step 1: Add validation helper methods** (add after line 66, before `get_event_detail`)

```python
def _validate_basic_info(self, event) -> list[FieldErrorResponse]:
    """Validate basic_info section based on location_mode and event_access_type."""
    errors = []

    # Required for all events
    if not getattr(event, 'title', None):
        errors.append(FieldErrorResponse(field="title", message="Title is required", code="MISSING_REQUIRED_FIELD"))
    if not getattr(event, 'event_access_type', None):
        errors.append(FieldErrorResponse(field="event_access_type", message="Event access type is required", code="MISSING_REQUIRED_FIELD"))
    if not getattr(event, 'location_mode', None):
        errors.append(FieldErrorResponse(field="location_mode", message="Location mode is required", code="MISSING_REQUIRED_FIELD"))
    if not getattr(event, 'timezone', None):
        errors.append(FieldErrorResponse(field="timezone", message="Timezone is required", code="MISSING_REQUIRED_FIELD"))

    # Location-specific validation
    lm = getattr(event, 'location_mode', None)
    if lm in ('venue', 'hybrid'):
        venue_fields = [
            ('venue_name', 'Venue name is required for venue events'),
            ('venue_address', 'Venue address is required for venue events'),
            ('venue_city', 'Venue city is required for venue events'),
            ('venue_country', 'Venue country is required for venue events'),
        ]
        for field, msg in venue_fields:
            if not getattr(event, field, None):
                errors.append(FieldErrorResponse(field=field, message=msg, code="MISSING_REQUIRED_FIELD"))

    if lm in ('online', 'hybrid'):
        if not getattr(event, 'online_event_url', None):
            errors.append(FieldErrorResponse(field="online_event_url", message="Online event URL is required for online events", code="MISSING_REQUIRED_FIELD"))

    if lm == 'recorded':
        if not getattr(event, 'recorded_event_url', None):
            errors.append(FieldErrorResponse(field="recorded_event_url", message="Recorded event URL is required for recorded events", code="MISSING_REQUIRED_FIELD"))

    return errors


def _validate_schedule(self, event, days: list) -> list[FieldErrorResponse]:
    """Validate schedule section - day count and day-level requirements."""
    errors = []

    if len(days) == 0:
        errors.append(FieldErrorResponse(field="days", message="At least 1 event day is required", code="MISSING_REQUIRED_FIELD"))
        return errors  # Can't validate day-level fields without days

    for day in days:
        if not getattr(day, 'date', None):
            errors.append(FieldErrorResponse(field=f"day_{day.day_index}.date", message=f"Day {day.day_index}: date is required", code="MISSING_REQUIRED_FIELD"))

        # start_time required for ticketed events
        if getattr(event, 'event_access_type', None) == 'ticketed':
            if not getattr(day, 'start_time', None):
                errors.append(FieldErrorResponse(field=f"day_{day.day_index}.start_time", message=f"Day {day.day_index}: start time is required for ticketed events", code="MISSING_REQUIRED_FIELD"))

    return errors


def _validate_tickets(self, event, ticket_types: list, allocations: list) -> list[FieldErrorResponse]:
    """Validate tickets section - requires ticket types and allocations for ticketed events."""
    errors = []

    if getattr(event, 'event_access_type', None) == 'open':
        return errors  # Open events don't need tickets

    if len(ticket_types) == 0:
        errors.append(FieldErrorResponse(field="ticket_types", message="At least 1 ticket type is required", code="MISSING_REQUIRED_FIELD"))

    if len(allocations) == 0:
        errors.append(FieldErrorResponse(field="allocations", message="At least 1 ticket allocation is required", code="MISSING_REQUIRED_FIELD"))
        return errors

    for alloc in allocations:
        if getattr(alloc, 'quantity', 0) <= 0:
            errors.append(FieldErrorResponse(field=f"allocation_{alloc.id}.quantity", message="Allocation quantity must be greater than 0", code="INVALID_FIELD_VALUE"))

    return errors
```

- [ ] **Step 2: Add `validate_for_publish` method** (add after `_validate_tickets`)

```python
async def validate_for_publish(self, owner_user_id, event_id):
    """Run all validations and return structured response for publish readiness."""
    event = await self.repository.get_by_id_for_owner(event_id, owner_user_id)
    if not event:
        raise EventNotFound

    days = await self.repository.list_event_days(event_id)
    ticket_types = await self.repository.list_ticket_types(event_id)
    allocations = await self.repository.list_allocations(event_id)

    basic_info_errors = self._validate_basic_info(event)
    schedule_errors = self._validate_schedule(event, days)
    ticket_errors = self._validate_tickets(event, ticket_types, allocations)

    basic_info_complete = len(basic_info_errors) == 0
    schedule_complete = len(schedule_errors) == 0
    tickets_complete = len(ticket_errors) == 0

    all_errors = basic_info_errors + schedule_errors + ticket_errors

    # Build blocking issues
    blocking_issues = []
    if not basic_info_complete:
        blocking_issues.append("Complete basic_info section")
    if not schedule_complete:
        blocking_issues.append("Complete schedule section")
    if not tickets_complete:
        blocking_issues.append("Complete tickets section")

    # Determine redirect hint (first incomplete section with errors)
    redirect_hint = None
    if not basic_info_complete and basic_info_errors:
        redirect_hint = {
            "section": "basic_info",
            "fields": [e.field for e in basic_info_errors]
        }
    elif not schedule_complete and schedule_errors:
        redirect_hint = {
            "section": "schedule",
            "fields": [e.field for e in schedule_errors]
        }
    elif not tickets_complete and ticket_errors:
        redirect_hint = {
            "section": "tickets",
            "fields": [e.field for e in ticket_errors]
        }

    return {
        "can_publish": basic_info_complete and schedule_complete and tickets_complete,
        "event_id": event_id,
        "published_at": None,
        "sections": {
            "basic_info": {"complete": basic_info_complete, "errors": basic_info_errors},
            "schedule": {"complete": schedule_complete, "errors": schedule_errors},
            "tickets": {"complete": tickets_complete, "errors": ticket_errors},
        },
        "blocking_issues": blocking_issues,
        "redirect_hint": redirect_hint,
    }
```

- [ ] **Step 3: Add `publish_event` method** (add after `validate_for_publish`)

```python
async def publish_event(self, owner_user_id, event_id):
    """Publish event if all validations pass. Returns updated event."""
    validation = await self.validate_for_publish(owner_user_id, event_id)

    if not validation["can_publish"]:
        raise CannotPublishEvent(validation)

    event = await self.repository.get_by_id_for_owner(event_id, owner_user_id)
    event.status = "published"
    event.is_published = True
    event.published_at = datetime.utcnow()
    await self.repository.session.flush()
    await self.repository.session.refresh(event)
    return event
```

- [ ] **Step 4: Add `CannotPublishEvent` exception** to `src/apps/event/exceptions.py`

```python
class CannotPublishEvent(CustomException):
    status_code = 400
    detail = "Event cannot be published due to validation errors"
```

- [ ] **Step 5: Commit**

```bash
git add src/apps/event/service.py src/apps/event/exceptions.py
git commit -m "feat(event): add publish validation and publish_event methods"
```

---

## Task 4: Add Publish Endpoint

**Files:**
- Modify: `src/apps/event/urls.py`

- [ ] **Step 1: Add import for PublishValidationResponse**

From line 14, update the response import to include `PublishValidationResponse`.

- [ ] **Step 2: Add endpoint** (add after line 73, after `get_event_readiness`)

```python
@router.get("/{event_id}/publish-validations")
async def get_publish_validations(
    event_id: UUID,
    request: Request,
    service: Annotated[EventService, Depends(get_event_service)],
) -> BaseResponse[PublishValidationResponse]:
    """Check if event is ready to publish, return section-by-section validation errors."""
    validation = await service.validate_for_publish(request.state.user.id, event_id)
    return BaseResponse(data=PublishValidationResponse.model_validate(validation))


@router.post("/{event_id}/publish")
async def publish_event(
    event_id: UUID,
    request: Request,
    service: Annotated[EventService, Depends(get_event_service)],
) -> BaseResponse[EventResponse]:
    """Publish event. Returns 400 with validation errors if not ready."""
    event = await service.publish_event(request.state.user.id, event_id)
    return BaseResponse(data=EventResponse.model_validate(event))
```

- [ ] **Step 3: Commit**

```bash
git add src/apps/event/urls.py
git commit -m "feat(event): add publish and publish-validations endpoints"
```

---

## Task 5: Update Repository with Missing Methods

**Files:**
- Modify: `src/apps/event/repository.py`

- [ ] **Step 1: Add `list_ticket_types` method** (add after `count_ticket_types`)

```python
async def list_ticket_types(self, event_id: UUID) -> list:
    result = await self._session.scalars(
        select(TicketTypeModel).where(TicketTypeModel.event_id == event_id)
    )
    return list(result.all())
```

Note: This requires `TicketTypeModel` to be imported. Already imported at line 8.

- [ ] **Step 2: Add `list_allocations` method** (add after `list_ticket_types`)

```python
async def list_allocations(self, event_id: UUID) -> list:
    result = await self._session.scalars(
        select(DayTicketAllocationModel)
        .join(TicketTypeModel, DayTicketAllocationModel.ticket_type_id == TicketTypeModel.id)
        .where(TicketTypeModel.event_id == event_id)
    )
    return list(result.all())
```

- [ ] **Step 3: Commit**

```bash
git add src/apps/event/repository.py
git commit -m "feat(event): add list_ticket_types and list_allocations to repository"
```

---

## Task 6: Update base.md Documentation

**Files:**
- Modify: `docs/schemas/base.md`

- [ ] **Step 1: Update Event table to include is_published**

In section 2.1 Event, add `is_published BOOLEAN NOT NULL DEFAULT false` after `published_at`.

```sql
published_at TIMESTAMP,
is_published BOOLEAN NOT NULL DEFAULT false,
created_at TIMESTAMP DEFAULT now(),
updated_at TIMESTAMP DEFAULT now()
```

- [ ] **Step 2: Add Publish Validation section (optional)**

Add a note about the publish endpoint validation behavior.

- [ ] **Step 3: Commit**

```bash
git add docs/schemas/base.md
git commit -m "docs: update base.md with is_published field"
```

---

## Task 7: Add Tests

**Files:**
- Modify: `tests/apps/event/test_event_urls.py`
- Modify: `tests/apps/event/test_event_service.py`

- [ ] **Step 1: Add publish validation tests to test_event_service.py**

```python
async def test_validate_for_publish_open_venue_complete():
    # Create open venue event with all required fields
    # Call validate_for_publish
    # Expect can_publish = True

async def test_validate_for_publish_ticketed_missing_tickets():
    # Create ticketed event without ticket types
    # Call validate_for_publish
    # Expect can_publish = False, tickets.complete = False

async def test_validate_for_publish_ticketed_no_start_time():
    # Create ticketed event day without start_time
    # Call validate_for_publish
    # Expect schedule.complete = False, error on start_time
```

- [ ] **Step 2: Add publish endpoint tests to test_event_urls.py**

```python
async def test_publish_event_success():
    # POST /api/events/{event_id}/publish
    # Expect 200 with is_published = True

async def test_publish_event_validation_failure():
    # POST /api/events/{event_id}/publish with incomplete event
    # Expect 400 with validation errors

async def test_get_publish_validations_returns_section_errors():
    # GET /api/events/{event_id}/publish-validations
    # Returns structured validation errors by section
```

- [ ] **Step 3: Run tests**

Run: `.venv/bin/python -m pytest tests/apps/event/ -v`

- [ ] **Step 4: Commit**

```bash
git add tests/apps/event/test_event_urls.py tests/apps/event/test_event_service.py
git commit -m "test(event): add publish and validation tests"
```

---

## Verification Checklist

- [ ] Migration creates `is_published` column with default `false`
- [ ] `GET /api/events/{id}/publish-validations` returns section-level errors for incomplete events
- [ ] `GET /api/events/{id}/publish-validations` returns `can_publish: true` for complete events
- [ ] `POST /api/events/{id}/publish` returns 400 with validation errors for incomplete events
- [ ] `POST /api/events/{id}/publish` sets `status="published"`, `is_published=True`, `published_at=now()` on success
- [ ] All existing tests still pass
- [ ] New tests cover validation scenarios: open/ticketed × venue/online/recorded/hybrid combinations

---

## Execution Order

1. Task 1: Add `is_published` field + migration
2. Task 2: Add response schemas
3. Task 5: Add repository methods (needed by service)
4. Task 3: Add validation logic in service
5. Task 4: Add publish endpoints
6. Task 6: Update base.md
7. Task 7: Add tests

**Plan complete and saved to `docs/superpowers/plans/2026-04-08-publish-event-api.md`**

Two execution options:

**1. Subagent-Driven (recommended)** - I dispatch a fresh subagent per task, review between tasks, fast iteration

**2. Inline Execution** - Execute tasks in this session using executing-plans, batch execution with checkpoints

Which approach?