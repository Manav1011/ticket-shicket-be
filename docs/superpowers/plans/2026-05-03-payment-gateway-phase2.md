# Payment Gateway Phase 2 — Gateway Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement `RazorpayPaymentGateway` — `create_payment_link()`, `verify_webhook_signature()`, `parse_webhook_event()`, `cancel_payment_link()` — plus all Razorpay Pydantic webhook schemas.

**Architecture:** `RazorpayPaymentGateway` implements the `PaymentGateway` ABC. `create_payment_link()` calls `razorpay.payment_link.create()` with a `notes` dict carrying internal IDs. Webhook signature uses HMAC-SHA256. `parse_webhook_event()` routes by `event` field in payload. `cancel_payment_link()` wraps the razorpay cancel API with idempotent error handling.

**Tech Stack:** Python 3.11+, `razorpay` SDK, Pydantic v2, `hmac`, `hashlib`

---

## What Phase 1 Left Stubbed

| Method | Phase 1 | Phase 2 |
|--------|---------|---------|
| `create_payment_link()` | `NotImplementedError` | Full implementation |
| `create_checkout_order()` | `NotImplementedError` | Still stub (V1 out of scope) |
| `verify_webhook_signature()` | `NotImplementedError` | Full implementation |
| `parse_webhook_event()` | `NotImplementedError` | Full implementation |
| `cancel_payment_link()` | `NotImplementedError` | Full implementation |
| `schemas/razorpay.py` | Empty stub | All Pydantic schemas |

---

## File Structure

```
src/apps/payment_gateway/
├── schemas/
│   ├── razorpay.py          # REPLACE stub with full Pydantic schemas
│   └── base.py              # ALREADY DONE in Phase 1 (WebhookEvent)
├── services/
│   └── razorpay.py          # REPLACE stub with full implementation
└── client.py                # ALREADY DONE in Phase 1
```

---

## Task 1: Razorpay Pydantic Webhook Schemas

**Files:**
- Replace: `src/apps/payment_gateway/schemas/razorpay.py`
- Test: `tests/apps/payment_gateway/test_schemas.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/apps/payment_gateway/test_schemas.py
import pytest
from apps.payment_gateway.schemas.razorpay import (
    OrderPaidPayload,
    PaymentFailedPayload,
    PaymentLinkPayload,
    RazorpayWebhookPayload,
)


def test_order_paid_payload_parses_correctly():
    payload = {
        "event": "order.paid",
        "id": "evt_abc123",
        "payload": {
            "order": {
                "entity": {
                    "id": "order_xyz",
                    "receipt": "optional-receipt",
                    "notes": {
                        "internal_order_id": "uuid-of-our-order",
                        "event_id": "uuid-of-event",
                        "flow_type": "b2b_transfer",
                        "transfer_type": "organizer_to_reseller",
                    },
                }
            },
            "payment": {
                "entity": {
                    "id": "pay_123",
                    "order_id": "order_xyz",
                    "amount": 100000,
                    "currency": "INR",
                    "status": "captured",
                }
            },
        },
    }
    parsed = OrderPaidPayload.model_validate(payload)
    assert parsed.event == "order.paid"
    assert parsed.payload.order.entity.id == "order_xyz"
    assert parsed.payload.payment.entity.amount == 100000
    assert parsed.payload.payment.entity.status == "captured"


def test_payment_failed_payload_parses_correctly():
    payload = {
        "event": "payment.failed",
        "id": "evt_failed123",
        "payload": {
            "payment": {
                "entity": {
                    "id": "pay_failed",
                    "order_id": "order_xyz",
                    "amount": 100000,
                    "currency": "INR",
                    "status": "failed",
                    "error_description": " insufficient funds",
                }
            }
        },
    }
    parsed = PaymentFailedPayload.model_validate(payload)
    assert parsed.event == "payment.failed"
    assert parsed.payload.payment.entity.error_description == "insufficient funds"


def test_payment_link_payload_parses_expired():
    payload = {
        "event": "payment_link.expired",
        "id": "evt_plink_expired",
        "payload": {
            "payment_link": {
                "entity": {
                    "id": "plink_abc",
                    "order_id": "order_xyz",
                    "status": "expired",
                }
            }
        },
    }
    parsed = PaymentLinkPayload.model_validate(payload)
    assert parsed.event == "payment_link.expired"
    assert parsed.payload.payment_link.entity.status == "expired"


def test_payment_link_payload_parses_cancelled():
    payload = {
        "event": "payment_link.cancelled",
        "id": "evt_plink_cancelled",
        "payload": {
            "payment_link": {
                "entity": {
                    "id": "plink_abc",
                    "order_id": "order_xyz",
                    "status": "cancelled",
                }
            }
        },
    }
    parsed = PaymentLinkPayload.model_validate(payload)
    assert parsed.event == "payment_link.cancelled"
    assert parsed.payload.payment_link.entity.status == "cancelled"


def test_razorpay_webhook_payload_unknown_event_raises():
    payload = {"event": "unknown.event", "id": "evt_unknown"}
    with pytest.raises(ValueError):
        RazorpayWebhookPayload.model_validate(payload)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `unset VIRTUAL_ENV && uv run pytest tests/apps/payment_gateway/test_schemas.py -v`
Expected: FAIL — schemas module is empty

- [ ] **Step 3: Write full Pydantic schemas**

```python
# src/apps/payment_gateway/schemas/razorpay.py
"""Razorpay Pydantic schemas for all webhook events."""
from pydantic import BaseModel, Field


