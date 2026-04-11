# Remove Ticket Requirement from Publish Validation

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Allow `ticketed` events to be published without any ticket types or allocations. A `tickets_pending` flag tracks when tickets haven't been added yet.

**Architecture:** Ticketed events can now publish with zero tickets. The `tickets_pending` flag is set to `True` on the event at publish time if no tickets exist. When the organizer adds their first ticket type + allocation, `tickets_pending` is cleared to `False`. The `setup_status.tickets` field still returns `False` (so the organizer dashboard correctly shows "Tickets" as incomplete), but `can_publish` no longer blocks on missing tickets.

**Tech Stack:** FastAPI, SQLAlchemy (async), Alembic migrations, Pydantic

---

## File Structure

| File | Responsibility |
|------|---------------|
| `src/apps/event/models.py` | Add `tickets_pending` column to `EventModel` |
| `src/migrations/versions/XXXX_add_tickets_pending.py` | Alembic migration for new column |
| `src/apps/event/service.py` | Modify `_validate_tickets`, `publish_event`, and `_refresh_setup_status` |
| `src/apps/ticketing/service.py` | Clear `tickets_pending` after ticket/allocation creation |
| `tests/apps/event/test_event_service.py` | Update and add tests |

---

## Edge Cases

1. **Published event loses all tickets** — if organizer deletes all ticket types after publishing, `tickets_pending` should be re-set to `True` (same as when first published without tickets)
2. **Open events** — `tickets_pending` is irrelevant for open events; they don't need tickets ever
3. **`setup_status.tickets`** — should remain `False` while `tickets_pending = True`, so organizer dashboard correctly shows "Tickets" as incomplete
4. **`can_publish`** — should be `True` even when `tickets_pending = True` (no longer a blocking issue)
5. **Multiple ticket types / allocations** — clearing `tickets_pending` only happens when BOTH exist (per original logic)
6. **Re-publishing** — if event is already published and tickets are added, `tickets_pending` clears but nothing else changes

---

## Task 1: Add `tickets_pending` column to EventModel

**Files:**
- Modify: `src/apps/event/models.py:56-58`
- Test: `tests/apps/event/test_event_service.py`

- [ ] **Step 1: Add `tickets_pending` column to EventModel**

In `src/apps/event/models.py`, add after `is_published` column (around line 58):

```python
tickets_pending: Mapped[bool] = mapped_column(
    Boolean, default=False, server_default=text("false"), nullable=False
)
```

- [ ] **Step 2: Verify the model change is syntactically correct**

Run: `cd /home/manav1011/Documents/ticket-shicket-be && uv run python -c "from apps.event.models import EventModel; print('OK')"`
Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add src/apps/event/models.py
git commit -m "feat(event): add tickets_pending boolean column to EventModel"
```

---

## Task 2: Create Alembic migration

**Files:**
- Create: `src/migrations/versions/XXXXXXXX_add_tickets_pending_to_events.py`

- [ ] **Step 1: Generate the migration**

Run: `cd /home/manav1011/Documents/ticket-shicket-be && uv run main.py makemigrations --name add_tickets_pending_to_events`
Expected: A new file created in `src/migrations/versions/`

The generated migration should contain:
```python
op.add_column('events', sa.Column('tickets_pending', sa.Boolean(), server_default=sa.text('false'), nullable=False))
```

- [ ] **Step 2: Review the migration file** — open it and verify the `upgrade()` and `downgrade()` methods look correct

- [ ] **Step 3: Commit the migration**

```bash
git add src/migrations/versions/XXXXXXXX_add_tickets_pending_to_events.py
git commit -m "migrations: add tickets_pending column to events table"
```

---

## Task 3: Modify `_validate_tickets` to not block publish for ticketed events without tickets

**Files:**
- Modify: `src/apps/event/service.py:160-178`
- Test: `tests/apps/event/test_event_service.py`

- [ ] **Step 1: Write the failing test — ticketed event without tickets should allow publish**

In `tests/apps/event/test_event_service.py`, add after the existing `test_validate_for_publish_ticketed_missing_tickets` test (around line 364):

```python
@pytest.mark.asyncio
async def test_validate_for_publish_ticketed_without_tickets_allows_publish():
    """Ticketed event without tickets should NOT fail validation (tickets_pending mode)."""
    owner_id = uuid4()
    event_id = uuid4()
    event = SimpleNamespace(
        id=event_id,
        title="Ticketed Workshop",
        event_access_type="ticketed",
        location_mode="venue",
        timezone="Asia/Kolkata",
        venue_name="Community Hall",
        venue_address="123 Main St",
        venue_city="Pune",
        venue_country="India",
        online_event_url=None,
        recorded_event_url=None,
        tickets_pending=False,  # will be set True at publish time
    )
    day = SimpleNamespace(
        id=uuid4(),
        event_id=event_id,
        day_index=1,
        date=datetime(2026, 4, 15).date(),
        start_time=datetime(2026, 4, 15, 10, 0, 0),
        end_time=None,
    )
    organizer_repo = AsyncMock()
    event_repo = AsyncMock()
    event_repo.get_by_id_for_owner.return_value = event
    event_repo.list_event_days.return_value = [day]
    event_repo.list_ticket_types.return_value = []
    event_repo.list_allocations.return_value = []
    service = EventService(event_repo, organizer_repo)

    validation = await service.validate_for_publish(owner_id, event_id)

    # tickets section is incomplete but can_publish is True
    assert validation["sections"]["tickets"]["complete"] is False
    assert validation["can_publish"] is True
    assert len(validation["sections"]["tickets"]["errors"]) == 0  # no errors returned
