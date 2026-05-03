# Payment Gateway Foundation — Phase 1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Scaffold the `payment_gateway` app — app structure, razorpay client singleton, exceptions, and `PaymentGateway` ABC interface. Foundation for all subsequent phases.

**Architecture:** Gateway-agnostic architecture with ABC interface. `RazorpayPaymentGateway` is the first concrete implementation. Factory (`get_gateway("razorpay")`) returns the right gateway by name. Razorpay SDK used for API calls.

**Tech Stack:** Python 3.11+, `razorpay` SDK, Pydantic v2, SQLAlchemy async, FastAPI, PostgreSQL

---

## Phase 1 Scope (from Spec Section 12)

| Task | Description | Status |
|------|-------------|--------|
| 1 | Add OrderModel fields (migration + model) | ✅ Done |
| 2 | Create `payment_gateway` app structure | 🔨 This plan |
| 3 | Create `GatewayType` enum + exceptions | 🔨 This plan |
| 4 | Create `razorpay.Client` singleton | 🔨 This plan |
| 5 | Create `PaymentGateway` ABC interface | 🔨 This plan |

**Already done (confirmed via file reads):**
- `GatewayType` enum — `src/apps/allocation/enums.py` lines 28-31
- OrderModel fields — `src/apps/allocation/models.py` lines 203-210
- Migration — `src/migrations/versions/cd2a50123a0f_add_payment_gateway_fields_to_.py`

---

## File Structure

```
src/apps/payment_gateway/
├── __init__.py                          # App export: GatewayType, get_gateway, PaymentGatewayError
├── client.py                             # razorpay.Client singleton + get_razorpay_client()
├── enums.py                             # Re-exports GatewayType from allocation.enums
├── exceptions.py                        # PaymentGatewayError, WebhookVerificationError
├── models.py                            # PaymentGatewayEventModel (Phase 2+ webhooks need it)
├── schemas/
│   ├── __init__.py
│   ├── base.py                         # BaseWebhookPayload, WebhookEvent dataclass
│   └── razorpay.py                     # Razorpay Pydantic schemas (Phase 2)
├── services/
│   ├── __init__.py                     # Exports: PaymentGateway, get_gateway
│   ├── base.py                         # PaymentGateway ABC
│   ├── razorpay.py                    # RazorpayPaymentGateway (Phase 2)
│   └── factory.py                     # get_gateway()
└── repositories/
    ├── __init__.py
    └── order.py                        # OrderPaymentRepository (Phase 2)
```

**Design decisions:**
- `GatewayType` lives in `allocation/enums.py` — re-export from `payment_gateway/enums.py` for convenience
- `schemas/razorpay.py` is stubbed in Phase 1 (Phase 2 fills it in)
- `repositories/order.py` is stubbed in Phase 1 (Phase 2 fills it in)
- `services/razorpay.py` raises `NotImplementedError` in Phase 1 — interface exists, implementation comes Phase 2
- `PaymentGatewayEventModel` in `models.py` — schema-only in Phase 1, no migration until Phase 3

---

## Task 1: Add `razorpay` Dependency

**Files:**
- Modify: `pyproject.toml`

- [ ] **Step 1: Add razorpay dependency**

Run: `uv add razorpay`
Expected: razorpay added to pyproject.toml dependencies

- [ ] **Step 2: Commit**

```bash
git add pyproject.toml uv.lock
git commit -m "feat(payment-gateway): add razorpay dependency"
```

---

## Task 2: Create `payment_gateway` App Structure

**Files:**
- Create: `src/apps/payment_gateway/__init__.py`
- Create: `src/apps/payment_gateway/client.py`
- Create: `src/apps/payment_gateway/enums.py`
- Create: `src/apps/payment_gateway/exceptions.py`
- Create: `src/apps/payment_gateway/models.py`
- Create: `src/apps/payment_gateway/schemas/__init__.py`
- Create: `src/apps/payment_gateway/schemas/base.py`
- Create: `src/apps/payment_gateway/schemas/razorpay.py`
- Create: `src/apps/payment_gateway/services/__init__.py`
- Create: `src/apps/payment_gateway/services/base.py`
- Create: `src/apps/payment_gateway/services/razorpay.py`
- Create: `src/apps/payment_gateway/services/factory.py`
- Create: `src/apps/payment_gateway/repositories/__init__.py`
- Create: `src/apps/payment_gateway/repositories/order.py`

