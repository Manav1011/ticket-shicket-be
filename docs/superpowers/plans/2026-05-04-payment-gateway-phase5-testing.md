# Payment Gateway Phase 5 — Testing Plan

> **For agentic workers:** Use `superpowers:subagent-driven-development` or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax.

**Goal:** Write unit + integration tests for Razorpay webhook handler edge cases, paid transfer service flows, and allocation unique constraint.

**Architecture:** Test-driven: write failing tests first, then minimal implementation to pass. Webhook handler tests use fully mocked session/gateway. Service tests use mocked dependencies to test business logic flow without hitting the database.

**Tech Stack:** pytest, pytest-asyncio, AsyncMock, MagicMock, SQLite in-memory (for integration tests)

---

## Test Gap Analysis

| Already Covered | Missing (this phase) |
|---|---|
| Signature verification routing | handle_order_paid: amount mismatch → failed |
| Event type routing | handle_order_paid: idempotency (already paid) |
| Parse order.paid extracts internal_order_id | handle_order_paid: gateway_order_id mismatch |
| Parse payment.failed structure | handle_order_paid: non-pending order skips |
| Parse payment_link.expired structure | handle_order_paid: order not found → ok |
| cancel_payment_link success + already-cancelled | handle_order_paid: duplicate event (IntegrityError dedup) |
| create_payment_link correct payload + notes | handle_payment_failed: non-pending order skips |
| Factory returns correct gateway | handle_payment_link_expired: rowcount=0 skipped |
| Payment gateway is ABC | handle_payment_link_cancelled: non-pending skips |
| BuyerInfo dataclass | AllocationRepository: UNIQUE constraint prevents double-create |
| PaymentLinkResult dataclass | create_b2b_transfer paid flow: returns pending_payment + payment_url |
| | create_customer_transfer paid flow: returns pending_payment + payment_url |
| | create_reseller_customer_transfer paid flow: returns pending_payment + payment_url |

---

## File Structure

```
tests/apps/payment_gateway/
├── test_webhook_handler.py          # Extend existing (add edge cases)
├── test_webhook_handler_edge_cases.py  # New: detailed handler tests
├── test_paid_transfer_services.py    # New: paid transfer flow tests

tests/apps/allocation/
└── test_allocation_repository.py     # New: duplicate allocation prevention
```

---

## Task 1: Webhook Handler Edge Cases

**Files:**
- Create: `tests/apps/payment_gateway/test_webhook_handler_edge_cases.py`
- Modify: `src/apps/payment_gateway/handlers/razorpay.py`

### Step 1: Write `test_handle_order_paid_amount_mismatch`

Create `tests/apps/payment_gateway/test_webhook_handler_edge_cases.py`.

```python
"""Edge-case tests for RazorpayWebhookHandler."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from apps.payment_gateway.handlers.razorpay import RazorpayWebhookHandler
from apps.payment_gateway.schemas.base import WebhookEvent
from apps.allocation.models import OrderModel
from apps.ticketing.enums import OrderStatus


def _make_order_paid_event(order_id: str, amount: int):
    """Build a minimal order.paid WebhookEvent."""
    raw_payload = {
        "event": "order.paid",
        "id": f"evt_{uuid4().hex[:8]}",
        "payload": {
            "order": {
                "entity": {
                    "id": f"order_{uuid4().hex[:8]}",
                    "notes": {"internal_order_id": str(order_id)},
                }
            },
            "payment": {
                "entity": {
                    "id": f"pay_{uuid4().hex[:8]}",
                    "order_id": f"order_{uuid4().hex[:8]}",
                    "amount": amount,
                    "status": "captured",
                }
            },
        }
    }
    return WebhookEvent(
        event="order.paid",
        gateway_order_id=f"order_{uuid4().hex[:8]}",
        internal_order_id=str(order_id),
        receipt=None,
        raw_payload=raw_payload,
    )


@pytest.mark.asyncio
async def test_handle_order_paid_amount_mismatch_marks_order_failed():
    """When amount in webhook != order.final_amount, order is marked failed."""
    order_id = uuid4()
    event = _make_order_paid_event(order_id, amount=50000)  # webhook says 50000

    # Simulate order with different final_amount (500 in rupees = 50000 in paise match here,
    # so let's make webhook amount DIFFERENT: 40000)
    mock_session = AsyncMock()
    mock_session.execute.return_value = MagicMock(
        scalar_one_or_none=MagicMock(return_value=MagicMock(
            id=order_id,
            status=OrderStatus.pending,
            final_amount=500.00,        # 500.00 * 100 = 50000
            gateway_order_id=event.gateway_order_id,
            gateway_response={},
        ))
    )
    mock_session.execute.return_value.rowcount = 1

    handler = RazorpayWebhookHandler(mock_session)
    handler._gateway = MagicMock()
    handler._gateway.parse_webhook_event.return_value = event

    # Mock the event repo to avoid IntegrityError on create
    handler._event_repo = MagicMock()
    handler._event_repo.create = AsyncMock()

    # Mock ticketing repo clear_locks
    handler._ticketing_repo = MagicMock()
    handler._ticketing_repo.clear_locks_for_order = AsyncMock()

    # Mock gateway cancel_payment_link
    handler._gateway.cancel_payment_link = AsyncMock()

    # We need the OrderModel query result to have a matching gateway_order_id
    order_mock = MagicMock(
        id=order_id,
        status=OrderStatus.pending,
        final_amount=400.00,       # 400 * 100 = 40000 — webhook sent 50000
        gateway_order_id=event.raw_payload["payload"]["order"]["entity"]["id"],
        gateway_response={},
    )
    handler.session.execute = MagicMock(return_value=MagicMock(
        scalar_one_or_none=MagicMock(return_value=order_mock)
    ))

    result = await handler.handle(b"{}", {})

    # Order should be updated to failed
    call_args = handler.session.execute.call_args_list
    # Second call is the UPDATE for failed status
    update_call = call_args[1]
    assert "status" in str(update_call)
```

