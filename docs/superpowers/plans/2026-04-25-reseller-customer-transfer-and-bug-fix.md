# Fix Transfer Bugs + Reseller→Customer Transfer

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix the `lock_tickets_for_transfer` event_day_id bug in both organizer transfers, clean up inline imports in `create_b2b_transfer`, and implement reseller→customer transfer following the same pattern.

**Architecture:**
- Fix `lock_tickets_for_transfer` to accept `event_day_id` and filter correctly
- Move inline imports to top-of-file in `organizer/service.py`
- Implement `create_reseller_customer_transfer` in `resellers/service.py` mirroring `create_customer_transfer`
- Add endpoint `POST /api/resellers/b2b/events/{event_id}/transfers/customer`

**Tech Stack:** Python, SQLAlchemy, FastAPI, async/await

---

## Bug Summary

### Bug 1: `lock_tickets_for_transfer` Missing `event_day_id` Filter

**Location:** `src/apps/ticketing/repository.py:157`

**Problem:** `lock_tickets_for_transfer` filters by `event_id`, `ticket_type_id`, `owner_holder_id`, and `lock_reference_id IS NULL` — but NOT `event_day_id`. This means:
- Count check (`list_b2b_tickets_by_holder`) correctly scopes to a specific day
- Lock picks tickets from ANY day (ordered by `ticket_index`)

**Affected callers:**
- `organizer/service.py:505` — `create_b2b_transfer` (org→reseller)
- `organizer/service.py:702` — `create_customer_transfer` (org→customer)

### Bug 2: Inline Imports in `create_b2b_transfer`

**Location:** `organizer/service.py:411-417`

Both `create_b2b_transfer` and `create_customer_transfer` have inline imports that should be at the top of the file:
```python
from apps.user.repository import UserRepository
from apps.ticketing.enums import OrderType, OrderStatus
from apps.allocation.enums import AllocationType
from apps.allocation.models import OrderModel
from apps.ticketing.models import TicketModel
from apps.organizer.response import B2BTransferResponse  # or CustomerTransferResponse
from sqlalchemy import update
from exceptions import BadRequestError, NotFoundError
```

---

## File Map

| File | Change |
|------|--------|
| `src/apps/ticketing/repository.py:157` | Add `event_day_id` param + filter to `lock_tickets_for_transfer` |
| `src/apps/organizer/service.py:1-19` | Add missing imports (OrderType, OrderStatus, AllocationType, OrderModel, TicketModel, BadRequestError, NotFoundError, UserRepository, B2BTransferResponse, update) |
| `src/apps/organizer/service.py:411-417` | Remove inline imports from `create_b2b_transfer` |
| `src/apps/organizer/service.py:601-612` | Remove inline imports from `create_customer_transfer` |
| `src/apps/organizer/service.py:505` | Pass `event_day_id` to `lock_tickets_for_transfer` |
| `src/apps/organizer/service.py:702` | Pass `event_day_id` to `lock_tickets_for_transfer` |
| `src/apps/resellers/service.py` | Add `create_reseller_customer_transfer` method |
| `src/apps/resellers/urls.py` | Add `POST /b2b/events/{event_id}/transfers/customer` endpoint |
| `src/apps/organizer/request.py` | Reuse `CreateCustomerTransferRequest` (already exists) |
| `src/apps/organizer/response.py` | Reuse `CustomerTransferResponse` (already exists) |

---

## Tasks

### Task 1: Fix `lock_tickets_for_transfer` — Add `event_day_id` Filter

**Files:**
- Modify: `src/apps/ticketing/repository.py:157-212`

- [ ] **Step 1: Read current `lock_tickets_for_transfer` implementation**

```python
async def lock_tickets_for_transfer(
    self,
    owner_holder_id: UUID,
    event_id: UUID,
    ticket_type_id: UUID,
    quantity: int,
    order_id: UUID,
    lock_ttl_minutes: int = 30,
) -> list[UUID]:
```

- [ ] **Step 2: Update method signature to add `event_day_id: UUID` parameter**

```python
async def lock_tickets_for_transfer(
    self,
    owner_holder_id: UUID,
    event_id: UUID,
    ticket_type_id: UUID,
    event_day_id: UUID,
    quantity: int,
    order_id: UUID,
    lock_ttl_minutes: int = 30,
) -> list[UUID]:
```

- [ ] **Step 3: Add `event_day_id` filter condition in the subquery**

In the `.where()` clause at line ~182, add:
```python
TicketModel.event_day_id == event_day_id,
```

The full condition block should be:
```python
conditions = [
    TicketModel.event_id == event_id,
    TicketModel.event_day_id == event_day_id,
    TicketModel.ticket_type_id == ticket_type_id,
    TicketModel.owner_holder_id == owner_holder_id,
    TicketModel.lock_reference_id.is_(None),
]
```

