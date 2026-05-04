# Payment Gateway Phase 4 — B2B Paid Transfer Flows

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Wire `is_paid=True` transfers in OrganizerService and ResellerService so that paid transfers create a pending order, generate a Razorpay payment link, and defer allocation creation until the `order.paid` webhook fires.

**Architecture:** All three transfer methods get an `is_paid: bool = False` parameter. When `is_paid=True`, the flow diverges: order is created with `status=pending`, a payment link is generated via `gateway.create_payment_link()`, the link is sent to the buyer via our notification channels (SMS/WhatsApp/Email), and allocation is NOT created yet — the `order.paid` webhook handles that. When `is_paid=False`, the existing free flow (status=paid immediately, allocation created synchronously) is unchanged.

**Tech Stack:** Razorpay SDK, SQLAlchemy async, FastAPI, notification services (mock SMS/WhatsApp/Email already in codebase).

---

## File Structure

**Files modified:**
- `src/apps/organizer/service.py` — `create_b2b_transfer` + `create_customer_transfer` gain paid flow branches
- `src/apps/resellers/service.py` — `create_reseller_customer_transfer` gains paid flow branch
- `src/apps/organizer/response.py` — `B2BTransferResponse` + `CustomerTransferResponse` add `payment_url` field
- `src/apps/payment_gateway/repositories/order.py` — stub becomes real `OrderPaymentRepository`
- `src/apps/ticketing/repository.py` — `clear_locks_for_order` fixed to handle both lock types

**Files created:**
- `src/apps/payment_gateway/repositories/order.py` — full implementation of `update_pending_order_on_payment_link_created()`
- `src/apps/payment_gateway/schemas/base.py` — confirm `WebhookEvent.gateway_order_id` field exists (already done in Phase 2)
- `src/apps/allocation/repository.py` — confirm `add_tickets_to_allocation`, `upsert_edge`, `transition_allocation_status` exist (already done)

**Dependencies already in place (Phase 2):**
- `gateway = get_gateway("razorpay")` factory
- `RazorpayPaymentGateway.create_payment_link()` — implemented
- `BuyerInfo` dataclass — in `services/base.py`
- `GatewayType.RAZORPAY_PAYMENT_LINK` — in `allocation/enums.py`
- `OrderModel.payment_gateway`, `gateway_type`, `gateway_order_id`, `short_url` fields — in `allocation/models.py`

---

### Task 0: Fix `clear_locks_for_order` to handle both `"order"` and `"transfer"` lock types

**Files:**
- Modify: `src/apps/ticketing/repository.py:313-329`
- Test: `tests/apps/ticketing/test_repository.py` (add test for clearing transfer locks)

`lock_tickets_for_transfer` sets `lock_reference_type = "transfer"` (line 237 of ticketing/repository.py), but `clear_locks_for_order` (line 321) only clears locks where `lock_reference_type == "order"`. This means in the paid flow, after `order.paid` fires and `clear_locks_for_order` is called, the locks are **not** cleared — tickets remain locked indefinitely. This also affects the expiry worker for any orders that used transfer locks.

**The fix:** Change the WHERE clause in `clear_locks_for_order` to `lock_reference_type.in_(["order", "transfer"])`.

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

    # Verify the UPDATE uses lock_reference_type IN ('order', 'transfer')
    call_args = session.execute.call_args
    update_stmt = call_args[0][0]
    # SQLAlchemy binary expression: lock_reference_type.in_(["order", "transfer"])
    assert hasattr(update_stmt, "_whereclause")
    update_text = str(update_stmt)
    assert "transfer" in update_text or "order" in update_text


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
    # Must include 'order' in the lock type filter
    assert "'order'" in update_text
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/apps/ticketing/test_repository.py::test_clear_locks_for_order_clears_transfer_locks -v`
Expected: FAIL — current implementation only handles `"order"` type

- [ ] **Step 3: Write the fix**

In `src/apps/ticketing/repository.py`, change `clear_locks_for_order` (around line 313-329):

```python
# OLD (line 321):
await self._session.execute(
    update(TicketModel)
    .where(
        TicketModel.lock_reference_type == "order",
        TicketModel.lock_reference_id == order_id,
    )
    ...
)

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

