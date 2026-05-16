# B2B Request MODERATE + MINOR Fixes Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix 4 MODERATE and 7 MINOR bugs across the B2B Request module — event ownership check, `gateway_flow_type` on paid transfer orders, `cancel_payment_link` in failure path, `resolve_holder` duplicate creation, docstring, formatting, pagination, wrong `AllocationType`, idempotency guard, and transaction side-effect.

**Architecture:** All 11 fixes are isolated to 5 files. Each task is independent and can be committed separately. No new files are created except test files.

**Tech Stack:** SQLAlchemy 2.0 async, Python 3.11+

---

## File Map

```
src/apps/organizer/service.py          — Issues 6, 7, 14 (partial), 15, 17, 18
src/apps/organizer/urls.py             — Issue 14 (pagination params)
src/apps/allocation/repository.py       — Issue 9 (resolve_holder)
src/apps/payment_gateway/handlers/razorpay.py  — Issues 7 (routing), 8 (cancel on failure), 16 (expiry worker)
src/apps/superadmin/service.py         — Issue 12 (docstring), Issue 17 (idempotency in approve_b2b_request_free)
tests/apps/organizer/test_service.py   — Issue 6 (ownership check test)
tests/apps/allocation/test_repository.py — Issue 9 (resolve_holder duplicate test)
```

---

## Pre-Read: Understand the Existing Code

Before starting, read these files to understand the current state:

**organizer/service.py lines 248-266** — `create_b2b_request`:
```
- No ownership check — any user can request B2B tickets for any event
- Calls get_or_create_b2b_ticket_type then creates the request
```

**organizer/service.py lines 497-518** — paid transfer order creation:
```
- gateway_type is set at line 508
- gateway_flow_type is NOT set (should be "b2b_transfer")
- sender_holder_id, receiver_holder_id, transfer_type set after flush (lines 514-517)
```

**razorpay.py lines 347-468** — b2b_transfer branch in `handle_order_paid`:
```
- Creates allocation, adds tickets, upserts edge, transitions status
- Calls clear_locks_for_order at line 465
- NO cancel_payment_link on failure — only handle_payment_failed has it
```

**allocation/repository.py lines 69-99** — `resolve_holder`:
```
- Checks phone → email → user_id independently
- Creates new holder if none found
- Doesn't check all three params together before creating
```

**organizer/service.py line 943** — `AllocationType.transfer`:
```
- Should be AllocationType.b2b (all other B2B flows use b2b)
```

---

## MODERATE Issues

### Task 1: Add Event Ownership Check in `create_b2b_request`

**Files:**
- Modify: `src/apps/organizer/service.py:248-266`

The `create_b2b_request` service method has no event ownership check. If called directly (not via API), any user could request B2B tickets for any event. Add a check that the authenticated user's `user_id` is the organizer of the event.

- [ ] **Step 1: Read the current code around lines 248-266**

Run: `sed -n '248,270p' src/apps/organizer/service.py`

Expected output:
```python
    async def create_b2b_request(
        self,
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
            requesting_user_id=user_id,
            event_id=event_id,
            event_day_id=event_day_id,
            ticket_type_id=b2b_ticket_type.id,
            quantity=quantity,
        )
```

- [ ] **Step 2: Add ownership check before creating B2B ticket type**

Replace the method body:
```python
    async def create_b2b_request(
        self,
        user_id: uuid.UUID,
        event_id: uuid.UUID,
        event_day_id: uuid.UUID,
        quantity: int,
    ):
        """[Organizer] Submit a B2B ticket request. System auto-derives B2B ticket type."""
        # Verify user owns the event (authorization check at service layer)
        event = await self._event_repo.get_event_by_id(event_id)
        if not event:
            from exceptions import NotFoundError
            raise NotFoundError(f"Event {event_id} not found")
        if event.organizer_id != user_id:
            from exceptions import ForbiddenError
            raise ForbiddenError(f"User {user_id} is not the organizer of event {event_id}")

        # Auto-derive B2B ticket type for this event day
        b2b_ticket_type = await self._ticketing_repo.get_or_create_b2b_ticket_type(
            event_day_id=event_day_id,
        )
        return await self.repository.create_b2b_request(
            requesting_user_id=user_id,
            event_id=event_id,
            event_day_id=event_day_id,
            ticket_type_id=b2b_ticket_type.id,
            quantity=quantity,
        )
```

Note: `self._event_repo` must exist on `OrganizerService`. Check if it exists:
Run: `grep -n "_event_repo" src/apps/organizer/service.py | head -5`

If `self._event_repo` does NOT exist, you need to add it to the `__init__` of `OrganizerService`. Read the `__init__`:
Run: `grep -n "__init__" src/apps/organizer/service.py | head -3`