- [ ] **Step 4: Run existing tests to verify nothing breaks**

Run: `uv run pytest tests/apps/ticketing/ -v -k "lock" --tb=short`
Expected: No failures (no tests currently cover this method directly)

---

### Task 2: Fix Inline Imports in `create_b2b_transfer` and `create_customer_transfer`

**Files:**
- Modify: `src/apps/organizer/service.py:1-19`

- [ ] **Step 1: Read current top-of-file imports (lines 1-19)**

Current imports at top:
```python
import re
import uuid
import hashlib
from uuid import UUID

from .exceptions import OrganizerNotFound, OrganizerSlugAlreadyExists
from .models import OrganizerPageModel
from src.utils.s3_client import get_s3_client
from src.utils.file_validation import FileValidator, FileValidationError
from apps.superadmin.service import SuperAdminService
from apps.superadmin.enums import B2BRequestStatus


from apps.ticketing.repository import TicketingRepository
from apps.allocation.enums import AllocationStatus
from apps.allocation.repository import AllocationRepository
from apps.allocation.service import AllocationService
from apps.event.repository import EventRepository
from exceptions import ForbiddenError
```

- [ ] **Step 2: Add missing imports to top-of-file**

After `from exceptions import ForbiddenError`, add:
```python
from apps.user.repository import UserRepository
from apps.ticketing.enums import OrderType, OrderStatus
from apps.allocation.enums import AllocationType
from apps.allocation.models import OrderModel
from apps.ticketing.models import TicketModel
from apps.organizer.response import B2BTransferResponse, CustomerTransferResponse
from exceptions import BadRequestError, NotFoundError
from sqlalchemy import update
```

- [ ] **Step 3: Remove inline imports from `create_b2b_transfer` (lines 411-417)**

Delete these lines from inside `create_b2b_transfer`:
```python
from apps.user.repository import UserRepository
from apps.ticketing.enums import OrderType, OrderStatus
from apps.allocation.enums import AllocationType
from apps.allocation.models import OrderModel
from apps.ticketing.models import TicketModel
from apps.organizer.response import B2BTransferResponse
from sqlalchemy import update
```

- [ ] **Step 4: Remove inline imports from `create_customer_transfer` — selective cleanup**

In `create_customer_transfer`, remove the SHARED imports that are now at the top. Keep ONLY the method-specific ones inline (not used anywhere else):

DELETE from inside `create_customer_transfer`:
```python
# REMOVE — now at top-of-file (shared with create_b2b_transfer)
from apps.ticketing.enums import OrderType, OrderStatus
from apps.allocation.enums import AllocationType
from apps.allocation.models import OrderModel
from apps.ticketing.models import TicketModel
from apps.organizer.response import CustomerTransferResponse
from exceptions import BadRequestError, NotFoundError
from sqlalchemy import update
```

KEEP INLINE — method-specific, not used elsewhere:
```python
# KEEP INLINE — only used in create_customer_transfer
from src.utils.claim_link_utils import generate_claim_link_token
from src.utils.notifications.sms import mock_send_sms
from src.utils.notifications.whatsapp import mock_send_whatsapp
from src.utils.notifications.email import mock_send_email
```

Note: `EventRepository` is used in BOTH `create_b2b_transfer` (line ~441) and `create_customer_transfer` (line ~627), so it must also move to top-of-file — NOT kept inline. Add `from apps.event.repository import EventRepository` to the top-of-file imports alongside the other shared imports.

- [ ] **Step 5: Verify imports are correct**

Run: `uv run python -c "from apps.organizer.service import OrganizerService; print('OK')"`
Expected: No import errors

---

### Task 3: Pass `event_day_id` to `lock_tickets_for_transfer` in Both Call Sites

**Files:**
- Modify: `src/apps/organizer/service.py:505` (create_b2b_transfer)
- Modify: `src/apps/organizer/service.py:702` (create_customer_transfer)

- [ ] **Step 1: Fix `create_b2b_transfer` call site**

Update the call at line 505:
```python
locked_ticket_ids = await self._ticketing_repo.lock_tickets_for_transfer(
    owner_holder_id=org_holder.id,
    event_id=event_id,
    ticket_type_id=b2b_ticket_type.id,
    event_day_id=event_day_id,  # ADD THIS
    quantity=quantity,
    order_id=order.id,
    lock_ttl_minutes=30,
)
```

- [ ] **Step 2: Fix `create_customer_transfer` call site**

Update the call at line 702:
```python
locked_ticket_ids = await self._ticketing_repo.lock_tickets_for_transfer(
    owner_holder_id=org_holder.id,
    event_id=event_id,
    ticket_type_id=b2b_ticket_type.id,
    event_day_id=event_day_id,  # ADD THIS
    quantity=quantity,
    order_id=order.id,
    lock_ttl_minutes=30,
)
```

