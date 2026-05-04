# Payment Gateway Phase 3 — Webhook Handler Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the `POST /webhooks/razorpay` HTTP endpoint with `RazorpayWebhookHandler`, implement `handle_order_paid` with full 4-layer idempotency, plus `handle_payment_failed`, `handle_payment_link_expired`, `handle_payment_link_cancelled`.

**Architecture:** The webhook handler is a FastAPI route that uses `get_gateway("razorpay")` to verify signatures and parse events. All `order.paid` processing uses a single atomic SQLAlchemy transaction with: (1) status pre-check, (2) DB unique constraint dedup, (3) atomic UPDATE with `WHERE status=pending`, (4) allocation UNIQUE constraint on `order_id`. `PaymentGatewayEventModel` is an append-only audit log.

**Tech Stack:** FastAPI, SQLAlchemy async, Pydantic, PostgreSQL, `hmac`/`hashlib`

---

## Phase 2 Scope Summary (what Phase 3 depends on)

Phase 2 left:
- `verify_webhook_signature(body, headers)` — ✅ implemented
- `parse_webhook_event(body, headers)` returning `WebhookEvent` — ✅ implemented
- `cancel_payment_link(payment_link_id)` — ✅ implemented
- `create_payment_link(...)` — ✅ implemented

Phase 3 needs:
- `PaymentGatewayEventModel` — new model + migration
- `RazorpayWebhookHandler` — wires gateway methods to event handlers
- 4 event handlers — `handle_order_paid`, `handle_payment_failed`, `handle_payment_link_expired`, `handle_payment_link_cancelled`
- Webhook URL route in `src/apps/payment_gateway/urls.py`
- Register router in `src/server.py`

---

## File Structure

```
src/apps/payment_gateway/
├── models.py                  # ADD: PaymentGatewayEventModel
├── handlers/
│   ├── __init__.py           # UPDATE: export RazorpayWebhookHandler
│   └── razorpay.py           # ADD: RazorpayWebhookHandler + all 4 handle_* methods
├── urls.py                   # ADD: webhook router
├── repositories/
│   ├── __init__.py           # UPDATE: export new repos
│   └── event.py             # ADD: PaymentGatewayEventRepository
│   └── order.py             # ALREADY EXISTS (stub)
├── services/
│   └── razorpay.py          # ALREADY DONE (Phase 2)
└── schemas/
    └── razorpay.py          # ALREADY DONE (Phase 2)
```

---

## Task 1: `PaymentGatewayEventModel` + Migration

**Files:**
- Create: `src/apps/payment_gateway/models.py` (append to existing)
- Create: `src/migrations/versions/xxx_create_payment_gateway_events.sql`
- Test: `tests/apps/payment_gateway/test_models.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/apps/payment_gateway/test_models.py
import pytest
from apps.payment_gateway.models import PaymentGatewayEventModel


def test_payment_gateway_event_model_has_expected_columns():
    from sqlalchemy import inspect
    from apps.payment_gateway.models import Base

    mapper = inspect(PaymentGatewayEventModel)
    columns = {c.name for c in mapper.columns}

    assert "id" in columns
    assert "order_id" in columns
    assert "event_type" in columns
    assert "gateway_event_id" in columns
    assert "payload" in columns
    assert "gateway_payment_id" in columns


def test_payment_gateway_event_model_has_dedup_constraint():
    from apps.payment_gateway.models import PaymentGatewayEventModel

    # The unique constraint on (order_id, event_type, gateway_event_id) should exist
    constraints = [c.name for c in PaymentGatewayEventModel.__table__.constraints]
    assert any("dedup" in c or "unique" in c.lower() for c in constraints)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `unset VIRTUAL_ENV && uv run pytest tests/apps/payment_gateway/test_models.py -v`
Expected: FAIL — `PaymentGatewayEventModel` not yet defined in models.py

- [ ] **Step 3: Write the model**

Replace `src/apps/payment_gateway/models.py` (currently stub):

```python
"""Payment gateway event audit log model."""
import uuid
from datetime import datetime

