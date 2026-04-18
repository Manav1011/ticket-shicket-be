# Move Invite Endpoints to User App — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Migrate invite `accept`, `decline`, and `cancel` endpoints from `event/urls.py` to `user/urls.py` — since invites are generic user-centric resources, not event-specific.

**Architecture:**
- Invites belong to `users/invites` — user is the primary actor, event is just metadata inside `meta`
- `accept` — needs `EventService` to create the `EventReseller` record (inject via dependency)
- `decline` — pure `InviteService` action, no event dependency
- `cancel` — pure `InviteService` action (checks `created_by_id`), no event dependency

**Tech Stack:** FastAPI, SQLAlchemy async, pytest-asyncio

---

## File Inventory

| File | Role |
|------|------|
| `src/apps/user/urls.py` | Add accept/decline/cancel endpoints under `protected_router` |
| `src/apps/event/urls.py` | Remove old accept/decline/cancel endpoints (lines 406-481) |
| `src/apps/event/response.py` | Ensure `ResellerResponse` is importable |
| `tests/apps/user/test_user_invite_urls.py` | New tests for moved endpoints |
| `tests/apps/event/test_event_urls.py` | Remove old endpoint tests |

---

## Task 1: Add Accept/Decline/Cancel Endpoints to User URLs

**Files:**
- Modify: `src/apps/user/urls.py` — add 3 new endpoints under `protected_router`
- Create: `tests/apps/user/test_user_invite_urls.py` — tests for moved endpoints

**Note:** The `protected_router` already has `get_user_invite_service` dependency at line 40. We need `EventService` too — we'll inject it the same way `event/urls.py` does.

- [ ] **Step 1: Write failing tests for moved endpoints**

Create `tests/apps/user/test_user_invite_urls.py`:

```python
from types import SimpleNamespace
from uuid import uuid4
from unittest.mock import AsyncMock, MagicMock
import pytest


@pytest.mark.asyncio
async def test_accept_invite_under_user_endpoint():
    """
    POST /api/user/invites/{invite_id}/accept
    1. Calls invite_service.accept_invite(user_id, invite_id)
    2. Validates event exists via event_service
    3. Creates EventReseller via event_service.repository
    """
    from apps.user.urls import accept_user_invite
    from utils.schema import BaseResponse

    user_id = uuid4()
    invite_id = uuid4()
    event_id = uuid4()
    reseller_id = uuid4()

    request = SimpleNamespace(state=SimpleNamespace(user=SimpleNamespace(id=user_id)))

    # Mock invite_service.accept_invite
    mock_invite = MagicMock()
    mock_invite.created_by_id = uuid4()
    mock_invite.meta = {"event_id": str(event_id), "permissions": []}

    mock_invite_service = AsyncMock()
    mock_invite_service.accept_invite = AsyncMock(return_value={
        "invite": mock_invite,
        "event_id": str(event_id),
        "permissions": [],
    })

    # Mock event_service
    mock_event = MagicMock(id=event_id)
    mock_event_service = AsyncMock()
    mock_event_service.repository.get_by_id = AsyncMock(return_value=mock_event)
    mock_event_service.repository.get_reseller_for_event = AsyncMock(return_value=None)
    mock_event_service.repository.create_event_reseller = AsyncMock(return_value=MagicMock(
        id=reseller_id,
        user_id=user_id,
        event_id=event_id,
        invited_by_id=mock_invite.created_by_id,
        permissions=[],
    ))

    response = await accept_user_invite(
        invite_id=invite_id,
        request=request,
        invite_service=mock_invite_service,
        event_service=mock_event_service,
    )

    assert response.data is not None
    mock_invite_service.accept_invite.assert_awaited_once_with(user_id, invite_id)
    mock_event_service.repository.create_event_reseller.assert_awaited_once()


@pytest.mark.asyncio
async def test_decline_invite_under_user_endpoint():
    """
    POST /api/user/invites/{invite_id}/decline
    Just calls invite_service.decline_invite(user_id, invite_id)
    """
    from apps.user.urls import decline_user_invite
    from utils.schema import BaseResponse

    user_id = uuid4()
    invite_id = uuid4()
    request = SimpleNamespace(state=SimpleNamespace(user=SimpleNamespace(id=user_id)))

    mock_invite_service = AsyncMock()
    mock_invite_service.decline_invite = AsyncMock()

    response = await decline_user_invite(
        invite_id=invite_id,
        request=request,
        invite_service=mock_invite_service,
    )

    assert response.data["declined"] is True
    mock_invite_service.decline_invite.assert_awaited_once_with(user_id, invite_id)


@pytest.mark.asyncio
async def test_cancel_invite_under_user_endpoint():
    """
    DELETE /api/user/invites/{invite_id}
    Just calls invite_service.cancel_invite(user_id, invite_id)
    """
    from apps.user.urls import cancel_user_invite
    from utils.schema import BaseResponse

    user_id = uuid4()
    invite_id = uuid4()
    request = SimpleNamespace(state=SimpleNamespace(user=SimpleNamespace(id=user_id)))

    mock_invite_service = AsyncMock()
    mock_invite_service.cancel_invite = AsyncMock()

    response = await cancel_user_invite(
        invite_id=invite_id,
        request=request,
        invite_service=mock_invite_service,
    )

    assert response.data["cancelled"] is True
    mock_invite_service.cancel_invite.assert_awaited_once_with(user_id, invite_id)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/apps/user/test_user_invite_urls.py -v`