- [ ] **Step 3: Run customer transfer tests**

Run: `uv run pytest tests/apps/organizer/test_customer_transfer.py -v --tb=short`
Expected: All pass

---

### Task 4: Implement Reseller→Customer Transfer Service Method

**Files:**
- Modify: `src/apps/resellers/service.py`

- [ ] **Step 1: Add imports needed at top of `resellers/service.py`**

Read current imports first, then add:
```python
import hashlib
import uuid as uuid_lib
from apps.allocation.enums import AllocationType, AllocationStatus
from apps.allocation.models import OrderModel
from apps.allocation.repository import AllocationRepository
from apps.ticketing.enums import OrderType, OrderStatus
from apps.ticketing.models import TicketModel
from apps.ticketing.repository import TicketingRepository
from apps.organizer.response import CustomerTransferResponse
from exceptions import BadRequestError, NotFoundError, ForbiddenError
from sqlalchemy import update, select
from src.utils.claim_link_utils import generate_claim_link_token
from src.utils.notifications.sms import mock_send_sms
from src.utils.notifications.whatsapp import mock_send_whatsapp
from src.utils.notifications.email import mock_send_email
```

Also need to initialize repos in `__init__`:
```python
def __init__(self, session):
    self._repo = ResellerRepository(session)
    self._allocation_repo = AllocationRepository(session)
    self._ticketing_repo = TicketingRepository(session)
```

- [ ] **Step 2: Write `create_reseller_customer_transfer` method**

Add after existing methods (~line 130):