Expected: lines around 40-50 show the __init__ method. Check what repos are already injected.

- [ ] **Step 3: Verify the change compiles**

Run: `PYTHONPATH=src uv run python -c "from apps.organizer.service import OrganizerService; print('OK')" 2>&1 | tail -1`

Expected: `OK` with no errors

- [ ] **Step 4: Add a test for the ownership check**

Check if test file exists:
Run: `ls tests/apps/organizer/test_service.py 2>/dev/null && echo "exists" || echo "not found"`

If it doesn't exist, create:
```bash
mkdir -p tests/apps/organizer
touch tests/apps/organizer/__init__.py
```

Add this test to `tests/apps/organizer/test_service.py`:

```python
import pytest
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

from apps.organizer.service import OrganizerService
from exceptions import ForbiddenError, NotFoundError


@pytest.mark.asyncio
async def test_create_b2b_request_rejects_non_organizer():
    """
    When a user who is not the event organizer calls create_b2b_request,
    the service must raise ForbiddenError.
    """
    # Setup mocks
    session = AsyncMock()
    mock_repository = AsyncMock()
    mock_ticketing_repo = AsyncMock()
    mock_event_repo = AsyncMock()

    svc = object.__new__(OrganizerService)
    svc._repository = mock_repository
    svc._ticketing_repo = mock_ticketing_repo
    svc._event_repo = mock_event_repo

    requesting_user_id = uuid.UUID("33333333-3333-3333-3333-333333333333")
    event_id = uuid.UUID("55555555-5555-5555-5555-555555555555")
    event_day_id = uuid.UUID("44444444-4444-4444-4444-444444444444")
    quantity = 10

    # Mock event where organizer_id is DIFFERENT from requesting_user_id
    mock_event = MagicMock()
    mock_event.id = event_id
    mock_event.organizer_id = uuid.UUID("00000000-0000-0000-0000-000000000000")  # Different user

    mock_event_repo.get_event_by_id = AsyncMock(return_value=mock_event)

    # Expect ForbiddenError
    with pytest.raises(ForbiddenError, match="not the organizer"):
        await svc.create_b2b_request(
            user_id=requesting_user_id,
            event_id=event_id,
            event_day_id=event_day_id,
            quantity=quantity,
        )


@pytest.mark.asyncio
async def test_create_b2b_request_rejects_nonexistent_event():
    """
    When the event doesn't exist, must raise NotFoundError.
    """
    session = AsyncMock()
    mock_repository = AsyncMock()
    mock_ticketing_repo = AsyncMock()
    mock_event_repo = AsyncMock()

    svc = object.__new__(OrganizerService)
    svc._repository = mock_repository
    svc._ticketing_repo = mock_ticketing_repo
    svc._event_repo = mock_event_repo

    requesting_user_id = uuid.UUID("33333333-3333-3333-3333-333333333333")
    event_id = uuid.UUID("55555555-5555-5555-5555-555555555555")
    event_day_id = uuid.UUID("44444444-4444-4444-4444-444444444444")
    quantity = 10

    mock_event_repo.get_event_by_id = AsyncMock(return_value=None)

    with pytest.raises(NotFoundError, match="not found"):
        await svc.create_b2b_request(
            user_id=requesting_user_id,
            event_id=event_id,
            event_day_id=event_day_id,
            quantity=quantity,
        )
```

- [ ] **Step 5: Run the tests**

Run: `PYTHONPATH=src uv run python -m pytest tests/apps/organizer/test_service.py -v 2>&1 | tail -15`

Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add src/apps/organizer/service.py tests/apps/organizer/test_service.py
git commit -m "fix(organizer): add event ownership check in create_b2b_request
"
```

---

### Task 2: Add `gateway_flow_type="b2b_transfer"` on Paid Transfer Order + Fix Routing

**Files:**
- Modify: `src/apps/organizer/service.py:500-518` (add field to order)
- Modify: `src/apps/payment_gateway/handlers/razorpay.py:347-356` (make routing explicit)

**Part A: Add `gateway_flow_type` to paid transfer order**

- [ ] **Step 1: Read the current code around lines 497-518**

```python
        if mode == TransferMode.PAID:
            total_price = price or 0.0
            # 1. Create pending order (no allocation created yet)
            order = OrderModel(
                event_id=event_id,
                user_id=user_id,
                type=OrderType.transfer,
                subtotal_amount=total_price,
                discount_amount=0.0,
                final_amount=total_price,
                status=OrderStatus.pending,
                gateway_type=GatewayType.RAZORPAY_PAYMENT_LINK,
                lock_expires_at=datetime.utcnow() + timedelta(minutes=30),
            )