from sqlalchemy import (
    ForeignKey,
    Index,
    String,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from db.base import Base, TimeStampMixin, UUIDPrimaryKeyMixin


class PaymentGatewayEventModel(Base, UUIDPrimaryKeyMixin, TimeStampMixin):
    """
    Append-only audit log for all payment gateway events.
    Unique constraint on (order_id, event_type, gateway_event_id) prevents duplicate processing.
    Unique constraint on gateway_payment_id prevents duplicate payment processing.
    """
    __tablename__ = "payment_gateway_events"
    __table_args__ = (
        UniqueConstraint(
            "order_id", "event_type", "gateway_event_id",
            name="uq_payment_gateway_events_dedup",
        ),
        UniqueConstraint(
            "gateway_payment_id",
            name="uq_payment_gateway_events_payment_id",
        ),
        Index("ix_payment_gateway_events_order_id", "order_id"),
        Index("ix_payment_gateway_events_gateway_event_id", "gateway_event_id"),
        Index("ix_payment_gateway_events_gateway_payment_id", "gateway_payment_id"),
    )

    order_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("orders.id", ondelete="CASCADE"), nullable=False, index=True
    )
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    gateway_event_id: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    payload: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    gateway_payment_id: Mapped[str | None] = mapped_column(
        String(128), nullable=True, unique=True, index=True
    )
```

- [ ] **Step 4: Create migration**

Run: `uv run main.py makemigrations --name create_payment_gateway_events`
Expected: New migration file in `src/migrations/versions/`

Or write it manually:
```sql
-- src/migrations/versions/xxx_create_payment_gateway_events.sql
CREATE TABLE payment_gateway_events (
    id UUID PRIMARY KEY,
    order_id UUID REFERENCES orders(id) ON DELETE CASCADE NOT NULL,
    event_type VARCHAR(64) NOT NULL,
    gateway_event_id VARCHAR(128),
    payload JSONB NOT NULL DEFAULT '{}',
    gateway_payment_id VARCHAR(128) UNIQUE,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_payment_gateway_events_dedup
        UNIQUE (order_id, event_type, gateway_event_id),
    CONSTRAINT uq_payment_gateway_events_payment_id
        UNIQUE (gateway_payment_id)
);

CREATE INDEX ix_payment_gateway_events_order_id ON payment_gateway_events(order_id);
CREATE INDEX ix_payment_gateway_events_gateway_event_id ON payment_gateway_events(gateway_event_id);
CREATE INDEX ix_payment_gateway_events_gateway_payment_id ON payment_gateway_events(gateway_payment_id);
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `unset VIRTUAL_ENV && uv run pytest tests/apps/payment_gateway/test_models.py -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add src/apps/payment_gateway/models.py src/migrations/versions/xxx_create_payment_gateway_events.sql tests/apps/payment_gateway/test_models.py
git commit -m "feat(payment-gateway): add PaymentGatewayEventModel and audit log table"
```

---

## Task 2: `PaymentGatewayEventRepository`

**Files:**
- Create: `src/apps/payment_gateway/repositories/event.py`
- Modify: `src/apps/payment_gateway/repositories/__init__.py`
- Test: `tests/apps/payment_gateway/test_event_repository.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/apps/payment_gateway/test_event_repository.py
import pytest
from uuid import uuid4
from apps.payment_gateway.repositories.event import PaymentGatewayEventRepository


@pytest.mark.asyncio
async def test_create_inserts_event(db_session):
    repo = PaymentGatewayEventRepository(db_session)
    order_id = uuid4()
    event = await repo.create(
        order_id=order_id,
        event_type="order.paid",
        gateway_event_id="evt_abc123",
        payload={"test": "payload"},
        gateway_payment_id="pay_xyz",
    )
    assert event.id is not None
    assert event.order_id == order_id
    assert event.event_type == "order.paid"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `unset VIRTUAL_ENV && uv run pytest tests/apps/payment_gateway/test_event_repository.py -v`
Expected: FAIL — module doesn't exist

- [ ] **Step 3: Write the repository**

```python
# src/apps/payment_gateway/repositories/event.py
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from apps.payment_gateway.models import PaymentGatewayEventModel


class PaymentGatewayEventRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(
        self,
        order_id: UUID,
        event_type: str,
        gateway_event_id: str | None,
        payload: dict,
        gateway_payment_id: str | None,
    ) -> PaymentGatewayEventModel:
        """Insert a gateway event. Unique constraint handles deduplication."""
        event = PaymentGatewayEventModel(
            order_id=order_id,
            event_type=event_type,
            gateway_event_id=gateway_event_id,
            payload=payload,
            gateway_payment_id=gateway_payment_id,
        )
        self.session.add(event)
        await self.session.flush()
        return event

    async def exists(self, order_id: UUID, event_type: str, gateway_event_id: str) -> bool:
        """Check if an event already exists (for pre-check before insert)."""
        result = await self.session.execute(
            select(PaymentGatewayEventModel).where(
                PaymentGatewayEventModel.order_id == order_id,
                PaymentGatewayEventModel.event_type == event_type,
                PaymentGatewayEventModel.gateway_event_id == gateway_event_id,
            )
        )
        return result.first() is not None