```python
async def create_reseller_customer_transfer(
    self,
    user_id: uuid_lib.UUID,
    event_id: uuid_lib.UUID,
    phone: str | None,
    email: str | None,
    quantity: int,
    event_day_id: uuid_lib.UUID,
    mode: str = "free",
) -> "CustomerTransferResponse":
    """
    [Reseller] Transfer B2B tickets to a customer (free mode).
    Customer receives a claim link; their ticket ownership is transferred immediately.

    Flow (free mode):
    1. Validate reseller is associated with this event
    2. Validate event_day_id exists and belongs to event
    3. Resolve customer TicketHolder (phone+email match, or phone-only, or email-only)
    4. Get reseller's TicketHolder
    5. Check reseller's available ticket count ≥ quantity (scoped to event_day)
    6. Create $0 TRANSFER order (status=paid, immediate)
    7. Lock tickets (FIFO, 30-min TTL) for specific ticket_type + event_day
    8. Create Allocation + ClaimLink in one transaction
    9. Add tickets to allocation
    10. Upsert AllocationEdge (reseller → customer)
    11. Update ticket ownership to customer, clear lock fields
    12. Mark allocation as completed (free transfer is immediate)
    13. Send notifications (mock SMS/WhatsApp/Email)

    Flow (paid mode):
    - Returns stub: status="not_implemented", mode="paid"

    Returns:
        CustomerTransferResponse with transfer_id, status, ticket_count, mode, claim_link
    """
    if mode == "paid":
        return CustomerTransferResponse(
            transfer_id=uuid_lib.UUID("00000000-0000-0000-0000-000000000000"),
            status="not_implemented",
            ticket_count=0,
            mode="paid",
            message="Paid customer transfer coming soon",
        )

    if not phone and not email:
        raise BadRequestError("Either phone or email must be provided")

    # 1. Validate reseller is associated with this event
    is_reseller = await self._repo.is_accepted_reseller(user_id, event_id)
    if not is_reseller:
        raise ForbiddenError("You are not a reseller for this event")

    # 2. Validate event_day_id exists and belongs to event
    from apps.event.repository import EventRepository
    event_repo = EventRepository(self._repo._session)
    event_day = await event_repo.get_event_day_by_id(event_day_id)
    if not event_day or event_day.event_id != event_id:
        raise NotFoundError("Event day not found or does not belong to this event")

    # 3. Resolve customer TicketHolder
    # Priority order when both phone+email provided:
    #   1. Try AND lookup
    #   2. Try phone-only lookup
    #   3. Try email-only lookup
    #   4. Create new if nothing found
    if phone and email:
        existing = await self._allocation_repo.get_holder_by_phone_and_email(phone, email)
        if existing:
            customer_holder = existing
        else:
            by_phone = await self._allocation_repo.get_holder_by_phone(phone)
            if by_phone:
                customer_holder = by_phone
            else:
                by_email = await self._allocation_repo.get_holder_by_email(email)
                if by_email:
                    customer_holder = by_email
                else:
                    customer_holder = await self._allocation_repo.create_holder(
                        phone=phone, email=email
                    )
    elif phone:
        customer_holder = await self._allocation_repo.get_holder_by_phone(phone)
        if not customer_holder:
            customer_holder = await self._allocation_repo.create_holder(phone=phone)
    else:
        customer_holder = await self._allocation_repo.get_holder_by_email(email)
        if not customer_holder:
            customer_holder = await self._allocation_repo.create_holder(email=email)

    # 4. Get reseller's holder
    reseller_holder = await self._repo.get_my_holder_for_event(user_id)
    if not reseller_holder:
        raise NotFoundError("Reseller has no ticket holder account")

    # 5. Check reseller's available ticket count ≥ quantity
    b2b_ticket_type = await self._ticketing_repo.get_b2b_ticket_type_for_event(event_id)
    if not b2b_ticket_type:
        raise NotFoundError("No B2B ticket type found for this event")

    ticket_rows = await self._allocation_repo.list_b2b_tickets_by_holder(
        event_id=event_id,
        holder_id=reseller_holder.id,
        b2b_ticket_type_id=b2b_ticket_type.id,
        event_day_id=event_day_id,
    )
    available = sum(r["count"] for r in ticket_rows)
    if available < quantity:
        raise BadRequestError(f"Only {available} B2B tickets available, requested {quantity}")

    # 6. Create $0 TRANSFER order (status=paid — immediate completion)
    order = OrderModel(
        event_id=event_id,
        user_id=user_id,
        type=OrderType.transfer,
        subtotal_amount=0.0,
        discount_amount=0.0,
        final_amount=0.0,
        status=OrderStatus.paid,
    )
    self._repo._session.add(order)
    await self._repo._session.flush()
    await self._repo._session.refresh(order)

    # 7. Lock tickets using order.id as lock_reference_id
    locked_ticket_ids = await self._ticketing_repo.lock_tickets_for_transfer(
        owner_holder_id=reseller_holder.id,
        event_id=event_id,
        ticket_type_id=b2b_ticket_type.id,
        event_day_id=event_day_id,
        quantity=quantity,
        order_id=order.id,
        lock_ttl_minutes=30,
    )

    # 8. Create allocation + claim link in one transaction
    raw_token = generate_claim_link_token(length=8)
    token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
    allocation, claim_link = await self._allocation_repo.create_allocation_with_claim_link(
        event_id=event_id,
        event_day_id=event_day_id,
        from_holder_id=reseller_holder.id,
        to_holder_id=customer_holder.id,
        order_id=order.id,
        allocation_type=AllocationType.transfer,
        ticket_count=len(locked_ticket_ids),
        token_hash=token_hash,
        created_by_holder_id=reseller_holder.id,
        metadata_={"source": "reseller_customer_free", "mode": mode},
    )

    # 9. Add tickets to allocation
    await self._allocation_repo.add_tickets_to_allocation(allocation.id, locked_ticket_ids)

    # 10. Upsert allocation edge (reseller → customer)
    await self._allocation_repo.upsert_edge(
        event_id=event_id,
        from_holder_id=reseller_holder.id,
        to_holder_id=customer_holder.id,
        ticket_count=len(locked_ticket_ids),
    )

    # 11. Update ticket ownership to customer, clear lock fields
    await self._repo._session.execute(
        update(TicketModel)
        .where(TicketModel.id.in_(locked_ticket_ids))
        .values(
            owner_holder_id=customer_holder.id,
            lock_reference_type=None,
            lock_reference_id=None,
            lock_expires_at=None,
        )
    )

    # 12. Mark allocation as completed (free transfer is immediate)
    await self._allocation_repo.transition_allocation_status(
        allocation.id,
        AllocationStatus.pending,
        AllocationStatus.completed,
    )

    # 13. Send notifications (mock — real integration replaces these later)
    claim_url = f"/claim/{raw_token}"
    message = f"You received {len(locked_ticket_ids)} ticket(s). Claim at: {claim_url}"

    mock_send_sms(phone or "", message, template="customer_transfer")
    mock_send_whatsapp(phone or "", message, template="customer_transfer")
    if email:
        mock_send_email(email, "You received tickets!", message)

    return CustomerTransferResponse(
        transfer_id=order.id,
        status="completed",
        ticket_count=len(locked_ticket_ids),
        mode=mode,
        claim_link=claim_url,
    )
```

- [ ] **Step 3: Verify the method is syntactically correct**

Run: `uv run python -c "from apps.resellers.service import ResellerService; print('OK')"`
Expected: No errors

---

### Task 5: Add Reseller→Customer Transfer Endpoint

**Files:**
- Modify: `src/apps/resellers/urls.py`

- [ ] **Step 1: Read current reseller urls.py**

- [ ] **Step 2: Add endpoint after existing endpoints (after `get_my_reseller_allocations`)**