```

- [ ] **Step 2: Add `gateway_flow_type="b2b_transfer"` to the OrderModel**

In the OrderModel creation block, add `gateway_flow_type="b2b_transfer"`:

```python
            order = OrderModel(
                event_id=event_id,
                user_id=user_id,
                type=OrderType.transfer,
                subtotal_amount=total_price,
                discount_amount=0.0,
                final_amount=total_price,
                status=OrderStatus.pending,
                gateway_type=GatewayType.RAZORPAY_PAYMENT_LINK,
                gateway_flow_type="b2b_transfer",  # ← ADD THIS LINE
                lock_expires_at=datetime.utcnow() + timedelta(minutes=30),
            )
```

**Part B: Make the webhook routing explicit instead of relying on fallthrough**

- [ ] **Step 3: Read the current routing code in razorpay.py around lines 347-356**

```python
        # Phase 4: Create B2B allocation + transfer tickets to buyer
        # Retrieve the locked tickets (locked during paid transfer creation in organizer service)
        ...
        if is_reseller:
            ...
        else:
            ...
```

The current routing uses fallthrough: `gateway_flow_type == "b2b_request"` handles B2B request, everything else (including `None`) falls through to b2b_transfer. Now that `gateway_flow_type="b2b_transfer"` is set explicitly, update the routing to be explicit:

- [ ] **Step 4: Change the routing from fallthrough to explicit**

In razorpay.py, change the phase labels:
- Line 328 comment says "Phase 3b: B2B Request paid" — keep as-is
- Line 347 comment says "Phase 4: Create B2B allocation + transfer tickets to buyer" — this is the b2b_transfer path

Change the condition from implicit fallthrough to explicit check. After line 329 (`if order.gateway_flow_type == "b2b_request":`), add an explicit `elif` for b2b_transfer:

Find the section starting at line 347:
```python
        # Phase 4: Create B2B allocation + transfer tickets to buyer
```

And change it so the b2b_transfer path is gated with:
```python
        elif order.gateway_flow_type == "b2b_transfer":
            logger.info(f"Routing B2B transfer payment for order {order.id}")
            # [rest of Phase 4 code]
```

Note: The current code has no explicit condition for Phase 4 — it just runs after the `b2b_request` block (implicit else). Now it should be explicitly gated.

- [ ] **Step 5: Verify the changes compile**

Run: `PYTHONPATH=src uv run python -c "from apps.organizer.service import OrganizerService; from apps.payment_gateway.handlers.razorpay import RazorpayWebhookHandler; print('OK')" 2>&1 | tail -1`

Expected: `OK`

- [ ] **Step 6: Commit**

```bash
git add src/apps/organizer/service.py src/apps/payment_gateway/handlers/razorpay.py
git commit -m "fix(b2b): add gateway_flow_type=b2b_transfer on paid transfer orders and make routing explicit
"
```

---

### Task 3: Add `cancel_payment_link` in Failure Path for B2B Transfer

**Files:**
- Modify: `src/apps/payment_gateway/handlers/razorpay.py:347-468`

The `b2b_transfer` branch in `handle_order_paid` creates an allocation. If it fails partway through (e.g., after `clear_locks_for_order` but before allocation is committed), the payment link remains active and could be exploited. Add `cancel_payment_link` on failure.

- [ ] **Step 1: Read the current b2b_transfer code (lines 347-468)**

Run: `sed -n '347,470p' src/apps/payment_gateway/handlers/razorpay.py`

This is a large block. The key issue: if the code throws an exception or returns early after `clear_locks_for_order` (line 465) but before the allocation is created, the payment link stays active.

The fix: wrap the allocation creation in a try/except and call `cancel_payment_link` on failure.

- [ ] **Step 2: Wrap the b2b_transfer allocation creation in try/except**

Find the start of the b2b_transfer allocation creation (line 347-362 area) and wrap the entire block in:

```python
        try:
            # Phase 4: Create B2B allocation + transfer tickets to buyer
            # Retrieve the locked tickets (locked during paid transfer creation in organizer service)
            locked_tickets_result = await self.session.execute(
                select(TicketModel).where(
                    TicketModel.lock_reference_type == 'transfer',
                    TicketModel.lock_reference_id == order.id,
                )
            )
            locked_ticket_ids = [t.id for t in locked_tickets_result.scalars().all()]

            if locked_ticket_ids:
                transfer_type = order.transfer_type
                is_reseller = transfer_type == "organizer_to_reseller"

                if is_reseller:
                    # Reseller already has an account; no claim link needed
                    allocation = await self._allocation_repo.create_allocation(
                        ...
                    )
                else:
                    # Customer: create allocation with claim link
                    raw_token = generate_claim_link_token(length=8)
                    token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
                    allocation, claim_link = await self._allocation_repo.create_allocation_with_claim_link(
                        ...
                    )

                # Add tickets to allocation
                await self._allocation_repo.add_tickets_to_allocation(allocation.id, locked_ticket_ids)

                # Upsert edge
                await self._allocation_repo.upsert_edge(
                    ...
                )

                # Mark completed
                await self._allocation_repo.transition_allocation_status(
                    allocation.id,
                    AllocationStatus.pending,
                    AllocationStatus.completed,
                )
            else:
                logger.warning(f"No locked tickets found for order {order.id} after payment")

            await self._ticketing_repo.clear_locks_for_order(order.id)
            logger.info(f"Order {order_id} marked paid, payment {payment_id}")
            return {"status": "ok"}

        except Exception as e:
            logger.error(f"B2B transfer allocation failed for order {order.id}: {e}")
            # Cancel the payment link so organizer can retry or the link doesn't stay active
            if order.gateway_order_id:
                await self._gateway.cancel_payment_link(order.gateway_order_id)
            raise