class OrderNotes(BaseModel):
    internal_order_id: str | None = None
    event_id: str | None = None
    flow_type: str | None = None
    transfer_type: str | None = None


class OrderEntity(BaseModel):
    id: str
    receipt: str | None = None
    notes: dict | None = None


class PaymentEntity(BaseModel):
    id: str
    order_id: str
    amount: int
    currency: str
    status: str
    error_description: str | None = None


class OrderPayload(BaseModel):
    entity: OrderEntity


class PaymentPayload(BaseModel):
    entity: PaymentEntity


class PaymentLinkEntity(BaseModel):
    id: str
    order_id: str | None = None
    status: str


class PaymentLinkPayloadWrapper(BaseModel):
    payment_link: PaymentLinkPayload


class OrderPaidOrderPayload(BaseModel):
    order: OrderPayload
    payment: PaymentPayload


class OrderFailedPaymentPayload(BaseModel):
    payment: PaymentPayload


class PaymentLinkPayloadWrapper(BaseModel):
    payment_link: PaymentLinkPayload


class OrderPaidPayload(BaseModel):
    event: str
    id: str
    payload: OrderPaidOrderPayload


class PaymentFailedPayload(BaseModel):
    event: str
    id: str
    payload: OrderFailedPaymentPayload


class PaymentLinkPayload(BaseModel):
    event: str
    id: str
    payload: PaymentLinkPayloadWrapper


# Union type for all webhook events
RazorpayWebhookPayload = OrderPaidPayload | PaymentFailedPayload | PaymentLinkPayload
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `unset VIRTUAL_ENV && uv run pytest tests/apps/payment_gateway/test_schemas.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/apps/payment_gateway/schemas/razorpay.py tests/apps/payment_gateway/test_schemas.py
git commit -m "feat(payment-gateway): add Razorpay Pydantic webhook schemas"
```

---

## Task 2: Implement `create_payment_link()`