```python
@router.post("/b2b/events/{event_id}/transfers/customer")
async def create_reseller_customer_transfer_endpoint(
    event_id: UUID,
    request: Request,
    body: Annotated[CreateCustomerTransferRequest, Body()],
    service: Annotated[ResellerService, Depends(get_reseller_service)],
) -> BaseResponse[CustomerTransferResponse]:
    """
    [Reseller] Transfer B2B tickets to a customer via phone or email.
    Free mode: immediately transfers ticket ownership and generates a claim link.
    Paid mode: returns not_implemented stub.
    """
    result = await service.create_reseller_customer_transfer(
        user_id=request.state.user.id,
        event_id=event_id,
        phone=body.phone,
        email=body.email,
        quantity=body.quantity,
        event_day_id=body.event_day_id,
        mode=body.mode,
    )
    return BaseResponse(data=result)
```

- [ ] **Step 3: Add `CreateCustomerTransferRequest` import**

In `urls.py`, add to imports:
```python
from apps.organizer.request import CreateCustomerTransferRequest
```

- [ ] **Step 4: Verify endpoint registers correctly**

Run: `uv run python -c "from apps.resellers.urls import router; print('OK')"`
Expected: No errors

---

### Task 6: Write Tests for Reseller→Customer Transfer

**Files:**
- Create: `tests/apps/resellers/test_reseller_customer_transfer.py`

- [ ] **Step 1: Write test file**