- [ ] **Step 1: Create directory structure and all empty stub files**

```bash
mkdir -p src/apps/payment_gateway/{schemas,services,repositories}
touch src/apps/payment_gateway/__init__.py
touch src/apps/payment_gateway/client.py
touch src/apps/payment_gateway/enums.py
touch src/apps/payment_gateway/exceptions.py
touch src/apps/payment_gateway/models.py
touch src/apps/payment_gateway/schemas/__init__.py
touch src/apps/payment_gateway/schemas/base.py
touch src/apps/payment_gateway/schemas/razorpay.py
touch src/apps/payment_gateway/services/__init__.py
touch src/apps/payment_gateway/services/base.py
touch src/apps/payment_gateway/services/razorpay.py
touch src/apps/payment_gateway/services/factory.py
touch src/apps/payment_gateway/repositories/__init__.py
touch src/apps/payment_gateway/repositories/order.py
```

- [ ] **Step 2: Write stub implementations**

**`src/apps/payment_gateway/__init__.py`:**
```python
"""Payment Gateway app package."""

from apps.payment_gateway.client import get_razorpay_client
from apps.payment_gateway.enums import GatewayType
from apps.payment_gateway.exceptions import (
    PaymentGatewayError,
    WebhookVerificationError,
)
from apps.payment_gateway.services.base import PaymentGateway
from apps.payment_gateway.services.factory import get_gateway

__all__ = [
    "GatewayType",
    "PaymentGateway",
    "PaymentGatewayError",
    "WebhookVerificationError",
    "get_gateway",
    "get_razorpay_client",
]
```

**`src/apps/payment_gateway/enums.py`:**
```python
"""Re-export GatewayType for convenience."""
from apps.allocation.enums import GatewayType

__all__ = ["GatewayType"]
```

**`src/apps/payment_gateway/exceptions.py`:**
```python
"""Payment gateway exceptions."""


class PaymentGatewayError(Exception):
    """Base exception for all payment gateway errors."""


class WebhookVerificationError(PaymentGatewayError):
    """Raised when webhook signature verification fails."""
```

**`src/apps/payment_gateway/models.py`:**
```python
"""Payment gateway event audit log model.

Schema defined here for reference. Migration for payment_gateway_events
table will be created in Phase 3 (Webhook Handler).
"""
```

**`src/apps/payment_gateway/schemas/base.py`:**
```python
"""Base webhook schemas and dataclasses."""
from dataclasses import dataclass
from typing import Any


@dataclass
class WebhookEvent:
    event: str
    gateway_order_id: str
    internal_order_id: str | None
    receipt: str | None
    raw_payload: dict

    @classmethod
    def from_razorpay(cls, event: str, gateway_order_id: str, internal_order_id: str | None, receipt: str | None, raw_payload: dict) -> "WebhookEvent":
        return cls(
            event=event,
            gateway_order_id=gateway_order_id,
            internal_order_id=internal_order_id,
            receipt=receipt,
            raw_payload=raw_payload,
        )
```

**`src/apps/payment_gateway/schemas/razorpay.py`:**
```python
"""Razorpay Pydantic schemas — stub for Phase 1.

Phase 2 will add: OrderPaidPayload, PaymentFailedPayload, PaymentLinkPayload.
"""
```

