# Payment Gateway Integration — Technical Specification

> **Status:** Draft — Pending Review

---

## 1. Overview

### 1.1 Goal

Integrate Razorpay as the first payment gateway into `ticket-shicket-be`, enabling paid B2B transfers (organizer→reseller, organizer→customer, reseller→customer). Build a gateway-agnostic architecture that future-proofs adding other payment gateways (Stripe, etc.) without architectural rewrites.

### 1.2 Background

The system currently has B2B transfer flows that only support free transfers. Every transfer creates a `$0 TRANSFER` order marked `paid` immediately, with no payment processing. This spec adds paid variants where an order is created with `status=pending`, a Razorpay payment link is generated, and the allocation is created only after Razorpay confirms payment via webhook.

### 1.3 Scope

**In Scope:**
- Razorpay payment gateway integration (payment links + checkout orders)
- Paid B2B transfers: organizer→reseller, organizer→customer, reseller→customer
- Order model extension with payment gateway metadata
- Webhook handling: `order.paid`, `payment.failed`, `payment_link.expired`, `payment_link.cancelled`
- Lock expiry handling for pending paid orders (30-minute TTL)
- Notification delivery (SMS, WhatsApp, Email) via our own services — NOT Razorpay's notify (which is paid)
- Base architecture ready for online checkout (customer direct purchase) — **not implemented in V1**

**Out of Scope (V1):**
- Online checkout flow (customer directly purchases tickets from event page)
- Refund handling (refund webhooks)
- Multi-gateway support beyond Razorpay
- Payment retry mechanism
- Partial payment support

---

## 2. Architecture

### 2.1 Gateway-Agnostic Design

```
┌─────────────────────────────────────────────────┐
│                 Business Logic                   │
│   (OrganizerService, ResellerService, etc.)     │
└──────────────────────┬──────────────────────────┘
                       │
         ┌─────────────▼─────────────┐
         │    PaymentGatewayFactory   │
         │   get_gateway("razorpay")  │
         └─────────────┬─────────────┘
                       │
    ┌──────────────────┼──────────────────┐
    │                  │                  │
┌───▼────┐      ┌─────▼─────┐     ┌──────▼─────┐
│ Razorpay│      │  Stripe   │     │  Future   │
│Gateway  │      │  (future) │     │  Gateway  │
└─────────┘      └───────────┘     └───────────┘
```

**Interface contract:**
```python
class PaymentGateway(ABC):
    @abstractmethod
    async def create_payment_link(self, order: OrderModel, buyer_info: BuyerInfo) -> PaymentLinkResult:
        """Create a shareable payment link. Returns short_url + gateway_order_id."""
        pass

    @abstractmethod
    async def create_checkout_order(self, order: OrderModel) -> CheckoutOrderResult:
        """Create a Razorpay checkout order for online purchase."""
        pass

    @abstractmethod
    def verify_webhook_signature(self, body: bytes, headers: dict) -> bool:
        """Verify the webhook request actually came from this gateway."""
        pass

    @abstractmethod
    def parse_webhook_event(self, body: bytes, headers: dict) -> WebhookEvent:
        """Parse and validate raw webhook payload into a structured event."""
        pass

    @abstractmethod
    async def cancel_payment_link(self, payment_link_id: str) -> bool:
        """Cancel an active payment link (when order expires/is cancelled)."""
        pass
```

### 2.2 Data Model Changes

#### OrderModel — New Fields

Added to `src/apps/allocation/models.py`:

```python
class OrderModel(Base, UUIDPrimaryKeyMixin, TimeStampMixin):
    # ... existing fields ...

    # === Payment Gateway Fields ===
    payment_gateway: Mapped[str | None] = mapped_column(
        String(32), nullable=True, index=True
    )  # "razorpay", "stripe"
    gateway_type: Mapped[str | None] = mapped_column(
        String(32), nullable=True
    )  # "razorpay_order" | "razorpay_payment_link"
    gateway_order_id: Mapped[str | None] = mapped_column(
        String(128), nullable=True, unique=True, index=True
    )  # Razorpay order_id OR payment_link id
    gateway_response: Mapped[dict] = mapped_column(
        JSONB, default=dict, server_default=text("'{}'::jsonb"), nullable=False
    )  # Full gateway response on creation
    short_url: Mapped[str | None] = mapped_column(
        String(512), nullable=True
    )  # Payment link short_url (for payment_link type only)
    gateway_payment_id: Mapped[str | None] = mapped_column(
        String(128), nullable=True, index=True
    )  # razorpay payment_id (set after capture)
    captured_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    expired_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
```

**GatewayType enum** (new file `src/apps/payment_gateway/enums.py`):

```python
class GatewayType(str, Enum):
    RAZORPAY_ORDER = "razorpay_order"        # Checkout flow (online purchase)
    RAZORPAY_PAYMENT_LINK = "razorpay_payment_link"  # Payment link flow (B2B)
    STRIPE_CHECKOUT = "stripe_checkout"       # Future
```

**OrderStatus extension** — no changes needed; `pending`, `paid`, `failed`, `expired` cover all states.

#### Ticket Lock Expiry

For paid orders, set `lock_expires_at = now + 30 minutes` when the order is created. This ensures locked tickets survive cleanup job cycles (which run every 5 minutes) and webhook delays.

#### Payment Gateway Events Audit Log

A `PaymentGatewayEventModel` stores every gateway event for audit/reconciliation:

```python
class PaymentGatewayEventModel(Base, UUIDPrimaryKeyMixin, TimeStampMixin):
    __tablename__ = "payment_gateway_events"

    order_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("orders.id", ondelete="CASCADE"), nullable=False, index=True
    )
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    gateway_event_id: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    # gateway_event_id stores Razorpay's event ID (e.g. "evt_xxx") for deduplication
    payload: Mapped[dict] = mapped_column(JSONB, default=dict)
    gateway_payment_id: Mapped[str | None] = mapped_column(
        String(128), nullable=True, unique=True, index=True
    )  # razorpay payment_id (set after capture). Unique to prevent duplicate payment processing

    __table_args__ = (
        UniqueConstraint("order_id", "event_type", "gateway_event_id",
                         name="uq_payment_gateway_events_dedup"),
    )
```

This is an append-only log — events are never overwritten, enabling dispute resolution and reconciliation. The unique constraint on `(order_id, event_type, gateway_event_id)` prevents duplicate event processing.

---

## 2.3 Webhook Security & Validation

### Signature Verification

Every webhook request must be verified before processing:

```python
def verify_webhook_signature(self, body: bytes, headers: dict) -> bool:
    # HMAC-SHA256 of raw body using RAZORPAY_WEBHOOK_SECRET
    # Compare with X-Razorpay-Signature header
    received_sig = headers.get("x-razorpay-signature")
    expected_sig = hmac.new(webhook_secret.encode(), body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected_sig, received_sig)
```

### Order Validation (handle_order_paid)

Before marking an order as paid, **mandatory validations**:

```python
async def handle_order_paid(event: WebhookEvent):
    # 1. Find order
    order = find_order(event)
    if not order:
        return  # Unknown order, ignore

    # 2. Idempotency: skip if already processed
    if order.status != OrderStatus.pending:
        return  # Already paid/failed/expired — ignore late webhooks

    # 3. Cross-check gateway_order_id
    # Both our record AND the webhook's order must match
    webhook_order_id = event.raw_payload["payload"]["order"]["entity"]["id"]
    if order.gateway_order_id != webhook_order_id:
        # Suspicious — gateway_order_id mismatch
        log.error(f"gateway_order_id mismatch: {order.gateway_order_id} vs {webhook_order_id}")
        return

    # 3b. Validate payment belongs to correct order
    # Razorpay payload has both order.id and payment.order_id — both must match
    payment_order_id = event.raw_payload["payload"]["payment"]["entity"]["order_id"]
    if payment_order_id != webhook_order_id:
        log.error(f"payment.order_id ({payment_order_id}) != order.id ({webhook_order_id})")
        return

    # 4. Validate payment amount
    payment_amount = event.raw_payload["payload"]["payment"]["entity"]["amount"]
    expected_amount = int(float(order.final_amount) * 100)  # convert to paise
    if payment_amount != expected_amount:
        # Amount mismatch — mark failed, do NOT create allocation
        order.status = OrderStatus.failed
        order.failure_reason = f"amount_mismatch: expected {expected_amount}, got {payment_amount}"
        await ticketing_repo.clear_locks_for_order(order.id)
        return

    # 5. Validate currency
    payment_currency = event.raw_payload["payload"]["payment"]["entity"]["currency"]
    if payment_currency != "INR":
        order.status = OrderStatus.failed
        order.failure_reason = f"currency_mismatch: expected INR, got {payment_currency}"
        await ticketing_repo.clear_locks_for_order(order.id)
        return

    # 6. Validate payment status
    payment_status = event.raw_payload["payload"]["payment"]["entity"]["status"]
    if payment_status != "captured":
        return  # Not yet captured, wait for payment.captured

    # All validations passed — proceed with payment capture
    ...
```

### Race Condition: Expiry Job vs Webhook

The expiry job must atomically expire orders AND cancel payment links — use a single bulk UPDATE to avoid inconsistent state mid-loop:

```python
# In lock_cleanup.py — updated logic
async def cleanup_expired_ticket_locks():
    # Bulk atomic update: expire all pending orders past their lock time
    # Uses RETURNING to get gateway_order_ids for cancellation
    result = await db.execute(
        update(OrderModel)
        .where(
            OrderModel.status == OrderStatus.pending,
            OrderModel.lock_expires_at < utcnow()
        )
        .values(
            status=OrderStatus.expired,
            expired_at=datetime.utcnow()
        )
        .returning(OrderModel.id, OrderModel.gateway_type, OrderModel.gateway_order_id)
    )
    expired_rows = result.fetchall()

    # Now safely process cancellations (no concurrent webhook issues — orders are already expired)
    for row in expired_rows:
        if row.gateway_type == GatewayType.RAZORPAY_PAYMENT_LINK:
            asyncio.create_task(
                razorpay_gateway.cancel_payment_link_with_retry(row.gateway_order_id)
            )
        await ticketing_repo.clear_locks_for_order(row.id)

    # Then: clear orphaned locks (standard cleanup)
    await ticketing_repo.clear_expired_locks()
```

This ensures:
- Webhook arriving after expiry job sees `order.status == expired` → ignored
- Payment link is cancelled so buyer cannot pay an expired order
- Tickets are unlocked for re-sale
- No inconsistent state mid-loop

### Payment Link Cancellation

When an order is expired/cancelled, the Razorpay payment link must be actively cancelled. Include retry with backoff for network failures:

```python
import asyncio

async def cancel_payment_link_with_retry(self, payment_link_id: str, max_retries: int = 3):
    """Cancel payment link with retry on network failures."""
    for attempt in range(max_retries):
        try:
            self._client.payment_link.cancel(payment_link_id)
            return True
        except razorpay.errors.BadRequestError:
            return True  # Link already cancelled/expired — success
        except (TimeoutError, ConnectionError) as e:
            if attempt == max_retries - 1:
                log.error(f"Failed to cancel payment link {payment_link_id} after {max_retries} attempts: {e}")
                # Enqueue for background retry OR log for manual cleanup
                return False
            await asyncio.sleep(2 ** attempt)  # Exponential backoff: 1s, 2s, 4s
    return False
```

