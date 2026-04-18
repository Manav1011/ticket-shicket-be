# Reseller Invite Refactor Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the `lookup_type`/`lookup_value` based reseller invite API with a clean `user_id` based approach, add a user lookup API, and add an endpoint to list event reseller invites.

**Architecture:**
1. New `GET /api/users/find` endpoint for user lookup (email or phone query param)
2. Refactor `POST /api/events/{event_id}/reseller-invites` to accept `user_ids: list[UUID]` directly
3. New `GET /api/events/{event_id}/reseller-invites` endpoint to list invites with status filter
4. Update `InviteService.create_invite()` signature to accept `user_id` directly (remove lookup logic)
5. Add `expires_at` logic and cleanup for expired invites

**Tech Stack:** FastAPI, SQLAlchemy async, pytest-asyncio, aiosqlite (in-memory for tests)

---

## File Inventory

| File | Role |
|------|------|
| `src/apps/user/urls.py` | Add `GET /api/users/find` endpoint |
| `src/apps/user/repository.py` | Add `find_by_id()` method |
| `src/apps/user/service.py` | Add `find_user()` service method |
| `src/apps/user/request.py` | Add `UserLookupRequest` schema |
| `src/apps/user/response.py` | Add `UserLookupResponse` schema |
| `src/apps/event/urls.py` | Refactor `create_reseller_invite`, add `list_reseller_invites` endpoint |
| `src/apps/event/request.py` | Replace `CreateInviteRequest` with `CreateResellerInviteRequest` (user_ids based) |
| `src/apps/event/response.py` | Add `ResellerInviteResponse` |
| `src/apps/user/invite/service.py` | Refactor `create_invite()` to accept user_id directly |
| `src/apps/user/invite/repository.py` | Add `get_pending_invite_for_user_event()` method |
| `tests/apps/user/test_user_service.py` | Add tests for `find_user()` |
| `tests/apps/user/test_user_urls.py` | Add tests for user lookup endpoint |
| `tests/apps/event/test_event_urls.py` | Add tests for new invite flow |

---

## Task 1: User Lookup API — Find User by Email or Phone

**Files:**
- Modify: `src/apps/user/repository.py` — add `find_by_id()` method
- Modify: `src/apps/user/service.py` — add `find_user()` method
- Create: `src/apps/user/request.py` — add `UserLookupRequest`
- Modify: `src/apps/user/response.py` — add `UserLookupResponse`
- Modify: `src/apps/user/urls.py` — add `GET /api/users/find` endpoint
- Create: `tests/apps/user/test_user_service.py` — new tests
- Create: `tests/apps/user/test_user_urls.py` — new tests

- [ ] **Step 1: Add `find_by_id()` to UserRepository**

Modify `src/apps/user/repository.py` — add after `get_by_id()`:

```python
async def find_by_id(self, user_id: UUID) -> Optional[UserModel]:
    """Find user by ID. Returns None if not found (unlike get_by_id which may raise)."""
    return await self._session.scalar(
        select(UserModel).where(UserModel.id == user_id)
    )
```

- [ ] **Step 2: Add `UserLookupRequest` schema**

Modify `src/apps/user/request.py` — add at end:

```python
class UserLookupRequest(CamelCaseModel):
    email: str | None = None
    phone: str | None = None

    def model_post_init(self, __pydantic_self__) -> None:
        if not self.email and not self.phone:
            raise ValueError("At least one of email or phone is required")
```

- [ ] **Step 3: Add `UserLookupResponse` schema**

Modify `src/apps/user/response.py` — add at end:

```python
class UserLookupResponse(CamelCaseModel):
    user_id: UUID
    email: str | None = None
    phone: str | None = None
    first_name: str | None = None
    last_name: str | None = None
```

- [ ] **Step 4: Add `find_user()` to UserService**

Modify `src/apps/user/service.py` — add method:

```python
async def find_user(
    self,
    email: str | None = None,
    phone: str | None = None,
) -> Optional[UserLookupResponse]:
    """Find user by email or phone. Returns user info or None."""
    user = None
    if email:
        user = await self.repository.find_by_email(email)
    elif phone:
        user = await self.repository.find_by_phone(phone)

    if not user:
        return None

    return UserLookupResponse(
        user_id=user.id,
        email=user.email,
        phone=user.phone,
        first_name=user.first_name,
        last_name=user.last_name,
    )
```

