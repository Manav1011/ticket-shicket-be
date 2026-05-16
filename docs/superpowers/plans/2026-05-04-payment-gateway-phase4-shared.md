# Payment Gateway Phase 4 — Shared Foundation

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add `TransferMode` enum, fix `clear_locks_for_order` bug, implement `OrderPaymentRepository`, add `payment_url` to response schemas. These are prerequisites for all three transfer-type plans.

**Architecture:** Shared infrastructure changes that all paid-flow tasks depend on. Task 0 fixes a lock-clearing bug that breaks paid flows. Tasks 1-2 add the repository and schema plumbing needed by Tasks 4A/4B/4C.

**Tech Stack:** SQLAlchemy async, Pydantic/FastAPI, Razorpay SDK.

---

## File Structure

**Files modified:**
- `src/apps/allocation/enums.py` — add `TransferMode` enum
- `src/apps/organizer/request.py` — `CreateB2BTransferRequest.mode` → `TransferMode` enum
- `src/apps/organizer/request.py` — `CreateCustomerTransferRequest.mode` → `TransferMode` enum
- `src/apps/organizer/response.py` — `B2BTransferResponse` + `CustomerTransferResponse` add `payment_url`
- `src/apps/ticketing/repository.py` — `clear_locks_for_order` fix
- `src/apps/payment_gateway/repositories/order.py` — fill stub → real implementation

**Files created:**
- `tests/apps/payment_gateway/test_order_repository.py`
- `tests/apps/organizer/test_response.py`
- `tests/apps/ticketing/test_repository.py` (extend existing)

---

### Task 0: Add `TransferMode` enum and fix `clear_locks_for_order` lock type

#### Part A — `TransferMode` enum

**Files:**
- Modify: `src/apps/allocation/enums.py`
- Test: `tests/apps/organizer/test_request.py` (extend existing or create)

- [ ] **Step 1: Write the failing test**

```python
# tests/apps/organizer/test_request.py
import pytest
from apps.organizer.request import CreateB2BTransferRequest, CreateCustomerTransferRequest
from apps.allocation.enums import TransferMode


def test_b2b_transfer_request_mode_accepts_transfer_mode_enum():
    req = CreateB2BTransferRequest(
        reseller_id="00000000-0000-0000-0000-000000000001",
        quantity=2,
        mode=TransferMode.FREE,
    )
    assert req.mode == TransferMode.FREE


def test_b2b_transfer_request_mode_accepts_paid_string():
    req = CreateB2BTransferRequest(
        reseller_id="00000000-0000-0000-0000-000000000001",
        quantity=2,
        mode="paid",
    )
    assert req.mode == TransferMode.PAID


def test_customer_transfer_request_mode_accepts_transfer_mode_enum():
    req = CreateCustomerTransferRequest(
        phone="+919999999999",
        quantity=1,
        event_day_id="00000000-0000-0000-0000-000000000001",
        mode=TransferMode.PAID,
    )
    assert req.mode == TransferMode.PAID
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/apps/organizer/test_request.py -v`
Expected: FAIL — `TransferMode` not defined

- [ ] **Step 3: Write implementation**

In `src/apps/allocation/enums.py`, add:

```python
class TransferMode(str, Enum):
    FREE = "free"
    PAID = "paid"
```

Then update request models in `src/apps/organizer/request.py`:

```python
from apps.allocation.enums import TransferMode

class CreateB2BTransferRequest(CamelCaseModel):
    reseller_id: UUID
    quantity: int = Field(gt=0)
    event_day_id: UUID | None = None
    mode: TransferMode = TransferMode.FREE


class CreateCustomerTransferRequest(CamelCaseModel):
    phone: str | None = None
    email: str | None = None
    quantity: int = Field(gt=0)
    event_day_id: UUID
    mode: TransferMode = TransferMode.FREE

    @model_validator(mode='after')
    def must_have_phone_or_email(self):
        if not self.phone and not self.email:
            raise ValueError('Either phone or email must be provided')
        return self
```

Remove the `@field_validator('mode')` from `CreateCustomerTransferRequest` — the enum handles validation.

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/apps/organizer/test_request.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/apps/allocation/enums.py src/apps/organizer/request.py tests/apps/organizer/test_request.py
git commit -m "feat(allocation): add TransferMode enum and use it in transfer requests"
```

---

#### Part B — Fix `clear_locks_for_order` to handle both `"order"` and `"transfer"` lock types

**Files:**
- Modify: `src/apps/ticketing/repository.py:313-329`
- Test: `tests/apps/ticketing/test_repository.py` (add tests)

- [ ] **Step 1: Write the failing test**

```python
# tests/apps/ticketing/test_repository.py
import pytest
from uuid import uuid4
from unittest.mock import AsyncMock
from apps.ticketing.repository import TicketingRepository