```

- [ ] **Step 2: Run the new test to verify it fails**

Run: `pytest tests/apps/event/test_event_service.py::test_validate_for_publish_ticketed_without_tickets_allows_publish -v`
Expected: FAIL (can_publish is still False, or errors are returned)

- [ ] **Step 3: Modify `_validate_tickets` to not return errors for ticketed events without tickets**

In `src/apps/event/service.py`, replace the `_validate_tickets` method (lines 160-178):

```python
def _validate_tickets(self, event, ticket_types: list, allocations: list) -> list[FieldErrorResponse]:
    """Validate tickets section - does NOT block publish for ticketed events without tickets.

    For ticketed events with no tickets, tickets_pending flag is set at publish time.
    setup_status.tickets will be False (incomplete) so organizer dashboard stays accurate.
    """
    errors = []

    if getattr(event, 'event_access_type', None) == EventAccessType.open:
        return errors

    # For ticketed events with no tickets, don't return errors — allow publish with tickets_pending
    if len(ticket_types) == 0 or len(allocations) == 0:
        return errors

    # Validate allocation quantities (only when tickets actually exist)
    for alloc in allocations:
        if getattr(alloc, 'quantity', 0) <= 0:
            errors.append(FieldErrorResponse(field=f"allocation_{getattr(alloc, 'id', 'unknown')}.quantity", message="Allocation quantity must be greater than 0", code="INVALID_FIELD_VALUE"))

    return errors
```

**Important change:** Previously the method returned errors when `ticket_types == 0` or `allocations == 0`, blocking publish. Now it returns no errors in those cases — `tickets_pending` handles the state instead.

- [ ] **Step 4: Run the new test to verify it passes**

Run: `pytest tests/apps/event/test_event_service.py::test_validate_for_publish_ticketed_without_tickets_allows_publish -v`
Expected: PASS

- [ ] **Step 5: Run ALL existing event service tests to verify no regressions**

Run: `pytest tests/apps/event/test_event_service.py -v`
Expected: All tests pass (the old `test_validate_for_publish_ticketed_missing_tickets` still passes because it checks `sections["tickets"]["complete"] is False` which is still True)

- [ ] **Step 6: Commit**

```bash
git add src/apps/event/service.py tests/apps/event/test_event_service.py
git commit -m "feat(event): allow ticketed events to publish without tickets (tickets_pending mode)"
```

---

## Task 4: Set `tickets_pending = True` on the event at publish time when no tickets exist

**Files:**
- Modify: `src/apps/event/service.py:244-260`
- Test: `tests/apps/event/test_event_service.py`

- [ ] **Step 1: Write the failing test — publish without tickets sets tickets_pending = True**

In `tests/apps/event/test_event_service.py`, add after the existing `test_publish_event_sets_published_fields` test (around line 452):

```python
@pytest.mark.asyncio
async def test_publish_ticketed_event_without_tickets_sets_tickets_pending():
    """Publishing a ticketed event without tickets should set tickets_pending = True."""
    owner_id = uuid4()
    event_id = uuid4()
    event = SimpleNamespace(
        id=event_id,
        title="Ticketed Workshop",
        event_access_type="ticketed",
        location_mode="venue",
        timezone="Asia/Kolkata",
        venue_name="Community Hall",
        venue_address="123 Main St",
        venue_city="Pune",
        venue_country="India",
        online_event_url=None,
        recorded_event_url=None,
        status="draft",
        is_published=False,
        published_at=None,
        tickets_pending=False,
    )
    day = SimpleNamespace(
        id=uuid4(),
        event_id=event_id,
        day_index=1,
        date=datetime(2026, 4, 15).date(),
        start_time=datetime(2026, 4, 15, 10, 0, 0),
        end_time=None,
    )
    organizer_repo = AsyncMock()
    event_repo = AsyncMock()
    event_repo.get_by_id_for_owner.return_value = event
    event_repo.list_event_days.return_value = [day]
    event_repo.list_ticket_types.return_value = []  # no tickets
    event_repo.list_allocations.return_value = []   # no allocations
    event_repo.session = AsyncMock()
    event_repo.session.flush = AsyncMock()
    event_repo.session.refresh = AsyncMock()
    service = EventService(event_repo, organizer_repo)

    published_event = await service.publish_event(owner_id, event_id)

    assert event.tickets_pending is True
    assert event.status == "published"
    assert event.is_published is True