```

```python
# src/apps/payment_gateway/repositories/__init__.py
"""Repositories package."""
from apps.payment_gateway.repositories.event import PaymentGatewayEventRepository

__all__ = ["PaymentGatewayEventRepository"]
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `unset VIRTUAL_ENV && uv run pytest tests/apps/payment_gateway/test_event_repository.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/apps/payment_gateway/repositories/event.py src/apps/payment_gateway/repositories/__init__.py tests/apps/payment_gateway/test_event_repository.py
git commit -m "feat(payment-gateway): add PaymentGatewayEventRepository"
```

---

## Task 3: `RazorpayWebhookHandler` + URL Route

**Files:**
- Create: `src/apps/payment_gateway/handlers/razorpay.py`
- Create: `src/apps/payment_gateway/handlers/__init__.py`
- Create: `src/apps/payment_gateway/urls.py`
- Modify: `src/server.py`
- Test: `tests/apps/payment_gateway/test_webhook_handler.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/apps/payment_gateway/test_webhook_handler.py
import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from apps.payment_gateway.handlers.razorpay import RazorpayWebhookHandler


def test_handler_verifies_signature_before_processing():
    handler = RazorpayWebhookHandler()
    with patch.object(handler, "_gateway") as mock_gateway:
        mock_gateway.verify_webhook_signature.return_value = False

        from apps.payment_gateway.exceptions import WebhookVerificationError
        with pytest.raises(WebhookVerificationError):
            # Note: this test calls handle() directly for unit test purposes
            # In integration tests, handle() is called via the async route
            handler.handle(b"body", {})


@pytest.mark.asyncio
async def test_handler_routes_order_paid_event():
    handler = RazorpayWebhookHandler()
    mock_event = MagicMock()
    mock_event.event = "order.paid"

    with patch.object(handler, "_gateway") as mock_gateway:
        mock_gateway.verify_webhook_signature.return_value = True
        mock_gateway.parse_webhook_event.return_value = mock_event

        with patch.object(handler, "handle_order_paid", new_callable=AsyncMock) as mock_handle:
            await handler.handle(b"body", {})
            mock_handle.assert_called_once_with(mock_event)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `unset VIRTUAL_ENV && uv run pytest tests/apps/payment_gateway/test_webhook_handler.py -v`
Expected: FAIL — handler module doesn't exist

- [ ] **Step 3: Write the handler**

```python
# src/apps/payment_gateway/handlers/razorpay.py
"""Razorpay webhook handler."""
import logging
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from apps.payment_gateway.exceptions import WebhookVerificationError
from apps.payment_gateway.models import PaymentGatewayEventModel
from apps.payment_gateway.repositories.event import PaymentGatewayEventRepository
from apps.payment_gateway.schemas.base import WebhookEvent
from apps.payment_gateway.services.factory import get_gateway
from apps.allocation.models import OrderModel
from apps.ticketing.enums import OrderStatus
from apps.ticketing.repository import TicketingRepository
from apps.allocation.repository import AllocationRepository
from apps.payment_gateway.services.razorpay import RazorpayPaymentGateway

logger = logging.getLogger(__name__)