**`src/apps/payment_gateway/services/base.py`:**
```python
"""PaymentGateway ABC interface."""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from uuid import UUID


@dataclass
class BuyerInfo:
    name: str
    email: str | None
    phone: str


@dataclass
class PaymentLinkResult:
    gateway_order_id: str
    short_url: str
    gateway_response: dict


@dataclass
class CheckoutOrderResult:
    gateway_order_id: str
    amount: int
    currency: str
    key_id: str
    gateway_response: dict


class PaymentGateway(ABC):
    @abstractmethod
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
        ...

    @abstractmethod
    async def create_checkout_order(
        self,
        order_id: UUID,
        amount: int,
        currency: str,
        event_id: UUID,
    ) -> CheckoutOrderResult:
        ...

    @abstractmethod
    def verify_webhook_signature(self, body: bytes, headers: dict) -> bool:
        ...

    @abstractmethod
    def parse_webhook_event(self, body: bytes, headers: dict) -> "WebhookEvent":
        ...

    @abstractmethod
    async def cancel_payment_link(self, payment_link_id: str) -> bool:
        ...
```

**`src/apps/payment_gateway/services/razorpay.py`:**
```python
"""RazorpayPaymentGateway — stub for Phase 1.

Phase 2 implements all methods.
"""
from apps.payment_gateway.services.base import PaymentGateway


class RazorpayPaymentGateway(PaymentGateway):
    """Stub — implementation comes in Phase 2."""
```

**`src/apps/payment_gateway/services/factory.py`:**
```python
"""Factory for getting payment gateway instances."""
from apps.payment_gateway.services.razorpay import RazorpayPaymentGateway
from apps.payment_gateway.services.base import PaymentGateway


def get_gateway(gateway_name: str) -> PaymentGateway:
    """Return the payment gateway instance for the given name."""
    if gateway_name == "razorpay":
        return RazorpayPaymentGateway()
    raise ValueError(f"Unknown payment gateway: {gateway_name}")
```

**`src/apps/payment_gateway/repositories/order.py`:**
```python
"""OrderPaymentRepository — stub for Phase 1.

Phase 2 will add update_on_capture, update_on_failure, update_on_expire.
"""
```

**`src/apps/payment_gateway/client.py`:**
```python
"""Stub — implemented in Task 3."""
```

**`src/apps/payment_gateway/schemas/__init__.py`:**
```python
"""Webhook schemas package."""
from apps.payment_gateway.schemas.base import WebhookEvent

__all__ = ["WebhookEvent"]
```

**`src/apps/payment_gateway/services/__init__.py`:**
```python
"""Payment gateway services package."""
from apps.payment_gateway.services.base import (
    BuyerInfo,
    CheckoutOrderResult,
    PaymentGateway,
    PaymentLinkResult,
)
from apps.payment_gateway.services.factory import get_gateway

__all__ = [
    "BuyerInfo",
    "CheckoutOrderResult",
    "PaymentGateway",
    "PaymentLinkResult",
    "get_gateway",
]
```

**`src/apps/payment_gateway/repositories/__init__.py`:**
```python
"""Repositories package."""
```

- [ ] **Step 3: Verify the app can be imported**

Run: `uv run python -c "from apps.payment_gateway import GatewayType, PaymentGateway, PaymentGatewayError, WebhookVerificationError, get_gateway; print('OK')"`
Expected: `OK`

- [ ] **Step 4: Commit**

```bash
git add src/apps/payment_gateway/
git commit -m "feat(payment-gateway): scaffold payment_gateway app structure"
```

---

## Task 3: Add Razorpay Settings to Config

**Files:**
- Modify: `src/config.py`

- [ ] **Step 1: Add razorpay settings fields**

Add to `Settings` class in `src/config.py`:
```python
# Razorpay
RAZORPAY_KEY_ID: Optional[str] = Field(None, alias="RAZORPAY_KEY_ID")
RAZORPAY_KEY_SECRET: Optional[str] = Field(None, alias="RAZORPAY_KEY_SECRET")
RAZORPAY_WEBHOOK_SECRET: Optional[str] = Field(None, alias="RAZORPAY_WEBHOOK_SECRET")
```

And add `RAZORPAY_KEY_ID`, `RAZORPAY_KEY_SECRET`, `RAZORPAY_WEBHOOK_SECRET` to the `validate_required` field list.