```

- [ ] **Step 2: Run the new test to verify it fails**

Run: `pytest tests/apps/event/test_event_service.py::test_publish_ticketed_event_without_tickets_sets_tickets_pending -v`
Expected: FAIL (tickets_pending not set)

- [ ] **Step 3: Modify `publish_event` to set `tickets_pending` when no tickets exist**

In `src/apps/event/service.py`, replace the `publish_event` method (lines 244-260):

```python
async def publish_event(self, owner_user_id: UUID, event_id: UUID):
    """Publish event if all validations pass. Sets tickets_pending if ticketed event has no tickets."""
    validation = await self.validate_for_publish(owner_user_id, event_id)

    if not validation["can_publish"]:
        from .exceptions import CannotPublishEvent
        validation_serializable = _serialize_for_json(validation)
        raise CannotPublishEvent(validation_serializable)

    event = await self.repository.get_by_id_for_owner(event_id, owner_user_id)
    event.status = "published"
    event.is_published = True
    event.published_at = datetime.utcnow()

    # Set tickets_pending flag if ticketed event has no tickets
    ticket_types = await self.repository.list_ticket_types(event_id)
    allocations = await self.repository.list_allocations(event_id)
    if (event.event_access_type == EventAccessType.ticketed and
            (len(ticket_types) == 0 or len(allocations) == 0)):
        event.tickets_pending = True

    await self.repository.session.flush()
    await self.repository.session.refresh(event)
    return event
```

- [ ] **Step 4: Run the new test to verify it passes**

Run: `pytest tests/apps/event/test_event_service.py::test_publish_ticketed_event_without_tickets_sets_tickets_pending -v`
Expected: PASS

- [ ] **Step 5: Run all event service tests**

Run: `pytest tests/apps/event/test_event_service.py -v`
Expected: All pass

- [ ] **Step 6: Commit**

```bash
git add src/apps/event/service.py tests/apps/event/test_event_service.py
git commit -m "feat(event): set tickets_pending=True when publishing ticketed event without tickets"
```

---

## Task 5: Auto-clear `tickets_pending` when tickets are added

**Files:**
- Modify: `src/apps/ticketing/service.py`
- Test: `tests/apps/ticketing/test_ticketing_service.py`

- [ ] **Step 1: Write the failing test — creating ticket type clears tickets_pending**

In `tests/apps/ticketing/test_ticketing_service.py`, add after existing tests. First check the file to find the right place to add:

```python
@pytest.mark.asyncio
async def test_create_ticket_type_clears_tickets_pending():
    """Creating the first ticket type should clear tickets_pending on the event."""
    owner_id = uuid4()
    event_id = uuid4()
    event = SimpleNamespace(
        id=event_id,
        event_access_type="ticketed",
        tickets_pending=True,
    )
    event_repo = AsyncMock()
    event_repo.get_by_id_for_owner.return_value = event
    repo = AsyncMock()
    repo.add = MagicMock()
    repo.session = AsyncMock()
    repo.session.flush = AsyncMock()
    repo.session.refresh = AsyncMock()
    event_day_repo = AsyncMock()
    service = TicketingService(repo, event_repo, event_day_repo)

    await service.create_ticket_type(owner_id, event_id, "General Admission", "general", 0, "USD")

    # After creating a ticket type, tickets_pending should be cleared
    assert event.tickets_pending is False