```python
import pytest
from uuid import uuid4
from unittest.mock import AsyncMock, patch


@pytest.mark.asyncio
async def test_reseller_customer_transfer_free_mode_happy_path():
    """
    Reseller transfers 2 B2B tickets to customer via phone+email.
    Customer is new (no existing holder). Transfer completes immediately.
    """
    from apps.resellers.service import ResellerService
    from apps.organizer.response import CustomerTransferResponse

    session = AsyncMock()
    repo = AsyncMock()
    allocation_repo = AsyncMock()
    ticketing_repo = AsyncMock()

    service = ResellerService.__new__(ResellerService)
    service._repo = repo
    service._allocation_repo = allocation_repo
    service._ticketing_repo = ticketing_repo

    user_id = uuid4()
    event_id = uuid4()
    event_day_id = uuid4()
    phone = "+1234567890"
    email = "customer@example.com"
    quantity = 2

    # Mock reseller is accepted for event
    repo.is_accepted_reseller = AsyncMock(return_value=True)

    # Mock get_my_holder_for_event returns reseller holder
    reseller_holder_id = uuid4()
    repo.get_my_holder_for_event = AsyncMock(return_value=AsyncMock(id=reseller_holder_id))

    # Mock get_b2b_ticket_type_for_event
    b2b_type_id = uuid4()
    ticketing_repo.get_b2b_ticket_type_for_event = AsyncMock(
        return_value=AsyncMock(id=b2b_type_id)
    )

    # Mock list_b2b_tickets_by_holder returns 5 available
    allocation_repo.list_b2b_tickets_by_holder = AsyncMock(
        return_value=[{"event_day_id": event_day_id, "count": 5}]
    )

    # Mock get_holder_by_phone_and_email returns None (new customer)
    allocation_repo.get_holder_by_phone_and_email = AsyncMock(return_value=None)
    allocation_repo.get_holder_by_phone = AsyncMock(return_value=None)
    allocation_repo.get_holder_by_email = AsyncMock(return_value=None)

    # Mock create_holder returns new customer holder
    customer_holder_id = uuid4()
    allocation_repo.create_holder = AsyncMock(
        return_value=AsyncMock(id=customer_holder_id)
    )

    # Mock order creation
    order_id = uuid4()
    mock_order = AsyncMock(id=order_id)
    session.add = AsyncMock()
    session.flush = AsyncMock()
    session.refresh = AsyncMock(side_effect=lambda o: setattr(o, 'id', order_id))
    session.execute = AsyncMock()

    # Mock lock_tickets_for_transfer
    locked_ids = [uuid4(), uuid4()]
    ticketing_repo.lock_tickets_for_transfer = AsyncMock(return_value=locked_ids)

    # Mock allocation creation
    allocation_id = uuid4()
    mock_allocation = AsyncMock(id=allocation_id)
    allocation_repo.create_allocation_with_claim_link = AsyncMock(
        return_value=(mock_allocation, AsyncMock(id=uuid4()))
    )
    allocation_repo.add_tickets_to_allocation = AsyncMock()
    allocation_repo.upsert_edge = AsyncMock()
    allocation_repo.transition_allocation_status = AsyncMock()

    with patch('apps.resellers.service.uuid_lib.UUID', return_value=uuid4()):
        result = await service.create_reseller_customer_transfer(
            user_id=user_id,
            event_id=event_id,
            phone=phone,
            email=email,
            quantity=quantity,
            event_day_id=event_day_id,
            mode="free",
        )

    assert isinstance(result, CustomerTransferResponse)
    assert result.status == "completed"
    assert result.ticket_count == 2
    assert result.mode == "free"
    assert result.claim_link.startswith("/claim/")


@pytest.mark.asyncio
async def test_reseller_customer_transfer_paid_mode_returns_stub():
    """
    Reseller requests paid mode — returns not_implemented stub.
    """
    from apps.resellers.service import ResellerService
    from apps.organizer.response import CustomerTransferResponse

    session = AsyncMock()
    repo = AsyncMock()

    service = ResellerService.__new__(ResellerService)
    service._repo = repo

    result = await service.create_reseller_customer_transfer(
        user_id=uuid4(),
        event_id=uuid4(),
        phone="+1234567890",
        email="customer@example.com",
        quantity=2,
        event_day_id=uuid4(),
        mode="paid",
    )

    assert isinstance(result, CustomerTransferResponse)
    assert result.status == "not_implemented"
    assert result.mode == "paid"
    assert result.ticket_count == 0


@pytest.mark.asyncio
async def test_reseller_customer_transfer_no_phone_or_email_raises():
    """
    Transfer without phone or email raises BadRequestError.
    """
    from apps.resellers.service import ResellerService
    from exceptions import BadRequestError

    service = ResellerService.__new__(ResellerService)
    service._repo = AsyncMock()

    with pytest.raises(BadRequestError):
        await service.create_reseller_customer_transfer(
            user_id=uuid4(),
            event_id=uuid4(),
            phone=None,
            email=None,
            quantity=2,
            event_day_id=uuid4(),
            mode="free",
        )


@pytest.mark.asyncio
async def test_reseller_customer_transfer_not_reseller_forbidden():
    """
    Non-reseller trying to transfer returns ForbiddenError.
    """
    from apps.resellers.service import ResellerService
    from exceptions import ForbiddenError

    session = AsyncMock()
    repo = AsyncMock()

    service = ResellerService.__new__(ResellerService)
    service._repo = repo

    repo.is_accepted_reseller = AsyncMock(return_value=False)

    with pytest.raises(ForbiddenError):
        await service.create_reseller_customer_transfer(
            user_id=uuid4(),
            event_id=uuid4(),
            phone="+1234567890",
            email=None,
            quantity=2,
            event_day_id=uuid4(),
            mode="free",
        )


@pytest.mark.asyncio
async def test_reseller_customer_transfer_insufficient_tickets():
    """
    Reseller requests 5 tickets but only 2 available — raises BadRequestError.
    """
    from apps.resellers.service import ResellerService
    from exceptions import BadRequestError

    session = AsyncMock()
    repo = AsyncMock()
    allocation_repo = AsyncMock()
    ticketing_repo = AsyncMock()

    service = ResellerService.__new__(ResellerService)
    service._repo = repo
    service._allocation_repo = allocation_repo
    service._ticketing_repo = ticketing_repo

    repo.is_accepted_reseller = AsyncMock(return_value=True)
    repo.get_my_holder_for_event = AsyncMock(return_value=AsyncMock(id=uuid4()))

    b2b_type_id = uuid4()
    ticketing_repo.get_b2b_ticket_type_for_event = AsyncMock(
        return_value=AsyncMock(id=b2b_type_id)
    )

    # Only 2 available, requesting 5
    allocation_repo.list_b2b_tickets_by_holder = AsyncMock(
        return_value=[{"event_day_id": uuid4(), "count": 2}]
    )

    with pytest.raises(BadRequestError) as exc:
        await service.create_reseller_customer_transfer(
            user_id=uuid4(),
            event_id=uuid4(),
            phone="+1234567890",
            email=None,
            quantity=5,
            event_day_id=uuid4(),
            mode="free",
        )

    assert "Only 2 B2B tickets available" in str(exc.value)


@pytest.mark.asyncio
async def test_reseller_customer_transfer_existing_holder_by_phone():
    """
    Customer already exists with phone only. Reseller transfers — uses existing holder.
    """
    from apps.resellers.service import ResellerService

    repo = AsyncMock()
    allocation_repo = AsyncMock()
    ticketing_repo = AsyncMock()

    service = ResellerService.__new__(ResellerService)
    service._repo = repo
    service._allocation_repo = allocation_repo
    service._ticketing_repo = ticketing_repo

    existing_holder_id = uuid4()

    repo.is_accepted_reseller = AsyncMock(return_value=True)
    repo.get_my_holder_for_event = AsyncMock(return_value=AsyncMock(id=uuid4()))

    b2b_type_id = uuid4()
    ticketing_repo.get_b2b_ticket_type_for_event = AsyncMock(
        return_value=AsyncMock(id=b2b_type_id)
    )
    allocation_repo.list_b2b_tickets_by_holder = AsyncMock(
        return_value=[{"event_day_id": uuid4(), "count": 5}]
    )

    # AND lookup fails, phone lookup succeeds
    allocation_repo.get_holder_by_phone_and_email = AsyncMock(return_value=None)
    allocation_repo.get_holder_by_phone = AsyncMock(
        return_value=AsyncMock(id=existing_holder_id)
    )

    # Mock everything else
    session = AsyncMock()
    session.add = AsyncMock()
    session.flush = AsyncMock()
    session.refresh = AsyncMock()
    session.execute = AsyncMock()

    ticketing_repo.lock_tickets_for_transfer = AsyncMock(return_value=[uuid4(), uuid4()])
    allocation_repo.create_allocation_with_claim_link = AsyncMock(
        return_value=(AsyncMock(id=uuid4()), AsyncMock(id=uuid4()))
    )
    allocation_repo.add_tickets_to_allocation = AsyncMock()
    allocation_repo.upsert_edge = AsyncMock()
    allocation_repo.transition_allocation_status = AsyncMock()

    with patch('apps.resellers.service.uuid_lib.UUID', return_value=uuid4()):
        result = await service.create_reseller_customer_transfer(
            user_id=uuid4(),
            event_id=uuid4(),
            phone="+1234567890",
            email="new@example.com",
            quantity=1,
            event_day_id=uuid4(),
            mode="free",
        )

    # create_holder should NOT have been called — used existing holder by phone
    allocation_repo.create_holder.assert_not_called()
    assert result.status == "completed"


@pytest.mark.asyncio
async def test_reseller_customer_transfer_self_transfer_allowed():
    """
    Reseller transfers tickets to their own phone — resolves to their own holder.
    Transfer completes normally. No self-transfer guard needed.
    """
    from apps.resellers.service import ResellerService

    repo = AsyncMock()
    allocation_repo = AsyncMock()
    ticketing_repo = AsyncMock()

    service = ResellerService.__new__(ResellerService)
    service._repo = repo
    service._allocation_repo = allocation_repo
    service._ticketing_repo = ticketing_repo

    reseller_holder_id = uuid4()

    repo.is_accepted_reseller = AsyncMock(return_value=True)
    repo.get_my_holder_for_event = AsyncMock(return_value=AsyncMock(id=reseller_holder_id))

    b2b_type_id = uuid4()
    ticketing_repo.get_b2b_ticket_type_for_event = AsyncMock(
        return_value=AsyncMock(id=b2b_type_id)
    )
    allocation_repo.list_b2b_tickets_by_holder = AsyncMock(
        return_value=[{"event_day_id": uuid4(), "count": 5}]
    )

    # AND lookup succeeds — finds reseller's own holder (same as from get_my_holder_for_event)
    allocation_repo.get_holder_by_phone_and_email = AsyncMock(
        return_value=AsyncMock(id=reseller_holder_id)  # same holder_id
    )

    # Mock everything else
    session = AsyncMock()
    session.add = AsyncMock()
    session.flush = AsyncMock()
    session.refresh = AsyncMock()
    session.execute = AsyncMock()

    ticketing_repo.lock_tickets_for_transfer = AsyncMock(return_value=[uuid4(), uuid4()])
    allocation_repo.create_allocation_with_claim_link = AsyncMock(
        return_value=(AsyncMock(id=uuid4()), AsyncMock(id=uuid4()))
    )
    allocation_repo.add_tickets_to_allocation = AsyncMock()
    allocation_repo.upsert_edge = AsyncMock()
    allocation_repo.transition_allocation_status = AsyncMock()

    result = await service.create_reseller_customer_transfer(
        user_id=uuid4(),
        event_id=uuid4(),
        phone="+1234567890",
        email="reseller@example.com",
        quantity=1,
        event_day_id=uuid4(),
        mode="free",
    )

    # Transfer completes — no error raised for self-transfer
    assert result.status == "completed"
    # create_holder was NOT called — existing holder was used
    allocation_repo.create_holder.assert_not_called()


@pytest.mark.asyncio
async def test_reseller_customer_transfer_event_day_not_found():
    """
    Provided event_day_id does not belong to the event — raises NotFoundError.
    """
    from apps.resellers.service import ResellerService
    from exceptions import NotFoundError
    from unittest.mock import AsyncMock

    repo = AsyncMock()
    service = ResellerService.__new__(ResellerService)
    service._repo = repo

    repo.is_accepted_reseller = AsyncMock(return_value=True)

    # Mock event_day lookup returning None (not found / wrong event)
    mock_event_repo = AsyncMock()
    mock_event_repo.get_event_day_by_id = AsyncMock(return_value=None)

    with patch('apps.resellers.service.EventRepository', return_value=mock_event_repo):
        with pytest.raises(NotFoundError):
            await service.create_reseller_customer_transfer(
                user_id=uuid4(),
                event_id=uuid4(),
                phone="+1234567890",
                email=None,
                quantity=2,
                event_day_id=uuid4(),
                mode="free",
            )
```

