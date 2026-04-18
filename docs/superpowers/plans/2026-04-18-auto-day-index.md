# Auto Day Index via days_count Denormalization

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a `days_count` field to `EventModel` for O(1) day index lookup, eliminating the need for users to provide `day_index` when creating event days. The field is atomically incremented on day creation and decremented on day deletion.

**Architecture:** Denormalize `days_count` on `EventModel` as the single source of truth for next day index. Atomic SQL `UPDATE SET days_count = days_count + 1` on insert; `days_count = days_count - 1` on delete. This avoids race conditions from read-then-write patterns.

**Tech Stack:** SQLAlchemy (async), Alembic migrations, pytest (unit tests)

---

## File Map

- **Modify:** `src/apps/event/models.py:12-65` — add `days_count` column to `EventModel`
- **Create:** `src/migrations/versions/<new_hash>_add_days_count_to_events.py` — migration to add column
- **Modify:** `src/apps/event/repository.py:46-61` — atomic increment of `days_count` in `create_event_day`
- **Modify:** `src/apps/event/repository.py:90-92` — atomic decrement of `days_count` in `delete_event_day`
- **Modify:** `src/apps/event/request.py:33-37` — remove `day_index` from `CreateEventDayRequest`
- **Modify:** `src/apps/event/service.py:337-345` — update `create_event_day` signature to auto-assign index
- **Modify:** `src/apps/event/urls.py:128-136` — pass only `date`, `start_time`, `end_time` to service
- **Modify:** `tests/apps/event/test_event_service.py` — update tests to reflect auto day_index

---

## Task 1: Add `days_count` to EventModel

**Files:**
- Modify: `src/apps/event/models.py:62-64` (after `interested_counter`)

- [ ] **Step 1: Add the `days_count` column to EventModel**

```python
# In EventModel, after interested_counter (line 64):
days_count: Mapped[int] = mapped_column(
    Integer, default=0, server_default=text("0"), nullable=False
)
```

- [ ] **Step 2: Run existing tests to verify model still valid**

Run: `cd /home/manav1011/Documents/ticket-shicket-be && uv run pytest tests/apps/event/test_event_service.py -v --tb=short -x 2>&1 | head -50`
Expected: PASS (model changes are backward-compatible)

- [ ] **Step 3: Commit**

```bash
git add src/apps/event/models.py
git commit -m "feat(event): add days_count denormalized counter to EventModel"
```

---

## Task 2: Create Migration for `days_count`

**Files:**
- Create: `src/migrations/versions/<hash>_add_days_count_to_events.py`

- [ ] **Step 1: Create migration file**

Using the latest migration `86361eeddf67` as parent, create:

```python
"""add days_count to events

Revision ID: <new_hash>
Revises: 86361eeddf67
Create Date: 2026-04-18 15:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '<new_hash>'
down_revision = '86361eeddf67'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        'events',
        sa.Column('days_count', sa.Integer(), server_default='0', nullable=False)
    )


def downgrade() -> None:
    op.drop_column('events', 'days_count')
```

- [ ] **Step 2: Generate new hash for migration filename**

Run: `cd /home/manav1011/Documents/ticket-shicket-be && python3 -c "import uuid; print(str(uuid.uuid4())[:12])"`
Replace `<hash>` in filename with the generated hash.

- [ ] **Step 3: Run migration**

Run: `cd /home/manav1011/Documents/ticket-shicket-be && uv run main.py migrate`
Expected: Migration applies successfully

- [ ] **Step 4: Verify column exists**

Run: `cd /home/manav1011/Documents/ticket-shicket-be && uv run main.py showmigrations`
Expected: All migrations show as applied ("[X]")

- [ ] **Step 5: Commit**

```bash
git add src/migrations/versions/
git commit -m "feat(migration): add days_count column to events table"
```

---

## Task 3: Update Repository `create_event_day` — Atomic Increment

**Files:**
- Modify: `src/apps/event/repository.py:46-61`

- [ ] **Step 1: Update `create_event_day` to use atomic increment**