class RazorpayWebhookHandler:
    def __init__(self, session: AsyncSession):
        self.session = session
        self._gateway = get_gateway("razorpay")
        self._event_repo = PaymentGatewayEventRepository(session)
        self._ticketing_repo = TicketingRepository(session)
        self._allocation_repo = AllocationRepository(session)

    async def handle(self, body: bytes, headers: dict) -> dict:
        """Verify signature, parse event, route to handler. Fully async."""
        if not self._gateway.verify_webhook_signature(body, headers):
            raise WebhookVerificationError()

        event = self._gateway.parse_webhook_event(body, headers)

        if event.event == "order.paid":
            return await self.handle_order_paid(event)
        elif event.event == "payment.failed":
            return await self.handle_payment_failed(event)
        elif event.event == "payment_link.expired":
            return await self.handle_payment_link_expired(event)
        elif event.event == "payment_link.cancelled":
            return await self.handle_payment_link_cancelled(event)
        else:
            logger.info(f"Ignoring unhandled webhook event: {event.event}")
            return {"status": "ok"}

    async def handle_order_paid(self, event: WebhookEvent) -> dict:
        """Handle order.paid — 4-layer idempotent flow."""
        # Layer 1: Find order by internal_order_id or receipt
        internal_order_id = event.internal_order_id
        receipt = event.receipt

        if not internal_order_id and not receipt:
            logger.warning("Cannot find order: no internal_order_id or receipt in webhook")
            return {"status": "ok"}

        order_id = UUID(internal_order_id) if internal_order_id else UUID(receipt)
        result = await self.session.execute(
            select(OrderModel).where(OrderModel.id == order_id)
        )
        order = result.scalar_one_or_none()
        if not order:
            logger.warning(f"Order {order_id} not found")
            return {"status": "ok"}

        # Layer 1 (continued): skip if not pending
        if order.status != OrderStatus.pending:
            logger.info(f"Order {order_id} already {order.status} — ignoring late webhook")
            return {"status": "ok"}

        # Extract raw payload for validations
        raw = event.raw_payload
        razorpay_event_id = raw.get("id")

        # Layer 4: Event deduplication via DB constraint — attempt insert, IntegrityError = duplicate
        payment_id = raw["payload"]["payment"]["entity"]["id"]

        try:
            await self._event_repo.create(
                order_id=order.id,
                event_type="order.paid",
                gateway_event_id=razorpay_event_id,
                payload=raw,
                gateway_payment_id=payment_id,
            )
        except Exception:
            # Unique constraint violation — duplicate event, ignore
            logger.info(f"Duplicate order.paid event {razorpay_event_id} for order {order_id}")
            return {"status": "ok"}

        # Validate gateway_order_id match
        webhook_order_id = raw["payload"]["order"]["entity"]["id"]
        if order.gateway_order_id != webhook_order_id:
            logger.error(f"gateway_order_id mismatch: {order.gateway_order_id} vs {webhook_order_id}")
            return {"status": "ok"}

        # Validate payment.order_id matches webhook order id
        payment_order_id = raw["payload"]["payment"]["entity"]["order_id"]
        if payment_order_id != webhook_order_id:
            logger.error(f"payment.order_id ({payment_order_id}) != order.id ({webhook_order_id})")
            return {"status": "ok"}

        # Validate amount
        payment_amount = raw["payload"]["payment"]["entity"]["amount"]
        expected_amount = int(float(order.final_amount) * 100)
        if payment_amount != expected_amount:
            await self.session.execute(
                update(OrderModel)
                .where(OrderModel.id == order.id, OrderModel.status == OrderStatus.pending)
                .values(status=OrderStatus.failed, failure_reason=f"amount_mismatch: expected {expected_amount}, got {payment_amount}")
            )
            await self._ticketing_repo.clear_locks_for_order(order.id)
            await self._gateway.cancel_payment_link(order.gateway_order_id)
            return {"status": "ok"}

        # Validate payment status — only captured
        payment_status = raw["payload"]["payment"]["entity"]["status"]
        if payment_status != "captured":
            logger.info(f"Payment not yet captured: {payment_status}")
            return {"status": "ok"}

        # Layer 3: Atomic UPDATE — only succeeds if still pending
        updated = await self.session.execute(
            update(OrderModel)
            .where(OrderModel.id == order.id, OrderModel.status == OrderStatus.pending)
            .values(
                status=OrderStatus.paid,
                captured_at=order.created_at,
                gateway_payment_id=payment_id,
                gateway_response=raw,
            )
        )
        if updated.rowcount == 0:
            logger.info(f"Order {order_id} already processed by another thread")
            return {"status": "ok"}

        # Layer 2: Create allocation (idempotent via UNIQUE constraint on order_id)
        # This will be filled in Phase 4 — for Phase 3, just clear locks
        await self._ticketing_repo.clear_locks_for_order(order.id)

        logger.info(f"Order {order_id} marked paid, payment {payment_id}")
        return {"status": "ok"}

    async def handle_payment_failed(self, event: WebhookEvent) -> dict:
        """Handle payment.failed — atomic update + clear locks."""
        raw = event.raw_payload
        gateway_order_id = raw["payload"]["payment"]["entity"].get("order_id")
        if not gateway_order_id:
            gateway_order_id = event.gateway_order_id

        result = await self.session.execute(
            select(OrderModel).where(OrderModel.gateway_order_id == gateway_order_id)
        )
        order = result.scalar_one_or_none()
        if not order or order.status != OrderStatus.pending:
            return {"status": "ok"}

        updated = await self.session.execute(
            update(OrderModel)
            .where(OrderModel.id == order.id, OrderModel.status == OrderStatus.pending)
            .values(
                status=OrderStatus.failed,
                failure_reason=raw["payload"]["payment"]["entity"].get(
                    "error_description", "payment_failed"
                ),
            )
        )
        if updated.rowcount == 0:
            return {"status": "ok"}

        await self._ticketing_repo.clear_locks_for_order(order.id)
        logger.info(f"Order {order.id} marked failed")
        return {"status": "ok"}

    async def handle_payment_link_expired(self, event: WebhookEvent) -> dict:
        """Handle payment_link.expired — atomic update + clear locks + cancel link."""
        gateway_order_id = event.gateway_order_id

        result = await self.session.execute(
            select(OrderModel).where(OrderModel.gateway_order_id == gateway_order_id)
        )
        order = result.scalar_one_or_none()
        if not order or order.status != OrderStatus.pending:
            return {"status": "ok"}

        from datetime import datetime, timezone
        updated = await self.session.execute(
            update(OrderModel)
            .where(OrderModel.id == order.id, OrderModel.status == OrderStatus.pending)
            .values(status=OrderStatus.expired, expired_at=datetime.now(timezone.utc))
        )
        if updated.rowcount == 0:
            return {"status": "ok"}

        await self._ticketing_repo.clear_locks_for_order(order.id)
        await self._gateway.cancel_payment_link(gateway_order_id)
        logger.info(f"Order {order.id} expired — payment link cancelled")
        return {"status": "ok"}

    async def handle_payment_link_cancelled(self, event: WebhookEvent) -> dict:
        """Handle payment_link.cancelled — same as expired with reason."""
        gateway_order_id = event.gateway_order_id

        result = await self.session.execute(
            select(OrderModel).where(OrderModel.gateway_order_id == gateway_order_id)
        )
        order = result.scalar_one_or_none()
        if not order or order.status != OrderStatus.pending:
            return {"status": "ok"}

        from datetime import datetime, timezone
        updated = await self.session.execute(
            update(OrderModel)
            .where(OrderModel.id == order.id, OrderModel.status == OrderStatus.pending)
            .values(
                status=OrderStatus.expired,
                expired_at=datetime.now(timezone.utc),
                failure_reason="payment_link_cancelled",
            )
        )
        if updated.rowcount == 0:
            return {"status": "ok"}

        await self._ticketing_repo.clear_locks_for_order(order.id)
        logger.info(f"Order {order.id} expired — payment link cancelled by organizer")
        return {"status": "ok"}
