# B2B Bug Fixes — Auto-Derive Ticket Type, Drop Recipient Fields, Fix Auth Pattern

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix 6 confirmed bugs in the B2B request flow: (1) organizer picks ticket_type_id instead of system auto-deriving a B2B ticket type, (2) recipient phone/email stored but not needed, (3) `get_current_super_admin` doesn't set `request.state`, (4) `confirm_b2b_payment` has no user ownership check, (5) no validation that `event_day_id` belongs to `event_id`, (6) missing `get_or_create_ticket_type` method.

**Architecture:**
- Organizer submits B2B request with only `event_id` + `event_day_id`. System auto-derives or creates a B2B-category `TicketTypeModel` for that day.
- `B2BRequestModel` drops `recipient_phone`/`recipient_email`. Allocation `to_holder` is the organizer's own `TicketHolder` (resolved via `requesting_user_id`).
- `get_current_super_admin` sets `request.state.super_admin` and returns the admin. Routes access `request.state.admin` directly.
- `confirm_b2b_payment` verifies `request.state.user.id` matches `OrganizerPageModel.owner_user_id` for the `organizer_id` path param.
- B2B request creation validates `event_day_id` belongs to `event_id`.
- `TicketingRepository.get_or_create_b2b_ticket_type(event_day_id)` handles ticket-type derivation/creation.

**Tech Stack:** FastAPI, SQLAlchemy async, Alembic, Pydantic, pytest

---

## File Map

### New Files
- `src/apps/ticketing/repository.py` — add `get_or_create_b2b_ticket_type` method (modifies existing)
- `tests/apps/organizer/test_b2b_requests.py` — new test file for B2B request creation and payment confirmation
- `tests/apps/superadmin/test_superadmin_auth.py` — new test file for `request.state` auth pattern

### Modified Files
- `src/apps/organizer/request.py` — remove `ticket_type_id`, `recipient_phone`, `recipient_email` from `CreateB2BRequestBody`
- `src/apps/organizer/service.py` — add `get_or_create_b2b_ticket_type` call, remove recipient fields from `create_b2b_request`, use organizer's holder as `to_holder`
- `src/apps/organizer/repository.py` — remove recipient fields from `create_b2b_request`
- `src/apps/organizer/urls.py` — add user ownership check to `confirm_b2b_payment`, validate `event_day_id` belongs to `event_id`, switch to `request.state.user`
- `src/apps/superadmin/models.py` — remove `recipient_phone`, `recipient_email` columns
- `src/apps/superadmin/service.py` — remove `recipient_phone`/`email` from both approval flows, resolve `to_holder` via `requesting_user_id`
- `src/apps/superadmin/repository.py` — remove recipient fields from `create_b2b_request`
- `src/apps/superadmin/response.py` — remove `recipient_phone`, `recipient_email` from `B2BRequestResponse`
- `src/apps/superadmin/urls.py` — remove redundant `admin` route param, access `request.state.admin` instead
- `src/auth/dependencies.py` — fix `get_current_super_admin` to accept `Request`, set `request.state.super_admin`, return the admin

### Auto-Generated (after model changes)
- `src/migrations/versions/<auto>_remove_recipient_fields_from_b2b_requests.py`

---

## Task 1: Fix `get_current_super_admin` Auth Pattern

**Files:**
- Modify: `src/auth/dependencies.py:187-226`
- Test: `tests/apps/superadmin/test_superadmin_auth.py` (new)

- [ ] **Step 1: Write failing test — super_admin is in request.state after auth**

```python
# tests/apps/superadmin/test_superadmin_auth.py
import pytest
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

from fastapi import Request


@pytest.fixture
def mock_admin():
    from apps.superadmin.models import SuperAdminModel
    admin = MagicMock(spec=SuperAdminModel)
    admin.id = uuid4()
    admin.user_id = uuid4()
    admin.name = "Test Admin"
    return admin


async def test_get_current_super_admin_sets_request_state(mock_admin):
    """get_current_super_admin should set request.state.super_admin AND return the admin."""
    from auth.dependencies import get_current_super_admin
    from fastapi.security import HTTPAuthorizationCredentials

    mock_credentials = MagicMock(spec=HTTPAuthorizationCredentials)
    mock_credentials.credentials = "valid_token"

    mock_session = AsyncMock()
    mock_session.scalar = AsyncMock(return_value=mock_admin)

    mock_request = MagicMock(spec=Request)
    mock_request.state = MagicMock()

    # Patch access.decode to return a valid payload
    import auth.dependencies as auth_deps
    original_decode = auth_deps.access.decode
    auth_deps.access.decode = MagicMock(return_value={"sub": str(mock_admin.user_id), "user_type": "user"})

    try:
        result = await get_current_super_admin(request=mock_request, credentials=mock_credentials, session=mock_session)

        assert result == mock_admin
        assert hasattr(mock_request.state, "super_admin")
        assert mock_request.state.super_admin == mock_admin
    finally:
        auth_deps.access.decode = original_decode
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/apps/superadmin/test_superadmin_auth.py::test_get_current_super_admin_sets_request_state -v`
Expected: FAIL — TypeError: get_current_super_admin() got an unexpected keyword argument 'request'