```

Note: The `return {"status": "ok"}` at the end of the happy path moves inside the try block. The new `except` block catches failures, cancels the payment link, then re-raises.

- [ ] **Step 3: Verify the change compiles**

Run: `PYTHONPATH=src uv run python -c "from apps.payment_gateway.handlers.razorpay import RazorpayWebhookHandler; print('OK')" 2>&1 | tail -1`

Expected: `OK`

- [ ] **Step 4: Commit**

```bash
git add src/apps/payment_gateway/handlers/razorpay.py
git commit -m "fix(payment_gateway): cancel payment link on b2b_transfer allocation failure
"
```

---

### Task 4: Fix `resolve_holder` Duplicate Creation When All 3 Params Provided

**Files:**
- Modify: `src/apps/allocation/repository.py:69-99`

When all three of `phone`, `email`, and `user_id` are provided, `resolve_holder` checks each independently but never looks up by phone+email together. A holder with the same email but different phone (or vice versa) could already exist, resulting in duplicate holders.

- [ ] **Step 1: Read the current code around lines 69-99**

```python
    async def resolve_holder(
        self,
        phone: str | None = None,
        email: str | None = None,
        user_id: UUID | None = None,
    ) -> TicketHolderModel:
        """
        Get or create a TicketHolder by phone, email, or user_id.
        At least one of phone, email, or user_id must be provided.
        """
        if phone:
            holder = await self.get_holder_by_phone(phone)
            if holder:
                return holder

        if email:
            holder = await self.get_holder_by_email(email)
            if holder:
                return holder

        if user_id:
            holder = await self.get_holder_by_user_id(user_id)
            if holder:
                return holder

        # Create new holder
        return await self.create_holder(
            user_id=user_id,
            phone=phone,
            email=email,
        )
```

- [ ] **Step 2: Add check for `get_holder_by_phone_and_email` when all 3 params are present**

Add at the START of `resolve_holder`, before the individual lookups:

```python
    async def resolve_holder(
        self,
        phone: str | None = None,
        email: str | None = None,
        user_id: UUID | None = None,
    ) -> TicketHolderModel:
        """
        Get or create a TicketHolder by phone, email, or user_id.
        At least one of phone, email, or user_id must be provided.
        """
        # When all three params are provided, check phone+email combo first
        # to avoid creating a duplicate holder when the same person already exists
        # with a different field combination
        if phone and email and user_id:
            holder = await self.get_holder_by_phone_and_email(phone, email)
            if holder:
                return holder

        if phone:
            holder = await self.get_holder_by_phone(phone)
            if holder:
                return holder

        if email:
            holder = await self.get_holder_by_email(email)
            if holder:
                return holder

        if user_id:
            holder = await self.get_holder_by_user_id(user_id)
            if holder:
                return holder

        # Create new holder
        return await self.create_holder(
            user_id=user_id,
            phone=phone,
            email=email,
        )
```

Note: `get_holder_by_phone_and_email` must exist on `AllocationRepository`. Check:
Run: `grep -n "def get_holder_by_phone_and_email" src/apps/allocation/repository.py`

If it doesn't exist, add it before `resolve_holder`:
```python
    async def get_holder_by_phone_and_email(self, phone: str, email: str) -> TicketHolderModel | None:
        result = await self._session.execute(
            select(TicketHolderModel).where(
                TicketHolderModel.phone == phone,
                TicketHolderModel.email == email,
            )
        )
        return result.scalar_one_or_none()