**Files:**
- Replace: `src/apps/payment_gateway/services/razorpay.py` (update the method)
- Modify: `src/apps/payment_gateway/client.py` (add `cancel_payment_link` proxy if needed)
- Test: `tests/apps/payment_gateway/test_create_payment_link.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/apps/payment_gateway/test_create_payment_link.py
import pytest
from unittest.mock import patch, MagicMock
from apps.payment_gateway.services.razorpay import RazorpayPaymentGateway
from apps.payment_gateway.services.base import BuyerInfo, PaymentLinkResult
from uuid import uuid4


@patch('apps.payment_gateway.services.razorpay.get_razorpay_client')
def test_create_payment_link_returns_correct_result(mock_get_client):
    mock_client = MagicMock()
    mock_client.payment_link.create.return_value = {
        "id": "plink_abc123",
        "short_url": "https://razorpay.in/pl/abc123",
        "amount": 100000,
        "currency": "INR",
        "status": "created",
    }
    mock_get_client.return_value = mock_client

    gateway = RazorpayPaymentGateway()
    order_id = uuid4()
    event_id = uuid4()
    buyer_holder_id = uuid4()

    result = gateway.create_payment_link(
        order_id=order_id,
        amount=100000,
        currency="INR",
        buyer=BuyerInfo(name="John", email="john@test.com", phone="+919999999999"),
        description="Test transfer",
        event_id=event_id,
        flow_type="b2b_transfer",
        transfer_type="organizer_to_reseller",
        buyer_holder_id=buyer_holder_id,
    )

    assert isinstance(result, PaymentLinkResult)
    assert result.gateway_order_id == "plink_abc123"
    assert result.short_url == "https://razorpay.in/pl/abc123"
    assert "id" in result.gateway_response


@patch('apps.payment_gateway.services.razorpay.get_razorpay_client')
def test_create_payment_link_calls_with_correct_notes(mock_get_client):
    mock_client = MagicMock()
    mock_client.payment_link.create.return_value = {
        "id": "plink_abc123",
        "short_url": "https://razorpay.in/pl/abc123",
    }
    mock_get_client.return_value = mock_client

    gateway = RazorpayPaymentGateway()
    order_id = uuid4()
    event_id = uuid4()
    buyer_holder_id = uuid4()

    gateway.create_payment_link(
        order_id=order_id,
        amount=100000,
        currency="INR",
        buyer=BuyerInfo(name="John", email="john@test.com", phone="+919999999999"),
        description="Test transfer",
        event_id=event_id,
        flow_type="b2b_transfer",
        transfer_type="organizer_to_reseller",
        buyer_holder_id=buyer_holder_id,
    )

    call_kwargs = mock_client.payment_link.create.call_args.kwargs
    assert call_kwargs["amount"] == 100000
    assert call_kwargs["currency"] == "INR"
    assert call_kwargs["description"] == "Test transfer"
    assert call_kwargs["notify"]["sms"] is False
    assert call_kwargs["notify"]["email"] is False
    notes = call_kwargs["notes"]
    assert notes["internal_order_id"] == str(order_id)
    assert notes["event_id"] == str(event_id)
    assert notes["flow_type"] == "b2b_transfer"
    assert notes["transfer_type"] == "organizer_to_reseller"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `unset VIRTUAL_ENV && uv run pytest tests/apps/payment_gateway/test_create_payment_link.py -v`
Expected: FAIL — method raises `NotImplementedError`

- [ ] **Step 3: Write the implementation**

Replace the `create_payment_link` method in `src/apps/payment_gateway/services/razorpay.py`:

```python
async def create_payment_link(
    self,
    order_id: UUID,
    amount: int,
    currency: str,
    buyer: BuyerInfo,
    description: str,
    event_id: UUID,
    flow_type: str,
    transfer_type: str | None,
    buyer_holder_id: UUID,
) -> PaymentLinkResult:
    payload = {
        "amount": amount,
        "currency": currency,
        "description": description,
        "customer": {
            "name": buyer.name,
            "email": buyer.email,
            "contact": buyer.phone,
        },
        "notes": {
            "internal_order_id": str(order_id),
            "event_id": str(event_id),
            "flow_type": flow_type,
            "transfer_type": transfer_type,
        },
        "notify": {
            "sms": False,
            "email": False,
        },
    }

    response = self._client.payment_link.create(payload=payload)
    gateway_order_id = response.get("id")
    short_url = response.get("short_url")

    return PaymentLinkResult(
        gateway_order_id=gateway_order_id,
        short_url=short_url,
        gateway_response=response,
    )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `unset VIRTUAL_ENV && uv run pytest tests/apps/payment_gateway/test_create_payment_link.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/apps/payment_gateway/services/razorpay.py tests/apps/payment_gateway/test_create_payment_link.py
git commit -m "feat(payment-gateway): implement create_payment_link()"
```

---

## Task 3: Implement `verify_webhook_signature()`