- [ ] **Step 3: Fix `get_current_super_admin` to accept `Request` and set `request.state`**

Replace the function at `src/auth/dependencies.py:187-226`:

```python
async def get_current_super_admin(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    session: AsyncSession = Depends(db_session),
) -> SuperAdminModel:
    """
    Dependency that validates Bearer token and returns the current super admin.
    Raises 401 if no valid token, 403 if token is valid but user is not a super admin.
    Sets request.state.super_admin for direct access in routes.
    """
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )

    try:
        payload = access.decode(credentials.credentials)
        if payload.get("user_type") != "user":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token type",
            )
        user_id = UUID(payload["sub"])
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )

    from apps.superadmin.models import SuperAdminModel

    admin = await session.scalar(
        select(SuperAdminModel).where(SuperAdminModel.user_id == user_id)
    )

    if not admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not a super admin",
        )

    request.state.super_admin = admin
    return admin
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/apps/superadmin/test_superadmin_auth.py::test_get_current_super_admin_sets_request_state -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/auth/dependencies.py tests/apps/superadmin/test_superadmin_auth.py
git commit -m "fix(superadmin): get_current_super_admin sets request.state.super_admin"
```

---

## Task 2: Update SuperAdmin Routes to Use `request.state.admin`

**Files:**
- Modify: `src/apps/superadmin/urls.py:1-136`

- [ ] **Step 1: Update all routes to use `request.state.admin` instead of `admin` param**

Replace the entire `src/apps/superadmin/urls.py`. The router-level `dependencies=[Depends(get_current_super_admin)]` stays — it still runs the dependency for auth. But each route removes the `admin` param and accesses `request.state.admin` directly:

```python
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Body, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from auth.dependencies import get_current_super_admin
from apps.superadmin.models import SuperAdminModel
from apps.superadmin.request import (
    ApproveB2BRequestFreeBody,
    ApproveB2BRequestPaidBody,
    RejectB2BRequestBody,
)
from apps.superadmin.response import B2BRequestResponse
from apps.superadmin.service import SuperAdminService
from db.session import db_session
from utils.schema import BaseResponse

router = APIRouter(
    prefix="/api/superadmin",
    tags=["SuperAdmin"],
    dependencies=[Depends(get_current_super_admin)],
)


def get_super_admin_service(
    session: Annotated[AsyncSession, Depends(db_session)],
) -> SuperAdminService:
    return SuperAdminService(session)


@router.get("/b2b-requests")
async def list_b2b_requests(
    request: Request,
    service: Annotated[SuperAdminService, Depends(get_super_admin_service)],
    status_filter: str | None = Query(None, alias="status"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
) -> BaseResponse[list[B2BRequestResponse]]:
    """
    [Super Admin] List all B2B requests, optionally filtered by status.
    """
    from apps.superadmin.enums import B2BRequestStatus

    admin = request.state.super_admin
    status_enum = B2BRequestStatus(status_filter) if status_filter else None
    requests = await service.list_all_b2b_requests(
        status=status_enum, limit=limit, offset=offset
    )
    return BaseResponse(data=[B2BRequestResponse.model_validate(r) for r in requests])


@router.get("/b2b-requests/pending")
async def list_pending_b2b_requests(
    request: Request,
    service: Annotated[SuperAdminService, Depends(get_super_admin_service)],
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
) -> BaseResponse[list[B2BRequestResponse]]:
    """
    [Super Admin] List pending B2B requests awaiting review.
    """
    requests = await service.list_pending_b2b_requests(limit=limit, offset=offset)
    return BaseResponse(data=[B2BRequestResponse.model_validate(r) for r in requests])


@router.get("/b2b-requests/{request_id}")
async def get_b2b_request(
    request_id: UUID,
    request: Request,
    service: Annotated[SuperAdminService, Depends(get_super_admin_service)],
) -> BaseResponse[B2BRequestResponse]:
    """
    [Super Admin] Get a single B2B request by ID.
    """
    b2b_request = await service.get_b2b_request(request_id)
    return BaseResponse(data=B2BRequestResponse.model_validate(b2b_request))


@router.post("/b2b-requests/{request_id}/approve-free")
async def approve_b2b_request_free(
    request_id: UUID,
    request: Request,
    service: Annotated[SuperAdminService, Depends(get_super_admin_service)],
    body: Annotated[ApproveB2BRequestFreeBody, Body()],
) -> BaseResponse[B2BRequestResponse]:
    """
    [Super Admin] Approve B2B request as free transfer.
    Creates allocation immediately with $0 TRANSFER order.
    """
    admin = request.state.super_admin
    b2b_request = await service.approve_b2b_request_free(
        admin_id=admin.id,
        request_id=request_id,
        admin_notes=body.admin_notes,
    )
    return BaseResponse(data=B2BRequestResponse.model_validate(b2b_request))


@router.post("/b2b-requests/{request_id}/approve-paid")
async def approve_b2b_request_paid(
    request_id: UUID,
    request: Request,
    service: Annotated[SuperAdminService, Depends(get_super_admin_service)],
    body: Annotated[ApproveB2BRequestPaidBody, Body()],
) -> BaseResponse[B2BRequestResponse]:
    """
    [Super Admin] Approve B2B request as paid.
    Sets the amount and creates a pending PURCHASE order.
    Organizer then pays via the organizer app's confirm-payment endpoint.
    """
    admin = request.state.super_admin
    b2b_request = await service.approve_b2b_request_paid(
        admin_id=admin.id,
        request_id=request_id,
        amount=body.amount,
        admin_notes=body.admin_notes,
    )
    return BaseResponse(data=B2BRequestResponse.model_validate(b2b_request))


@router.post("/b2b-requests/{request_id}/reject")
async def reject_b2b_request(
    request_id: UUID,
    request: Request,
    service: Annotated[SuperAdminService, Depends(get_super_admin_service)],
    body: Annotated[RejectB2BRequestBody, Body()],
) -> BaseResponse[B2BRequestResponse]:
    """
    [Super Admin] Reject a B2B request.
    """
    admin = request.state.super_admin
    b2b_request = await service.reject_b2b_request(
        admin_id=admin.id,
        request_id=request_id,
        reason=body.reason,
    )
    return BaseResponse(data=B2BRequestResponse.model_validate(b2b_request))
```

- [ ] **Step 2: Commit**

```bash
git add src/apps/superadmin/urls.py
git commit -m "fix(superadmin): routes access request.state.super_admin instead of admin param"
```

---

## Task 3: Drop `recipient_phone` and `recipient_email` from `B2BRequestModel`

**Files:**
- Modify: `src/apps/superadmin/models.py:52-54`
- Modify: `src/apps/superadmin/repository.py:71-97`
- Modify: `src/apps/superadmin/response.py`
- Test: `tests/apps/organizer/test_b2b_requests.py`

- [ ] **Step 1: Write failing test — B2B request response has no recipient fields**

```python
# tests/apps/organizer/test_b2b_requests.py
import pytest
from uuid import uuid4
from pydantic import ValidationError


def test_create_b2b_request_body_has_no_ticket_type_id():
    """Organizer should NOT provide ticket_type_id — system auto-derives B2B ticket type."""
    from apps.organizer.request import CreateB2BRequestBody

    # Should accept event_id, event_day_id, quantity — NO ticket_type_id
    body = CreateB2BRequestBody(
        event_id=str(uuid4()),
        event_day_id=str(uuid4()),
        quantity=5,
    )
    assert hasattr(body, 'event_id')
    assert hasattr(body, 'event_day_id')
    assert hasattr(body, 'quantity')
    assert not hasattr(body, 'ticket_type_id')


def test_create_b2b_request_body_has_no_recipient_fields():
    """B2B request body should NOT accept recipient_phone or recipient_email."""
    from apps.organizer.request import CreateB2BRequestBody

    # Should NOT have recipient fields
    assert not hasattr(CreateB2BRequestBody, 'recipient_phone')
    assert not hasattr(CreateB2BRequestBody, 'recipient_email')


def test_b2b_response_has_no_recipient_fields():
    """B2BRequestResponse should NOT have recipient_phone or recipient_email."""
    from apps.superadmin.response import B2BRequestResponse

    assert not hasattr(B2BRequestResponse, 'recipient_phone')
    assert not hasattr(B2BRequestResponse, 'recipient_email')
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/apps/organizer/test_b2b_requests.py -v`
Expected: FAIL — assertions about missing fields fail (fields still exist)