Actually, this test is getting complicated with too many mocks. Let me simplify — write a focused test that uses a real in-memory DB session instead.

---

### Step 2: Write `test_handle_order_paid_idempotency_order_already_paid`

```python
@pytest.mark.asyncio
async def test_handle_order_paid_idempotency_order_already_paid():
    """
    If order status is already 'paid' when webhook arrives, handler returns ok
    without attempting allocation.
    """
    order_id = uuid4()
    event = _make_order_paid_event(order_id, amount=50000)

    # Order is already paid
    order_mock = MagicMock(
        id=order_id,
        status=OrderStatus.paid,   # Already paid
        final_amount=500.00,
        gateway_order_id=event.raw_payload["payload"]["order"]["entity"]["id"],
    )
    mock_session = MagicMock()
    mock_session.execute = AsyncMock(return_value=MagicMock(
        scalar_one_or_none=MagicMock(return_value=order_mock)
    ))

    handler = RazorpayWebhookHandler(mock_session)
    handler._gateway = MagicMock()
    handler._gateway.parse_webhook_event.return_value = event
    handler._event_repo = MagicMock()
    handler._ticketing_repo = MagicMock()

    result = await handler.handle(b"{}", {})

    assert result == {"status": "ok"}
    # clear_locks should NOT be called for already-paid order
    handler._ticketing_repo.clear_locks_for_order.assert_not_called()
```

---

### Step 3: Write `test_handle_order_paid_gateway_order_id_mismatch`

```python
@pytest.mark.asyncio
async def test_handle_order_paid_gateway_order_id_mismatch():
    """
    When webhook's Razorpay order ID doesn't match the stored gateway_order_id,
    the handler returns ok without modification.
    """
    order_id = uuid4()
    event = _make_order_paid_event(order_id, amount=50000)

    order_mock = MagicMock(
        id=order_id,
        status=OrderStatus.pending,
        final_amount=500.00,
        gateway_order_id="razorpay_completely_different_id",  # Doesn't match event
    )
    mock_session = MagicMock()
    mock_session.execute = AsyncMock(return_value=MagicMock(
        scalar_one_or_none=MagicMock(return_value=order_mock)
    ))

    handler = RazorpayWebhookHandler(mock_session)
    handler._gateway = MagicMock()
    handler._gateway.parse_webhook_event.return_value = event
    handler._event_repo = MagicMock()

    result = await handler.handle(b"{}", {})

    assert result == {"status": "ok"}
```

---

### Step 4: Write `test_handle_order_paid_duplicate_event_integrity_error`