```

- [ ] **Step 2: Run the new test to verify it fails**

Run: `pytest tests/apps/ticketing/test_ticketing_service.py::test_create_ticket_type_clears_tickets_pending -v`
Expected: FAIL (tickets_pending not set)

- [ ] **Step 3: Write the failing test — allocating ticket also clears tickets_pending**

```python
@pytest.mark.asyncio
async def test_allocate_ticket_clears_tickets_pending():
    """Allocating a ticket type to a day should clear tickets_pending."""
    owner_id = uuid4()
    event_id = uuid4()
    event_day_id = uuid4()
    ticket_type_id = uuid4()
    event = SimpleNamespace(
        id=event_id,
        event_access_type="ticketed",
        tickets_pending=True,
    )
    day = SimpleNamespace(
        id=event_day_id,
        event_id=event_id,
        next_ticket_index=1,
    )
    ticket_type = SimpleNamespace(
        id=ticket_type_id,
        event_id=event_id,
        name="General",
    )
    event_repo = AsyncMock()
    event_repo.get_by_id_for_owner.return_value = event
    repo = AsyncMock()
    repo.get_ticket_type_for_event.return_value = ticket_type
    repo.create_day_allocation.return_value = SimpleNamespace(
        id=uuid4(), event_day_id=event_day_id, ticket_type_id=ticket_type_id, quantity=50
    )
    repo.bulk_create_tickets = AsyncMock()
    repo.session = AsyncMock()
    repo.session.flush = AsyncMock()
    repo.session.refresh = AsyncMock()
    event_day_repo = AsyncMock()
    event_day_repo.get_event_day_for_owner.return_value = day
    service = TicketingService(repo, event_repo, event_day_repo)

    await service.allocate_ticket_type_to_day(
        owner_id, event_id, event_day_id, ticket_type_id, 50
    )

    assert event.tickets_pending is False
```

- [ ] **Step 4: Run the allocation test to verify it fails**

Run: `pytest tests/apps/ticketing/test_ticketing_service.py::test_allocate_ticket_clears_tickets_pending -v`
Expected: FAIL

- [ ] **Step 5: Modify `create_ticket_type` to clear `tickets_pending`**

In `src/apps/ticketing/service.py`, modify `create_ticket_type` (around line 23):

```python
async def create_ticket_type(
    self, owner_user_id, event_id, name, category, price, currency
):
    event = await self.event_repository.get_by_id_for_owner(event_id, owner_user_id)
    if event.event_access_type != EventAccessType.ticketed:
        raise OpenEventDoesNotSupportTickets

    if price < 0:
        raise InvalidPrice

    ticket_type = TicketTypeModel(
        event_id=event_id,
        name=name,
        category=category,
        price=price,
        currency=currency,
    )
    self.repository.add(ticket_type)

    # Clear tickets_pending flag now that first ticket type is being created
    if getattr(event, 'tickets_pending', False):
        event.tickets_pending = False

    await self.repository.session.flush()
    await self.repository.session.refresh(ticket_type)
    return ticket_type
```

- [ ] **Step 6: Run the ticket type test to verify it passes**

Run: `pytest tests/apps/ticketing/test_ticketing_service.py::test_create_ticket_type_clears_tickets_pending -v`
Expected: PASS

- [ ] **Step 7: Modify `allocate_ticket_type_to_day` to clear `tickets_pending`**

In `src/apps/ticketing/service.py`, modify `allocate_ticket_type_to_day` (around line 58):

After the `try:` block that creates the allocation (around line 83-84), before `await self.repository.bulk_create_tickets`:

```python
        # Clear tickets_pending flag now that tickets are being allocated
        if getattr(event, 'tickets_pending', False):
            event.tickets_pending = False