**Files:**
- Modify: `src/apps/payment_gateway/services/razorpay.py`
- Modify: `src/apps/payment_gateway/client.py` (add webhook_secret to constructor)
- Test: `tests/apps/payment_gateway/test_verify_signature.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/apps/payment_gateway/test_verify_signature.py
import pytest
import hmac
import hashlib
from unittest.mock import patch, MagicMock
from apps.payment_gateway.services.razorpay import RazorpayPaymentGateway
from apps.payment_gateway.exceptions import WebhookVerificationError
from uuid import uuid4


WEBHOOK_SECRET = "razorpay_webhook_secret_123"
VALID_BODY = b'{"event": "order.paid", "id": "evt_abc"}'


def _compute_signature(body: bytes, secret: str) -> str:
    return hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()


@patch('apps.payment_gateway.services.razorpay.get_razorpay_client')
def test_verify_webhook_signature_valid(mock_get_client):
    mock_client = MagicMock()
    mock_get_client.return_value = mock_client

    gateway = RazorpayPaymentGateway()
    gateway._webhook_secret = WEBHOOK_SECRET

    sig = _compute_signature(VALID_BODY, WEBHOOK_SECRET)
    headers = {"x-razorpay-signature": sig}

    result = gateway.verify_webhook_signature(VALID_BODY, headers)
    assert result is True


@patch('apps.payment_gateway.services.razorpay.get_razorpay_client')
def test_verify_webhook_signature_invalid(mock_get_client):
    mock_client = MagicMock()
    mock_get_client.return_value = mock_client

    gateway = RazorpayPaymentGateway()
    gateway._webhook_secret = WEBHOOK_SECRET

    headers = {"x-razorpay-signature": "invalid_signature"}
    result = gateway.verify_webhook_signature(VALID_BODY, headers)
    assert result is False


@patch('apps.payment_gateway.services.razorpay.get_razorpay_client')
def test_verify_webhook_signature_missing_header(mock_get_client):
    mock_client = MagicMock()
    mock_get_client.return_value = mock_client

    gateway = RazorpayPaymentGateway()
    gateway._webhook_secret = WEBHOOK_SECRET

    result = gateway.verify_webhook_signature(VALID_BODY, {})
    assert result is False
```

- [ ] **Step 2: Run test to verify it fails**

Run: `unset VIRTUAL_ENV && uv run pytest tests/apps/payment_gateway/test_verify_signature.py -v`
Expected: FAIL — method raises `NotImplementedError`

- [ ] **Step 3: Write the implementation**

In `src/apps/payment_gateway/services/razorpay.py`, update `__init__` and `verify_webhook_signature`:

```python
class RazorpayPaymentGateway(PaymentGateway):
    def __init__(self):
        self._client = get_razorpay_client()
        self._webhook_secret = settings.RAZORPAY_WEBHOOK_SECRET
```

```python
    def verify_webhook_signature(self, body: bytes, headers: dict) -> bool:
        received_sig = headers.get("x-razorpay-signature")
        if not received_sig:
            return False
        expected_sig = hmac.new(
            self._webhook_secret.encode(),
            body,
            hashlib.sha256,
        ).hexdigest()
        return hmac.compare_digest(expected_sig, received_sig)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `unset VIRTUAL_ENV && uv run pytest tests/apps/payment_gateway/test_verify_signature.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/apps/payment_gateway/services/razorpay.py tests/apps/payment_gateway/test_verify_signature.py
git commit -m "feat(payment-gateway): implement verify_webhook_signature()"
```

---

## Task 4: Implement `parse_webhook_event()`

**Files:**
- Modify: `src/apps/payment_gateway/services/razorpay.py`
- Modify: `src/apps/payment_gateway/schemas/base.py` (add `from_razorpay` factory)
- Test: `tests/apps/payment_gateway/test_parse_webhook.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/apps/payment_gateway/test_parse_webhook.py
import pytest
from unittest.mock import patch, MagicMock
from apps.payment_gateway.services.razorpay import RazorpayPaymentGateway
from apps.payment_gateway.schemas.base import WebhookEvent
from uuid import uuid4