### Allocation Idempotency

Even with `order.status == paid` check, a duplicate webhook could theoretically slip through. A DB unique constraint ensures safety:

```python
# Allocation model — add unique constraint on order_id
__table_args__ = (
    UniqueConstraint("order_id", name="uq_allocations_order_id"),
)

# When creating allocation:
try:
    allocation = await allocation_repo.create_allocation(...)
except IntegrityError:
    # Allocation already exists for this order — idempotent, ignore
    return
```

### Layer 3: Atomic Update (Critical for Race Safety)

Application-level status checks are not safe under concurrent webhook delivery. Use an atomic UPDATE with a WHERE clause:

```python
# Instead of: order.status = OrderStatus.paid (not safe under concurrency)
# Use atomic UPDATE:
updated = await db.execute(
    update(OrderModel)
    .where(
        OrderModel.id == order.id,
        OrderModel.status == OrderStatus.pending  # Only if still pending
    )
    .values(
        status=OrderStatus.paid,
        captured_at=datetime.utcnow(),
        gateway_payment_id=payment_id,
        gateway_response=event.raw_payload
    )
)
if updated.rowcount == 0:
    return  # Already processed by another thread — race condition prevented
```

### Layer 4: Event Deduplication (DB-Enforced)

Instead of pre-checking before the transaction, rely on the DB unique constraint as the authoritative dedup mechanism:

```python
# Attempt insert — unique constraint on (order_id, event_type, gateway_event_id) catches duplicates
try:
    await gateway_event_repo.create(
        order_id=order.id,
        event_type="order.paid",
        gateway_event_id=razorpay_event_id,
        payload=event.raw_payload,
        gateway_payment_id=payment_id
    )
except IntegrityError:
    return  # Duplicate event — constraint enforced, no pre-check needed
```

This is **stronger than pre-checking** because:
- Pre-check has a race window (two threads both pass check simultaneously)
- Constraint-based insert is atomic — no race possible
- Simpler code, single DB round-trip

### Complete Idempotent Flow (4-Layer)

```python
async def handle_order_paid(event: WebhookEvent):
    # Layer 1: Find order
    order = find_order(event)
    if not order:
        return

    # Layer 1 (continued): skip if not pending
    if order.status != OrderStatus.pending:
        return  # Already paid/failed/expired — ignore late webhooks

    # Validations (amount, currency, gateway_order_id cross-check, payment.order_id)...

    payment_id = event.raw_payload["payload"]["payment"]["entity"]["id"]
    razorpay_event_id = event.raw_payload.get("id")

    # Layer 4: Rely on DB constraint — attempt insert, catch duplicate
    # This is stronger than pre-checking: the unique constraint is the real guard
    try:
        await gateway_event_repo.create(
            order_id=order.id,
            event_type="order.paid",
            gateway_event_id=razorpay_event_id,
            payload=event.raw_payload,
            gateway_payment_id=payment_id
        )
    except IntegrityError:
        return  # Duplicate event — constraint prevented insert

    # Layer 3 + Layer 2: EVERYTHING in one atomic transaction
    # - Atomic UPDATE: only succeeds if status is still pending
    # - Allocation creation: idempotent via UNIQUE constraint on order_id
    async with db.begin():
        updated = await db.execute(
            update(OrderModel)
            .where(
                OrderModel.id == order.id,
                OrderModel.status == OrderStatus.pending
            )
            .values(
                status=OrderStatus.paid,
                captured_at=datetime.utcnow(),
                gateway_payment_id=payment_id,
                gateway_response=event.raw_payload
            )
        )
        if updated.rowcount == 0:
            return  # Already processed by another thread

        # Layer 2: Create allocation (idempotent via UNIQUE constraint on order_id)
        try:
            allocation = await allocation_repo.create_allocation(...)
            await allocation_repo.add_tickets_to_allocation(...)
            await allocation_repo.upsert_edge(...)
            await ticketing_repo.update_ticket_ownership_batch(...)
            await allocation_repo.transition_allocation_status(...)
        except IntegrityError:
            pass  # Allocation already exists — unique constraint prevented duplicate

        await ticketing_repo.clear_locks_for_order(order.id)

    # Notifications: fire-and-forget (outside transaction)
    asyncio.create_task(send_confirmation_notifications(order))
```

### 4-Layer Idempotency Summary

| Layer | Mechanism | Protects Against |
|-------|-----------|-----------------|
| App-level check | `order.status != pending` | Late webhooks after expiry/failure |
| Event dedup | `UNIQUE(order_id, event_type, gateway_event_id)` — insert-then-catch | Same event retried by Razorpay |
| Atomic update | `UPDATE ... WHERE status = pending` | Parallel webhooks (race condition) |
| DB constraint | `UNIQUE(order_id)` on allocations | Duplicate allocation creation |

---

## 3. Payment Flows

### 3.1 B2B Paid Transfer Flow

All three paid B2B flows follow the same pattern:

```
Organizer/Reseller initiates paid transfer
         │
         ▼
Resolve buyer TicketHolder (from OrganizerService/ResellerService)
         │
         ▼
Create OrderModel (status=pending, final_amount=X)
         │
         ▼
Lock tickets with order_id as lock_reference, lock_expires_at=now+30min
         │
         ▼
Call razorpay.payment_link.create({amount, customer, notes})
         │
         ▼
Save gateway_order_id=plink_xxx, gateway_response, short_url to OrderModel
         │
         ▼
Send payment link to buyer via our notification channels
(SMS, WhatsApp, Email — using our own services, NOT Razorpay's notify)
         │
         ▼
[ASYNCHRONOUS] Buyer pays via link
         │
         ▼
Razorpay sends webhook: order.paid
         │
         ▼
Handler finds OrderModel by gateway_order_id
         │
         ▼
Skip if already paid (idempotency)
         │
         ▼
Update OrderModel: status=paid, captured_at, gateway_response
         │
         ▼
Create Allocation, transfer ticket ownership, clear lock
         │
         ▼
Send payment confirmation to buyer
(SMS, WhatsApp, Email — using our own services)
         │
         ▼
Return 200 OK to Razorpay
```

### 3.2 Failure / Expiry Handling

```
payment.failed webhook
         │
         ▼
Find OrderModel by gateway_order_id
         │
         ▼
Update status=failed, release lock, unlock tickets
         │
         ▼

payment_link.expired / payment_link.cancelled webhook
         │
         ▼
Find OrderModel by gateway_order_id
         │
         ▼
Update status=expired, release lock, unlock tickets
```

### 3.3 Notification Delivery

**We own all notification delivery. Razorpay's built-in `notify` parameter is NOT used** — it is paid and limits our control over message content and delivery tracking.

**When payment link is created (after gateway response):**
- Organizer/Reseller initiates paid transfer
- System sends the `short_url` to the buyer via our notification channels:
  - **SMS** — via existing `send_sms()` mock service
  - **WhatsApp** — via existing `send_whatsapp()` mock service
  - **Email** — via existing `send_email()` mock service
- The message includes the payment link and event details

**When payment is confirmed (after `order.paid` webhook):**
- System sends a confirmation to the buyer via our notification channels
- Includes ticket/event details (what they purchased)

**Notification service integration** (existing mock services, real providers later):

```python
# Sending payment link
await sms_service.send(phone=buyer.phone, message=f"Pay for your tickets: {short_url}")
await whatsapp_service.send(phone=buyer.phone, message=f"Complete your ticket purchase: {short_url}")
await email_service.send(to_email=buyer.email, subject="Complete Your Ticket Purchase", body=f"Pay here: {short_url}")

# Sending confirmation
await sms_service.send(phone=buyer.phone, message="Payment confirmed! Your tickets are ready.")
await whatsapp_service.send(phone=buyer.phone, message="Payment confirmed! Tickets assigned.")
await email_service.send(to_email=buyer.email, subject="Payment Confirmed - Tickets Assigned", body="...")
```

**When the notification is sent** is determined by the calling service (OrganizerService/ResellerService) — the `create_payment_link()` method returns the `short_url` and the caller decides how to notify the buyer.

### 3.3 Online Checkout Flow (Base Ready — V1 Out of Scope)

This document establishes the base for the online checkout flow, but it is not implemented in V1. The base includes:
- `gateway_type: razorpay_order` — distinguishing checkout orders from payment links
- `receipt` field set to our order UUID for lookup in webhook
- `notes` field with `internal_order_id`, `event_id`, `flow_type = "online_purchase"`
- `create_checkout_order()` method on the gateway interface

When implemented, the flow will be:

```
Buyer initiates checkout
         │
         ▼
Resolve/creates TicketHolder for buyer
         │
         ▼
Create OrderModel (status=pending)
         │
         ▼
Lock tickets
         │
         ▼
Call razorpay.order.create({amount, receipt=order_uuid, notes})
         │
         ▼
Return order_id + key_id to frontend
         │
         ▼
Frontend opens Razorpay checkout modal
         │
         ▼
Buyer pays
         │
         ▼
order.paid webhook → create allocation → transfer ownership
```

---

## 4. Razorpay Integration

### 4.1 Notes Field Strategy

Both `order.create()` and `payment_link.create()` accept a `notes` dict. We use it to pass our internal identifiers so the webhook handler can find our order.

**For payment links:**
```python
notes = {
    "internal_order_id": "uuid-of-our-order",
    "event_id": "uuid-of-event",
    "flow_type": "b2b_transfer",
    "transfer_type": "organizer_to_reseller",  # or _to_customer, reseller_to_customer
}
# IMPORTANT: Set notify.sms=False and notify.email=False — we own all delivery
```

**For checkout orders (V1 out of scope):**
```python
receipt = "our-order-uuid"  # primary lookup key in webhook
notes = {
    "event_id": "uuid-of-event",
    "flow_type": "online_purchase"
}
```

### 4.2 Webhook Events to Handle

| Event | Action |
|-------|--------|
| `order.paid` | **Primary trigger** — create allocation, transfer ownership, mark order paid. Works for both payment link and checkout flows. |
| `payment.failed` | Mark order failed, release locked tickets |
| `payment_link.expired` | Mark order expired, release locked tickets |
| `payment_link.cancelled` | Mark order expired, release locked tickets |

**Why `order.paid` instead of `payment.captured`?**
- `order.paid` contains both `payment` and `order` entities in full
- `order.paid` works for both payment link and checkout flows
- `payment.captured` alone doesn't have `payment_link` details in the payment link flow

### 4.3 Order Lookup in Webhook

| Flow | Lookup Key | Source |
|------|-----------|--------|
| Payment link | `payload["payload"]["order"]["entity"]["notes"]["internal_order_id"]` | In `order.paid` webhook |
| Checkout (V1 out of scope) | `payload["payload"]["order"]["entity"]["receipt"]` | In `order.paid` webhook |

---

## 5. App Structure

### 5.1 New App: `payment_gateway`