Expected: FAIL — endpoints not defined

- [ ] **Step 3: Add `get_event_service` dependency to user/urls.py**

Modify `src/apps/user/urls.py` — add after `get_user_invite_service`:

```python
def get_event_service(session: Annotated[AsyncSession, Depends(db_session)]):
    from apps.event.repository import EventRepository
    from apps.organizer.repository import OrganizerRepository
    from apps.event.service import EventService
    return EventService(EventRepository(session), OrganizerRepository(session))
```

Also add missing imports at top of file:

```python
from apps.event.response import ResellerResponse
from apps.organizer.repository import OrganizerRepository
from apps.event.repository import EventRepository
from apps.event.service import EventService
from apps.event.exceptions import EventNotFound
```

- [ ] **Step 4: Add 3 endpoints under `protected_router`**

Modify `src/apps/user/urls.py` — add after the `list_pending_invites` endpoint (after line 56):

```python
@protected_router.post("/invites/{invite_id}/accept")
async def accept_user_invite(
    invite_id: UUID,
    request: Request,
    invite_service: Annotated[UserInviteService, Depends(get_user_invite_service)],
    event_service: Annotated[EventService, Depends(get_event_service)],
) -> BaseResponse[ResellerResponse]:
    """
    Accept a pending invite (reseller invite).
    Creates EventReseller record if event exists.
    """
    result = await invite_service.accept_invite(request.state.user.id, invite_id)

    event_id_str = result["event_id"]
    if not event_id_str:
        from apps.user.invite.exceptions import InviteNotFound
        raise InviteNotFound("Invite missing event_id in metadata")

    event_id = UUID(event_id_str)

    # Check if event exists
    event = await event_service.repository.get_by_id(event_id)
    if not event:
        raise EventNotFound("Event not found")

    # Check if reseller already exists (idempotent — return existing)
    existing = await event_service.repository.get_reseller_for_event(
        request.state.user.id, event_id
    )
    if existing:
        return BaseResponse(data=ResellerResponse.model_validate(existing))

    permissions = result["permissions"]

    reseller = await event_service.repository.create_event_reseller(
        user_id=request.state.user.id,
        event_id=event_id,
        invited_by_id=result["invite"].created_by_id,
        permissions=permissions,
    )
    return BaseResponse(data=ResellerResponse.model_validate(reseller))


@protected_router.post("/invites/{invite_id}/decline")
async def decline_user_invite(
    invite_id: UUID,
    request: Request,
    invite_service: Annotated[UserInviteService, Depends(get_user_invite_service)],
) -> BaseResponse[dict]:
    """Decline a pending invite."""
    await invite_service.decline_invite(request.state.user.id, invite_id)
    return BaseResponse(data={"declined": True})


@protected_router.delete("/invites/{invite_id}")
async def cancel_user_invite(
    invite_id: UUID,
    request: Request,
    invite_service: Annotated[UserInviteService, Depends(get_user_invite_service)],
) -> BaseResponse[dict]:
    """Cancel a pending invite (only the invite creator can cancel)."""
    await invite_service.cancel_invite(request.state.user.id, invite_id)
    return BaseResponse(data={"cancelled": True})
```

- [ ] **Step 5: Run test to verify it passes**

Run: `pytest tests/apps/user/test_user_invite_urls.py -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add src/apps/user/urls.py tests/apps/user/test_user_invite_urls.py
git commit -m "feat: move invite accept/decline/cancel to user app"
```