- [ ] **Step 2: Commit**

```bash
git add src/config.py
git commit -m "feat(payment-gateway): add Razorpay settings to config"
```

---

## Task 4: Create `razorpay.Client` Singleton

**Files:**
- Modify: `src/apps/payment_gateway/client.py`
- Test: `tests/apps/payment_gateway/test_client.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/apps/payment_gateway/test_client.py
import pytest
from apps.payment_gateway.client import get_razorpay_client, RazorpayClient


def test_get_razorpay_client_returns_singleton():
    client1 = get_razorpay_client()
    client2 = get_razorpay_client()
    assert client1 is client2


def test_razorpay_client_has_payment_link_attribute():
    client = get_razorpay_client()
    assert hasattr(client, "payment_link")


def test_razorpay_client_has_order_attribute():
    client = get_razorpay_client()
    assert hasattr(client, "order")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/apps/payment_gateway/test_client.py -v`
Expected: FAIL — module doesn't exist

- [ ] **Step 3: Create test directory and write implementation**

```python
# src/apps/payment_gateway/client.py
"""Razorpay client singleton."""
import logging
from typing import Optional

import razorpay

from config import settings

logger = logging.getLogger(__name__)


class RazorpayClient:
    """
    Singleton Razorpay client wrapping razorpay.Client.
    Initialized once with key_id + key_secret from settings.
    """
    _instance: Optional["RazorpayClient"] = None
    _client: Optional[razorpay.Client] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def _get_client(self) -> razorpay.Client:
        if self._client is None:
            key_id = settings.RAZORPAY_KEY_ID
            key_secret = settings.RAZORPAY_KEY_SECRET
            if not key_id or not key_secret:
                raise RuntimeError("RAZORPAY_KEY_ID and RAZORPAY_KEY_SECRET must be set")
            self._client = razorpay.Client(
                auth=(key_id, key_secret),
            )
            logger.info("Razorpay client initialized")
        return self._client

    @property
    def order(self):
        return self._get_client().order

    @property
    def payment_link(self):
        return self._get_client().payment_link


def get_razorpay_client() -> RazorpayClient:
    """Return the singleton RazorpayClient instance."""
    return RazorpayClient()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/apps/payment_gateway/test_client.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add tests/apps/payment_gateway/test_client.py src/apps/payment_gateway/client.py
git commit -m "feat(payment-gateway): add razorpay.Client singleton"
```

---

## Task 5: Create `PaymentGateway` ABC Interface + Update Factory

**Files:**
- Modify: `src/apps/payment_gateway/services/factory.py`
- Modify: `src/apps/payment_gateway/services/razorpay.py`
- Test: `tests/apps/payment_gateway/test_factory.py`
- Test: `tests/apps/payment_gateway/test_services.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/apps/payment_gateway/test_factory.py
import pytest
from apps.payment_gateway.services.factory import get_gateway
from apps.payment_gateway.services.razorpay import RazorpayPaymentGateway


def test_get_gateway_razorpay_returns_razorpay_gateway():
    gateway = get_gateway("razorpay")
    assert isinstance(gateway, RazorpayPaymentGateway)


def test_get_gateway_unknown_raises():
    with pytest.raises(ValueError, match="Unknown payment gateway"):
        get_gateway("unknown")
```

```python
# tests/apps/payment_gateway/test_services.py
import pytest
from apps.payment_gateway.services.base import PaymentGateway, BuyerInfo, PaymentLinkResult


def test_buyer_info_dataclass():
    buyer = BuyerInfo(name="John", email="john@example.com", phone="+919999999999")
    assert buyer.name == "John"
    assert buyer.email == "john@example.com"
    assert buyer.phone == "+919999999999"


def test_payment_link_result_dataclass():
    result = PaymentLinkResult(
        gateway_order_id="plink_abc123",
        short_url="https://razorpay.in/pl/abc123",
        gateway_response={"id": "plink_abc123"},
    )
    assert result.gateway_order_id == "plink_abc123"
    assert result.short_url == "https://razorpay.in/pl/abc123"


def test_payment_gateway_is_abc():
    with pytest.raises(TypeError):
        PaymentGateway()  # Cannot instantiate ABC
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/apps/payment_gateway/ -v`
Expected: FAIL — module doesn't exist