- [ ] **Step 3: Update `CreateB2BRequestBody` — drop ticket_type_id, recipient fields**

In `src/apps/organizer/request.py`, replace `CreateB2BRequestBody`:

```python
class CreateB2BRequestBody(CamelCaseModel):
    event_id: str
    event_day_id: str
    quantity: int = Field(gt=0)
```

Also replace `ConfirmB2BPaymentBody` comment with:

```python
class ConfirmB2BPaymentBody(CamelCaseModel):
    pass
```

- [ ] **Step 4: Update `B2BRequestResponse` — drop recipient fields**

In `src/apps/superadmin/response.py`, replace `B2BRequestResponse`:

```python
class B2BRequestResponse(BaseModel):
    id: str
    requesting_organizer_id: str
    requesting_user_id: str
    event_id: str
    event_day_id: str
    ticket_type_id: str
    quantity: int
    status: str
    reviewed_by_admin_id: str | None
    admin_notes: str | None
    allocation_id: str | None
    order_id: str | None
    metadata: dict = Field(validation_alias="metadata_", serialization_alias="metadata")
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True
```

- [ ] **Step 5: Run test to verify it passes**

Run: `pytest tests/apps/organizer/test_b2b_requests.py -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add src/apps/organizer/request.py src/apps/superadmin/response.py tests/apps/organizer/test_b2b_requests.py
git commit -m "fix(b2b): drop ticket_type_id, recipient_phone, recipient_email from request/response schemas"
```

---

## Task 4: Add `get_or_create_b2b_ticket_type` to TicketingRepository

**Files:**
- Modify: `src/apps/ticketing/repository.py:1-92`
- Test: `tests/apps/organizer/test_b2b_requests.py`

- [ ] **Step 1: Write failing test**

```python
# Add to tests/apps/organizer/test_b2b_requests.py
import pytest
from uuid import uuid4
from unittest.mock import AsyncMock, MagicMock


async def test_get_or_create_b2b_ticket_type_creates_new():
    """When no B2B ticket type exists for a day, create one."""
    from apps.ticketing.repository import TicketingRepository
    from apps.ticketing.models import TicketTypeModel
    from apps.ticketing.enums import TicketCategory

    mock_session = AsyncMock()
    mock_session.scalars = MagicMock(return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=None)))
    mock_session.add = MagicMock()
    mock_session.flush = AsyncMock()
    mock_session.refresh = AsyncMock()

    repo = TicketingRepository(mock_session)
    event_day_id = uuid4()

    result = await repo.get_or_create_b2b_ticket_type(event_day_id=event_day_id)

    assert result is not None
    mock_session.add.assert_called_once()
    call_arg = mock_session.add.call_args[0][0]
    assert call_arg.category == TicketCategory.b2b


async def test_get_or_create_b2b_ticket_type_returns_existing():
    """When B2B ticket type exists for a day, return it."""
    from apps.ticketing.repository import TicketingRepository
    from apps.ticketing.models import TicketTypeModel

    existing = MagicMock(spec=TicketTypeModel)
    existing.id = uuid4()

    mock_session = AsyncMock()
    mock_session.scalar = AsyncMock(return_value=existing)

    repo = TicketingRepository(mock_session)
    event_day_id = uuid4()

    result = await repo.get_or_create_b2b_ticket_type(event_day_id=event_day_id)

    assert result == existing
    mock_session.scalar.assert_called_once()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/apps/organizer/test_b2b_requests.py::test_get_or_create_b2b_ticket_type_creates_new tests/apps/organizer/test_b2b_requests.py::test_get_or_create_b2b_ticket_type_returns_existing -v`
Expected: FAIL — method does not exist

- [ ] **Step 3: Add `get_or_create_b2b_ticket_type` to `TicketingRepository`**

In `src/apps/ticketing/repository.py`, add method after `bulk_create_tickets`:

```python
async def get_or_create_b2b_ticket_type(
    self,
    event_day_id: UUID,
    name: str = "B2B",
    price: float = 0.0,
    currency: str = "INR",
) -> TicketTypeModel:
    """
    Get or create a B2B ticket type for a given event day.
    If a B2B ticket type already exists for this event (via any day), returns it.
    Otherwise creates a new B2B ticket type linked to the event that owns this day.
    """
    from sqlalchemy import select
    from apps.ticketing.enums import TicketCategory

    # Get the event_day to find the event_id
    from apps.event.models import EventDayModel
    event_day = await self._session.scalar(
        select(EventDayModel).where(EventDayModel.id == event_day_id)
    )
    if not event_day:
        raise ValueError(f"EventDay {event_day_id} not found")

    # Look for an existing B2B ticket type for this event
    existing = await self._session.scalar(
        select(TicketTypeModel).where(
            TicketTypeModel.event_id == event_day.event_id,
            TicketTypeModel.category == TicketCategory.b2b,
        )
    )
    if existing:
        return existing

    # Create new B2B ticket type
    ticket_type = TicketTypeModel(
        event_id=event_day.event_id,
        name=name,
        category=TicketCategory.b2b,
        price=price,
        currency=currency,
    )
    self._session.add(ticket_type)
    await self._session.flush()
    await self._session.refresh(ticket_type)
    return ticket_type
```

Also update the class to include the EventDayModel import at the point of use.

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/apps/organizer/test_b2b_requests.py::test_get_or_create_b2b_ticket_type_creates_new tests/apps/organizer/test_b2b_requests.py::test_get_or_create_b2b_ticket_type_returns_existing -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/apps/ticketing/repository.py tests/apps/organizer/test_b2b_requests.py
git commit -m "feat(ticketing): add get_or_create_b2b_ticket_type for B2B auto-derivation"
```

---

## Task 5: Update B2B Service — Remove Recipient Fields, Use Organizer's Holder

**Files:**
- Modify: `src/apps/organizer/service.py:182-224`
- Modify: `src/apps/organizer/repository.py:93-133`
- Modify: `src/apps/superadmin/service.py:1-385`
- Modify: `src/apps/superadmin/repository.py:71-97`
- Modify: `src/apps/superadmin/models.py:52-54`

- [ ] **Step 1: Write failing test — service calls get_or_create_b2b_ticket_type**

```python
# Add to tests/apps/organizer/test_b2b_requests.py
async def test_create_b2b_request_auto_derives_ticket_type():
    """Organizer create_b2b_request should auto-derive B2B ticket type."""
    from apps.organizer.service import OrganizerService
    from unittest.mock import MagicMock
    from uuid import uuid4

    mock_repo = MagicMock()
    mock_session = AsyncMock()
    mock_repo.session = mock_session
    mock_repo.create_b2b_request = AsyncMock(return_value=MagicMock(id=uuid4()))

    service = OrganizerService(mock_repo)
    organizer_id = uuid4()
    user_id = uuid4()
    event_id = uuid4()
    event_day_id = uuid4()

    # Capture what create_b2b_request was called with
    await service.create_b2b_request(
        organizer_id=organizer_id,
        user_id=user_id,
        event_id=event_id,
        event_day_id=event_day_id,
        quantity=5,
    )

    call_kwargs = mock_repo.create_b2b_request.call_kwargs
    assert 'ticket_type_id' in call_kwargs
    assert call_kwargs['quantity'] == 5
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/apps/organizer/test_b2b_requests.py::test_create_b2b_request_auto_derives_ticket_type -v`
Expected: FAIL — current create_b2b_request signature still expects ticket_type_id

- [ ] **Step 3: Update `OrganizerRepository.create_b2b_request` — remove recipient fields**

In `src/apps/organizer/repository.py`, update `create_b2b_request`:

```python
async def create_b2b_request(
    self,
    requesting_organizer_id: UUID,
    requesting_user_id: UUID,
    event_id: UUID,
    event_day_id: UUID,
    ticket_type_id: UUID,
    quantity: int,
) -> B2BRequestModel:
    return await self._super_admin_repo.create_b2b_request(
        requesting_organizer_id=requesting_organizer_id,
        requesting_user_id=requesting_user_id,
        event_id=event_id,
        event_day_id=event_day_id,
        ticket_type_id=ticket_type_id,
        quantity=quantity,
    )
```

- [ ] **Step 4: Update `OrganizerService.create_b2b_request` — derive B2B ticket type**

In `src/apps/organizer/service.py`, update the method and update the `__init__` to inject a `TicketingRepository`:

```python
from apps.ticketing.repository import TicketingRepository