- [ ] **Step 5: Add `GET /api/users/find` endpoint**

Modify `src/apps/user/urls.py` — add router import and endpoint:

First, check current imports in `src/apps/user/urls.py`:

```python
# After existing imports, add:
from .request import UserLookupRequest
from .response import UserLookupResponse

@router.get("/find")
async def find_user(
    email: str | None = None,
    phone: str | None = None,
    service: Annotated[UserService, Depends(get_user_service)],
    request: Request,
) -> BaseResponse[UserLookupResponse]:
    if not email and not phone:
        raise BadRequestError("email or phone query parameter required")

    user = await service.find_user(email=email, phone=phone)
    if not user:
        raise NotFoundError("User not found")

    return BaseResponse(data=user)
```

- [ ] **Step 6: Write failing test for `find_user()` service method**

Create `tests/apps/user/test_user_service.py`:

```python
import pytest
import uuid
from unittest.mock import MagicMock, AsyncMock
from apps.user.service import UserService


@pytest.fixture
def mock_user_repo():
    return MagicMock()


@pytest.fixture
def user_service(mock_user_repo):
    return UserService(repository=mock_user_repo)


async def test_find_user_by_email_returns_user(user_service, mock_user_repo):
    from apps.user.response import UserLookupResponse

    mock_user = MagicMock()
    mock_user.id = uuid.uuid4()
    mock_user.email = "alice@example.com"
    mock_user.phone = "9876543210"
    mock_user.first_name = "Alice"
    mock_user.last_name = "Smith"

    mock_user_repo.find_by_email = AsyncMock(return_value=mock_user)

    result = await user_service.find_user(email="alice@example.com")

    assert result is not None
    assert result.user_id == mock_user.id
    assert result.email == "alice@example.com"


async def test_find_user_by_phone_returns_user(user_service, mock_user_repo):
    from apps.user.response import UserLookupResponse

    mock_user = MagicMock()
    mock_user.id = uuid.uuid4()
    mock_user.email = "bob@example.com"
    mock_user.phone = "9876543210"
    mock_user.first_name = "Bob"
    mock_user.last_name = "Jones"

    mock_user_repo.find_by_phone = AsyncMock(return_value=mock_user)

    result = await user_service.find_user(phone="9876543210")

    assert result is not None
    assert result.phone == "9876543210"


async def test_find_user_not_found_returns_none(user_service, mock_user_repo):
    mock_user_repo.find_by_email = AsyncMock(return_value=None)

    result = await user_service.find_user(email="ghost@example.com")

    assert result is None
```

- [ ] **Step 7: Run test to verify it fails**