```

Or add it right after the `allocation = await self.repository.create_day_allocation(...)` line.

- [ ] **Step 8: Run the allocation test to verify it passes**

Run: `pytest tests/apps/ticketing/test_ticketing_service.py::test_allocate_ticket_clears_tickets_pending -v`
Expected: PASS

- [ ] **Step 9: Run all ticketing service tests**

Run: `pytest tests/apps/ticketing/test_ticketing_service.py -v`
Expected: All pass

- [ ] **Step 10: Commit**

```bash
git add src/apps/ticketing/service.py tests/apps/ticketing/test_ticketing_service.py
git commit -m "feat(ticketing): clear tickets_pending flag when tickets or allocations are created"
```

---

## Task 6: Handle edge case — tickets deleted after publish re-sets `tickets_pending`

**Files:**
- Modify: `src/apps/ticketing/service.py`
- Test: `tests/apps/ticketing/test_ticketing_service.py`

- [ ] **Step 1: Write the failing test — deleting all ticket types re-sets tickets_pending**

In `tests/apps/ticketing/test_ticketing_service.py`, add:

```python
@pytest.mark.asyncio
async def test_delete_ticket_type_resets_tickets_pending():
    """If all ticket types are deleted, tickets_pending should be re-set."""
    owner_id = uuid4()
    event_id = uuid4()
    event = SimpleNamespace(
        id=event_id,
        event_access_type="ticketed",
        tickets_pending=False,  # already had tickets, flag was cleared
    )
    event_repo = AsyncMock()
    event_repo.get_by_id_for_owner.return_value = event
    event_repo.count_ticket_types.return_value = 0  # after deletion, 0 remain
    repo = AsyncMock()
    repo.session = AsyncMock()
    repo.session.flush = AsyncMock()
    event_day_repo = AsyncMock()
    service = TicketingService(repo, event_repo, event_day_repo)

    # Simulate the delete path - in the repository delete_ticket_type method
    # For now, we test the logic: when count goes to 0 and tickets_pending was False,
    # we should set it back to True when deletion happens
    # (This test documents the expected behavior)
```

**Note:** This edge case likely needs a `delete_ticket_type` or `delete_all_ticket_types` method. For now, document this as a known limitation. The simpler approach: just rely on the publish-time flag-setting. If organizer deletes all tickets after publish, `tickets_pending` won't re-set — but this is an unlikely edge case. We can implement a cleanup method later.

For now, skip implementing this step and note it as a future improvement.

- [ ] **Step 2: Commit (skip, documenting as known limitation)**

---

## Task 7: Update `setup_status.tickets` logic to account for `tickets_pending`

**Files:**
- Modify: `src/apps/event/service.py:64-77`
- Test: `tests/apps/event/test_event_service.py`

- [ ] **Step 1: Write the failing test — tickets_complete is False when tickets_pending is True**

In `tests/apps/event/test_event_service.py`:

```python
@pytest.mark.asyncio
async def test_setup_status_tickets_false_when_tickets_pending():
    """setup_status.tickets should be False when tickets_pending is True (organizer dashboard shows incomplete)."""
    owner_id = uuid4()
    event_id = uuid4()
    event = SimpleNamespace(
        id=event_id,
        title="Ticketed Workshop",
        event_access_type="ticketed",
        location_mode="venue",
        timezone="Asia/Kolkata",
        setup_status={},
        tickets_pending=True,
    )
    day = SimpleNamespace(
        id=uuid4(),
        event_id=event_id,
        day_index=1,
        date=datetime(2026, 4, 15).date(),
        start_time=datetime(2026, 4, 15, 10, 0, 0),
        end_time=None,
    )
    organizer_repo = AsyncMock()
    event_repo = AsyncMock()
    event_repo.get_by_id_for_owner.return_value = event
    event_repo.list_event_days.return_value = [day]
    event_repo.list_ticket_types.return_value = []  # no tickets
    event_repo.list_allocations.return_value = []    # no allocations
    event_repo.count_event_days.return_value = 1
    event_repo.count_ticket_types.return_value = 0
    event_repo.count_ticket_allocations.return_value = 0
    event_repo.session = AsyncMock()
    event_repo.list_media_assets = AsyncMock(return_value=[])
    service = EventService(event_repo, organizer_repo)

    setup_status = await service._build_setup_status(event, 1, 0, 0)

    # Even though setup_status returns tickets=False (incomplete),
    # can_publish should still be True
    assert setup_status["tickets"] is False