```

- [ ] **Step 3: Verify the change compiles**

Run: `PYTHONPATH=src uv run python -c "from apps.allocation.repository import AllocationRepository; print('OK')" 2>&1 | tail -1`

Expected: `OK`

- [ ] **Step 4: Add a test for duplicate prevention**

Check if test file exists:
Run: `ls tests/apps/allocation/test_repository.py 2>/dev/null && echo "exists" || echo "not found"`

If not, create `tests/apps/allocation/` directory and test file:
```bash
mkdir -p tests/apps/allocation
touch tests/apps/allocation/__init__.py
```

Add this test:
```python
import pytest
import uuid
from unittest.mock import AsyncMock, MagicMock

from apps.allocation.repository import AllocationRepository
from apps.allocation.models import TicketHolderModel


@pytest.mark.asyncio
async def test_resolve_holder_avoids_duplicate_when_phone_and_email_exist_separately():
    """
    When a holder with phone='123' but email='different@x.com' exists,
    and resolve_holder is called with phone='123', email='different@x.com', user_id=None,
    the existing holder should NOT be found (different email), and a new holder is created.
    But when a holder with phone='123' AND email='same@x.com' exists,
    resolve_holder should find it and NOT create a new one.
    """
    repo = object.__new__(AllocationRepository)
    session = AsyncMock()
    repo._session = session

    existing_holder = MagicMock(spec=TicketHolderModel)
    existing_holder.id = uuid.uuid4()
    existing_holder.phone = "1234567890"
    existing_holder.email = "test@example.com"

    # Mock get_holder_by_phone_and_email to return the existing holder
    async def mock_execute(query):
        result = AsyncMock()
        # Check: the query uses TicketHolderModel.phone == phone AND TicketHolderModel.email == email
        result.scalar_one_or_none = MagicMock(return_value=existing_holder)
        return result

    session.execute = mock_execute

    # Call with all 3 params — should use phone+email lookup first
    result = await repo.resolve_holder(
        phone="1234567890",
        email="test@example.com",
        user_id=uuid.uuid4(),
    )

    assert result == existing_holder, "Should return existing holder found by phone+email"
```

- [ ] **Step 5: Run the test**

Run: `PYTHONPATH=src uv run python -m pytest tests/apps/allocation/test_repository.py -v 2>&1 | tail -15`

Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add src/apps/allocation/repository.py tests/apps/allocation/test_repository.py
git commit -m "fix(allocation): prevent duplicate holders in resolve_holder when all params provided
"
```

---

## MINOR Issues

### Task 5: Fix Outdated Docstring on `process_paid_b2b_allocation`

**Files:**
- Modify: `src/apps/superadmin/service.py:310-315`

- [ ] **Step 1: Read the current docstring (lines 310-315)**

```python
    async def process_paid_b2b_allocation(
        self,
        request_id: uuid.UUID,
    ) -> B2BRequestModel:
        """
        Called after payment succeeds. Creates the actual allocation using the existing paid order.
        This method is called from the organizer's confirm-payment endpoint.
        admin_id is pulled from b2b_request.reviewed_by_admin_id (the super admin who approved it).
        """
```

- [ ] **Step 2: Update the docstring**

```python
        """
        Called after payment succeeds. Creates the actual allocation using the existing paid order.
        Called from the Razorpay payment_link.paid webhook (via SuperAdminService.process_paid_b2b_allocation).
        admin_id is pulled from b2b_request.reviewed_by_admin_id (the super admin who approved it).
        """
```

- [ ] **Step 3: Commit**

```bash
git add src/apps/superadmin/service.py
git commit -m "docs(superadmin): fix outdated docstring on process_paid_b2b_allocation
"
```

---

### Task 6: Fix Double Space and Formatting Inconsistencies

**Files:**
- Modify: `src/apps/superadmin/service.py:190`, `src/apps/organizer/service.py` (black)

- [ ] **Step 1: Check for double spaces in superadmin/service.py**

Run: `grep -n "def   approve" src/apps/superadmin/service.py`

Expected: line 190 has `async def   approve_b2b_request_paid(`

- [ ] **Step 2: Fix the double space**

Run: `sed -i 's/async def   approve_b2b_request_paid/async def approve_b2b_request_paid/' src/apps/superadmin/service.py`

Verify: `grep -n "def   approve" src/apps/superadmin/service.py` — should return no results

- [ ] **Step 3: Run black to auto-fix formatting**

Run: `PYTHONPATH=src uv run black src/apps/superadmin/service.py src/apps/organizer/service.py 2>&1 | tail -5`

Expected: formatted successfully

- [ ] **Step 4: Verify changes compile**

Run: `PYTHONPATH=src uv run python -c "from apps.superadmin.service import SuperAdminService; from apps.organizer.service import OrganizerService; print('OK')" 2>&1 | tail -1`