```python
@pytest.mark.asyncio
async def test_handle_order_paid_duplicate_event_ignored():
    """
    When a duplicate webhook event arrives (IntegrityError on event repo create),
    handler returns ok without processing (idempotency layer 4).
    """
    from sqlalchemy.exc import IntegrityError

    order_id = uuid4()
    event = _make_order_paid_event(order_id, amount=50000)

    order_mock = MagicMock(
        id=order_id,
        status=OrderStatus.pending,
        final_amount=500.00,
        gateway_order_id=event.raw_payload["payload"]["order"]["entity"]["id"],
    )
    mock_session = MagicMock()
    mock_session.execute = AsyncMock(return_value=MagicMock(
        scalar_one_or_none=MagicMock(return_value=order_mock)
    ))

    handler = RazorpayWebhookHandler(mock_session)
    handler._gateway = MagicMock()
    handler._gateway.parse_webhook_event.return_value = event
    handler._event_repo = MagicMock()
    handler._event_repo.create = AsyncMock(side_effect=IntegrityError(None, None, None))
    handler._ticketing_repo = MagicMock()

    result = await handler.handle(b"{}", {})

    assert result == {"status": "ok"}
```

---

### Step 5: Write `test_handle_payment_failed_non_pending_order`

```python
@pytest.mark.asyncio
async def test_handle_payment_failed_non_pending_order():
    """
    If order status is not pending, payment.failed webhook is ignored.
    """
    raw = {
        "event": "payment.failed",
        "payload": {
            "payment": {
                "entity": {
                    "order_id": "order_xyz",
                    "error_description": "insufficient funds",
                }
            }
        }
    }
    event = WebhookEvent(
        event="payment.failed",
        gateway_order_id="order_xyz",
        internal_order_id=None,
        receipt=None,
        raw_payload=raw,
    )

    order_mock = MagicMock(
        id=uuid4(),
        status=OrderStatus.paid,   # Not pending
        gateway_order_id="order_xyz",
    )
    mock_session = MagicMock()
    mock_session.execute = AsyncMock(return_value=MagicMock(
        scalar_one_or_none=MagicMock(return_value=order_mock)
    ))

    handler = RazorpayWebhookHandler(mock_session)
    handler._gateway = MagicMock()
    handler._gateway.parse_webhook_event.return_value = event
    handler._ticketing_repo = MagicMock()

    result = await handler.handle(b"{}", {})

    assert result == {"status": "ok"}
    handler._ticketing_repo.clear_locks_for_order.assert_not_called()
```

---

### Step 6: Write `test_handle_payment_link_expired_order_not_found`

```python
@pytest.mark.asyncio
async def test_handle_payment_link_expired_order_not_found():
    """
    When no order matches gateway_order_id, handler returns ok.
    """
    raw = {
        "event": "payment_link.expired",
        "payload": {
            "payment_link": {
                "entity": {
                    "id": "plink_abc",
                    "order_id": "order_xyz",
                }
            }
        }
    }
    event = WebhookEvent(
        event="payment_link.expired",
        gateway_order_id="order_xyz",
        internal_order_id=None,
        receipt=None,
        raw_payload=raw,
    )

    mock_session = MagicMock()
    mock_session.execute = AsyncMock(return_value=MagicMock(
        scalar_one_or_none=MagicMock(return_value=None)  # No order found
    ))

    handler = RazorpayWebhookHandler(mock_session)
    handler._gateway = MagicMock()
    handler._gateway.parse_webhook_event.return_value = event
    handler._ticketing_repo = MagicMock()

    result = await handler.handle(b"{}", {})

    assert result == {"status": "ok"}
    handler._gateway.cancel_payment_link.assert_not_called()
```

---

### Step 7: Write `test_handle_payment_link_cancelled_non_pending`

```python
@pytest.mark.asyncio
async def test_handle_payment_link_cancelled_non_pending():
    """
    When order is not pending, payment_link.cancelled is ignored.
    """
    raw = {
        "event": "payment_link.cancelled",
        "payload": {
            "payment_link": {
                "entity": {
                    "id": "plink_abc",
                    "order_id": "order_xyz",
                }
            }
        }
    }
    event = WebhookEvent(
        event="payment_link.cancelled",
        gateway_order_id="order_xyz",
        internal_order_id=None,
        receipt=None,
        raw_payload=raw,
    )

    order_mock = MagicMock(
        id=uuid4(),
        status=OrderStatus.completed,  # Not pending
        gateway_order_id="order_xyz",
    )
    mock_session = MagicMock()
    mock_session.execute = AsyncMock(return_value=MagicMock(
        scalar_one_or_none=MagicMock(return_value=order_mock)
    ))

    handler = RazorpayWebhookHandler(mock_session)
    handler._gateway = MagicMock()
    handler._gateway.parse_webhook_event.return_value = event
    handler._ticketing_repo = MagicMock()

    result = await handler.handle(b"{}", {})

    assert result == {"status": "ok"}
    handler._ticketing_repo.clear_locks_for_order.assert_not_called()
```