Replace the `create_event_day` method in `repository.py`:

```python
async def create_event_day(
    self, event_id, day_date, start_time=None, end_time=None
) -> EventDayModel:
    # Atomic increment of days_count and retrieval in single statement
    result = await self._session.execute(
        update(EventModel)
        .where(EventModel.id == event_id)
        .values(days_count=EventModel.days_count + 1)
        .returning(EventModel.days_count)
    )
    day_index = await self._session.scalar(result)
    if day_index is None:
        raise ValueError(f"Event {event_id} not found")

    event_day = EventDayModel(
        event_id=event_id,
        day_index=day_index,  # Already incremented — new day gets this index
        date=day_date,
        start_time=start_time,
        end_time=end_time,
        scan_status="not_started",
        next_ticket_index=1,
    )
    self._session.add(event_day)
    await self._session.flush()
    await self._session.refresh(event_day)
    return event_day
```

Note: `Repository.create_event_day` signature changes — `day_index` parameter removed.

- [ ] **Step 2: Verify the change compiles**

Run: `cd /home/manav1011/Documents/ticket-shicket-be && python3 -c "from apps.event.repository import EventRepository; print('OK')"`
Expected: No import errors

- [ ] **Step 3: Commit**

```bash
git add src/apps/event/repository.py
git commit -m "feat(event): auto-assign day_index via atomic days_count increment"
```

---

## Task 4: Update Repository `delete_event_day` — Atomic Decrement

**Files:**
- Modify: `src/apps/event/repository.py:90-92`

- [ ] **Step 1: Update `delete_event_day` to decrement days_count**

Replace the `delete_event_day` method:

```python
async def delete_event_day(self, event_day: EventDayModel) -> None:
    await self._session.delete(event_day)
    await self._session.flush()
    # Decrement days_count atomically after delete
    await self._session.execute(
        update(EventModel)
        .where(EventModel.id == event_day.event_id)
        .values(days_count=EventModel.days_count - 1)
    )
    await self._session.flush()
```

- [ ] **Step 2: Commit**

```bash
git add src/apps/event/repository.py
git commit -m "feat(event): decrement days_count on day deletion"
```

---

## Task 5: Update CreateEventDayRequest — Remove `day_index`

**Files:**
- Modify: `src/apps/event/request.py:33-37`

- [ ] **Step 1: Remove `day_index` from CreateEventDayRequest**

```python
class CreateEventDayRequest(CamelCaseModel):
    date: Date                          # day_index is now auto-assigned
    start_time: datetime | None = None
    end_time: datetime | None = None
```

- [ ] **Step 2: Verify it compiles**

Run: `cd /home/manav1011/Documents/ticket-shicket-be && python3 -c "from apps.event.request import CreateEventDayRequest; print('OK')"`
Expected: OK

- [ ] **Step 3: Commit**

```bash
git add src/apps/event/request.py
git commit -m "feat(api): remove day_index from CreateEventDayRequest — now auto-assigned"
```

---

## Task 6: Update Service `create_event_day` — Auto Index

**Files:**
- Modify: `src/apps/event/service.py:337-345`

- [ ] **Step 1: Update service method signature**

Replace:

```python
async def create_event_day(self, owner_user_id, event_id, date, start_time=None, end_time=None):
    event = await self.repository.get_by_id_for_owner(event_id, owner_user_id)
    if not event:
        raise EventNotFound
    day = await self.repository.create_event_day(
        event_id, date, start_time=start_time, end_time=end_time
    )
    await self._refresh_setup_status(event)
    return day
```

- [ ] **Step 2: Commit**

```bash
git add src/apps/event/service.py
git commit -m "feat(event): create_event_day auto-assigns day_index from days_count"
```

---

## Task 7: Update URL Endpoint — Pass Only Date/Time Fields

**Files:**
- Modify: `src/apps/event/urls.py:128-136`

- [ ] **Step 1: Update route handler**