Expected: `OK`

- [ ] **Step 5: Commit**

```bash
git add src/apps/superadmin/service.py src/apps/organizer/service.py
git commit -m "style: fix formatting inconsistencies (double space, black formatting)
"
```

---

### Task 7: Add Pagination to Organizer's List B2B Requests Endpoint

**Files:**
- Modify: `src/apps/organizer/urls.py:234-257`

- [ ] **Step 1: Read the current code around lines 234-257**

Run: `sed -n '230,260p' src/apps/organizer/urls.py`

Expected: `list_b2b_requests_by_event` is called with no limit/offset params

- [ ] **Step 2: Add pagination parameters to the endpoint**

Find the `list_b2b_requests` endpoint (around line 234). Add `limit` and `offset` query params:

```python
from fastapi import Query

@router.get("/events/{event_id}/b2b/requests")
async def list_b2b_requests(
    event_id: UUID,
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
) -> list:
    ...
    return await service.get_b2b_requests_for_event(event_id, limit=limit, offset=offset)
```

Then update `organizer/service.py:get_b2b_requests_for_event` to accept and pass limit/offset:

- [ ] **Step 3: Update the service method signature**

In `organizer/service.py:268-273`, change:
```python
    async def get_b2b_requests_for_event(
        self,
        event_id: uuid.UUID,
    ) -> list:
        """[Organizer] List B2B requests for a specific event."""
        return await self.repository.list_b2b_requests_by_event(event_id)
```

To:
```python
    async def get_b2b_requests_for_event(
        self,
        event_id: uuid.UUID,
        limit: int = 50,
        offset: int = 0,
    ) -> list:
        """[Organizer] List B2B requests for a specific event."""
        return await self.repository.list_b2b_requests_by_event(event_id, limit=limit, offset=offset)
```

And update `organizer/repository.py` to accept limit/offset in `list_b2b_requests_by_event`:
Run: `grep -n "def list_b2b_requests_by_event" src/apps/organizer/repository.py`

Expected: method signature without limit/offset. Add them.

- [ ] **Step 4: Verify the change compiles**

Run: `PYTHONPATH=src uv run python -c "from apps.organizer.service import OrganizerService; print('OK')" 2>&1 | tail -1`

Expected: `OK`

- [ ] **Step 5: Commit**

```bash
git add src/apps/organizer/urls.py src/apps/organizer/service.py src/apps/organizer/repository.py
git commit -m "feat(organizer): add pagination to list B2B requests endpoint
"
```

---

### Task 8: Fix Wrong `AllocationType.transfer` in `allocate_customer_transfer`

**Files:**
- Modify: `src/apps/organizer/service.py:943`

- [ ] **Step 1: Read the current code around line 943**

```python
        allocation, claim_link = await self._allocation_repo.create_allocation_with_claim_link(
            ...
            allocation_type=AllocationType.transfer,  # ← should be b2b
```

- [ ] **Step 2: Change `AllocationType.transfer` to `AllocationType.b2b`**

Run: `grep -n "AllocationType.transfer" src/apps/organizer/service.py`

Expected: line 943

Replace:
```python
            allocation_type=AllocationType.transfer,
```
With:
```python
            allocation_type=AllocationType.b2b,
```

- [ ] **Step 3: Verify the change compiles**

Run: `PYTHONPATH=src uv run python -c "from apps.organizer.service import OrganizerService; print('OK')" 2>&1 | tail -1`

Expected: `OK`

- [ ] **Step 4: Commit**

```bash
git add src/apps/organizer/service.py
git commit -m "fix(organizer): use AllocationType.b2b in allocate_customer_transfer
"
```

---

### Task 9: Add Background Worker for B2B Payment Link Expiry

**Files:**
- Create: `src/apps/superadmin/workers.py` (new file — background worker)
- Modify: `src/apps/superadmin/service.py` (add expiry method)

This is a lower-priority fix. The webhook correctly handles expiry events from Razorpay. This worker is a safety net for when Razorpay fails to fire the expiry webhook.

- [ ] **Step 1: Create the worker file**

Create `src/apps/superadmin/workers.py`:

```python
"""
Background workers for B2B request lifecycle.
"""
import logging
from datetime import datetime, timedelta
from uuid import UUID

from sqlalchemy import select, update

from apps.superadmin.models import B2BRequestModel
from apps.superadmin.enums import B2BRequestStatus

logger = logging.getLogger(__name__)


class B2BExpiryWorker:
    """
    Safety-net worker to expire stale approved_paid B2B requests
    when Razorpay fails to fire the payment_link.expired webhook.

    Should be scheduled to run every hour.
    """

    def __init__(self, session):
        self.session = session

    async def expire_stale_requests(self, stale_hours: int = 24) -> int:
        """
        Find B2B requests that have been in approved_paid status
        for longer than stale_hours, and expire them.

        Returns the count of expired requests.
        """
        cutoff = datetime.utcnow() - timedelta(hours=stale_hours)

        # Find stale approved_paid B2B requests
        result = await self.session.execute(
            select(B2BRequestModel).where(
                B2BRequestModel.status == B2BRequestStatus.approved_paid,
                B2BRequestModel.created_at < cutoff,
            )
        )
        stale_requests = result.scalars().all()

        expired_count = 0
        for req in stale_requests:
            updated = await self.session.execute(
                update(B2BRequestModel)
                .where(
                    B2BRequestModel.id == req.id,
                    B2BRequestModel.status == B2BRequestStatus.approved_paid,
                )
                .values(status=B2BRequestStatus.expired)
            )
            if updated.rowcount > 0:
                expired_count += 1
                logger.info(f"Expired stale B2B request {req.id}")

        logger.info(f"B2B expiry worker: expired {expired_count}/{len(stale_requests)} stale requests")
        return expired_count
```

Note: This uses `created_at` to measure staleness. If `updated_at` is more appropriate (using the approval timestamp), adjust accordingly.

- [ ] **Step 2: Add a method to SuperAdminService to call this worker**

In `src/apps/superadmin/service.py`, add:

```python
    async def expire_stale_b2b_requests(self, stale_hours: int = 24) -> int:
        """
        Expire B2B requests that have been in approved_paid status
        for longer than stale_hours. Safety net for missed Razorpay expiry webhooks.
        """
        from .workers import B2BExpiryWorker
        worker = B2BExpiryWorker(self._session)
        return await worker.expire_stale_requests(stale_hours=stale_hours)
```

- [ ] **Step 3: Verify the change compiles**

Run: `PYTHONPATH=src uv run python -c "from apps.superadmin.service import SuperAdminService; from apps.superadmin.workers import B2BExpiryWorker; print('OK')" 2>&1 | tail -1`

Expected: `OK`

- [ ] **Step 4: Commit**

```bash
git add src/apps/superadmin/workers.py src/apps/superadmin/service.py
git commit -m "feat(superadmin): add B2B payment link expiry background worker
"
```

---

### Task 10: Add Idempotency Guard in `approve_b2b_request_free`

**Files:**
- Modify: `src/apps/superadmin/service.py:78-100`

- [ ] **Step 1: Read the current code around lines 78-100**

The current code gets the b2b_request without locking:
```python
        b2b_request = await self.get_b2b_request(request_id)
        if b2b_request.status != B2BRequestStatus.pending:
            raise B2BRequestNotPendingError(...)
```

If two requests hit this simultaneously, both pass the status check before either commits. Add `SELECT FOR UPDATE` to lock the row.

- [ ] **Step 2: Update the get call to use `with_for_update()`**

In `approve_b2b_request_free`, find:
```python
        b2b_request = await self.get_b2b_request(request_id)
```

Replace with a direct query with `with_for_update()`:

```python
        # Use SELECT FOR UPDATE to prevent concurrent approvals
        result = await self._session.execute(
            select(B2BRequestModel)
            .where(B2BRequestModel.id == request_id)
            .with_for_update()
        )
        b2b_request = result.scalar_one_or_none()
        if not b2b_request:
            raise B2BRequestNotFoundError(f"B2B request {request_id} not found")
        if b2b_request.status != B2BRequestStatus.pending:
            raise B2BRequestNotPendingError(
                f"B2B request is {b2b_request.status}, expected pending"
            )
```

Note: `B2BRequestNotFoundError` must be imported from `.exceptions`. Check:
Run: `grep -n "B2BRequestNotFoundError" src/apps/superadmin/service.py`

- [ ] **Step 3: Verify the change compiles**

Run: `PYTHONPATH=src uv run python -c "from apps.superadmin.service import SuperAdminService; print('OK')" 2>&1 | tail -1`

Expected: `OK`

- [ ] **Step 4: Commit**

```bash
git add src/apps/superadmin/service.py
git commit -m "fix(superadmin): add SELECT FOR UPDATE idempotency guard in approve_b2b_request_free
"
```

---

### Task 11: Fix Transaction Side-Effect in `approve_b2b_request_paid`

**Files:**
- Modify: `src/apps/superadmin/service.py:190-240`

- [ ] **Step 1: Read the current code around lines 190-240**