- [ ] **Step 3: Run tests**

Run: `uv run pytest tests/apps/resellers/test_reseller_customer_transfer.py -v --tb=short`
Expected: All 8 tests pass (6 original + 2 new)

---

### Task 7: Commit All Changes

Run:
```bash
git add src/apps/ticketing/repository.py \
  src/apps/organizer/service.py \
  src/apps/resellers/service.py \
  src/apps/resellers/urls.py \
  tests/apps/resellers/test_reseller_customer_transfer.py

git commit -m "$(cat <<'EOF'
fix(transfer): add event_day_id filter to lock_tickets_for_transfer

- lock_tickets_for_transfer now requires event_day_id parameter
- Organizer→reseller and organizer→customer transfers pass event_day_id
- Both transfers correctly lock only tickets for the specified day
- Reseller→customer transfer implemented following same pattern

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>
EOF
)"
```

---

## Verification Checklist

After all tasks:
- [ ] `uv run pytest tests/apps/organizer/test_customer_transfer.py -v` — all pass
- [ ] `uv run pytest tests/apps/resellers/test_reseller_customer_transfer.py -v` — all 8 pass
- [ ] `uv run python -c "from apps.organizer.service import OrganizerService; print('OK')"` — no import errors
- [ ] `uv run python -c "from apps.resellers.service import ResellerService; print('OK')"` — no import errors
- [ ] `uv run python -c "from apps.resellers.urls import router; print('OK')"` — no import errors