```python
@router.post("/{event_id}/days")
async def create_event_day(
    event_id: UUID,
    request: Request,
    body: Annotated[CreateEventDayRequest, Body()],
    service: Annotated[EventService, Depends(get_event_service)],
) -> BaseResponse[EventDayResponse]:
    day = await service.create_event_day(
        request.state.user.id,
        event_id,
        body.date,
        start_time=body.start_time,
        end_time=body.end_time,
    )
    return BaseResponse(data=EventDayResponse.model_validate(day))
```

- [ ] **Step 2: Verify endpoint compiles**

Run: `cd /home/manav1011/Documents/ticket-shicket-be && python3 -c "from apps.event.urls import router; print('OK')"`
Expected: OK

- [ ] **Step 3: Commit**

```bash
git add src/apps/event/urls.py
git commit -m "feat(api): create_event_day endpoint passes only date/start_time/end_time"
```

---

## Task 8: Update Tests

**Files:**
- Modify: `tests/apps/event/test_event_service.py:39-72`, `182-218`, and any other tests using `create_event_day`

- [ ] **Step 1: Update `test_create_event_day_and_start_scan_from_same_service`**

Find the test around line 39. Update the mock setup — `event_repo.create_event_day.return_value` should still work but the signature changed. Update mock for `count_event_days` not needed since days_count is on the model now:

```python
async def test_create_event_day_and_start_scan_from_same_service():
    owner_id = uuid4()
    event_id = uuid4()
    event = SimpleNamespace(id=event_id, organizer_page_id=uuid4(), days_count=0)
    day = SimpleNamespace(
        id=uuid4(),
        event_id=event_id,
        day_index=0,  # First day gets index 0
        date=datetime(2026, 4, 15).date(),
        scan_status="not_started",
        scan_started_at=None,
        scan_paused_at=None,
        scan_ended_at=None,
    )
    organizer_repo = AsyncMock()
    event_repo = AsyncMock()
    event_repo.get_by_id_for_owner.return_value = event
    # Mock the atomic increment result — returning updated days_count
    mock_result = MagicMock()
    mock_result.scalar = AsyncMock(return_value=1)  # days_count after increment = 1
    event_repo._session.execute = AsyncMock(return_value=mock_result)
    event_repo.create_event_day.return_value = day
    event_repo.get_event_day_for_owner.return_value = day
    event_repo.count_ticket_types.return_value = 0
    event_repo.count_ticket_allocations.return_value = 0
    event_repo.session = AsyncMock()
    service = EventService(event_repo, organizer_repo)

    created_day = await service.create_event_day(
        owner_id, event_id, datetime(2026, 4, 15).date()
    )
    updated_day = await service.start_scan(owner_id, created_day.id)

    assert created_day.event_id == event_id
    assert created_day.day_index == 0
    assert updated_day.scan_status == "active"
    assert updated_day.scan_started_at is not None
```

- [ ] **Step 2: Update `test_create_event_day_marks_schedule_complete`**

Update around line 182 to remove `day_index=1` from the call and adjust day mock:

```python
async def test_create_event_day_marks_schedule_complete():
    owner_id = uuid4()
    event_id = uuid4()
    event = SimpleNamespace(
        id=event_id,
        title="Ahmedabad Startup Meetup",
        event_access_type="open",
        location_mode="venue",
        timezone="Asia/Kolkata",
        setup_status={},
        days_count=0,
    )
    day = SimpleNamespace(
        id=uuid4(),
        event_id=event_id,
        day_index=0,  # auto-assigned
        date=datetime(2026, 4, 15).date(),
        start_time=None,
        end_time=None,
        scan_status="not_started",
        scan_started_at=None,
        scan_paused_at=None,
        scan_ended_at=None,
        next_ticket_index=1,
    )
    organizer_repo = AsyncMock()
    event_repo = AsyncMock()
    event_repo.get_by_id_for_owner.return_value = event
    mock_result = MagicMock()
    mock_result.scalar = AsyncMock(return_value=1)
    event_repo._session.execute = AsyncMock(return_value=mock_result)
    event_repo.create_event_day.return_value = day
    event_repo.count_ticket_types.return_value = 0
    event_repo.count_ticket_allocations.return_value = 0
    event_repo.session = AsyncMock()
    service = EventService(event_repo, organizer_repo)

    await service.create_event_day(owner_id, event_id, datetime(2026, 4, 15).date())

    assert event.setup_status["schedule"] is True
```