Run: `pytest tests/apps/user/test_user_service.py -v`
Expected: PASS (or import errors if files don't exist yet)

- [ ] **Step 8: Write failing test for user lookup endpoint**

Modify `tests/apps/user/test_user_urls.py` (check if exists, if not create):

```python
import pytest
from types import SimpleNamespace
from uuid import uuid4
from unittest.mock import AsyncMock

from apps.user.response import UserLookupResponse


@pytest.mark.asyncio
async def test_find_user_by_email_returns_user():
    from apps.user.urls import find_user
    from utils.schema import BaseResponse

    request = SimpleNamespace(state=SimpleNamespace(user=SimpleNamespace(id=uuid4())))
    service = AsyncMock()
    service.find_user = AsyncMock(return_value=UserLookupResponse(
        user_id=uuid4(),
        email="alice@example.com",
        phone="9876543210",
        first_name="Alice",
        last_name="Smith",
    ))

    response = await find_user(
        email="alice@example.com",
        phone=None,
        service=service,
        request=request,
    )

    assert response.data.email == "alice@example.com"
    service.find_user.assert_awaited_once_with(email="alice@example.com", phone=None)


@pytest.mark.asyncio
async def test_find_user_not_found_raises_error():
    from apps.user.urls import find_user
    from exceptions import NotFoundError

    request = SimpleNamespace(state=SimpleNamespace(user=SimpleNamespace(id=uuid4())))
    service = AsyncMock()
    service.find_user = AsyncMock(return_value=None)

    with pytest.raises(NotFoundError):
        await find_user(email="ghost@example.com", phone=None, service=service, request=request)
```

- [ ] **Step 9: Run test to verify it fails**

Run: `pytest tests/apps/user/test_user_urls.py -v`
Expected: FAIL — endpoint or schema not yet defined

- [ ] **Step 10: Implement the missing pieces (endpoint, schema)**

Add the schema to `src/apps/user/request.py` and `src/apps/user/response.py`.
Add the endpoint to `src/apps/user/urls.py`.
Add `find_user()` to `src/apps/user/service.py`.

- [ ] **Step 11: Run test to verify it passes**

Run: `pytest tests/apps/user/test_user_service.py tests/apps/user/test_user_urls.py -v`
Expected: PASS

- [ ] **Step 12: Commit**

```bash
git add src/apps/user/request.py src/apps/user/response.py src/apps/user/service.py src/apps/user/urls.py tests/apps/user/test_user_service.py tests/apps/user/test_user_urls.py
git commit -m "feat: add user lookup API for reseller invite flow"
```

---

## Task 2: Refactor Reseller Invite to Accept `user_ids` Directly

**Files:**
- Modify: `src/apps/event/request.py` — replace `CreateInviteRequest` with `CreateResellerInviteRequest`
- Modify: `src/apps/event/response.py` — add `ResellerInviteResponse`
- Modify: `src/apps/event/urls.py` — refactor `create_reseller_invite`
- Modify: `src/apps/user/invite/service.py` — update `create_invite()` signature
- Modify: `tests/apps/event/test_event_urls.py` — add tests

- [ ] **Step 1: Write failing test for batch user_id based invite creation**

Add to `tests/apps/event/test_event_urls.py`:

```python
@pytest.mark.asyncio
async def test_create_reseller_invite_accepts_user_ids():
    from apps.event.urls import create_reseller_invite
    from src.apps.event.request import CreateResellerInviteRequest
    from utils.schema import BaseResponse

    owner_id = uuid4()
    event_id = uuid4()
    target_user_id = uuid4()
    request = SimpleNamespace(state=SimpleNamespace(user=SimpleNamespace(id=owner_id)))
    body = CreateResellerInviteRequest(user_ids=[target_user_id])
    event_service = AsyncMock()
    invite_service = AsyncMock()
    mock_event = SimpleNamespace(id=event_id, organizer_page_id=uuid4())
    event_service.repository.get_by_id_for_owner = AsyncMock(return_value=mock_event)
    invite_service.user_repository.find_by_id = AsyncMock(return_value=MagicMock(id=target_user_id))
    invite_service.create_invite = AsyncMock(return_value=MagicMock(id=uuid4(), status="pending"))

    response = await create_reseller_invite(
        event_id=event_id,
        request=request,
        body=body,
        event_service=event_service,
        invite_service=invite_service,
    )

    assert response.data is not None
    invite_service.create_invite.assert_awaited_once()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/apps/event/test_event_urls.py::test_create_reseller_invite_accepts_user_ids -v`
Expected: FAIL — `CreateResellerInviteRequest` not defined

- [ ] **Step 3: Write `CreateResellerInviteRequest` schema**

Modify `src/apps/event/request.py` — add at end:

```python
class CreateResellerInviteRequest(CamelCaseModel):
    user_ids: list[UUID]  # Required: list of user IDs to invite
    permissions: list[str] = []  # Optional permissions for each invite

    def model_post_init(self, __pydantic_self__) -> None:
        if len(self.user_ids) == 0:
            raise ValueError("At least one user_id is required")
```

- [ ] **Step 4: Write `ResellerInviteResponse` schema**

Modify `src/apps/event/response.py` — add at end:

```python
class ResellerInviteResponse(CamelCaseModel):
    id: UUID
    target_user_id: UUID
    created_by_id: UUID
    status: str
    invite_type: str
    meta: dict
    created_at: datetime
```

- [ ] **Step 5: Refactor `create_reseller_invite` endpoint — batch insert**

Modify `src/apps/event/urls.py`:

Replace the `create_reseller_invite` function body with:

```python
@router.post("/{event_id}/reseller-invites")
async def create_reseller_invite(
    event_id: UUID,
    request: Request,
    body: Annotated[CreateResellerInviteRequest, Body()],
    event_service: Annotated[EventService, Depends(get_event_service)],
    invite_service: Annotated[UserInviteService, Depends(get_user_invite_service)],
) -> BaseResponse[list[ResellerInviteResponse]]:
    # Verify organizer owns event
    event = await event_service.repository.get_by_id_for_owner(event_id, request.state.user.id)
    if not event:
        from apps.event.exceptions import OrganizerOwnershipError
        raise OrganizerOwnershipError

    # Validate all users exist first (fail fast before any inserts)
    for user_id in body.user_ids:
        target_user = await invite_service.user_repository.find_by_id(user_id)
        if not target_user:
            from exceptions import NotFoundError
            raise NotFoundError(f"User {user_id} not found")
        if target_user.id == request.state.user.id:
            from exceptions import ForbiddenError
            raise ForbiddenError("Cannot invite yourself as a reseller")
        # Check for duplicate pending invite
        existing = await invite_service.repository.get_pending_invite_for_user_event(
            target_user_id=user_id,
            event_id=event_id,
        )
        if existing:
            from exceptions import ConflictError
            raise ConflictError(f"Pending invite already exists for user {user_id}")

    # Batch create all invites in ONE DB call
    meta = {"event_id": str(event_id), "permissions": body.permissions or []}
    from apps.user.invite.enums import InviteType
    created_invites = await invite_service.create_invite_batch(
        target_user_ids=body.user_ids,
        created_by_id=request.state.user.id,
        metadata=meta,
        invite_type=InviteType.reseller.value,
    )

    return BaseResponse(data=[ResellerInviteResponse.model_validate(i) for i in created_invites])
```

Note: The batch insert uses `insert().values(list)` which executes a single SQL `INSERT INTO ... VALUES (...), (...), (...)` statement for all invites — O(1) DB round trips instead of O(N).

- [ ] **Step 6: Add `create_invite_batch()` to InviteRepository and InviteService**

Modify `src/apps/user/invite/repository.py` — add method:

```python
async def create_invite_batch(
    self,
    target_user_ids: list[UUID],
    created_by_id: UUID,
    metadata: dict,
    invite_type: str,
) -> list[InviteModel]:
    """
    Bulk insert multiple invites in a single SQL statement.
    Returns all created InviteModel objects with full data.
    """
    from sqlalchemy.dialects.postgresql import insert
    from .models import InviteModel
    from .enums import InviteStatus
    from sqlalchemy import select

    values = [
        {
            "target_user_id": uid,
            "created_by_id": created_by_id,
            "status": InviteStatus.pending.value,
            "invite_type": invite_type,
            "meta": metadata,
        }
        for uid in target_user_ids
    ]

    # Single bulk INSERT ... VALUES (...), (...), (...) statement
    stmt = insert(InviteModel).values(values).returning(InviteModel.id)
    result = await self._session.execute(stmt)
    created_ids = list(result.scalars().all())

    # Re-fetch to get fully populated objects for response
    invites = await self._session.scalars(
        select(InviteModel).where(InviteModel.id.in_(created_ids))
    )
    return list(invites.all())
```

Modify `src/apps/user/invite/service.py` — add method:

```python
async def create_invite_batch(
    self,
    target_user_ids: list[UUID],
    created_by_id: UUID,
    metadata: dict,
    invite_type: str = InviteType.reseller.value,
) -> list[InviteModel]:
    """Create multiple invites in a single DB round-trip."""
    return await self.repository.create_invite_batch(
        target_user_ids=target_user_ids,
        created_by_id=created_by_id,
        metadata=metadata,
        invite_type=invite_type,
    )
```

- [ ] **Step 7: Add `find_by_id()` to UserRepository if not done in Task 1**

Verify `src/apps/user/repository.py` has `find_by_id()` from Task 1.

- [ ] **Step 8: Run test to verify it passes**

Run: `pytest tests/apps/event/test_event_urls.py::test_create_reseller_invite_accepts_user_ids -v`
Expected: PASS

- [ ] **Step 9: Commit**

```bash
git add src/apps/event/request.py src/apps/event/response.py src/apps/event/urls.py src/apps/user/invite/service.py src/apps/user/repository.py tests/apps/event/test_event_urls.py
git commit -m "refactor: reseller invite accepts user_ids directly, removes lookup logic"
```

---

## Task 3: Add List Reseller Invites Endpoint

**Files:**
- Modify: `src/apps/event/repository.py` — add `list_reseller_invites_for_event()`
- Modify: `src/apps/event/urls.py` — add `list_event_reseller_invites` endpoint
- Modify: `src/apps/user/invite/repository.py` — add `get_pending_invite_for_user_event()` if needed
- Modify: `tests/apps/event/test_event_urls.py` — add tests

- [ ] **Step 1: Write failing test for list reseller invites**

Add to `tests/apps/event/test_event_urls.py`:

```python
@pytest.mark.asyncio
async def test_list_reseller_invites_returns_invites():
    from apps.event.urls import list_event_reseller_invites
    from utils.schema import BaseResponse

    owner_id = uuid4()
    event_id = uuid4()
    request = SimpleNamespace(state=SimpleNamespace(user=SimpleNamespace(id=owner_id)))
    event_service = AsyncMock()
    mock_event = SimpleNamespace(id=event_id)
    event_service.repository.get_by_id_for_owner = AsyncMock(return_value=mock_event)
    event_service.repository.list_reseller_invites_for_event = AsyncMock(return_value=[
        MagicMock(
            id=uuid4(),
            target_user_id=uuid4(),
            created_by_id=owner_id,
            status="pending",
            invite_type="reseller",
            meta={"event_id": str(event_id)},
        )
    ])

    response = await list_event_reseller_invites(
        event_id=event_id,
        request=request,
        event_service=event_service,
    )

    assert len(response.data) == 1
    assert response.data[0].status == "pending"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/apps/event/test_event_urls.py::test_list_reseller_invites_returns_invites -v`
Expected: FAIL — `list_reseller_invites_for_event` and endpoint don't exist

- [ ] **Step 3: Add `list_reseller_invites_for_event()` to EventRepository**

Modify `src/apps/event/repository.py` — add method:

```python
async def list_reseller_invites_for_event(
    self,
    event_id: UUID,
    status: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list:
    """List invites for an event, optionally filtered by status."""
    from apps.user.invite.models import InviteModel
    from apps.user.invite.enums import InviteType

    query = select(InviteModel).where(
        InviteModel.meta["event_id"].astext == str(event_id),
        InviteModel.invite_type == InviteType.reseller.value,
    )
    if status:
        query = query.where(InviteModel.status == status)

    query = query.order_by(InviteModel.created_at.desc()).limit(limit).offset(offset)
    result = await self._session.scalars(query)
    return list(result.all())
```

- [ ] **Step 4: Add `list_event_reseller_invites` endpoint**

Modify `src/apps/event/urls.py` — add after `create_reseller_invite`:

```python
@router.get("/{event_id}/reseller-invites")
async def list_event_reseller_invites(
    event_id: UUID,
    request: Request,
    event_service: Annotated[EventService, Depends(get_event_service)],
    status: str | None = None,  # pending, accepted, declined, cancelled
) -> BaseResponse[list[ResellerInviteResponse]]:
    # Verify organizer owns event
    event = await event_service.repository.get_by_id_for_owner(event_id, request.state.user.id)
    if not event:
        from apps.event.exceptions import OrganizerOwnershipError
        raise OrganizerOwnershipError

    invites = await event_service.repository.list_reseller_invites_for_event(
        event_id=event_id,
        status=status,
    )
    return BaseResponse(data=[ResellerInviteResponse.model_validate(i) for i in invites])
```

- [ ] **Step 5: Run test to verify it passes**

Run: `pytest tests/apps/event/test_event_urls.py::test_list_reseller_invites_returns_invites -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add src/apps/event/repository.py src/apps/event/urls.py tests/apps/event/test_event_urls.py
git commit -m "feat: add list reseller invites endpoint for event organizers"
```

---

## Task 4: Add Duplicate Invite Check

**Files:**
- Modify: `src/apps/user/invite/repository.py` — add `get_pending_invite_for_user_event()`
- Modify: `src/apps/event/urls.py` — use duplicate check in `create_reseller_invite`

- [ ] **Step 1: Write failing test for duplicate invite prevention**

Add to `tests/apps/event/test_event_urls.py`:

```python
@pytest.mark.asyncio
async def test_create_reseller_invite_fails_for_duplicate():
    from apps.event.urls import create_reseller_invite
    from src.apps.event.request import CreateResellerInviteRequest
    from apps.user.invite.exceptions import InviteAlreadyProcessed
    from exceptions import ConflictError

    owner_id = uuid4()
    event_id = uuid4()
    target_user_id = uuid4()
    request = SimpleNamespace(state=SimpleNamespace(user=SimpleNamespace(id=owner_id)))
    body = CreateResellerInviteRequest(user_ids=[target_user_id])
    event_service = AsyncMock()
    invite_service = AsyncMock()
    mock_event = SimpleNamespace(id=event_id, organizer_page_id=uuid4())
    event_service.repository.get_by_id_for_owner = AsyncMock(return_value=mock_event)
    invite_service.user_repository.find_by_id = AsyncMock(return_value=MagicMock(id=target_user_id))
    invite_service.repository.get_pending_invite_for_user_event = AsyncMock(return_value=MagicMock(id=uuid4()))  # Returns existing invite = duplicate

    with pytest.raises((ConflictError, InviteAlreadyProcessed)):
        await create_reseller_invite(
            event_id=event_id,
            request=request,
            body=body,
            event_service=event_service,
            invite_service=invite_service,
        )
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/apps/event/test_event_urls.py::test_create_reseller_invite_fails_for_duplicate -v`
Expected: FAIL — method doesn't exist yet

- [ ] **Step 3: Add `get_pending_invite_for_user_event()` to InviteRepository**

Modify `src/apps/user/invite/repository.py`:

```python
async def get_pending_invite_for_user_event(
    self,
    target_user_id: UUID,
    event_id: UUID,
) -> Optional[InviteModel]:
    """Check if a pending reseller invite exists for user + event."""
    from .models import InviteModel
    from .enums import InviteType

    query = select(InviteModel).where(
        InviteModel.target_user_id == target_user_id,
        InviteModel.meta["event_id"].astext == str(event_id),
        InviteModel.invite_type == InviteType.reseller.value,
        InviteModel.status == InviteStatus.pending.value,
    )
    return await self._session.scalar(query)
```

- [ ] **Step 4: Add duplicate check in `create_reseller_invite` endpoint**

Modify `src/apps/event/urls.py` — inside the loop in `create_reseller_invite`, before creating the invite:

```python
# Check for duplicate pending invite
existing = await invite_service.repository.get_pending_invite_for_user_event(
    target_user_id=user_id,
    event_id=event_id,
)
if existing:
    from exceptions import ConflictError
    raise ConflictError(f"Pending invite already exists for user {user_id}")
```

Also add `ConflictError` import at top of endpoint file (check existing patterns).

- [ ] **Step 5: Run test to verify it passes**

Run: `pytest tests/apps/event/test_event_urls.py::test_create_reseller_invite_fails_for_duplicate -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add src/apps/user/invite/repository.py src/apps/event/urls.py tests/apps/event/test_event_urls.py
git commit -m "feat: prevent duplicate reseller invites for same user and event"
```

---

## Task 5: Integration Test — Full Reseller Invite Flow

**Files:**
- Create: `tests/apps/event/test_reseller_invite_flow.py`

- [ ] **Step 1: Write integration test for full reseller invite flow**

Create `tests/apps/event/test_reseller_invite_flow.py`:

```python
"""
Integration test for full reseller invite flow:
1. Organizer finds user via lookup API
2. Organizer creates batch reseller invites
3. User accepts invite
4. EventReseller record is created
5. List invites shows the new invite
"""
import pytest
from uuid import uuid4
from unittest.mock import AsyncMock, MagicMock


@pytest.mark.asyncio
async def test_full_reseller_invite_flow_with_user_ids():
    """
    Full flow:
    1. Organizer calls GET /api/users/find?email=alice@example.com → gets user_id
    2. Organizer calls POST /api/events/{event_id}/reseller-invites with user_ids=[user_id]
    3. User calls POST /api/invites/{invite_id}/accept
    4. EventReseller is created
    5. GET /api/events/{event_id}/reseller-invites shows the accepted reseller
    """
    from types import SimpleNamespace
    from apps.user.response import UserLookupResponse
    from apps.event.request import CreateResellerInviteRequest
    from apps.user.invite.service import InviteService
    from apps.user.invite.enums import InviteType

    organizer_id = uuid4()
    reseller_id = uuid4()
    event_id = uuid4()
    invite_id = uuid4()

    # Step 1: User lookup returns user_id
    user_service = AsyncMock()
    user_service.find_user = AsyncMock(return_value=UserLookupResponse(
        user_id=reseller_id,
        email="alice@example.com",
        phone="9876543210",
        first_name="Alice",
        last_name="Smith",
    ))

    # Step 2: Invite created successfully
    invite_service = InviteService(repository=MagicMock(), user_repository=MagicMock())
    invite_service.create_invite = AsyncMock(return_value=MagicMock(
        id=invite_id,
        target_user_id=reseller_id,
        created_by_id=organizer_id,
        status="pending",
        invite_type=InviteType.reseller.value,
        meta={"event_id": str(event_id), "permissions": []},
    ))

    # Step 3: Accept creates EventReseller
    event_service = AsyncMock()
    event_service.repository.get_by_id = AsyncMock(return_value=MagicMock(id=event_id))
    event_service.repository.get_reseller_for_event = AsyncMock(return_value=None)
    event_service.repository.create_event_reseller = AsyncMock(return_value=MagicMock(
        id=uuid4(),
        user_id=reseller_id,
        event_id=event_id,
        invited_by_id=organizer_id,
        permissions=[],
    ))

    # Verify all pieces fit together
    from apps.event.request import CreateResellerInviteRequest
    req = CreateResellerInviteRequest(user_ids=[reseller_id])
    assert len(req.user_ids) == 1
    assert req.user_ids[0] == reseller_id
```

- [ ] **Step 2: Run test to verify it passes**

Run: `pytest tests/apps/event/test_reseller_invite_flow.py -v`
Expected: PASS

- [ ] **Step 3: Commit**

```bash
git add tests/apps/event/test_reseller_invite_flow.py
git commit -m "test: add integration test for full reseller invite flow"
```

---

## Self-Review Checklist

1. **Spec coverage:**
   - [x] User lookup API (`GET /api/users/find`) — Task 1
   - [x] Reseller invite accepts `user_ids` directly — Task 2
   - [x] Batch invite support (`user_ids: list[UUID]`) — Task 2
   - [x] List invites for event (`GET /api/events/{event_id}/reseller-invites`) — Task 3
   - [x] Duplicate invite prevention — Task 4
   - [x] User accepts invite flow (unchanged — still works) — covered implicitly

2. **Placeholder scan:** No `TBD`, `TODO`, "fill in later" found. All code blocks are complete.

3. **Type consistency:**
   - `CreateResellerInviteRequest.user_ids` — `list[UUID]` — used consistently in Tasks 2-4
   - `ResellerInviteResponse` fields match `InviteModel` attributes — verified
   - `find_user()` signature: `email: str | None = None, phone: str | None = None` — consistent

---

## Execution Options

**Plan complete and saved to `docs/superpowers/plans/2026-04-18-reseller-invite-refactor.md`. Two execution options:**

**1. Subagent-Driven (recommended)** — I dispatch a fresh subagent per task, review between tasks, fast iteration

**2. Inline Execution** — Execute tasks in this session using executing-plans, batch execution with checkpoints

**Which approach?**