```
src/apps/payment_gateway/
├── __init__.py                           # App export
├── client.py                             # razorpay.Client singleton
├── enums.py                              # GatewayType enum
├── exceptions.py                         # PaymentGatewayError, WebhookVerificationError
├── schemas/
│   ├── __init__.py
│   ├── base.py                           # BaseWebhookPayload
│   └── razorpay.py                       # Razorpay-specific Pydantic schemas
├── services/
│   ├── __init__.py
│   ├── base.py                           # PaymentGateway abstract interface
│   ├── razorpay.py                       # RazorpayPaymentGateway implementation
│   └── factory.py                        # get_gateway(gateway_name) factory
├── handlers/
│   ├── __init__.py
│   └── razorpay.py                       # RazorpayWebhookHandler
└── repositories/
    ├── __init__.py
    └── order.py                          # OrderPaymentRepository (update payment fields)
```

### 5.2 File Responsibilities

| File | Responsibility |
|------|---------------|
| `client.py` | Single `razorpay.Client` instance, initialized from settings |
| `enums.py` | `GatewayType` enum |
| `exceptions.py` | `PaymentGatewayError`, `WebhookVerificationError` |
| `schemas/razorpay.py` | Pydantic models for each Razorpay webhook event (`OrderPaidPayload`, `PaymentFailedPayload`, `PaymentLinkPayload`) |
| `services/base.py` | `PaymentGateway` ABC — interface all gateways must implement |
| `services/razorpay.py` | `RazorpayPaymentGateway` — concrete implementation of `PaymentGateway` |
| `services/factory.py` | `get_gateway("razorpay")` → returns `RazorpayPaymentGateway` instance |
| `handlers/razorpay.py` | `RazorpayWebhookHandler` — receives webhook, validates signature, routes to event handler |
| `repositories/order.py` | `OrderPaymentRepository.update_on_capture()`, `update_on_failure()`, `update_on_expire()` |

---

## 6. Service Interfaces

### 6.1 PaymentGateway Interface

```python
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

@dataclass
class BuyerInfo:
    name: str
    email: str | None
    phone: str

@dataclass
class PaymentLinkResult:
    gateway_order_id: str      # razorpay order_id OR plink_xxx
    short_url: str            # shareable URL
    gateway_response: dict

@dataclass
class CheckoutOrderResult:
    gateway_order_id: str     # razorpay order_id
    amount: int              # in paise
    currency: str
    key_id: str              # for frontend
    gateway_response: dict

@dataclass
class WebhookEvent:
    event: str               # "order.paid", "payment.failed", etc.
    gateway_order_id: str    # razorpay order_id or plink_xxx
    internal_order_id: str | None  # from notes (payment links)
    receipt: str | None      # our order UUID (checkout)
    raw_payload: dict       # full payload for processing

class PaymentGateway(ABC):
    @abstractmethod
    async def create_payment_link(
        self,
        order_id: UUID,
        amount: int,  # in paise
        currency: str,
        buyer: BuyerInfo,
        description: str,
        event_id: UUID,
        flow_type: str,
        transfer_type: str | None,
        buyer_holder_id: UUID,
    ) -> PaymentLinkResult:
        pass

    @abstractmethod
    async def create_checkout_order(
        self,
        order_id: UUID,
        amount: int,
        currency: str,
        event_id: UUID,
    ) -> CheckoutOrderResult:
        """Online checkout order (V1 out of scope, interface only)."""
        pass

    @abstractmethod
    def verify_webhook_signature(self, body: bytes, headers: dict) -> bool:
        pass

    @abstractmethod
    def parse_webhook_event(self, body: bytes, headers: dict) -> WebhookEvent:
        """Parse raw webhook body into structured event."""
        pass
```

### 6.2 RazorpayPaymentGateway

```python
class RazorpayPaymentGateway(PaymentGateway):
    def __init__(self, client: razorpay.Client, webhook_secret: str):
        self._client = client
        self._webhook_secret = webhook_secret

    async def create_payment_link(self, ...) -> PaymentLinkResult:
        # Build notes dict
        # Call self._client.payment_link.create()
        # Return PaymentLinkResult

    async def create_checkout_order(self, ...) -> CheckoutOrderResult:
        # V1: Not implemented, raises NotImplementedError
        pass

    def verify_webhook_signature(self, body: bytes, headers: dict) -> bool:
        # HMAC-SHA256 of body using RAZORPAY_WEBHOOK_SECRET
        # Compare with X-Razorpay-Signature header

    def parse_webhook_event(self, body: bytes, headers: dict) -> WebhookEvent:
        # Validate with Pydantic schema based on event type
        # Extract gateway_order_id and internal_order_id
        # Return WebhookEvent

    async def cancel_payment_link(self, payment_link_id: str) -> bool:
        try:
            self._client.payment_link.cancel(payment_link_id)
            return True
        except razorpay.errors.BadRequestError:
            return False  # Already cancelled/expired
```

---

## 7. Webhook Handler

### 7.1 Route

```
POST /webhooks/razorpay
X-Razorpay-Signature: <hmac signature>
```

### 7.2 Handler Logic (pseudocode)

```python
async def razorpay_webhook(request: Request):
    body = await request.body()
    headers = dict(request.headers)

    # 1. Verify signature
    gateway = get_gateway("razorpay")
    if not gateway.verify_webhook_signature(body, headers):
        raise WebhookVerificationError()

    # 2. Parse event
    event = gateway.parse_webhook_event(body, headers)

    # 3. Route
    if event.event == "order.paid":
        await handle_order_paid(event)
    elif event.event == "payment.failed":
        await handle_payment_failed(event)
    elif event.event == "payment_link.expired":
        await handle_payment_link_expired(event)
    elif event.event == "payment_link.cancelled":
        await handle_payment_link_cancelled(event)
    else:
        pass  # Ignore unhandled events

    return {"status": "ok"}
```