- [ ] **Step 3: Run all event service tests**

Run: `cd /home/manav1011/Documents/ticket-shicket-be && uv run pytest tests/apps/event/test_event_service.py -v --tb=short 2>&1 | tail -30`
Expected: All PASS

- [ ] **Step 4: Commit**

```bash
git add tests/apps/event/test_event_service.py
git commit -m "test(event): update tests for auto-assigned day_index"
```

---

## Task 9: Integration Smoke Test

**Files:**
- (No new files — run commands)

- [ ] **Step 1: Start services and test create day flow**

Run local infrastructure: `cd /home/manav1011/Documents/ticket-shicket-be && docker compose up -d`
Run server: `uv run main.py run --debug`
In another terminal, test the API:

```bash
# Get a token first (login as existing user)
TOKEN=$(curl -s http://localhost:8000/api/auth/login ... | jq -r '.data.access_token')

# Create organizer first
ORG_ID=$(curl -s -X POST http://localhost:8000/api/organizers \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name":"Test Org"}' | jq -r '.data.id')

# Create event
EVENT_ID=$(curl -s -X POST http://localhost:8000/api/events \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"title":"Test Event","event_access_type":"open"}' | jq -r '.data.id')

# Create first day — no day_index needed
curl -s -X POST "http://localhost:8000/api/events/$EVENT_ID/days" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"date":"2026-04-20","start_time":"2026-04-20T10:00:00"}' | jq '.data | {id, day_index, date}'

# Create second day — should get day_index=1 automatically
curl -s -X POST "http://localhost:8000/api/events/$EVENT_ID/days" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"date":"2026-04-21","start_time":"2026-04-21T10:00:00"}' | jq '.data | {id, day_index, date}'
```

Expected for first day: `day_index: 0`
Expected for second day: `day_index: 1`

- [ ] **Step 2: Verify via list endpoint**

```bash
curl -s "http://localhost:8000/api/events/$EVENT_ID/days" \
  -H "Authorization: Bearer $TOKEN" | jq '.data[] | {day_index, date}'
```

Expected: Two days with indices 0 and 1.

- [ ] **Step 3: Commit if all smoke tests pass**

```bash
git add -A
git commit -m "test: integration smoke test for auto day_index"
```

---

## Self-Review Checklist

1. **Spec coverage:** All requirements covered?
   - `days_count` added to EventModel ✓
   - Migration created ✓
   - Atomic increment on create ✓
   - Atomic decrement on delete ✓
   - `day_index` removed from user-facing API ✓
   - Service updated ✓
   - Tests updated ✓

2. **Placeholder scan:** No "TBD", "TODO", or placeholder code in plan ✓

3. **Type consistency:**
   - `EventModel.days_count` type: `Mapped[int]` ✓
   - `Repository.create_event_day` signature: `(self, event_id, day_date, start_time=None, end_time=None)` — removed `day_index` ✓
   - `Service.create_event_day` signature: `(self, owner_user_id, event_id, date, start_time=None, end_time=None)` ✓
   - `CreateEventDayRequest`: removed `day_index` ✓

4. **Query optimization:**
   - Atomic `UPDATE ... RETURNING` avoids race condition ✓
   - No extra `SELECT MAX(day_index)` query needed ✓
   - Decrement uses atomic update, no read required ✓

---

## Handoff

**Plan complete and saved to `docs/superpowers/plans/2026-04-18-auto-day-index.md`.**

Two execution options:

**1. Subagent-Driven (recommended)** - I dispatch a fresh subagent per task, review between tasks, fast iteration

**2. Inline Execution** - Execute tasks in this session using executing-plans, batch execution with checkpoints

Which approach?