---

## Task 2: Remove Old Endpoints from Event URLs

**Files:**
- Modify: `src/apps/event/urls.py` — remove lines 406-481 (accept, decline, cancel)
- Modify: `tests/apps/event/test_event_urls.py` — remove old endpoint tests

- [ ] **Step 1: Remove accept/decline/cancel endpoints from event/urls.py**

Remove these three endpoint functions from `src/apps/event/urls.py`:
- `accept_invite` (lines 406–444)
- `decline_invite` (lines 447–454)
- `cancel_reseller_invite` (lines 457–481)

The `get_user_invite_service` dependency and its import can also be removed if it's no longer used by other endpoints in the file. Check remaining usages first:

```bash
grep -n "get_user_invite_service\|UserInviteService\|invite_service" src/apps/event/urls.py
```

If only the removed endpoints used it, remove the dependency function and its import lines (lines 17-20 in the original file).

- [ ] **Step 2: Remove old endpoint tests from event test file**

Check for old tests:

```bash
grep -n "accept_invite\|decline_invite\|cancel_reseller_invite" tests/apps/event/test_event_urls.py
```

Remove tests that reference these endpoints. The tests `test_create_reseller_invite_accepts_user_ids`, `test_list_reseller_invites_returns_invites`, and `test_create_reseller_invite_fails_for_duplicate` should remain (they test the invite creation/list endpoints which stay in event/urls.py).

- [ ] **Step 3: Run all event tests to confirm nothing broke**

Run: `pytest tests/apps/event/test_event_urls.py -v`
Expected: PASS (remaining tests still work)

- [ ] **Step 4: Commit**

```bash
git add src/apps/event/urls.py tests/apps/event/test_event_urls.py
git commit -m "refactor: remove invite accept/decline/cancel from event app, moved to user app"
```

---

## Task 3: Verify All Endpoint URLs are Correct

- [ ] **Step 1: Confirm new URL paths**

After migration, the final routes should be:

| Method | Old URL | New URL |
|--------|---------|---------|
| POST | `/api/events/invites/{id}/accept` | `/api/user/invites/{id}/accept` |
| POST | `/api/events/invites/{id}/decline` | `/api/user/invites/{id}/decline` |
| DELETE | `/api/events/{event_id}/reseller-invites/{id}` | `/api/user/invites/{id}` |

Verify by running:
```bash
grep -n "invite" src/apps/user/urls.py
grep -n "/invites" src/apps/user/urls.py
```

Expected output should show:
- `/invites/{invite_id}/accept` route
- `/invites/{invite_id}/decline` route
- `/invites/{invite_id}` DELETE route

- [ ] **Step 2: Run full test suite**

Run: `pytest tests/apps/user/test_user_invite_urls.py tests/apps/event/test_event_urls.py -v`
Expected: ALL PASS

- [ ] **Step 3: Commit**

```bash
git commit -m "chore: verify new invite routes under user app"
```

---

## Self-Review Checklist

1. **Spec coverage:**
   - [x] Accept moved to `/api/user/invites/{id}/accept` — Task 1
   - [x] Decline moved to `/api/user/invites/{id}/decline` — Task 1
   - [x] Cancel moved to `/api/user/invites/{id}` — Task 1
   - [x] Old endpoints removed — Task 2
   - [x] EventService properly injected for accept — Task 1

2. **Placeholder scan:** No `TBD`, `TODO`, or incomplete code. All step code is complete and runnable.

3. **Type consistency:**
   - `accept_user_invite` signature: `invite_id: UUID, request: Request, invite_service, event_service` — matches old accept pattern
   - `decline_user_invite` signature: `invite_id: UUID, request: Request, invite_service` — matches old decline pattern
   - `cancel_user_invite` signature: `invite_id: UUID, request: Request, invite_service` — DELETE without body

4. **Breaking changes to check:**
   - Frontend/app clients calling old URLs need to be updated to new URLs
   - Old URLs return 404 after migration — ensure clients are updated

---

## Execution Options

**Plan complete and saved to `docs/superpowers/plans/2026-04-18-move-invites-to-user-app.md`. Two execution options:**

**1. Subagent-Driven (recommended)** — I dispatch a fresh subagent per task, review between tasks, fast iteration

**2. Inline Execution** — Execute tasks in this session using executing-plans, batch execution with checkpoints

**Which approach?**