### 7.3 handle_order_paid Logic (Production-Grade Idempotent)

```python
async def handle_order_paid(event: WebhookEvent):
    # Layer 1: Find our order
    if event.internal_order_id:
        order = await OrderModel.find_by(id=event.internal_order_id)
    elif event.receipt:
        order = await OrderModel.find_by(id=event.receipt)
    else:
        return  # Cannot find order, ignore

    # Layer 4: Event deduplication — skip if this exact event already processed
    # Scoped by order_id to avoid false positives
    razorpay_event_id = event.raw_payload.get("id")
    if razorpay_event_id:
        existing = await db.execute(
            select(PaymentGatewayEventModel).where(
                PaymentGatewayEventModel.gateway_event_id == razorpay_event_id,
                PaymentGatewayEventModel.order_id == order.id
            )
        )
        if existing.first():
            return  # Duplicate event, ignore

    # Layer 1 (continued): Idempotency — skip if not pending
    if order.status != OrderStatus.pending:
        return  # Already paid/failed/expired — ignore late webhooks

    # Validate: gateway_order_id matches webhook's order id
    webhook_order_id = event.raw_payload["payload"]["order"]["entity"]["id"]
    if order.gateway_order_id != webhook_order_id:
        log.error(f"gateway_order_id mismatch for order {order.id}")
        return

    # Validate: payment.order_id matches order.id (proves payment belongs to this order)
    payment_order_id = event.raw_payload["payload"]["payment"]["entity"]["order_id"]
    if payment_order_id != webhook_order_id:
        log.error(f"payment.order_id ({payment_order_id}) != order.id ({webhook_order_id})")
        return

    # Validate payment amount (prevent underpayment)
    payment_amount = event.raw_payload["payload"]["payment"]["entity"]["amount"]
    expected_amount = int(float(order.final_amount) * 100)  # paise
    if payment_amount != expected_amount:
        async with db.begin():
            await db.execute(
                update(OrderModel)
                .where(OrderModel.id == order.id, OrderModel.status == OrderStatus.pending)
                .values(status=OrderStatus.failed,
                        failure_reason=f"amount_mismatch: expected {expected_amount}, got {payment_amount}")
            )
        await ticketing_repo.clear_locks_for_order(order.id)
        await razorpay_gateway.cancel_payment_link(order.gateway_order_id)
        return

    # Validate payment status — only process when captured
    # Note: Razorpay fires payment.authorized first, then payment.captured later
    # Our handler ignores authorized (status != "captured" returns early)
    # We only act on captured which is the final confirmed state
    payment_status = event.raw_payload["payload"]["payment"]["entity"]["status"]
    if payment_status != "captured":
        return  # Not yet captured, ignore

    payment_id = event.raw_payload["payload"]["payment"]["entity"]["id"]

    # Layer 3 + 2: EVERYTHING in one atomic transaction
    # - Atomic UPDATE: only succeeds if status is still pending
    # - Allocation creation: idempotent via UNIQUE constraint on order_id
    async with db.begin():
        updated = await db.execute(
            update(OrderModel)
            .where(
                OrderModel.id == order.id,
                OrderModel.status == OrderStatus.pending
            )
            .values(
                status=OrderStatus.paid,
                captured_at=datetime.utcnow(),
                gateway_payment_id=payment_id,
                gateway_response=event.raw_payload
            )
        )
        if updated.rowcount == 0:
            return  # Already processed by another thread — race prevented

        # Layer 2: Create allocation (idempotent via UNIQUE constraint on order_id)
        try:
            allocation = await allocation_repo.create_allocation(
                event_id=order.event_id,
                from_holder_id=...,  # from order metadata
                to_holder_id=buyer_holder_id,
                order_id=order.id,
                allocation_type=AllocationType.transfer,
                ticket_count=len(ticket_ids),
            )
            await allocation_repo.add_tickets_to_allocation(allocation.id, ticket_ids)
            await allocation_repo.upsert_edge(...)
            await ticketing_repo.update_ticket_ownership_batch(ticket_ids, buyer_holder_id)
            await allocation_repo.transition_allocation_status(
                allocation.id, AllocationStatus.pending, AllocationStatus.completed
            )
        except IntegrityError:
            # Allocation already exists — unique constraint prevented duplicate
            pass

        # Log gateway event (unique constraint prevents duplicate event logging)
        await gateway_event_repo.create(
            order_id=order.id,
            event_type="order.paid",
            gateway_event_id=razorpay_event_id,
            payload=event.raw_payload,
            gateway_payment_id=payment_id
        )

        await ticketing_repo.clear_locks_for_order(order.id)

    # Notifications: fire-and-forget (outside transaction)
    # If notification fails, order is already processed — log but don't fail
    try:
        buyer_info = get_buyer_from_order(order)
        asyncio.create_task(send_sms(buyer_info.phone, "Payment confirmed! Your tickets are ready."))
        asyncio.create_task(send_whatsapp(buyer_info.phone, "Payment confirmed! Tickets assigned."))
        if buyer_info.email:
            asyncio.create_task(send_email(buyer_info.email, "Payment Confirmed", "Your tickets have been assigned."))
    except Exception as e:
        log.warning(f"Notification failed for order {order.id}: {e}")
```
```
```

### 7.4 handle_payment_failed / expire / cancelled Logic