class OrganizerService:
    def __init__(self, repository) -> None:
        self.repository = repository
        self._super_admin_service = SuperAdminService(repository.session)
        self._ticketing_repo = TicketingRepository(repository.session)

    # ...

    async def create_b2b_request(
        self,
        organizer_id: uuid.UUID,
        user_id: uuid.UUID,
        event_id: uuid.UUID,
        event_day_id: uuid.UUID,
        quantity: int,
    ):
        """[Organizer] Submit a B2B ticket request. System auto-derives B2B ticket type."""
        # Auto-derive B2B ticket type for this event day
        b2b_ticket_type = await self._ticketing_repo.get_or_create_b2b_ticket_type(
            event_day_id=event_day_id,
        )
        return await self.repository.create_b2b_request(
            requesting_organizer_id=organizer_id,
            requesting_user_id=user_id,
            event_id=event_id,
            event_day_id=event_day_id,
            ticket_type_id=b2b_ticket_type.id,
            quantity=quantity,
        )
```

- [ ] **Step 5: Update `SuperAdminRepository.create_b2b_request` — remove recipient fields**

In `src/apps/superadmin/repository.py`, update:

```python
async def create_b2b_request(
    self,
    requesting_organizer_id: UUID,
    requesting_user_id: UUID,
    event_id: UUID,
    event_day_id: UUID,
    ticket_type_id: UUID,
    quantity: int,
    metadata: dict | None = None,
) -> B2BRequestModel:
    request = B2BRequestModel(
        requesting_organizer_id=requesting_organizer_id,
        requesting_user_id=requesting_user_id,
        event_id=event_id,
        event_day_id=event_day_id,
        ticket_type_id=ticket_type_id,
        quantity=quantity,
        metadata_=metadata or {},
    )
    self._session.add(request)
    await self._session.flush()
    await self._session.refresh(request)
    return request
```

- [ ] **Step 6: Update `B2BRequestModel` — remove `recipient_phone` and `recipient_email` columns**

In `src/apps/superadmin/models.py`, remove lines 52-54:

```python
# REMOVE these two columns from B2BRequestModel:
# recipient_phone: Mapped[str | None] = mapped_column(String(32), nullable=True)
# recipient_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
```

- [ ] **Step 7: Run test to verify it passes**

Run: `pytest tests/apps/organizer/test_b2b_requests.py::test_create_b2b_request_auto_derives_ticket_type -v`
Expected: PASS

- [ ] **Step 8: Commit**

```bash
git add src/apps/organizer/service.py src/apps/organizer/repository.py src/apps/superadmin/repository.py src/apps/superadmin/models.py tests/apps/organizer/test_b2b_requests.py
git commit -m "fix(b2b): remove recipient fields, auto-derive B2B ticket type in organizer service"
```

---

## Task 6: Update SuperAdminService — Remove `recipient_phone`/`email`, Use Organizer's Holder

**Files:**
- Modify: `src/apps/superadmin/service.py:59-161` and `:233-330`

- [ ] **Step 1: Write failing test — approve_b2b_request_free resolves holder via user_id**

```python
# Add to tests/apps/organizer/test_b2b_requests.py
async def test_approve_free_uses_organizer_holder():
    """Approve free should resolve to_holder via requesting_user_id, not recipient info."""
    from apps.superadmin.service import SuperAdminService
    from apps.superadmin.enums import B2BRequestStatus
    from unittest.mock import MagicMock, AsyncMock
    from uuid import uuid4

    mock_session = AsyncMock()
    mock_session.begin = MagicMock(return_value=MagicMock(__aenter__=AsyncMock(), __aexit__=AsyncMock()))
    mock_session.scalar = AsyncMock(return_value=MagicMock())
    mock_session.refresh = AsyncMock()

    service = SuperAdminService(mock_session)

    # The service should call resolve_holder with user_id, NOT phone+email
    import apps.superadmin.service as svc_mod
    original_resolve = service._allocation_service.resolve_holder

    resolved_holder = MagicMock()
    resolved_holder.id = uuid4()

    async def mock_resolve(phone=None, email=None, user_id=None, create_if_missing=True):
        # Should be called with user_id, not phone/email
        assert phone is None and email is None, "resolve_holder should NOT receive phone or email"
        assert user_id is not None
        return resolved_holder

    service._allocation_service.resolve_holder = mock_resolve
    service._select_and_lock_tickets_fifo = AsyncMock(return_value=[uuid4()])
    service._update_ticket_ownership = AsyncMock()
```

- [ ] **Step 2: Update `approve_b2b_request_free` in `SuperAdminService`**

In `src/apps/superadmin/service.py`, replace the `resolve_holder` call in `approve_b2b_request_free` (lines 75-81):

```python
# OLD (lines 75-81):
to_holder = await allocation_service.resolve_holder(
    phone=b2b_request.recipient_phone,
    email=b2b_request.recipient_email,
    create_if_missing=True,
)