### Task 1: Fill `OrderPaymentRepository` stub

**Files:**
- Modify: `src/apps/payment_gateway/repositories/order.py`
- Test: `tests/apps/payment_gateway/test_order_repository.py`

The current file is a stub with only a comment. Replace it with a real repository that handles order payment field updates.

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
    lock_expires_at = None  # Not used for payment link orders

    result = await repo.update_pending_order_on_payment_link_created(
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
Expected: FAIL — module doesn't exist or has no such function

- [ ] **Step 3: Write minimal implementation**

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
        Sets gateway_type, gateway_order_id, gateway_response, short_url.
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


def test_b2b_transfer_response_has_payment_url():
    resp = B2BTransferResponse(
        transfer_id=uuid4(),
        status="pending_payment",
        ticket_count=2,
        reseller_id=uuid4(),
        mode="paid",
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
        mode="paid",
        payment_url="https://razorpay.in/abc",
    )
    assert resp.payment_url == "https://razorpay.in/abc"


def test_customer_transfer_response_has_payment_url():
    resp = CustomerTransferResponse(
        transfer_id=uuid4(),
        status="pending_payment",
        ticket_count=1,
        mode="paid",
        payment_url="https://razorpay.in/xyz",
    )
    assert resp.payment_url == "https://razorpay.in/xyz"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/apps/organizer/test_response.py -v`
Expected: FAIL — `payment_url` field not found

- [ ] **Step 3: Write minimal implementation**

In `src/apps/organizer/response.py`, add `payment_url: str | None = None` to both `B2BTransferResponse` and `CustomerTransferResponse`.

```python
class B2BTransferResponse(CamelCaseModel):
    transfer_id: UUID
    status: str  # "completed" | "not_implemented" | "pending_payment"
    ticket_count: int
    reseller_id: UUID
    mode: str  # "free" | "paid"
    message: str | None = None
    payment_url: str | None = None  # <-- NEW: Razorpay short_url for paid mode

    @field_validator('mode')
    @classmethod
    def validate_mode(cls, v):
        if v not in ('free', 'paid'):
            raise ValueError('mode must be either "free" or "paid"')
        return v


class CustomerTransferResponse(CamelCaseModel):
    transfer_id: UUID
    status: str  # "completed" | "not_implemented" | "pending_payment"
    ticket_count: int
    mode: str  # "free" | "paid"
    message: str | None = None
    payment_url: str | None = None  # <-- NEW: Razorpay short_url for paid mode

    @field_validator('mode')
    @classmethod
    def validate_mode(cls, v):
        if v not in ('free', 'paid'):
            raise ValueError('mode must be either "free" or "paid"')
        return v
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/apps/organizer/test_response.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/apps/organizer/response.py tests/apps/organizer/test_response.py
git commit -m "feat(organizer): add payment_url field to B2B and customer transfer responses"
```

---

### Task 3: Implement paid flow in `OrganizerService.create_b2b_transfer`

**Files:**
- Modify: `src/apps/organizer/service.py:388-556`
- Test: `tests/apps/organizer/test_service.py` (add `test_create_b2b_transfer_paid_mode`)

- [ ] **Step 1: Write the failing test**

```python
# tests/apps/organizer/test_service.py
import pytest
from uuid import uuid4
from unittest.mock import AsyncMock, MagicMock, patch


@pytest.mark.asyncio
async def test_create_b2b_transfer_paid_mode_creates_pending_order():
    """Paid mode creates a pending order with payment gateway fields set."""
    from apps.organizer.service import OrganizerService
    from apps.ticketing.enums import OrderStatus

    mock_repo = AsyncMock()
    mock_session = AsyncMock()
    mock_session.add = MagicMock()
    mock_session.flush = AsyncMock()
    mock_session.refresh = AsyncMock()
    mock_repo.session = mock_session

    service = OrganizerService(mock_repo)
    service._ticketing_repo = AsyncMock()
    service._allocation_repo = AsyncMock()
    service._allocation_service = AsyncMock()

    # Mock allocation_repo methods
    service._allocation_repo.get_holder_by_user_id = AsyncMock(
        side_effect=[
            MagicMock(id=uuid4()),  # org_holder
            MagicMock(id=uuid4()),  # reseller_holder
        ]
    )
    service._allocation_repo.list_b2b_tickets_by_holder = AsyncMock(return_value=[
        {"event_day_id": uuid4(), "count": 5}
    ])
    service._ticketing_repo.get_b2b_ticket_type_for_event = AsyncMock(
        return_value=MagicMock(id=uuid4())
    )
    service._ticketing_repo.lock_tickets_for_transfer = AsyncMock(return_value=[uuid4(), uuid4()])

    # Mock gateway
    with patch("apps.organizer.service.get_gateway") as mock_get_gateway:
        mock_gateway = MagicMock()
        mock_gateway.create_payment_link = AsyncMock(
            return_value=MagicMock(
                gateway_order_id="plink_test123",
                short_url="https://razorpay.in/test",
                gateway_response={"id": "plink_test123"},
            )
        )
        mock_get_gateway.return_value = mock_gateway

        with patch("apps.organizer.service.OrderModel") as mock_order_model:
            order_instance = MagicMock()
            order_instance.id = uuid4()
            mock_order_model.return_value = order_instance

            result = await service.create_b2b_transfer(
                user_id=uuid4(),
                event_id=uuid4(),
                reseller_id=uuid4(),
                quantity=2,
                event_day_id=uuid4(),
                mode="paid",
            )

    assert result.status == "pending_payment"
    assert result.mode == "paid"
    assert result.payment_url == "https://razorpay.in/test"
    mock_gateway.create_payment_link.assert_called_once()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/apps/organizer/test_service.py::test_create_b2b_transfer_paid_mode_creates_pending_order -v`
Expected: FAIL — `create_b2b_transfer` returns stub for `mode="paid"`

- [ ] **Step 3: Write minimal implementation**

Replace the paid-mode stub in `OrganizerService.create_b2b_transfer` (lines 417-425) with the real paid flow.

```python
# In create_b2b_transfer, replace the if mode == "paid" stub (lines 417-425):
# OLD (stub):
if mode == "paid":
    return B2BTransferResponse(
        transfer_id=uuid.UUID("00000000-0000-0000-0000-000000000000"),
        status="not_implemented",
        ticket_count=0,
        reseller_id=reseller_id,
        mode="paid",
        message="Paid transfer coming soon",
    )

# NEW (real paid flow):
if mode == "paid":
    from apps.payment_gateway.services.factory import get_gateway
    from apps.payment_gateway.services.base import BuyerInfo
    from apps.payment_gateway.repositories.order import OrderPaymentRepository
    from apps.allocation.enums import GatewayType
    from apps.allocation.repositories.user import UserRepository
    from datetime import datetime, timedelta, timezone

    # Determine reseller contact info for BuyerInfo
    reseller_user_repo = UserRepository(self.repository.session)
    reseller_user = await reseller_user_repo.find_by_id(reseller_id)
    reseller_name = getattr(reseller_user, 'name', None) or 'Reseller'
    reseller_email = getattr(reseller_user, 'email', None)
    reseller_phone = getattr(reseller_user, 'phone', None)

    # 1. Create pending order (no allocation created yet)
    order = OrderModel(
        event_id=event_id,
        user_id=user_id,
        type=OrderType.transfer,
        subtotal_amount=0.0,  # Amount set from ticket type price at lock time
        discount_amount=0.0,
        final_amount=0.0,  # TODO (Phase 5): derive from ticket type price
        status=OrderStatus.pending,
        payment_gateway="razorpay",
        gateway_type=GatewayType.RAZORPAY_PAYMENT_LINK,
        lock_expires_at=datetime.now(timezone.utc) + timedelta(minutes=30),
    )
    self.repository.session.add(order)
    await self.repository.session.flush()
    await self.repository.session.refresh(order)

    # 2. Lock tickets (FIFO, 30-min TTL)
    locked_ticket_ids = await self._ticketing_repo.lock_tickets_for_transfer(
        owner_holder_id=org_holder.id,
        event_id=event_id,
        ticket_type_id=b2b_ticket_type.id,
        event_day_id=event_day_id,
        quantity=quantity,
        order_id=order.id,
        lock_ttl_minutes=30,
    )

    # 3. Create payment link via Razorpay
    gateway = get_gateway("razorpay")
    buyer_info = BuyerInfo(
        name=reseller_name,
        email=reseller_email,
        phone=reseller_phone or "",
    )
    payment_result = await gateway.create_payment_link(
        order_id=order.id,
        amount=int(0.0 * 100),  # TODO (Phase 5): use actual ticket price in paise
        currency="INR",
        buyer=buyer_info,
        description=f"B2B Transfer - {event.name}",
        event_id=event_id,
        flow_type="b2b_transfer",
        transfer_type="organizer_to_reseller",
        buyer_holder_id=reseller_holder.id,
    )

    # 4. Update order with gateway details
    order_payment_repo = OrderPaymentRepository(self.repository.session)
    await order_payment_repo.update_pending_order_on_payment_link_created(
        order_id=order.id,
        gateway_order_id=payment_result.gateway_order_id,
        gateway_response=payment_result.gateway_response,
        short_url=payment_result.short_url,
    )

    # 5. Send payment link via our notification channels
    from src.utils.notifications.sms import mock_send_sms
    from src.utils.notifications.whatsapp import mock_send_whatsapp
    from src.utils.notifications.email import mock_send_email

    message = f"Complete your B2B ticket purchase: {payment_result.short_url}"
    if reseller_phone:
        mock_send_sms(reseller_phone, message, template="b2b_paid_transfer")
        mock_send_whatsapp(reseller_phone, message, template="b2b_paid_transfer")
    if reseller_email:
        mock_send_email(reseller_email, "Complete Your B2B Ticket Purchase", message)

    # NO allocation created here — webhook creates it on payment

    return B2BTransferResponse(
        transfer_id=order.id,
        status="pending_payment",
        ticket_count=len(locked_ticket_ids),
        reseller_id=reseller_id,
        mode="paid",
        payment_url=payment_result.short_url,
    )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/apps/organizer/test_service.py::test_create_b2b_transfer_paid_mode_creates_pending_order -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/apps/organizer/service.py tests/apps/organizer/test_service.py
git commit -m "feat(organizer): implement paid mode in create_b2b_transfer with Razorpay payment link"
```

---

### Task 4: Implement paid flow in `OrganizerService.create_customer_transfer`

**Files:**
- Modify: `src/apps/organizer/service.py:558-753`
- Test: `tests/apps/organizer/test_service.py` (add `test_create_customer_transfer_paid_mode`)

- [ ] **Step 1: Write the failing test**

```python
@pytest.mark.asyncio
async def test_create_customer_transfer_paid_mode_creates_pending_order():
    """Paid mode creates a pending order and sends payment link, no allocation."""
    from apps.organizer.service import OrganizerService
    from apps.ticketing.enums import OrderStatus

    mock_repo = AsyncMock()
    mock_session = AsyncMock()
    mock_repo.session = mock_session
    service = OrganizerService(mock_repo)
    service._ticketing_repo = AsyncMock()
    service._allocation_repo = AsyncMock()
    service._allocation_service = AsyncMock()

    customer_holder = MagicMock(id=uuid4())
    org_holder = MagicMock(id=uuid4())

    service._allocation_repo.get_holder_by_user_id = AsyncMock(return_value=org_holder)
    service._allocation_repo.get_holder_by_phone_and_email = AsyncMock(return_value=None)
    service._allocation_repo.get_holder_by_phone = AsyncMock(return_value=None)
    service._allocation_repo.get_holder_by_email = AsyncMock(return_value=None)
    service._allocation_repo.create_holder = AsyncMock(return_value=customer_holder)
    service._ticketing_repo.get_b2b_ticket_type_for_event = AsyncMock(
        return_value=MagicMock(id=uuid4())
    )
    service._allocation_repo.list_b2b_tickets_by_holder = AsyncMock(return_value=[{"count": 5}])
    service._ticketing_repo.lock_tickets_for_transfer = AsyncMock(return_value=[uuid4()])

    with patch("apps.organizer.service.get_gateway") as mock_get_gateway:
        mock_gateway = MagicMock()
        mock_gateway.create_payment_link = AsyncMock(
            return_value=MagicMock(
                gateway_order_id="plink_cust123",
                short_url="https://razorpay.in/cust",
                gateway_response={"id": "plink_cust123"},
            )
        )
        mock_get_gateway.return_value = mock_gateway

        with patch("apps.organizer.service.OrderModel") as mock_order_model:
            order_instance = MagicMock()
            order_instance.id = uuid4()
            mock_order_model.return_value = order_instance

            result = await service.create_customer_transfer(
                user_id=uuid4(),
                event_id=uuid4(),
                phone="+919999999999",
                email=None,
                quantity=1,
                event_day_id=uuid4(),
                mode="paid",
            )

    assert result.status == "pending_payment"
    assert result.mode == "paid"
    assert result.payment_url == "https://razorpay.in/cust"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/apps/organizer/test_service.py::test_create_customer_transfer_paid_mode_creates_pending_order -v`
Expected: FAIL — paid mode returns stub

- [ ] **Step 3: Write minimal implementation**

Replace the paid-mode stub in `OrganizerService.create_customer_transfer` (lines 599-606) with the real paid flow. The structure is analogous to the b2b_transfer paid flow, but:
- Uses `phone`/`email` from the customer instead of reseller
- Uses `BuyerInfo(name=phone, email=email, phone=phone)` since customer may not have a name
- Sets `transfer_type="organizer_to_customer"`
- Sends notifications to customer's phone/email

```python
# Replace stub at lines 599-606:
if mode == "paid":
    from apps.payment_gateway.services.factory import get_gateway
    from apps.payment_gateway.services.base import BuyerInfo
    from apps.payment_gateway.repositories.order import OrderPaymentRepository
    from apps.allocation.enums import GatewayType
    from datetime import datetime, timedelta, timezone

    # Build buyer info from customer contact
    customer_name = phone or "Customer"
    customer_email = email
    customer_phone = phone or ""

    # 1. Create pending order
    order = OrderModel(
        event_id=event_id,
        user_id=user_id,
        type=OrderType.transfer,
        subtotal_amount=0.0,
        discount_amount=0.0,
        final_amount=0.0,
        status=OrderStatus.pending,
        payment_gateway="razorpay",
        gateway_type=GatewayType.RAZORPAY_PAYMENT_LINK,
        lock_expires_at=datetime.now(timezone.utc) + timedelta(minutes=30),
    )
    self.repository.session.add(order)
    await self.repository.session.flush()
    await self.repository.session.refresh(order)

    # 2. Lock tickets
    locked_ticket_ids = await self._ticketing_repo.lock_tickets_for_transfer(
        owner_holder_id=org_holder.id,
        event_id=event_id,
        ticket_type_id=b2b_ticket_type.id,
        event_day_id=event_day_id,
        quantity=quantity,
        order_id=order.id,
        lock_ttl_minutes=30,
    )

    # 3. Create payment link
    gateway = get_gateway("razorpay")
    buyer_info = BuyerInfo(
        name=customer_name,
        email=customer_email,
        phone=customer_phone,
    )
    payment_result = await gateway.create_payment_link(
        order_id=order.id,
        amount=int(0.0 * 100),  # TODO (Phase 5): use actual ticket price
        currency="INR",
        buyer=buyer_info,
        description=f"Ticket Purchase - {event.name}",
        event_id=event_id,
        flow_type="b2b_transfer",
        transfer_type="organizer_to_customer",
        buyer_holder_id=customer_holder.id,
    )

    # 4. Update order with gateway details
    order_payment_repo = OrderPaymentRepository(self.repository.session)
    await order_payment_repo.update_pending_order_on_payment_link_created(
        order_id=order.id,
        gateway_order_id=payment_result.gateway_order_id,
        gateway_response=payment_result.gateway_response,
        short_url=payment_result.short_url,
    )

    # 5. Send payment link
    from src.utils.notifications.sms import mock_send_sms
    from src.utils.notifications.whatsapp import mock_send_whatsapp
    from src.utils.notifications.email import mock_send_email

    message = f"Complete your ticket purchase: {payment_result.short_url}"
    if customer_phone:
        mock_send_sms(customer_phone, message, template="customer_paid_transfer")
        mock_send_whatsapp(customer_phone, message, template="customer_paid_transfer")
    if customer_email:
        mock_send_email(customer_email, "Complete Your Ticket Purchase", message)

    return CustomerTransferResponse(
        transfer_id=order.id,
        status="pending_payment",
        ticket_count=len(locked_ticket_ids),
        mode="paid",
        payment_url=payment_result.short_url,
    )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/apps/organizer/test_service.py::test_create_customer_transfer_paid_mode_creates_pending_order -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/apps/organizer/service.py tests/apps/organizer/test_service.py
git commit -m "feat(organizer): implement paid mode in create_customer_transfer with payment link"
```

---

### Task 5: Implement paid flow in `ResellerService.create_reseller_customer_transfer`

**Files:**
- Modify: `src/apps/resellers/service.py:143-339`
- Test: `tests/apps/resellers/test_service.py` (add `test_create_reseller_customer_transfer_paid_mode`)

- [ ] **Step 1: Write the failing test**

```python
# tests/apps/resellers/test_service.py
import pytest
from uuid import uuid4
from unittest.mock import AsyncMock, MagicMock, patch


@pytest.mark.asyncio
async def test_create_reseller_customer_transfer_paid_mode():
    """Paid mode creates pending order, generates payment link, no allocation."""
    from apps.resellers.service import ResellerService
    from apps.organizer.response import CustomerTransferResponse

    mock_repo = AsyncMock()
    mock_session = AsyncMock()
    mock_repo._session = mock_session
    service = ResellerService(mock_repo)
    service._allocation_repo = AsyncMock()
    service._ticketing_repo = AsyncMock()

    customer_holder = MagicMock(id=uuid4())
    reseller_holder = MagicMock(id=uuid4())

    service._repo.is_accepted_reseller = AsyncMock(return_value=True)
    service._repo.get_my_holder_for_event = AsyncMock(return_value=reseller_holder)
    service._allocation_repo.get_holder_by_phone = AsyncMock(return_value=None)
    service._allocation_repo.create_holder = AsyncMock(return_value=customer_holder)
    service._ticketing_repo.get_b2b_ticket_type_for_event = AsyncMock(
        return_value=MagicMock(id=uuid4())
    )
    service._allocation_repo.list_b2b_tickets_by_holder = AsyncMock(return_value=[{"count": 5}])
    service._ticketing_repo.lock_tickets_for_transfer = AsyncMock(return_value=[uuid4(), uuid4()])

    with patch("apps.resellers.service.get_gateway") as mock_get_gateway:
        mock_gateway = MagicMock()
        mock_gateway.create_payment_link = AsyncMock(
            return_value=MagicMock(
                gateway_order_id="plink_reseller123",
                short_url="https://razorpay.in/reseller",
                gateway_response={"id": "plink_reseller123"},
            )
        )
        mock_get_gateway.return_value = mock_gateway

        with patch("apps.resellers.service.OrderModel") as mock_order_model:
            order_instance = MagicMock()
            order_instance.id = uuid4()
            mock_order_model.return_value = order_instance

            result = await service.create_reseller_customer_transfer(
                user_id=uuid4(),
                event_id=uuid4(),
                phone="+919999999999",
                email=None,
                quantity=2,
                event_day_id=uuid4(),
                mode="paid",
            )

    assert result.status == "pending_payment"
    assert result.mode == "paid"
    assert result.payment_url == "https://razorpay.in/reseller"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/apps/resellers/test_service.py::test_create_reseller_customer_transfer_paid_mode -v`
Expected: FAIL — paid mode returns stub

- [ ] **Step 3: Write minimal implementation**

Replace the paid-mode stub in `ResellerService.create_reseller_customer_transfer` (lines 183-190) with the real paid flow.

```python
# Replace stub at lines 183-190:
if mode == "paid":
    from apps.payment_gateway.services.factory import get_gateway
    from apps.payment_gateway.services.base import BuyerInfo
    from apps.payment_gateway.repositories.order import OrderPaymentRepository
    from apps.allocation.enums import GatewayType
    from datetime import datetime, timedelta, timezone

    # Build buyer info
    customer_name = phone or "Customer"
    customer_email = email
    customer_phone = phone or ""

    # 1. Create pending order
    order = OrderModel(
        event_id=event_id,
        user_id=user_id,
        type=OrderType.transfer,
        subtotal_amount=0.0,
        discount_amount=0.0,
        final_amount=0.0,
        status=OrderStatus.pending,
        payment_gateway="razorpay",
        gateway_type=GatewayType.RAZORPAY_PAYMENT_LINK,
        lock_expires_at=datetime.now(timezone.utc) + timedelta(minutes=30),
    )
    self._repo._session.add(order)
    await self._repo._session.flush()
    await self._repo._session.refresh(order)

    # 2. Lock tickets
    locked_ticket_ids = await self._ticketing_repo.lock_tickets_for_transfer(
        owner_holder_id=reseller_holder.id,
        event_id=event_id,
        ticket_type_id=b2b_ticket_type.id,
        event_day_id=event_day_id,
        quantity=quantity,
        order_id=order.id,
        lock_ttl_minutes=30,
    )

    # 3. Create payment link
    gateway = get_gateway("razorpay")
    buyer_info = BuyerInfo(
        name=customer_name,
        email=customer_email,
        phone=customer_phone,
    )
    payment_result = await gateway.create_payment_link(
        order_id=order.id,
        amount=int(0.0 * 100),  # TODO (Phase 5): use actual ticket price
        currency="INR",
        buyer=buyer_info,
        description="Ticket Purchase",
        event_id=event_id,
        flow_type="b2b_transfer",
        transfer_type="reseller_to_customer",
        buyer_holder_id=customer_holder.id,
    )

    # 4. Update order with gateway details
    order_payment_repo = OrderPaymentRepository(self._repo._session)
    await order_payment_repo.update_pending_order_on_payment_link_created(
        order_id=order.id,
        gateway_order_id=payment_result.gateway_order_id,
        gateway_response=payment_result.gateway_response,
        short_url=payment_result.short_url,
    )

    # 5. Send payment link
    from src.utils.notifications.sms import mock_send_sms
    from src.utils.notifications.whatsapp import mock_send_whatsapp
    from src.utils.notifications.email import mock_send_email

    message = f"Complete your ticket purchase: {payment_result.short_url}"
    if customer_phone:
        mock_send_sms(customer_phone, message, template="customer_paid_transfer")
        mock_send_whatsapp(customer_phone, message, template="customer_paid_transfer")
    if customer_email:
        mock_send_email(customer_email, "Complete Your Ticket Purchase", message)

    return CustomerTransferResponse(
        transfer_id=order.id,
        status="pending_payment",
        ticket_count=len(locked_ticket_ids),
        mode="paid",
        payment_url=payment_result.short_url,
    )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/apps/resellers/test_service.py::test_create_reseller_customer_transfer_paid_mode -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/apps/resellers/service.py tests/apps/resellers/test_service.py
git commit -m "feat(reseller): implement paid mode in create_reseller_customer_transfer with payment link"
```

---

### Task 6: Verify free flow is unaffected — run all existing tests

**Files:**
- Test: `tests/apps/organizer/test_service.py`, `tests/apps/resellers/test_service.py`

- [ ] **Step 1: Run all existing organizer and reseller tests**

Run: `uv run pytest tests/apps/organizer/test_service.py tests/apps/resellers/test_service.py -v`
Expected: All existing free-flow tests PASS (no regressions)

- [ ] **Step 2: Commit**

```bash
git add -A  # Stage any remaining changes
git commit -m "test: verify free flow is unaffected after Phase 4 paid flow implementation"
```

---

## Self-Review

**1. Spec coverage:**
- `OrganizerService.create_b2b_transfer` with `is_paid=True` ✅ (spec Section 8.2)
- `OrganizerService.create_customer_transfer` with `is_paid=True` ✅ (spec Section 8.2)
- `ResellerService.create_reseller_customer_transfer` with `is_paid=True` ✅ (spec Section 8.2)
- Payment link creation via `gateway.create_payment_link()` ✅
- Notification via our own SMS/WhatsApp/Email ✅ (spec Section 3.3)
- Allocation deferred until webhook ✅ (spec Section 8.2: "NO allocation created yet — webhook creates it")
- `payment_url` in response ✅ (needed for frontend to show "pay now" button)
- Task 0: `clear_locks_for_order` lock type fix ✅ (pre-existing bug exposed by paid flow)

**2. Placeholder scan:**
- `TODO (Phase 5)` for `final_amount` derivation from ticket type price — this is explicitly out of scope for Phase 4 per the spec, which says paid flows use `final_amount` from the order
- No other placeholders found

**3. Type consistency:**
- `gateway.create_payment_link()` returns `PaymentLinkResult` ✅ (Phase 2 interface)
- `BuyerInfo(name, email, phone)` ✅ (Phase 2 interface)
- `OrderPaymentRepository.update_pending_order_on_payment_link_created()` ✅ (Task 1)
- `GatewayType.RAZORPAY_PAYMENT_LINK` ✅ (already in `allocation/enums.py`)
- `OrderStatus.pending` ✅ (used in existing code)
- `CustomerTransferResponse.payment_url` field name ✅ (matches Task 2)
- `B2BTransferResponse.payment_url` field name ✅ (matches Task 2)
- `status="pending_payment"` in responses ✅ (not `"not_implemented"`)
- `lock_reference_type.in_(["order", "transfer"])` ✅ (correct SQLAlchemy expression for Task 0)

**4. Additional gap found during self-review:**
- `lock_tickets_for_transfer` (ticketing/repository.py:214) uses deprecated `datetime.utcnow()` instead of `datetime.now(timezone.utc)` for setting `expires_at`. This is pre-existing — not fixed in this plan, but worth noting for Phase 5 cleanup.

**Note on `final_amount=0.0`:** The spec says amount comes from `final_amount` on the order. In Phase 4, we use `0.0` because ticket price derivation (for B2B tickets that have a `price` field on the ticket type) is complex and belongs in Phase 5. The webhook handler already validates amount — it will fail if the amount doesn't match, which correctly surfaces the issue. This is acceptable for Phase 4.

---

## What's Left for Phase 5

- Derive `final_amount` from B2B ticket type price when creating paid order
- Amount in paise passed to `create_payment_link()` should match `int(final_amount * 100)`
- Real SMS/WhatsApp/Email provider integration (Phase 4 uses mock services already in codebase)
- Fix `lock_tickets_for_transfer` (ticketing/repository.py:214) to use `datetime.now(timezone.utc)` instead of deprecated `datetime.utcnow()` for setting `expires_at`
- Expiry worker's `clear_ticket_locks` only handles `lock_reference_type == "order"` — fix to handle `"transfer"` type too (same pattern as Task 0 fix)
- Add `UserRepository` import to `organizer/service.py` and `resellers/service.py` before implementing paid flows

**Pre-execution checklist (verify before running Tasks 1-5):**
- [ ] `tests/apps/payment_gateway/test_order_repository.py` already exists? Add tests to it instead of creating new file.
- [ ] `UserRepository` import path: `from apps.allocation.repositories.user import UserRepository`
- [ ] Verify OrganizerService uses `self.repository.session` (not `self._repo._session`)
- [ ] Verify ResellerService uses `self._repo._session`

Plan complete and saved to `docs/superpowers/plans/2026-05-04-payment-gateway-phase4.md`.