```python
async def handle_payment_failed(event: WebhookEvent):
    order = find_order(event)
    if not order or order.status != OrderStatus.pending:
        return

    # Atomic update: only fails if already processed
    updated = await db.execute(
        update(OrderModel)
        .where(OrderModel.id == order.id, OrderModel.status == OrderStatus.pending)
        .values(
            status=OrderStatus.failed,
            failure_reason=event.raw_payload["payload"]["payment"]["entity"].get(
                "error_description", "payment_failed"
            )
        )
    )
    if updated.rowcount == 0:
        return

    await ticketing_repo.clear_locks_for_order(order.id)
    asyncio.create_task(razorpay_gateway.cancel_payment_link(order.gateway_order_id))

    # Fire-and-forget notification
    try:
        buyer_info = get_buyer_from_order(order)
        asyncio.create_task(send_sms(buyer_info.phone, "Your ticket payment failed. Please contact the organizer."))
    except Exception:
        pass


async def handle_payment_link_expired(event: WebhookEvent):
    order = find_order(event)
    if not order or order.status != OrderStatus.pending:
        return

    # Atomic update
    updated = await db.execute(
        update(OrderModel)
        .where(OrderModel.id == order.id, OrderModel.status == OrderStatus.pending)
        .values(status=OrderStatus.expired, expired_at=datetime.utcnow())
    )
    if updated.rowcount == 0:
        return

    await ticketing_repo.clear_locks_for_order(order.id)
    asyncio.create_task(razorpay_gateway.cancel_payment_link(order.gateway_order_id))

    # Fire-and-forget notification
    try:
        buyer_info = get_buyer_from_order(order)
        asyncio.create_task(send_sms(buyer_info.phone, "Your ticket payment link has expired. Please request a new one."))
    except Exception:
        pass


async def handle_payment_link_cancelled(event: WebhookEvent):
    # Same as expired — link cancelled by organizer manually
    order = find_order(event)
    if not order or order.status != OrderStatus.pending:
        return

    # Atomic update
    updated = await db.execute(
        update(OrderModel)
        .where(OrderModel.id == order.id, OrderModel.status == OrderStatus.pending)
        .values(status=OrderStatus.expired, expired_at=datetime.utcnow(),
                failure_reason="payment_link_cancelled")
    )
    if updated.rowcount == 0:
        return

    await ticketing_repo.clear_locks_for_order(order.id)

    # Fire-and-forget notification
    try:
        buyer_info = get_buyer_from_order(order)
        asyncio.create_task(send_sms(buyer_info.phone, "Your ticket payment was cancelled by the organizer."))
    except Exception:
        pass
```

---

## 8. B2B Transfer Updates

### 8.1 Existing Free Flow (Unchanged)

All three free transfer flows remain unchanged — order is created with `status=paid` at `$0`, allocation created immediately.

### 8.2 New Paid Flow

For each of the three B2B flows, a `is_paid: bool` parameter is added to the existing transfer method. When `is_paid=True`:

**Before (free only):**
```python
order = OrderModel(..., status=OrderStatus.paid, final_amount=0)
allocation = await self._allocation_repo.create_allocation(...)
```

**After (free + paid):**
```python
order = OrderModel(
    event_id=event_id,
    user_id=creator_user_id,
    type=OrderType.transfer,
    subtotal_amount=final_amount,
    discount_amount=0,
    final_amount=final_amount,
    status=OrderStatus.pending,  # differs: pending, not paid
    payment_gateway="razorpay",
    gateway_type=GatewayType.RAZORPAY_PAYMENT_LINK,
)
# Save order first to get ID

# Lock tickets with order.id as reference, lock_expires_at=now+30min
locked_ticket_ids = await self._ticketing_repo.lock_tickets_for_transfer(...)

# Create payment link via gateway
buyer_info = BuyerInfo(name=buyer.name, email=buyer.email, phone=buyer.phone)
payment_result = await razorpay_gateway.create_payment_link(
    order_id=order.id,
    amount=int(final_amount * 100),  # paise
    currency="INR",
    buyer=buyer_info,
    description=f"B2B Transfer - {event.name}",
    event_id=event_id,
    flow_type="b2b_transfer",
    transfer_type="organizer_to_reseller",  # per flow
    buyer_holder_id=buyer_holder.id,
)

# IMPORTANT: razorpay.payment_link.create() is called with notify.sms=False, notify.email=False
# All buyer notifications are sent via our own SMS/WhatsApp/Email services

# Save gateway details to order
order.gateway_order_id = payment_result.gateway_order_id
order.gateway_response = payment_result.gateway_response
order.short_url = payment_result.short_url

# NO allocation created yet — webhook creates it

# Send payment link to buyer via our notification channels
await send_sms(buyer.phone, f"Complete your ticket purchase: {payment_result.short_url}")
await send_whatsapp(buyer.phone, f"Pay for your tickets: {payment_result.short_url}")
if buyer.email:
    await send_email(buyer.email, "Complete Your Ticket Purchase", f"Pay here: {payment_result.short_url}")
```

### 8.3 Endpoints to Update

| Service | Method | Change |
|---------|--------|--------|
| `OrganizerService` | `create_b2b_transfer` | Add `is_paid: bool = False` param |
| `OrganizerService` | `create_customer_transfer` | Add `is_paid: bool = False` param |
| `ResellerService` | `create_reseller_customer_transfer` | Add `is_paid: bool = False` param |

---

## 9. Settings

### 9.1 New Environment Variables

```python
class Settings(BaseSettings):
    # ... existing settings ...

    # Razorpay
    razorpay_key_id: str
    razorpay_key_secret: str
    razorpay_webhook_secret: str
```

---

## 10. Testing Strategy

### 10.1 Unit Tests