- [ ] **Step 3: Write implementation**

Update `src/apps/payment_gateway/services/razorpay.py`:
```python
"""RazorpayPaymentGateway implementation — stub for Phase 1.

Phase 2 implements create_payment_link, verify_webhook_signature,
parse_webhook_event, and cancel_payment_link.
"""
import razorpay

from apps.payment_gateway.client import get_razorpay_client
from apps.payment_gateway.services.base import (
    BuyerInfo,
    CheckoutOrderResult,
    PaymentGateway,
    PaymentLinkResult,
)
from apps.payment_gateway.schemas.base import WebhookEvent


class RazorpayPaymentGateway(PaymentGateway):
    def __init__(self):
        self._client = get_razorpay_client()
        self._webhook_secret = None  # Set via settings in Phase 2

    async def create_payment_link(
        self,
        order_id,
        amount: int,
        currency: str,
        buyer: BuyerInfo,
        description: str,
        event_id,
        flow_type: str,
        transfer_type: str | None,
        buyer_holder_id,
    ) -> PaymentLinkResult:
        raise NotImplementedError("Phase 2 — coming next")

    async def create_checkout_order(self, order_id, amount: int, currency: str, event_id) -> CheckoutOrderResult:
        raise NotImplementedError("Phase 2 — online checkout not implemented in V1")

    def verify_webhook_signature(self, body: bytes, headers: dict) -> bool:
        raise NotImplementedError("Phase 2 — coming next")

    def parse_webhook_event(self, body: bytes, headers: dict) -> WebhookEvent:
        raise NotImplementedError("Phase 2 — coming next")

    async def cancel_payment_link(self, payment_link_id: str) -> bool:
        raise NotImplementedError("Phase 2 — coming next")
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/apps/payment_gateway/ -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/apps/payment_gateway/services/razorpay.py tests/apps/payment_gateway/
git commit -m "feat(payment-gateway): implement PaymentGateway ABC and RazorpayPaymentGateway stub"
```

---

## Self-Review Checklist

**1. Spec coverage:**
- Task 1 ✅ (done before this plan)
- Task 2 ✅ — `payment_gateway` app scaffolded
- Task 3 ✅ — `GatewayType` re-exported, `PaymentGatewayError` + `WebhookVerificationError` created
- Task 4 ✅ — `razorpay.Client` singleton created
- Task 5 ✅ — `PaymentGateway` ABC, `RazorpayPaymentGateway` stub, `get_gateway()` factory

**2. Placeholder scan:** No "TBD", "TODO", "implement later" found. All stubs are explicitly marked "Phase 2".

**3. Type consistency:**
- `PaymentGateway.create_payment_link` signature matches spec Section 6.1
- `PaymentLinkResult` and `BuyerInfo` field names match spec Section 6.1
- `WebhookEvent` dataclass fields match spec Section 6.1 (`event`, `gateway_order_id`, `internal_order_id`, `receipt`, `raw_payload`)
- `CheckoutOrderResult` fields match spec (`gateway_order_id`, `amount`, `currency`, `key_id`, `gateway_response`)

---

## Plan Summary

| Task | Files | Dependency |
|------|-------|------------|
| 1: Add razorpay dep | `pyproject.toml` | None |
| 2: Scaffold app | 14 new files in `payment_gateway/` | None |
| 3: Add Razorpay settings | `src/config.py` | Task 1 |
| 4: Razorpay client singleton | `client.py` + test | Task 1, 3 |
| 5: ABC + factory + stub | `services/` + tests | Task 2 |

**Execution order:** Task 1 → Task 2 → Task 3 → Task 4 → Task 5