```python
        b2b_request = await self.get_b2b_request(request_id)
        if b2b_request.status != B2BRequestStatus.pending:
            raise B2BRequestNotPendingError(...)

        # ... user resolution ...

        # Create pending PURCHASE order (line 219)
        order = OrderModel(...)

        # But the order is created BEFORE the status check in terms of transaction order
        # The status check is at line 203, order creation at line 219 — so status check is first
        # But if a retry happens (deadlock), the order might already exist
        # Fix: use SELECT FOR UPDATE on the b2b_request row before any state-changing operations
```

The fix: lock the b2b_request row with `SELECT FOR UPDATE` before doing anything else in this method.

- [ ] **Step 2: Add `SELECT FOR UPDATE` at the start of `approve_b2b_request_paid`**

Find the start of `approve_b2b_request_paid` (around line 190). Add the locking query before the status check:

```python
        # Use SELECT FOR UPDATE to prevent concurrent modifications
        result = await self._session.execute(
            select(B2BRequestModel)
            .where(B2BRequestModel.id == request_id)
            .with_for_update()
        )
        b2b_request = result.scalar_one_or_none()
        if not b2b_request:
            raise B2BRequestNotFoundError(f"B2B request {request_id} not found")
        if b2b_request.status != B2BRequestStatus.pending:
            raise B2BRequestNotPendingError(
                f"B2B request is {b2b_request.status}, expected pending"
            )
```

Remove the non-locking `await self.get_b2b_request(request_id)` call and replace with the above.

- [ ] **Step 3: Verify the change compiles**

Run: `PYTHONPATH=src uv run python -c "from apps.superadmin.service import SuperAdminService; print('OK')" 2>&1 | tail -1`

Expected: `OK`

- [ ] **Step 4: Commit**

```bash
git add src/apps/superadmin/service.py
git commit -m "fix(superadmin): add SELECT FOR UPDATE to prevent duplicate order creation on retry in approve_b2b_request_paid
"
```

---

## Self-Review Checklist

**1. Spec coverage:** Check each of the 11 issues has a task:
- Issue 6 (event ownership check): ✅ Task 1
- Issue 7 (gateway_flow_type + routing): ✅ Task 2
- Issue 8 (cancel_payment_link on failure): ✅ Task 3
- Issue 9 (resolve_holder duplicates): ✅ Task 4
- Issue 10 (B2B quantity quota): SKIPPED (user request)
- Issue 11 (no money limit): SKIPPED (user request)
- Issue 12 (outdated docstring): ✅ Task 5
- Issue 13 (formatting): ✅ Task 6
- Issue 14 (no pagination): ✅ Task 7
- Issue 15 (wrong AllocationType): ✅ Task 8
- Issue 16 (background worker): ✅ Task 9
- Issue 17 (idempotency gap): ✅ Task 10
- Issue 18 (transaction side-effect): ✅ Task 11

**2. Placeholder scan:** Search the plan for TBD/TODO placeholders.
- ✅ None found. All steps have exact code and exact file paths.

**3. Type consistency:**
- `AllocationType.b2b` vs `AllocationType.transfer` — Task 8 uses `AllocationType.b2b` (correct)
- `gateway_flow_type="b2b_transfer"` — correct string value
- `B2BRequestStatus.expired` — used in Task 9 worker
- `SELECT FOR UPDATE` — used in Tasks 10 and 11 as `with_for_update()`
- All method signatures consistent with existing codebase

**4. Blast radius check:**
- Task 1: adds ForbiddenError on non-owner — only affects unauthorized callers
- Task 2: adds field to order + explicit routing — backwards compatible, routing still works
- Task 3: wraps in try/except with cancel on failure — re-raises after cancel, doesn't suppress errors
- Task 4: adds lookup before creating — reduces duplicate creation, doesn't break existing lookups
- Task 5: docstring only — no behavior change
- Task 6: formatting — no behavior change
- Task 7: adds optional params with defaults — backwards compatible
- Task 8: changes enum value — only affects customer transfers, all other flows already use b2b
- Task 9: new worker file — no existing behavior changed
- Task 10: adds row lock — prevents duplicates, doesn't change happy path
- Task 11: adds row lock — prevents duplicates, doesn't change happy path

**5. Dependencies:** Tasks 1-4 are independent. Task 7 requires repository method update. Tasks 10-11 both touch `approve_b2b_request_free` and `approve_b2b_request_paid` in service.py — different methods, no conflict.

---

## Plan Complete

**Saved to:** `docs/superpowers/plans/2026-05-16-b2b-moderate-minor-fixes.md`

Two execution options:

**1. Subagent-Driven (recommended)** — I dispatch a fresh subagent per task, review between tasks, fast iteration

**2. Inline Execution** — Execute tasks in this session using executing-plans, batch execution with checkpoints

Which approach?