- `test_razorpay_payment_link_creation` — verify correct payload built, response parsed
- `test_webhook_signature_verification` — verify valid/invalid signatures handled
- `test_parse_order_paid_webhook` — verify correct extraction of `internal_order_id` from notes
- `test_parse_payment_failed_webhook` — verify structure parsing
- `test_payment_gateway_factory` — verify correct gateway returned by name
- `test_handle_order_paid_amount_mismatch` — verify order marked failed when amount doesn't match
- `test_handle_order_paid_idempotency` — verify duplicate webhook is ignored when order already paid
- `test_handle_order_paid_gateway_order_id_mismatch` — verify webhook ignored when gateway_order_id doesn't match
- `test_cancel_payment_link` — verify payment link cancellation called on expiry
- `test_allocation_unique_constraint` — verify duplicate allocation creation fails via DB constraint

### 10.2 Integration Tests

- End-to-end test with Razorpay test mode — create payment link, simulate payment, verify allocation created
- Webhook verification with real HMAC signatures

---

## 11. Files to Create / Modify

### New Files

| File | Purpose |
|------|---------|
| `src/apps/payment_gateway/__init__.py` | App export |
| `src/apps/payment_gateway/client.py` | `get_razorpay_client()` singleton |
| `src/apps/payment_gateway/enums.py` | `GatewayType` enum |
| `src/apps/payment_gateway/exceptions.py` | `PaymentGatewayError`, `WebhookVerificationError` |
| `src/apps/payment_gateway/schemas/__init__.py` | Schema exports |
| `src/apps/payment_gateway/schemas/base.py` | `BaseWebhookPayload` |
| `src/apps/payment_gateway/schemas/razorpay.py` | All Razorpay Pydantic schemas |
| `src/apps/payment_gateway/services/__init__.py` | Service exports |
| `src/apps/payment_gateway/services/base.py` | `PaymentGateway` ABC |
| `src/apps/payment_gateway/services/razorpay.py` | `RazorpayPaymentGateway` |
| `src/apps/payment_gateway/services/factory.py` | `get_gateway()` |
| `src/apps/payment_gateway/handlers/__init__.py` | Handler exports |
| `src/apps/payment_gateway/handlers/razorpay.py` | Webhook handler |
| `src/apps/payment_gateway/repositories/__init__.py` | Repo exports |
| `src/apps/payment_gateway/repositories/order.py` | `OrderPaymentRepository` |
| `src/apps/payment_gateway/repositories/event.py` | `PaymentGatewayEventRepository` — append-only audit log |
| `src/apps/payment_gateway/models.py` | `PaymentGatewayEventModel` |
| `tests/apps/payment_gateway/...` | Unit tests |

### Files to Modify

| File | Change |
|------|--------|
| `src/apps/allocation/models.py` | Add `payment_gateway`, `gateway_type`, `gateway_order_id`, `gateway_response`, `short_url`, `gateway_payment_id`, `captured_at`, `expired_at` fields to `OrderModel` |
| `src/apps/allocation/enums.py` | Add `GatewayType` enum (or import from payment_gateway) |
| `src/apps/allocation/models.py` | Add unique constraint `uq_allocations_order_id` on `AllocationModel.order_id` |
| `src/apps/organizer/service.py` | `create_b2b_transfer` — add `is_paid` param, paid flow with payment link |
| `src/apps/organizer/service.py` | `create_customer_transfer` — add `is_paid` param, paid flow |
| `src/apps/reseller/service.py` | `create_reseller_customer_transfer` — add `is_paid` param, paid flow |
| `src/main.py` | Add webhook route `POST /webhooks/razorpay` |
| `src/settings.py` | Add `razorpay_key_id`, `razorpay_key_secret`, `razorpay_webhook_secret` |
| `src/jobs/lock_cleanup.py` | Expire pending orders whose lock expired, cancel payment links |
| `src/db/base.py` | Add `text` import if not present (for server_default) |

### Migration

| Migration | Change |
|-----------|--------|
| `xxx_add_payment_gateway_fields_to_orders.sql` | Add `payment_gateway`, `gateway_type`, `gateway_order_id`, `gateway_response`, `short_url`, `gateway_payment_id` (UNIQUE), `captured_at`, `expired_at` columns to `orders` table, add unique constraint on `gateway_order_id` |
| `xxx_add_order_id_unique_to_allocations.sql` | Add unique constraint `uq_allocations_order_id` on `allocations.order_id` |
| `xxx_create_payment_gateway_events.sql` | Create `payment_gateway_events` table with unique constraint on `(order_id, event_type, gateway_event_id)` |

---

## 12. Implementation Order

### Phase 1: Foundation
1. Add OrderModel fields (migration + model update)
2. Create `payment_gateway` app structure
3. Create `GatewayType` enum and exceptions
4. Create `razorpay.Client` singleton
5. Create `PaymentGateway` ABC interface

### Phase 2: Gateway Implementation
6. Create Razorpay Pydantic schemas for all webhook events
7. Implement `RazorpayPaymentGateway.create_payment_link()`
8. Implement `verify_webhook_signature()`
9. Implement `parse_webhook_event()`
10. Create `get_gateway()` factory

### Phase 3: Webhook Handler
11. Create `RazorpayWebhookHandler` with event routing
12. Implement `handle_order_paid`
13. Implement `handle_payment_failed`, `handle_payment_link_expired`, `handle_payment_link_cancelled`
14. Add webhook route to `main.py`

### Phase 4: B2B Paid Flows
15. Update `OrganizerService.create_b2b_transfer` with paid mode
16. Update `OrganizerService.create_customer_transfer` with paid mode
17. Update `ResellerService.create_reseller_customer_transfer` with paid mode

### Phase 5: Testing
18. Write unit tests for gateway, schemas, webhook handler
19. Integration test with Razorpay test mode

---

*Last updated: 2026-05-02*