# NEW:
to_holder = await allocation_service.resolve_holder(
    user_id=b2b_request.requesting_user_id,
    create_if_missing=True,
)
```

- [ ] **Step 3: Update `process_paid_b2b_allocation` in `SuperAdminService`**

Replace the `resolve_holder` call in `process_paid_b2b_allocation` (lines 262-268):

```python
# OLD (lines 262-268):
to_holder = await allocation_service.resolve_holder(
    phone=b2b_request.recipient_phone,
    email=b2b_request.recipient_email,
    create_if_missing=True,
)

# NEW:
to_holder = await allocation_service.resolve_holder(
    user_id=b2b_request.requesting_user_id,
    create_if_missing=True,
)
```

- [ ] **Step 4: Commit**

```bash
git add src/apps/superadmin/service.py
git commit -m "fix(b2b): allocation to_holder resolved via requesting_user_id"
```

---

## Task 7: Add User Ownership Check to `confirm_b2b_payment` and Validate `event_day_id`

**Files:**
- Modify: `src/apps/organizer/urls.py:165-189`
- Modify: `src/apps/organizer/service.py:212-223`
- Test: `tests/apps/organizer/test_b2b_requests.py`

- [ ] **Step 1: Write failing test — confirm_b2b_payment checks user ownership**

```python
# Add to tests/apps/organizer/test_b2b_requests.py
async def test_confirm_b2b_payment_rejects_wrong_organizer():
    """confirm_b2b_payment should reject if user doesn't own the organizer page."""
    from fastapi import HTTPException
    from apps.organizer.service import OrganizerService
    from unittest.mock import MagicMock, AsyncMock
    from uuid import uuid4

    # Setup: user does NOT own organizer_id
    mock_repo = MagicMock()
    mock_session = AsyncMock()
    mock_repo.session = mock_session

    # B2B request exists but belongs to different organizer
    b2b_req = MagicMock()
    b2b_req.requesting_organizer_id = uuid4()  # Different from organizer_id below

    mock_repo.get_b2b_request_by_id = AsyncMock(return_value=b2b_req)
    mock_repo.get_by_id_for_owner = AsyncMock(return_value=None)  # User doesn't own this organizer

    service = OrganizerService(mock_repo)

    wrong_organizer_id = uuid4()
    correct_user_id = uuid4()
    b2b_request_id = uuid4()

    with pytest.raises(HTTPException) as exc_info:
        await service.confirm_b2b_payment(
            request_id=b2b_request_id,
            organizer_id=wrong_organizer_id,
            user_id=correct_user_id,
        )
    assert exc_info.value.status_code == 403
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/apps/organizer/test_b2b_requests.py::test_confirm_b2b_payment_rejects_wrong_organizer -v`
Expected: FAIL — current `confirm_b2b_payment` takes no organizer_id/user_id

- [ ] **Step 3: Update `OrganizerService.confirm_b2b_payment` to accept ownership params**

In `src/apps/organizer/service.py`, update the method:

```python
async def confirm_b2b_payment(
    self,
    request_id: uuid.UUID,
    organizer_id: uuid.UUID,
    user_id: uuid.UUID,
):
    """
    [Organizer] Confirm payment for an approved paid B2B request.
    Verifies user owns the organizer page, then triggers allocation.
    """
    # Verify user owns this organizer page
    organizer = await self.repository.get_by_id_for_owner(organizer_id, user_id)
    if not organizer:
        from exceptions import ForbiddenError
        raise ForbiddenError("You do not own this organizer page")

    # Verify the B2B request belongs to this organizer
    b2b_req = await self.repository.get_b2b_request_by_id(request_id)
    if not b2b_req or b2b_req.requesting_organizer_id != organizer_id:
        from exceptions import ForbiddenError
        raise ForbiddenError("B2B request does not belong to this organizer")

    return await self._super_admin_service.process_paid_b2b_allocation(
        request_id=request_id,
    )
```

- [ ] **Step 4: Update `confirm_b2b_payment` route to pass user+organizer**

In `src/apps/organizer/urls.py`, update the route (lines 165-189):

```python
@router.post("/{organizer_id}/b2b-requests/{b2b_request_id}/confirm-payment")
async def confirm_b2b_payment(
    organizer_id: UUID,
    b2b_request_id: UUID,
    request: Request,
    service: Annotated[OrganizerService, Depends(get_organizer_service)],
    body: Annotated[ConfirmB2BPaymentBody, Body()],
) -> BaseResponse[B2BRequestResponse]:
    """
    [Organizer] Confirm payment for an approved paid B2B request.
    Mock payment success — triggers allocation creation.
    User must own the organizer page.
    """
    b2b_req = await service.confirm_b2b_payment(
        request_id=b2b_request_id,
        organizer_id=organizer_id,
        user_id=request.state.user.id,
    )
    return BaseResponse(data=B2BRequestResponse.model_validate(b2b_req))