ORDER_PAID_BODY = b'{"event": "order.paid", "id": "evt_abc", "payload": {"order": {"entity": {"id": "order_xyz", "notes": {"internal_order_id": "uuid-123"}}}, "payment": {"entity": {"id": "pay_123", "order_id": "order_xyz", "amount": 100000, "currency": "INR", "status": "captured"}}}}'

PAYMENT_LINK_EXPIRED_BODY = b'{"event": "payment_link.expired", "id": "evt_plink", "payload": {"payment_link": {"entity": {"id": "plink_abc", "order_id": "order_xyz", "status": "expired"}}}}'


@patch('apps.payment_gateway.services.razorpay.get_razorpay_client')
def test_parse_order_paid_extracts_internal_order_id(mock_get_client):
    mock_client = MagicMock()
    mock_get_client.return_value = mock_client

    gateway = RazorpayPaymentGateway()
    event = gateway.parse_webhook_event(ORDER_PAID_BODY, {})

    assert isinstance(event, WebhookEvent)
    assert event.event == "order.paid"
    assert event.gateway_order_id == "order_xyz"
    assert event.internal_order_id == "uuid-123"
    assert event.receipt is None


@patch('apps.payment_payment_gateway.services.razorpay.get_razorpay_client')
def test_parse_payment_link_expired(mock_get_client):
    mock_client = MagicMock()
    mock_get_client.return_value = mock_client

    gateway = RazorpayPaymentGateway()
    event = gateway.parse_webhook_event(PAYMENT_LINK_EXPIRED_BODY, {})

    assert isinstance(event, WebhookEvent)
    assert event.event == "payment_link.expired"
    assert event.gateway_order_id == "plink_abc"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `unset VIRTUAL_ENV && uv run pytest tests/apps/payment_gateway/test_parse_webhook.py -v`
Expected: FAIL — method raises `NotImplementedError`

- [ ] **Step 3: Write the implementation**

In `src/apps/payment_gateway/services/razorpay.py`:

```python
import json

def parse_webhook_event(self, body: bytes, headers: dict) -> WebhookEvent:
    raw = json.loads(body)
    event_type = raw.get("event")

    if event_type == "order.paid":
        from apps.payment_gateway.schemas.razorpay import OrderPaidPayload
        parsed = OrderPaidPayload.model_validate(raw)
        order_entity = parsed.payload.order.entity
        gateway_order_id = order_entity.id
        notes = order_entity.notes or {}
        internal_order_id = notes.get("internal_order_id")
        receipt = order_entity.receipt

    elif event_type in ("payment_link.expired", "payment_link.cancelled"):
        from apps.payment_gateway.schemas.razorpay import PaymentLinkPayload
        parsed = PaymentLinkPayload.model_validate(raw)
        gateway_order_id = parsed.payload.payment_link.entity.id
        internal_order_id = None
        receipt = None

    elif event_type == "payment.failed":
        from apps.payment_gateway.schemas.razorpay import PaymentFailedPayload
        parsed = PaymentFailedPayload.model_validate(raw)
        gateway_order_id = parsed.payload.payment.entity.order_id
        internal_order_id = None
        receipt = None

    else:
        raise ValueError(f"Unknown Razorpay webhook event: {event_type}")

    return WebhookEvent(
        event=event_type,
        gateway_order_id=gateway_order_id,
        internal_order_id=internal_order_id,
        receipt=receipt,
        raw_payload=raw,
    )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `unset VIRTUAL_ENV && uv run pytest tests/apps/payment_gateway/test_parse_webhook.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/apps/payment_gateway/services/razorpay.py tests/apps/payment_gateway/test_parse_webhook.py
git commit -m "feat(payment-gateway): implement parse_webhook_event()"
```

---

## Task 5: Implement `cancel_payment_link()`

**Files:**
- Modify: `src/apps/payment_gateway/services/razorpay.py`
- Test: `tests/apps/payment_gateway/test_cancel_payment_link.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/apps/payment_gateway/test_cancel_payment_link.py
import pytest
from unittest.mock import patch, MagicMock
from apps.payment_gateway.services.razorpay import RazorpayPaymentGateway
from uuid import uuid4