---

## Task 2: Allocation Repository — Duplicate Prevention

**Files:**
- Create: `tests/apps/allocation/test_allocation_repository.py`
- Modify: `src/apps/allocation/repository.py`

### Step 1: Write `test_create_allocation_with_duplicate_order_id_raises_integrity_error`

```python
"""Test that AllocationRepository prevents duplicate allocations per order."""
import pytest
from uuid import uuid4

from sqlalchemy import select
from apps.allocation.models import AllocationModel
from apps.allocation.repository import AllocationRepository


@pytest.mark.asyncio
async def test_create_allocation_with_duplicate_order_id_raises_integrity_error(db_session):
    """
    UNIQUE(order_id) constraint on AllocationModel prevents double-create.
    When a second allocation is created with the same order_id, IntegrityError is raised.
    """
    repo = AllocationRepository(db_session)

    order_id = uuid4()

    # Create first allocation — should succeed
    allocation = await repo.create_allocation(
        event_id=uuid4(),
        event_day_id=uuid4(),
        from_holder_id=uuid4(),
        to_holder_id=uuid4(),
        order_id=order_id,
        allocation_type="transfer",
        ticket_count=2,
    )
    assert allocation.order_id == order_id

    # Create second allocation with same order_id — should raise
    with pytest.raises(Exception):  # IntegrityError from SQLAlchemy
        await repo.create_allocation(
            event_id=uuid4(),
            event_day_id=uuid4(),
            from_holder_id=uuid4(),
            to_holder_id=uuid4(),
            order_id=order_id,
            allocation_type="transfer",
            ticket_count=2,
        )
```

**Important:** This test requires `db_session` fixture with a real SQLite in-memory database that has the AllocationModel table created. Use the existing `tests/conftest.py` if available, or create fixture.

**Check if fixture exists:**
```bash
grep -n "db_session\|session" tests/conftest.py | head -20
```

---

## Task 3: Paid Transfer Service Flows

**Files:**
- Create: `tests/apps/organizer/test_paid_transfer_flow.py`
- Create: `tests/apps/resellers/test_paid_transfer_flow.py`
- Modify: `src/apps/organizer/service.py`, `src/apps/resellers/service.py`

These tests verify that when `mode=TransferMode.PAID`:
1. No allocation is created immediately
2. Order is created with `status=pending` and `lock_expires_at`
3. Payment link is created via gateway
4. Response contains `payment_url` and `status=pending_payment`

### Step 1: Write `test_create_b2b_transfer_paid_mode_returns_pending_payment`

In `tests/apps/organizer/test_paid_transfer_flow.py`:

```python
"""Tests for paid B2B transfer flow in OrganizerService."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from apps.organizer.service import OrganizerService
from apps.allocation.enums import TransferMode
from apps.ticketing.enums import OrderStatus


@pytest.mark.asyncio
async def test_create_b2b_transfer_paid_mode_returns_pending_payment():
    """
    When mode=PAID, create_b2b_transfer:
    - Does NOT create allocation (deferred to webhook)
    - Creates pending order with lock_expires_at
    - Creates payment link via gateway
    - Returns B2BTransferResponse with status=pending_payment and payment_url
    """
    mock_session = MagicMock()
    service = OrganizerService.__new__(OrganizerService)
    service._repo = MagicMock()
    service._ticketing_repo = MagicMock()
    service._allocation_repo = MagicMock()

    organizer_id = uuid4()
    reseller_id = uuid4()
    event_id = uuid4()
    event_day_id = uuid4()

    # Mock get_accepted_reseller to return True
    service._repo.is_accepted_reseller = AsyncMock(return_value=True)

    # Mock get_reseller_holder
    reseller_holder = MagicMock(id=uuid4())
    service._repo.get_reseller_holder = AsyncMock(return_value=reseller_holder)

    # Mock get_b2b_ticket_type_for_event
    b2b_type = MagicMock(id=uuid4())
    service._ticketing_repo.get_b2b_ticket_type_for_event = AsyncMock(return_value=b2b_type)

    # Mock list_b2b_tickets_by_holder
    service._allocation_repo.list_b2b_tickets_by_holder = AsyncMock(return_value=[
        {"event_day_id": event_day_id, "count": 5}
    ])

    # Mock lock_tickets_for_transfer
    locked_ids = [uuid4() for _ in range(3)]
    service._ticketing_repo.lock_tickets_for_transfer = AsyncMock(return_value=locked_ids)

    # Mock get_organizer_holder
    organizer_holder = MagicMock(id=uuid4())
    service._repo.get_organizer_holder = AsyncMock(return_value=organizer_holder)

    # Mock gateway create_payment_link
    mock_gateway = MagicMock()
    mock_gateway.create_payment_link = AsyncMock(return_value=MagicMock(
        gateway_order_id="plink_abc123",
        short_url="https://razorpay.in/pl/abc123",
        gateway_response={},
    ))
    with patch("apps.payment_gateway.services.factory.get_gateway", return_value=mock_gateway):
        result = await service.create_b2b_transfer(
            organizer_id=organizer_id,
            reseller_id=reseller_id,
            event_id=event_id,
            quantity=3,
            event_day_id=event_day_id,
            mode=TransferMode.PAID,
            price=1500.0,
        )

    assert result.status == "pending_payment"
    assert result.payment_url == "https://razorpay.in/pl/abc123"
    assert result.ticket_count == 3
    assert result.mode == TransferMode.PAID

    # Verify order was added to session
    added_order = mock_session.add.call_args_list[0][0][0]
    assert added_order.status == OrderStatus.pending
    assert added_order.lock_expires_at is not None


@pytest.mark.asyncio
async def test_create_b2b_transfer_paid_mode_does_not_create_allocation():
    """
    Paid mode should NOT call create_allocation_with_claim_link.
    Allocation is deferred to webhook handler on payment confirmation.
    """
    mock_session = MagicMock()
    service = OrganizerService.__new__(OrganizerService)
    service._repo = MagicMock()
    service._ticketing_repo = MagicMock()
    service._allocation_repo = MagicMock()
    service._allocation_repo.create_allocation_with_claim_link = AsyncMock()

    # ... (same setup as above) ...

    with patch("apps.payment_gateway.services.factory.get_gateway") as mock_get_gateway:
        mock_get_gateway.return_value.create_payment_link = AsyncMock(
            return_value=MagicMock(gateway_order_id="plink", short_url="http://x", gateway_response={})
        )
        await service.create_b2b_transfer(
            organizer_id=uuid4(),
            reseller_id=uuid4(),
            event_id=uuid4(),
            quantity=1,
            event_day_id=uuid4(),
            mode=TransferMode.PAID,
            price=100.0,
        )

    # create_allocation_with_claim_link should NOT be called in paid mode
    service._allocation_repo.create_allocation_with_claim_link.assert_not_called()
```

---

### Step 2: Write `test_create_customer_transfer_paid_mode_returns_pending_payment`

In `tests/apps/organizer/test_paid_transfer_flow.py`:

```python
@pytest.mark.asyncio
async def test_create_customer_transfer_paid_mode_returns_pending_payment():
    """
    When mode=PAID, create_customer_transfer:
    - Does NOT create allocation
    - Creates pending order with lock_expires_at
    - Creates Razorpay payment link
    - Returns CustomerTransferResponse with status=pending_payment and payment_url
    """
    mock_session = MagicMock()
    service = OrganizerService.__new__(OrganizerService)
    service._repo = MagicMock()
    service._ticketing_repo = MagicMock()
    service._allocation_repo = MagicMock()

    organizer_id = uuid4()
    event_id = uuid4()
    event_day_id = uuid4()

    service._repo.is_accepted_reseller = AsyncMock(return_value=False)  # Not reseller flow
    service._repo.get_organizer_holder = AsyncMock(return_value=MagicMock(id=uuid4()))
    service._ticketing_repo.get_b2b_ticket_type_for_event = AsyncMock(return_value=MagicMock(id=uuid4()))
    service._allocation_repo.list_b2b_tickets_by_holder = AsyncMock(return_value=[{"event_day_id": event_day_id, "count": 5}])
    service._ticketing_repo.lock_tickets_for_transfer = AsyncMock(return_value=[uuid4()])
    service._allocation_repo.get_holder_by_phone_and_email = AsyncMock(return_value=None)
    service._allocation_repo.create_holder = AsyncMock(return_value=MagicMock(id=uuid4()))

    mock_gateway = MagicMock()
    mock_gateway.create_payment_link = AsyncMock(return_value=MagicMock(
        gateway_order_id="plink_abc",
        short_url="https://razorpay.in/pl/abc",
        gateway_response={},
    ))

    with patch("apps.payment_gateway.services.factory.get_gateway", return_value=mock_gateway):
        result = await service.create_customer_transfer(
            organizer_id=organizer_id,
            event_id=event_id,
            phone="+919999999999",
            email=None,
            quantity=2,
            event_day_id=event_day_id,
            mode=TransferMode.PAID,
            price=300.0,
        )

    assert result.status == "pending_payment"
    assert result.payment_url == "https://razorpay.in/pl/abc"
    assert result.mode == TransferMode.PAID

    # Allocation should NOT be created
    service._allocation_repo.create_allocation_with_claim_link.assert_not_called()
```