@pytest.mark.asyncio
async def test_clear_locks_for_order_clears_transfer_locks():
    """clear_locks_for_order must clear locks created with lock_reference_type='transfer'."""
    session = AsyncMock()
    session.execute = AsyncMock()
    repo = TicketingRepository(session)

    order_id = uuid4()
    await repo.clear_locks_for_order(order_id)

    call_args = session.execute.call_args
    update_stmt = call_args[0][0]
    update_text = str(update_stmt)
    assert "transfer" in update_text


@pytest.mark.asyncio
async def test_clear_locks_for_order_clears_order_locks():
    """clear_locks_for_order must still clear locks with lock_reference_type='order'."""
    session = AsyncMock()
    session.execute = AsyncMock()
    repo = TicketingRepository(session)

    order_id = uuid4()
    await repo.clear_locks_for_order(order_id)

    call_args = session.execute.call_args
    update_stmt = call_args[0][0]
    update_text = str(update_stmt)
    assert "'order'" in update_text
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/apps/ticketing/test_repository.py::test_clear_locks_for_order_clears_transfer_locks tests/apps/ticketing/test_repository.py::test_clear_locks_for_order_clears_order_locks -v`
Expected: FAIL — current implementation only handles `"order"` type

- [ ] **Step 3: Write the fix**

In `src/apps/ticketing/repository.py`, change `clear_locks_for_order` (around line 313-329):

```python
# OLD:
await self._session.execute(
    update(TicketModel)
    .where(
        TicketModel.lock_reference_type == "order",
        TicketModel.lock_reference_id == order_id,
    )
    ...

# NEW:
await self._session.execute(
    update(TicketModel)
    .where(
        TicketModel.lock_reference_type.in_(["order", "transfer"]),
        TicketModel.lock_reference_id == order_id,
    )
    ...
)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/apps/ticketing/test_repository.py::test_clear_locks_for_order_clears_transfer_locks tests/apps/ticketing/test_repository.py::test_clear_locks_for_order_clears_order_locks -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/apps/ticketing/repository.py tests/apps/ticketing/test_repository.py
git commit -m "fix(ticketing): clear_locks_for_order handles both 'order' and 'transfer' lock types"
```

---

### Task 1: Implement `OrderPaymentRepository`

**Files:**
- Modify: `src/apps/payment_gateway/repositories/order.py` (replace stub with real implementation)
- Test: `tests/apps/payment_gateway/test_order_repository.py` (create if not exists)

**Pre-execution:** Check if `tests/apps/payment_gateway/test_order_repository.py` already exists. If it does, add tests to it instead of creating a new file.

- [ ] **Step 1: Write the failing test**

```python
# tests/apps/payment_gateway/test_order_repository.py
import pytest
from uuid import uuid4
from unittest.mock import AsyncMock, MagicMock
from apps.payment_gateway.repositories.order import OrderPaymentRepository


@pytest.fixture
def mock_session():
    session = AsyncMock()
    session.execute = AsyncMock()
    session.flush = AsyncMock()
    return session


@pytest.fixture
def repo(mock_session):
    return OrderPaymentRepository(mock_session)


@pytest.mark.asyncio
async def test_update_pending_order_on_payment_link_created(repo, mock_session):
    order_id = uuid4()
    gateway_order_id = "plink_abc123"
    gateway_response = {"id": "plink_abc123", "short_url": "https://razorpay.in/abc"}
    short_url = "https://razorpay.in/abc"

    await repo.update_pending_order_on_payment_link_created(
        order_id=order_id,
        gateway_order_id=gateway_order_id,
        gateway_response=gateway_response,
        short_url=short_url,
    )

    mock_session.execute.assert_called_once()
    mock_session.flush.assert_called_once()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/apps/payment_gateway/test_order_repository.py -v`
Expected: FAIL — function not implemented

- [ ] **Step 3: Write implementation**

```python
# src/apps/payment_gateway/repositories/order.py
"""OrderPaymentRepository — update payment fields on OrderModel."""
from uuid import UUID

from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from apps.allocation.models import OrderModel


class OrderPaymentRepository:
    """Updates payment gateway fields on OrderModel."""

    def __init__(self, session: AsyncSession):
        self._session = session

    async def update_pending_order_on_payment_link_created(
        self,
        order_id: UUID,
        gateway_order_id: str,
        gateway_response: dict,
        short_url: str,
    ) -> None:
        """
        Update order with Razorpay payment link details after link is created.
        Sets gateway_order_id, gateway_response, short_url.
        Called when a paid transfer flow creates a payment link.
        """
        await self._session.execute(
            update(OrderModel)
            .where(OrderModel.id == order_id)
            .values(
                gateway_order_id=gateway_order_id,
                gateway_response=gateway_response,
                short_url=short_url,
            )
        )
        await self._session.flush()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/apps/payment_gateway/test_order_repository.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/apps/payment_gateway/repositories/order.py tests/apps/payment_gateway/test_order_repository.py
git commit -m "feat(payment-gateway): add OrderPaymentRepository for order payment field updates"
```

---

### Task 2: Add `payment_url` to response schemas

**Files:**
- Modify: `src/apps/organizer/response.py:60-67` and `src/apps/organizer/response.py:76-88`
- Test: `tests/apps/organizer/test_response.py` (create if not exists)

- [ ] **Step 1: Write the failing test**

```python
# tests/apps/organizer/test_response.py
import pytest
from uuid import uuid4
from apps.organizer.response import B2BTransferResponse, CustomerTransferResponse
from apps.allocation.enums import TransferMode


def test_b2b_transfer_response_has_payment_url_field():
    resp = B2BTransferResponse(
        transfer_id=uuid4(),
        status="pending_payment",
        ticket_count=2,
        reseller_id=uuid4(),
        mode=TransferMode.PAID,
        message="Payment link sent",
    )
    assert hasattr(resp, "payment_url")
    assert resp.payment_url is None


def test_b2b_transfer_response_payment_url_set():
    resp = B2BTransferResponse(
        transfer_id=uuid4(),
        status="pending_payment",
        ticket_count=2,
        reseller_id=uuid4(),
        mode=TransferMode.PAID,
        payment_url="https://razorpay.in/abc",
    )
    assert resp.payment_url == "https://razorpay.in/abc"


def test_customer_transfer_response_has_payment_url_field():
    resp = CustomerTransferResponse(
        transfer_id=uuid4(),
        status="pending_payment",
        ticket_count=1,
        mode=TransferMode.PAID,
        payment_url="https://razorpay.in/xyz",
    )
    assert resp.payment_url == "https://razorpay.in/xyz"


def test_customer_transfer_response_mode_accepts_transfer_mode_enum():
    resp = CustomerTransferResponse(
        transfer_id=uuid4(),
        status="pending_payment",
        ticket_count=1,
        mode=TransferMode.FREE,
    )
    assert resp.mode == TransferMode.FREE
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/apps/organizer/test_response.py -v`
Expected: FAIL — `payment_url` field not found

- [ ] **Step 3: Write implementation**

In `src/apps/organizer/response.py`, add `payment_url: str | None = None` to both response models and update `mode` to use `TransferMode`:

```python
from apps.allocation.enums import TransferMode


class B2BTransferResponse(CamelCaseModel):
    transfer_id: UUID
    status: str  # "completed" | "not_implemented" | "pending_payment"
    ticket_count: int
    reseller_id: UUID
    mode: TransferMode
    message: str | None = None
    payment_url: str | None = None  # Razorpay short_url for paid mode


class CustomerTransferResponse(CamelCaseModel):
    transfer_id: UUID
    status: str  # "completed" | "not_implemented" | "pending_payment"
    ticket_count: int
    mode: TransferMode
    message: str | None = None
    payment_url: str | None = None  # Razorpay short_url for paid mode
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/apps/organizer/test_response.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/apps/organizer/response.py tests/apps/organizer/test_response.py
git commit -m "feat(organizer): add payment_url field and TransferMode to transfer responses"
```

---

## Self-Review

**1. Spec coverage:**
- `TransferMode` enum ✅ (replaces string `"free"`/`"paid"` comparisons)
- Task 0 Part B: `clear_locks_for_order` handles both lock types ✅ (paid flow bug fix)
- Task 1: `OrderPaymentRepository` ✅
- Task 2: `payment_url` in responses ✅

**2. Placeholder scan:** No "TBD", "TODO", or placeholder patterns.

**3. Type consistency:**
- `TransferMode` used in both request and response models ✅
- `mode: TransferMode` vs `mode: str` in existing models — consistent ✅
- `OrderPaymentRepository.update_pending_order_on_payment_link_created(order_id, gateway_order_id, gateway_response, short_url)` ✅ (matches callers in Tasks 4A/4B/4C)

**4. Dependency order:**
- Part A must run before Part B (or they can run in parallel — different files)
- Task 1 and 2 are independent of Part A and Part B — all can run in parallel once Part A adds the enum
- All tasks in this plan must complete before starting Plans 4A, 4B, 4C

**5. Pre-existing issues NOT fixed here (Phase 5 scope):**
- `lock_tickets_for_transfer` uses `datetime.utcnow()` (deprecated)
- Expiry worker's `clear_ticket_locks` only handles `lock_reference_type == "order"` — fix to handle `"transfer"` type too

---

**What's left for Phase 5:** Derive `final_amount` from B2B ticket type price, real SMS/WhatsApp/Email provider integration, `datetime.utcnow()` deprecation fixes.

Plan complete and saved to `docs/superpowers/plans/2026-05-04-payment-gateway-phase4-shared.md`.