@patch('apps.payment_gateway.services.razorpay.get_razorpay_client')
def test_cancel_payment_link_success(mock_get_client):
    mock_client = MagicMock()
    mock_get_client.return_value = mock_client

    gateway = RazorpayPaymentGateway()
    result = gateway.cancel_payment_link("plink_abc123")

    assert result is True
    mock_client.payment_link.cancel.assert_called_once_with("plink_abc123")


@patch('apps.payment_gateway.services.razorpay.get_razorpay_client')
def test_cancel_payment_link_already_cancelled_returns_false(mock_get_client):
    import razorpay
    mock_client = MagicMock()
    mock_client.payment_link.cancel.side_effect = razorpay.errors.BadRequestError("Link already cancelled")
    mock_get_client.return_value = mock_client

    gateway = RazorpayPaymentGateway()
    result = gateway.cancel_payment_link("plink_abc123")

    assert result is False
```

- [ ] **Step 2: Run test to verify it fails**

Run: `unset VIRTUAL_ENV && uv run pytest tests/apps/payment_gateway/test_cancel_payment_link.py -v`
Expected: FAIL — method raises `NotImplementedError`

- [ ] **Step 3: Write the implementation**

In `src/apps/payment_gateway/services/razorpay.py`:

```python
async def cancel_payment_link(self, payment_link_id: str) -> bool:
    try:
        self._client.payment_link.cancel(payment_link_id)
        return True
    except razorpay.errors.BadRequestError:
        return False  # Already cancelled/expired
```

Also add `import razorpay` at the top of the file.

- [ ] **Step 4: Run tests to verify they pass**

Run: `unset VIRTUAL_ENV && uv run pytest tests/apps/payment_gateway/test_cancel_payment_link.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/apps/payment_gateway/services/razorpay.py tests/apps/payment_gateway/test_cancel_payment_link.py
git commit -m "feat(payment-gateway): implement cancel_payment_link()"
```

---

## Self-Review Checklist

**1. Spec coverage:**
- Task 1 ✅ — Pydantic schemas for `order.paid`, `payment.failed`, `payment_link.expired`, `payment_link.cancelled` (spec Section 4.2)
- Task 2 ✅ — `create_payment_link()` with correct notes field strategy (spec Section 4.1)
- Task 3 ✅ — `verify_webhook_signature()` with HMAC-SHA256 (spec Section 2.3)
- Task 4 ✅ — `parse_webhook_event()` extracting `internal_order_id` from notes (spec Section 4.3)
- Task 5 ✅ — `cancel_payment_link()` with idempotent error handling (spec Section 3.2)

**2. Placeholder scan:** No "TBD", "TODO", or "Phase X" stubs remain in the implementation files. All methods are fully implemented.

**3. Type consistency:**
- `PaymentLinkResult.gateway_order_id` and `PaymentLinkResult.short_url` match spec Section 6.1
- `WebhookEvent` field names (`event`, `gateway_order_id`, `internal_order_id`, `receipt`, `raw_payload`) are consistent across all tasks
- `BuyerInfo.name`, `BuyerInfo.email`, `BuyerInfo.phone` used correctly in `create_payment_link()`
- `notify.sms=False`, `notify.email=False` set per spec Section 4.1

**4. Notes field contract (spec Section 4.1):**
```python
notes = {
    "internal_order_id": str(order_id),
    "event_id": str(event_id),
    "flow_type": flow_type,
    "transfer_type": transfer_type,
}
```
All four keys are set. `notify.sms=False` and `notify.email=False` are set.

---

## Plan Summary

| Task | Files | What it implements |
|------|-------|--------------------|
| 1 | `schemas/razorpay.py` + test | All Pydantic webhook schemas |
| 2 | `services/razorpay.py` + test | `create_payment_link()` |
| 3 | `services/razorpay.py` + test | `verify_webhook_signature()` |
| 4 | `services/razorpay.py` + test | `parse_webhook_event()` |
| 5 | `services/razorpay.py` + test | `cancel_payment_link()` |

**Execution order:** Task 1 → Task 2 → Task 3 → Task 4 → Task 5