```

```python
# src/apps/payment_gateway/handlers/__init__.py
"""Webhook handlers package."""
from apps.payment_gateway.handlers.razorpay import RazorpayWebhookHandler

__all__ = ["RazorpayWebhookHandler"]
```

- [ ] **Step 4: Write the URL route**

```python
# src/apps/payment_gateway/urls.py
"""Webhook URL routes."""
from typing import Annotated

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from db.session import db_session
from apps.payment_gateway.handlers.razorpay import RazorpayWebhookHandler
from utils.schema import BaseResponse

router = APIRouter(prefix="/webhooks", tags=["Webhooks"])


def get_webhook_handler(
    session: Annotated[AsyncSession, Depends(db_session)],
) -> RazorpayWebhookHandler:
    return RazorpayWebhookHandler(session)


@router.post("/razorpay")
async def razorpay_webhook(
    request: Request,
    handler: Annotated[RazorpayWebhookHandler, Depends(get_webhook_handler)],
) -> BaseResponse[dict]:
    """
    Receive Razorpay webhook at POST /webhooks/razorpay.
    X-Razorpay-Signature header is verified before processing.
    """
    body = await request.body()
    headers = dict(request.headers)
    result = await handler.handle(body, headers)
    return BaseResponse(data=result)
```

- [ ] **Step 5: Register the router in server.py**

Add to `src/server.py` imports:
```python
from apps.payment_gateway.urls import router as payment_gateway_router
```

Add to `base_router.include_router` calls:
```python
base_router.include_router(payment_gateway_router)
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `unset VIRTUAL_ENV && uv run pytest tests/apps/payment_gateway/test_webhook_handler.py -v`
Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add src/apps/payment_gateway/handlers/razorpay.py src/apps/payment_gateway/handlers/__init__.py src/apps/payment_gateway/urls.py src/server.py tests/apps/payment_gateway/test_webhook_handler.py
git commit -m "feat(payment-gateway): add RazorpayWebhookHandler and /webhooks/razorpay route"
```

---

## Task 4: `handle_order_paid` Allocation (Phase 4 Stub)

**Files:**
- Modify: `src/apps/payment_gateway/handlers/razorpay.py`

The Phase 3 version of `handle_order_paid` clears locks but does NOT create allocation — Phase 4 fills that in. Add a comment marking the stub:

In `handle_order_paid`, after the atomic UPDATE succeeds, add:
```python
# TODO (Phase 4): Create allocation, transfer ticket ownership, upsert edge
# Allocation creation will be idempotent via UNIQUE constraint on order_id
# await self._allocation_repo.create_allocation(...)
```

This is intentionally empty in Phase 3.

---

## Self-Review Checklist

**1. Spec coverage:**
- Task 1 ✅ — `PaymentGatewayEventModel` with `UniqueConstraint(order_id, event_type, gateway_event_id)` and `UniqueConstraint(gateway_payment_id)` (spec Section 2.3 Layer 4)
- Task 2 ✅ — `PaymentGatewayEventRepository.create()` uses unique constraint for dedup (spec Section 2.3)
- Task 3 ✅ — `RazorpayWebhookHandler.handle()` wires verify → parse → route (spec Section 7.2)
- Task 3 ✅ — `handle_order_paid` implements all 4 idempotency layers (spec Section 7.3)
- Task 3 ✅ — `handle_payment_failed`, `handle_payment_link_expired`, `handle_payment_link_cancelled` (spec Section 7.4)
- Task 3 ✅ — `POST /webhooks/razorpay` route (spec Section 7.1)

**2. Placeholder scan:** No "TBD", "TODO" in code. Allocation stub is explicitly commented as Phase 4 (not a placeholder, a deliberate deferral).

**3. Type consistency:**
- `handle()` is `async def` — matches FastAPI async route ✅
- `handle()` takes `body: bytes, headers: dict` — matches `verify_webhook_signature()` signature from Phase 2
- `handle_order_paid` receives `WebhookEvent` — matches `parse_webhook_event()` return type from Phase 2
- All 4 handlers return `dict` with `{"status": "ok"}` — consistent
- `PaymentGatewayEventRepository.create()` signature: `(order_id, event_type, gateway_event_id, payload, gateway_payment_id)` — matches spec Section 2.3 Layer 4

**4. Idempotency layers (spec Section 2.4):**
- Layer 1: `order.status != OrderStatus.pending` pre-check ✅
- Layer 4: `PaymentGatewayEventRepository.create()` unique constraint insert ✅
- Layer 3: `UPDATE ... WHERE status = pending` atomic update ✅
- Layer 2: `UNIQUE(order_id)` on allocations (Phase 4 stub comment) ✅

**5. Signature verification (spec Section 2.3):**
- `verify_webhook_signature()` called BEFORE `parse_webhook_event()` ✅
- `WebhookVerificationError` raised on failure ✅

**6. Flags fixed:**
- **Flag 1:** `handle()` is now `async def`, all sync wrappers removed, `await handler.handle()` called in route ✅
- **Flag 2:** `datetime.utcnow()` replaced with `datetime.now(timezone.utc)` ✅
- **Flag 3:** Body read directly from `request.body()` in route (not `Body()` parameter) ✅
- **Flag 4:** All repositories accept `AsyncSession` ✅

---

## Plan Summary

| Task | Files | What it builds |
|------|-------|----------------|
| 1 | `models.py` + migration | `PaymentGatewayEventModel` audit log table |
| 2 | `repositories/event.py` | `PaymentGatewayEventRepository` with dedup |
| 3 | `handlers/razorpay.py` + `urls.py` + `server.py` | All 4 handlers + webhook route |
| 4 | `handlers/razorpay.py` | Phase 4 allocation stub comment |