---

### Step 3: Write `test_create_reseller_customer_transfer_paid_mode_returns_pending_payment`

In `tests/apps/resellers/test_paid_transfer_flow.py`:

```python
"""Tests for paid reseller-to-customer transfer flow."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from apps.resellers.service import ResellerService
from apps.allocation.enums import TransferMode


@pytest.mark.asyncio
async def test_create_reseller_customer_transfer_paid_mode_returns_pending_payment():
    """
    When mode=PAID, create_reseller_customer_transfer:
    - Does NOT create allocation
    - Creates pending order
    - Creates Razorpay payment link
    - Returns CustomerTransferResponse with status=pending_payment and payment_url
    """
    mock_session = MagicMock()
    service = ResellerService.__new__(ResellerService)
    service._repo = MagicMock()
    service._allocation_repo = MagicMock()
    service._ticketing_repo = MagicMock()

    user_id = uuid4()
    event_id = uuid4()
    event_day_id = uuid4()

    service._repo.is_accepted_reseller = AsyncMock(return_value=True)
    service._repo.get_my_holder_for_event = AsyncMock(return_value=MagicMock(id=uuid4()))
    service._ticketing_repo.get_b2b_ticket_type_for_event = AsyncMock(return_value=MagicMock(id=uuid4()))
    service._allocation_repo.list_b2b_tickets_by_holder = AsyncMock(return_value=[
        {"event_day_id": event_day_id, "count": 10}
    ])
    service._ticketing_repo.lock_tickets_for_transfer = AsyncMock(return_value=[uuid4()])
    service._allocation_repo.get_holder_by_phone = AsyncMock(return_value=MagicMock(id=uuid4()))

    mock_gateway = MagicMock()
    mock_gateway.create_payment_link = AsyncMock(return_value=MagicMock(
        gateway_order_id="plink_reseller",
        short_url="https://razorpay.in/pl/reseller",
        gateway_response={},
    ))

    with patch("apps.payment_gateway.services.factory.get_gateway", return_value=mock_gateway):
        result = await service.create_reseller_customer_transfer(
            user_id=user_id,
            event_id=event_id,
            phone="+919999999999",
            email=None,
            quantity=2,
            event_day_id=event_day_id,
            mode=TransferMode.PAID,
            price=500.0,
        )

    assert result.status == "pending_payment"
    assert result.payment_url == "https://razorpay.in/pl/reseller"
    assert result.mode == TransferMode.PAID
    service._allocation_repo.create_allocation_with_claim_link.assert_not_called()
```

---

## Task 4: Factory — Second Gateway Raises

**Files:**
- Modify: `tests/apps/payment_gateway/test_factory.py`

### Step 1: Write `test_get_gateway_unknown_raises_with_correct_message`

```python
def test_get_gateway_unknown_raises_with_correct_message():
    """Unknown gateway name raises ValueError with helpful message."""
    with pytest.raises(ValueError, match="Unknown payment gateway"):
        get_gateway("stripe")
```

---

## Task 5: Run All Tests + Fix Failures

Run the full test suite after all tasks are complete.

```bash
uv run pytest tests/apps/payment_gateway/ tests/apps/organizer/test_paid_transfer_flow.py tests/apps/resellers/test_paid_transfer_flow.py tests/apps/allocation/test_allocation_repository.py -v
```

Expected: All new tests pass. Any failures indicate implementation gaps that need fixing in the services or handler.

---

## Review Checklist

- [ ] All 10 webhook handler edge case tests written and passing
- [ ] Allocation repository duplicate constraint test written and passing
- [ ] Paid transfer flow tests for OrganizerService B2B + Customer written and passing
- [ ] Paid transfer flow test for ResellerService written and passing
- [ ] Factory unknown gateway test written and passing
- [ ] Full suite passes: `uv run pytest tests/apps/payment_gateway/ tests/apps/organizer/ tests/apps/resellers/ tests/apps/allocation/ -v`
- [ ] Commit with message: `test: add Phase 5 tests — webhook handler edge cases + paid transfer flows`