---

## Self-Review Corrections (2026-04-25)

### 1. Inline import cleanup — clarify which imports stay inline in `create_customer_transfer`

**Clarification:** After moving the shared imports to the top-of-file, these imports are ONLY used in `create_customer_transfer` — keep them inline:
```python
# KEEP INLINE in create_customer_transfer — method-specific, not shared
from apps.event.repository import EventRepository
from src.utils.claim_link_utils import generate_claim_link_token
from src.utils.notifications.sms import mock_send_sms
from src.utils.notifications.whatsapp import mock_send_whatsapp
from src.utils.notifications.email import mock_send_email
```

The `from exceptions import BadRequestError, NotFoundError` import was incorrectly listed to keep inline — these are used in BOTH methods, so move to top-of-file. Do NOT keep inline.

### 2. Add test for self-transfer case

Reseller sending tickets to their own phone/email is allowed. The cascading holder resolution naturally handles it — if reseller's phone resolves to their own holder, the transfer creates allocation to the same holder. No special handling needed, but add a test to confirm.

### 3. Note: `event_repo` initialization uses `self._repo._session` (private access)

This is the established pattern in `ResellerRepository.get_my_holder_for_event` which also uses `self._session` directly. This is fine — no change needed, just document it as known.

### 4. Import conflict check: `from sqlalchemy import update` already at top of `organizer/service.py`

Current `organizer/service.py` does NOT have `update` at top. Adding it is correct. The file currently has no `from sqlalchemy import update` at the top — it only appears inline in methods. Adding `update` to top-of-file is correct.

### 5. Self-transfer is allowed for both organizer and reseller

No self-transfer guard is needed. If the phone/email resolves to the transferrer's own holder, the transfer completes normally — the holder receives their own tickets. This is valid and works correctly with the cascading holder resolution.

---

## What Was Fixed

| Bug | Fix |
|-----|-----|
| `lock_tickets_for_transfer` missing `event_day_id` filter | Added `event_day_id: UUID` param + condition |
| Organizer→reseller transfer locking wrong day | Now passes `event_day_id` to lock |
| Organizer→customer transfer locking wrong day | Now passes `event_day_id` to lock |
| Inline imports in `create_b2b_transfer` | Moved `UserRepository, OrderType, OrderStatus, AllocationType, OrderModel, TicketModel, B2BTransferResponse, update` to top-of-file |
| Inline imports in `create_customer_transfer` | Moved shared imports (`OrderType, OrderStatus, AllocationType, OrderModel, TicketModel, CustomerTransferResponse, BadRequestError, NotFoundError, update`) to top-of-file; kept method-specific ones inline |
| Inline import cleanup was vague | Now clarified — only `EventRepository, claim_link_utils, notification utils` stay inline in `create_customer_transfer` |

---

*Plan updated after self-review: 2026-04-25*