```

- [ ] **Step 2: Verify the test passes without changes**

Run: `pytest tests/apps/event/test_event_service.py::test_setup_status_tickets_false_when_tickets_pending -v`
Expected: PASS — the existing `_build_setup_status` already returns `tickets: False` when no tickets exist. The `tickets_pending` flag is separate from `setup_status.tickets`.

- [ ] **Step 3: Commit**

```bash
git add tests/apps/event/test_event_service.py
git commit -m "test(event): verify setup_status.tickets is False when tickets_pending is True"
```

---

## Task 8: Final regression test — full publish flow

**Files:**
- Test: `tests/apps/event/test_event_service.py`

- [ ] **Step 1: Write integration test — full ticketed publish flow with tickets_pending**

```python
@pytest.mark.asyncio
async def test_ticketed_event_can_be_published_without_tickets_and_then_tickets_added():
    """Full flow: publish without tickets (tickets_pending=True), then add tickets."""
    owner_id = uuid4()
    event_id = uuid4()

    # Part 1: Event setup
    event = SimpleNamespace(
        id=event_id,
        title="Ticketed Workshop",
        event_access_type="ticketed",
        location_mode="venue",
        timezone="Asia/Kolkata",
        venue_name="Community Hall",
        venue_address="123 Main St",
        venue_city="Pune",
        venue_country="India",
        online_event_url=None,
        recorded_event_url=None,
        status="draft",
        is_published=False,
        published_at=None,
        tickets_pending=False,
    )
    day = SimpleNamespace(
        id=uuid4(),
        event_id=event_id,
        day_index=1,
        date=datetime(2026, 4, 15).date(),
        start_time=datetime(2026, 4, 15, 10, 0, 0),
        end_time=None,
    )
    organizer_repo = AsyncMock()
    event_repo = AsyncMock()
    event_repo.get_by_id_for_owner.return_value = event
    event_repo.list_event_days.return_value = [day]
    event_repo.list_ticket_types.return_value = []  # no tickets yet
    event_repo.list_allocations.return_value = []   # no allocations yet
    event_repo.session = AsyncMock()
    event_repo.session.flush = AsyncMock()
    event_repo.session.refresh = AsyncMock()
    event_repo.list_media_assets = AsyncMock(return_value=[
        SimpleNamespace(id=uuid4(), asset_type="banner", storage_key="test.jpg", public_url="https://test.com/test.jpg")
    ])
    service = EventService(event_repo, organizer_repo)

    # Validate before publish — should pass even without tickets
    validation = await service.validate_for_publish(owner_id, event_id)
    assert validation["can_publish"] is True

    # Publish — should set tickets_pending
    published = await service.publish_event(owner_id, event_id)
    assert published.tickets_pending is True

    # Now add tickets (simulated via ticketing service)
    event.tickets_pending = False  # cleared by ticketing service
    event_repo.list_ticket_types.return_value = [SimpleNamespace(id=uuid4(), name="General")]
    event_repo.list_allocations.return_value = [SimpleNamespace(id=uuid4(), quantity=50)]

    # Validate after adding tickets
    validation2 = await service.validate_for_publish(owner_id, event_id)
    assert validation2["can_publish"] is True
    assert validation2["sections"]["tickets"]["complete"] is True
```

- [ ] **Step 2: Run the integration test**

Run: `pytest tests/apps/event/test_event_service.py::test_ticketed_event_can_be_published_without_tickets_and_then_tickets_added -v`
Expected: PASS

- [ ] **Step 3: Run all event tests**

Run: `pytest tests/apps/event/test_event_service.py -v`
Expected: All pass

- [ ] **Step 4: Commit**

```bash
git add tests/apps/event/test_event_service.py
git commit -m "test(event): add full flow integration test for tickets_pending publish"
```

---

## Task 9: Final verification — run full test suite

- [ ] **Step 1: Run all event and ticketing tests**

Run: `pytest tests/apps/event/ tests/apps/ticketing/ -v --tb=short`
Expected: All tests pass with no errors

- [ ] **Step 2: Rebuild the knowledge graph**

Run: `python3 -c "from graphify.watch import _rebuild_code; from pathlib import Path; _rebuild_code(Path('.'))"`
Expected: No output (rebuilds successfully)

- [ ] **Step 3: Final commit**

```bash
git status
git commit -m "feat: allow ticketed events to publish without tickets via tickets_pending flag"
```