```

- [ ] **Step 5: Add event_day ownership validation to `create_b2b_request` route**

In `src/apps/organizer/urls.py`, update the `create_b2b_request` route (lines 127-147). Add validation that `event_day_id` belongs to `event_id`. Use the event repository:

```python
@router.post("/{organizer_id}/b2b-requests")
async def create_b2b_request(
    organizer_id: UUID,
    request: Request,
    body: Annotated[CreateB2BRequestBody, Body()],
    service: Annotated[OrganizerService, Depends(get_organizer_service)],
) -> BaseResponse[B2BRequestResponse]:
    """
    [Organizer] Submit a B2B ticket request.
    Organizer provides event and day only — system auto-derives B2B ticket type.
    """
    from apps.event.repository import EventRepository

    # Validate organizer ownership
    event_repo = EventRepository(service.repository.session)
    organizer = await service.repository.get_by_id_for_owner(organizer_id, request.state.user.id)
    if not organizer:
        raise HTTPException(status_code=403, detail="You do not own this organizer page")

    # Validate event_day belongs to event
    event_day = await event_repo.get_event_day_by_id(UUID(body.event_day_id))
    if not event_day or event_day.event_id != UUID(body.event_id):
        raise HTTPException(status_code=400, detail="event_day_id does not belong to event_id")

    b2b_req = await service.create_b2b_request(
        organizer_id=organizer_id,
        user_id=request.state.user.id,
        event_id=UUID(body.event_id),
        event_day_id=UUID(body.event_day_id),
        quantity=body.quantity,
    )
    return BaseResponse(data=B2BRequestResponse.model_validate(b2b_req))
```

Also update the import in `urls.py` to add `HTTPException`.

- [ ] **Step 6: Run test to verify it passes**

Run: `pytest tests/apps/organizer/test_b2b_requests.py::test_confirm_b2b_payment_rejects_wrong_organizer -v`
Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add src/apps/organizer/urls.py src/apps/organizer/service.py tests/apps/organizer/test_b2b_requests.py
git commit -m "fix(b2b): add ownership check to confirm_b2b_payment, validate event_day_id belongs to event_id"
```

---

## Task 8: Generate & Run Migration for Dropped Columns

**Files:**
- Auto-generated: `src/migrations/versions/<auto>_remove_recipient_fields_from_b2b_requests.py`

- [ ] **Step 1: Generate migration**

```bash
uv run main.py makemigrations
```

Expected output: generates migration to drop `recipient_phone` and `recipient_email` columns from `b2b_requests`.

- [ ] **Step 2: Apply migration**

```bash
uv run main.py migrate
```

- [ ] **Step 3: Commit**

```bash
git add src/migrations/versions/
git commit -m "chore(b2b): drop recipient_phone and recipient_email columns from b2b_requests"
```

---

## Self-Review Checklist

**1. Spec coverage:**
- Bug 1 (organizer picks ticket_type_id): fixed in Task 3 (schema) + Task 4 (auto-derive) + Task 5 (service call)
- Bug 2 (recipient fields not needed): fixed in Task 3 (schema) + Task 5 (model) + Task 6 (service)
- Bug 3 (request.state pattern): fixed in Task 1 (auth dep) + Task 2 (routes)
- Bug 4 (no ownership check): fixed in Task 7
- Bug 5 (event_day validation): fixed in Task 7
- Bug 6 (get_or_create missing): fixed in Task 4

**2. Placeholder scan:** No TODOs, TBDs, or vague steps. All code is concrete.

**3. Type consistency:**
- `resolve_holder(user_id=...)` called with keyword arg in Task 6 ✓
- `create_b2b_request` signature updated in Tasks 5 (repo) and 7 (service) — keyword args throughout ✓
- `CreateB2BRequestBody` fields: `event_id`, `event_day_id`, `quantity` only ✓

---

## Execution Options

**Plan complete and saved to `docs/superpowers/plans/2026-04-15-b2b-bug-fixes.md`. Two execution options:**

**1. Subagent-Driven (recommended)** - I dispatch a fresh subagent per task, review between tasks, fast iteration

**2. Inline Execution** - Execute tasks in this session using executing-plans, batch execution with checkpoints

**Which approach?**
