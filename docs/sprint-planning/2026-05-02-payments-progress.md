# feat-payments Branch — Implementation Progress

> Track what was built on the `feat-payments` branch, from payment gateway integration to B2B paid transfers with Razorpay.

**Branch:** `feat-payments`
**Started:** 2026-05-02
**Current Status:** ✅ PHASE 5 COMPLETE — All paid transfer flows implemented + tested

---

## Overview

The `feat-payments` branch implements the Razorpay payment gateway integration for B2B paid transfers. Before this work, all transfers were free (`price=0`, immediate completion). After this work, there are two modes per transfer:

| Mode | Behavior |
|------|----------|
| `TransferMode.FREE` | $0 order, immediate completion, no payment gateway |
| `TransferMode.PAID` | Creates pending order → Razorpay payment link → webhook confirms payment → allocation created |

The implementation spans 5 phases, each building on the previous:

```
Phase 1          → Expiration handler (scheduler-based)
Phase 2          → Payment gateway app scaffold
Phase 3          → Webhook handler (order.paid, payment.failed, etc.)
Phase 4 (A/B/C)  → Paid transfer flows (3 directions)
Phase 5          → Tests
```

---

## Architecture

### Payment Flow (Paid Mode)

```
┌─────────────────────────────────────────────────────────────────┐
│                        PAID TRANSFER FLOW                        │
│                                                                   │
│  User calls endpoint (mode=PAID, price=X)                       │
│                         │                                        │
│                         ▼                                        │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │ Step 1: Create PENDING order with lock_expires_at (30 min)   ││
│  └────────────────────────────┬──────────────────────────────────┘│
│                               │                                   │
│                               ▼                                   │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │ Step 2: Lock tickets (FIFO, by order_id as lock_reference)   ││
│  └────────────────────────────┬──────────────────────────────────┘│
│                               │                                   │
│                               ▼                                   │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │ Step 3: Create Razorpay payment link                        ││
│  │   • internal_order_id in notes → maps webhook to our order   ││
│  │   • sms/email notify disabled → we send our own notifications││
│  └────────────────────────────┬──────────────────────────────────┘│
│                               │                                   │
│                               ▼                                   │
│              ┌────────────────────────────────┐                  │
│              │ Payment link sent to customer   │                  │
│              │ (SMS/WhatsApp/Email)           │                  │
│              └─────────────┬────────────────────┘                  │
│                            │                                      │
│            ┌───────────────┴───────────────┐                      │
│            ▼                               ▼                      │
│  ┌──────────────────────┐     ┌──────────────────────┐           │
│  │ Customer pays        │     │ Customer doesn't pay  │           │
│  │ ─────────────────────│     │ ─────────────────────│           │
│  │ Razorpay → webhook   │     │ Expiry worker (30s)  │           │
│  │ order.paid event     │     │ ─────────────────────│           │
│  │ ─────────────────────│     │ Order → expired      │           │
│  │ handle_order_paid()  │     │ Tickets unlocked     │           │
│  │ ─────────────────────│     │ Payment link cancelled│           │
│  │ • Dedup (IntegrityError on UNIQUE(order_id, event_type, gateway_event_id)) │
│  │ • Validate amount match (order.final_amount * 100)           │           │
│  │ • Validate gateway_order_id match                            │           │
│  │ • Atomic UPDATE order → paid                                 │           │
│  │ • Create allocation + claim link                             │           │
│  │ • Update ticket ownership                                    │           │
│  │ • Upsert AllocationEdge                                      │           │
│  └──────────────────────┘     └──────────────────────┘           │
└─────────────────────────────────────────────────────────────────┘
```

### Lock Reference Types

Tickets have two lock reference types depending on which flow locked them:

| lock_reference_type | Used in | Cleared by |
|---|---|---|
| `"order"` | Free transfer flow | `clear_locks_for_order(order_id)` |
| `"transfer"` | Paid transfer flow (before webhook) | `clear_locks_for_order(order_id)` |

Both types are cleared by `clear_locks_for_order()` — the expiry worker clears both.

---

## Phase 1: Expiration Handler ✅

**Spec:** `docs/superpowers/specs/2026-05-02-payment-gateway-design.md`
**Plan:** `docs/superpowers/plans/2026-05-02-expiration-handler.md`
**Completed:** 2026-05-03

### Problem

Paid orders have a 30-minute window for payment. If the customer doesn't pay, the order must be expired and tickets released back to the pool. This needed a background worker.

### Decision: Scheduler vs Message-Driven

**Why NOT message-driven?**
- NATS `NATS-Deliver-Time` headers don't work reliably in the nats-py version
- Message-driven would need complex retry logic and dead-letter queues

**Why scheduler-based?**
- Single SQL UPDATE scans all expired orders at once (efficient)
- Deterministic max latency: 30 seconds from actual expiry time
- No retry logic needed — next scheduler run picks up any missed orders
- Atomic with RETURNING clause

### What Was Built

```
src/apps/queues/
├── __init__.py                    # Exports: STREAMS, NATSClient, OrderExpiryRepository
├── config.py                      # StreamConfig + STREAMS dict
├── repository.py                  # OrderExpiryRepository
│                                  #   • bulk_expire_pending_orders()
│                                  #   • clear_ticket_locks(order_id)
└── workers/
    ├── __init__.py
    └── expiry.py                  # ExpiryWorker (every 30s)

scripts/
└── run_expiry_worker.py           # Entry point (systemd/supervisor)

tests/apps/queues/
└── test_expiry_worker.py          # 10 unit tests (all passing ✅)
```

### Order Lifecycle

```
[pending] ───pay──▶ [paid]                    (normal flow)
    ▲
    │
    └──expiry── [expired]                    (failed to pay in time)
         │
         └──payment_link_cancelled── [expired] (organizer cancelled)
```

### Flow Diagram

```
┌──────────────────────────────────────────────────────────────┐
│                   EXPIRY WORKER (every 30s)                  │
└─────────────────────────────┬────────────────────────────────┘
                              │
                              ▼
              ┌─────────────────────────────┐
              │  bulk_expire_pending_orders  │     ◄── Single SQL UPDATE
              │  WHERE status='pending'       │         with RETURNING
              │  AND lock_expires_at < now    │
              └──────────────┬────────────────┘
                             │  returns list of expired orders
                             ▼
              ┌─────────────────────────────┐
              │  For EACH expired order:    │
              │  clear_ticket_locks(order)   │     ◄── Unlocks held tickets
              └──────────────┬───────────────┘
                             │
                            ┌┴─────────────────────────────┐
                            │ lock_reference_type ==        │
                            │   "order" OR "transfer" ?    │     ◄── Both types cleared
                            └──────────────────────────────┘
                                   │
                                   ▼
                          cancel_payment_link()
                          (fire-and-forget, 3x retry)
```

### Before vs After Expiry

| Field | Before Expiry | After Expiry |
|-------|-------------|--------------|
| `status` | `pending` | `expired` |
| `lock_expires_at` | `2026-05-03 15:40:00+00` | unchanged |
| `expired_at` | `NULL` | `2026-05-03 15:40:15+00` |
| Ticket locks | Held for this order | Released (lock ref cleared) |

### Partial Index

The expiry scan uses a partial index for efficiency:

```sql
CREATE INDEX ix_orders_pending_lock_expiry
  ON orders (status, lock_expires_at)
  WHERE status = 'pending';
```

Only `pending` orders are scanned — never touches `completed`, `expired`, or `failed`.

### Ticket Lock Release

`clear_ticket_locks(order_id)` releases tickets locked with either reference type:

```sql
UPDATE tickets
SET lock_reference_type = NULL,
    lock_reference_id   = NULL,
    lock_expires_at     = NULL
WHERE lock_reference_id = <order_id>
  AND lock_reference_type IN ('order', 'transfer')  -- handles both paid and free flows
```

### Tests

```bash
uv run pytest tests/apps/queues/test_expiry_worker.py -v  → 10 passed ✅
```

**Commit:** `feat(queues): add expiration handler with scheduler-based worker`

---

## Phase 2: Payment Gateway App Scaffold ✅

**Plan:** `docs/superpowers/plans/2026-05-03-payment-gateway-foundation.md`
**Completed:** 2026-05-03

### What Was Built

```
src/apps/payment_gateway/
├── __init__.py                    # App export
├── client.py                      # RazorpayClient singleton (get_razorpay_client())
├── enums.py                       # GatewayType enum (RAZORPAY_PAYMENT_LINK)
├── exceptions.py                  # PaymentGatewayError, WebhookVerificationError
├── models.py                      # PaymentGatewayEventModel (append-only audit log)
├── schemas/
│   ├── __init__.py
│   ├── base.py                   # WebhookEvent dataclass
│   └── razorpay.py               # Pydantic schemas for all Razorpay events
│                                  #   OrderPaidPayload, PaymentFailedPayload,
│                                  #   PaymentLinkPayload (expired + cancelled)
├── services/
│   ├── __init__.py
│   ├── base.py                   # PaymentGateway ABC
│   │                            #   • create_payment_link()
│   │                            #   • create_checkout_order()
│   │                            #   • verify_webhook_signature()
│   │                            #   • parse_webhook_event()
│   │                            #   • cancel_payment_link()
│   ├── razorpay.py              # RazorpayPaymentGateway (implements ABC)
│   └── factory.py               # get_gateway("razorpay") — singleton factory
├── handlers/
│   ├── __init__.py
│   └── razorpay.py              # RazorpayWebhookHandler (routes + processes events)
├── repositories/
│   ├── __init__.py
│   ├── order.py                 # OrderPaymentRepository
│   │                            #   • update_pending_order_on_payment_link_created()
│   │                            #   • update_order_on_payment_success()
│   └── event.py                 # PaymentGatewayEventRepository (audit log)
└── webhooks.py                  # HTTP endpoint (POST /webhooks/razorpay)

tests/apps/payment_gateway/
├── test_client.py               # Razorpay client singleton
├── test_enums.py                # GatewayType enum
├── test_exceptions.py           # Exception classes
├── test_models.py               # PaymentGatewayEventModel
├── test_schemas.py              # Pydantic schema parsing
├── test_services.py             # BuyerInfo, PaymentLinkResult dataclasses
├── test_factory.py              # get_gateway() factory
├── test_verify_signature.py     # HMAC signature verification
├── test_create_payment_link.py  # create_payment_link() call construction
├── test_cancel_payment_link.py  # cancel_payment_link() + error handling
├── test_parse_webhook.py        # parse_webhook_event() extraction
├── test_webhook_handler.py      # Event routing (order.paid, etc.)
└── test_event_repository.py     # Event audit log creation
```

### Key Interfaces

**PaymentGateway ABC:**
```python
class PaymentGateway(ABC):
    async def create_payment_link(
        order_id, amount: int, currency: str, buyer: BuyerInfo,
        description: str, event_id, flow_type: str,
        transfer_type: str | None, buyer_holder_id
    ) -> PaymentLinkResult

    async def create_checkout_order(...) -> CheckoutOrderResult  # NotImplemented in V1

    def verify_webhook_signature(body: bytes, headers: dict) -> bool

    def parse_webhook_event(body: bytes, headers: dict) -> WebhookEvent

    async def cancel_payment_link(payment_link_id: str) -> bool
```

**BuyerInfo dataclass (sent with payment link):**
```python
@dataclass
class BuyerInfo:
    name: str
    email: str | None
    phone: str | None
```

**PaymentLinkResult (returned from create_payment_link):**
```python
@dataclass
class PaymentLinkResult:
    gateway_order_id: str   # Razorpay payment link ID (plink_xxx)
    short_url: str          # razorpay.in/pl/xxx
    gateway_response: dict  # Full API response
```

**WebhookEvent (returned from parse_webhook_event):**
```python
@dataclass
class WebhookEvent:
    event: str                    # "order.paid", "payment.failed", etc.
    gateway_order_id: str        # Razorpay order/payment link ID
    internal_order_id: str | None  # Our order UUID (from notes)
    receipt: str | None
    raw_payload: dict            # Full raw payload for handler
```

### Razorpay Notes Architecture

The `notes` field in Razorpay payment links is how we map a webhook back to our order:

```python
payload = {
    "notes": {
        "internal_order_id": str(order_id),   # Our UUID — primary lookup key
        "event_id": str(event_id),
        "flow_type": "b2b_transfer",
        "transfer_type": "organizer_to_reseller",  # or _to_customer, reseller_to_customer
    }
}
```

When Razorpay sends `order.paid` webhook, we extract `notes.internal_order_id` to find our `Order.id`.

### Tests

```bash
uv run pytest tests/apps/payment_gateway/ -v → 35 passed ✅
```

**Commit:** `feat(payment-gateway): add Phase 1 foundation`

---

## Phase 3: Webhook Handler ✅

**Plan:** `docs/superpowers/plans/2026-05-03-payment-gateway-phase3.md`
**Completed:** 2026-05-04

### What Was Built

`RazorpayWebhookHandler` in `src/apps/payment_gateway/handlers/razorpay.py` with 4-layer idempotent processing for `order.paid`:

### 4-Layer Idempotency (order.paid)

```
Layer 1: Fast pre-checks (no DB write)
  ├── Missing internal_order_id + receipt → return ok
  ├── Invalid UUID format → return ok
  ├── Order not found → return ok
  └── Order status != pending → return ok (already processed)

Layer 2: Event deduplication (DB write attempt)
  └── Attempt insert into payment_gateway_events
      UNIQUE(order_id, event_type, gateway_event_id)
      ├── Success → continue to validation
      └── IntegrityError → duplicate, return ok

Layer 3: Atomic UPDATE (only if still pending)
  └── UPDATE orders SET status=paid WHERE id=X AND status=pending
      ├── rowcount == 1 → success, continue
      └── rowcount == 0 → another thread already processed, return ok

Layer 4: Allocation creation (idempotent via UNIQUE constraint)
  └── INSERT INTO allocations (order_id, ...)
      UNIQUE(order_id)
      ├── Success → allocation created
      └── IntegrityError → already exists (shouldn't happen if Layer 3 worked)
```

### Webhook Handler Methods

| Method | Trigger | Behavior |
|--------|---------|----------|
| `handle_order_paid()` | `order.paid` | 4-layer idempotent flow; validate amount; create allocation |
| `handle_payment_failed()` | `payment.failed` | Atomic UPDATE to failed; clear ticket locks |
| `handle_payment_link_expired()` | `payment_link.expired` | Atomic UPDATE to expired; clear locks; cancel payment link |
| `handle_payment_link_cancelled()` | `payment_link.cancelled` | Same as expired, with reason=cancelled |

### Amount Validation

For `order.paid`, the handler validates the paid amount matches our order's `final_amount`:

```python
payment_amount = raw["payload"]["payment"]["entity"]["amount"]  # in paise
expected_amount = int(float(order.final_amount) * 100)

if payment_amount != expected_amount:
    # Mark order failed, clear locks, cancel payment link
    await order UPDATE status=failed, failure_reason="amount_mismatch"
    await ticketing_repo.clear_locks_for_order(order.id)
    await gateway.cancel_payment_link(order.gateway_order_id)
```

### Payment Link Cancellation

When orders expire or fail, the Razorpay payment link is cancelled via `cancel_payment_link()`:

```python
async def cancel_payment_link(self, payment_link_id: str) -> bool:
    try:
        self._client.payment_link.cancel(payment_link_id)
        return True
    except razorpay.errors.BadRequestError:
        return False  # Already cancelled/expired — that's fine
```

### Tests

The handler routing was tested in Phase 2 (`test_webhook_handler.py`). Phase 5 added the edge case tests.

**Commit:** `feat(payment-gateway): add webhook handler with 4-layer idempotency`

---

## Phase 4: Paid Transfer Flows ✅

**Plans:**
- `docs/superpowers/plans/2026-05-04-payment-gateway-phase4.md` (shared foundation)
- `docs/superpowers/plans/2026-05-04-payment-gateway-phase4a-organizer-to-reseller.md`
- `docs/superpowers/plans/2026-05-04-payment-gateway-phase4b-organizer-to-customer.md`
- `docs/superpowers/plans/2026-05-04-payment-gateway-phase4c-reseller-to-customer.md`

**Completed:** 2026-05-04

### TransferMode Enum

Added to `src/apps/allocation/enums.py`:

```python
class TransferMode(str, Enum):
    FREE = "free"   # $0 order, immediate completion
    PAID = "paid"   # Pending order + payment link → webhook confirms
```

Both modes use the same ticket-locking flow. The difference is whether payment is involved.

### Phase 4-Shared: Foundation

**Files modified:**
- `src/apps/allocation/enums.py` — Added `TransferMode` enum
- `src/apps/organizer/request.py` — Added `mode: TransferMode`, `price: float | None` to `CreateB2BTransferRequest` + `CreateCustomerTransferRequest`
- `src/apps/resellers/request.py` — Same for `CreateResellerCustomerTransferRequest`
- `src/apps/organizer/response.py` — Added `mode: TransferMode`, `payment_url: str | None` to responses
- `src/apps/organizer/service.py` — `create_b2b_transfer` and `create_customer_transfer` support PAID mode
- `src/apps/resellers/service.py` — `create_reseller_customer_transfer` supports PAID mode
- `src/apps/payment_gateway/repositories/order.py` — Implemented `update_pending_order_on_payment_link_created()`
- `src/apps/ticketing/repository.py` — Fixed `clear_locks_for_order` to handle both `"order"` and `"transfer"` lock types
- `src/apps/queues/repository.py` — Fixed `clear_ticket_locks` to handle both lock types

### Phase 4A: Organizer → Reseller (Paid)

**Endpoint:** `POST /organizers/{id}/b2b-transfer`
**Flow:** When `mode=PAID`, organizer sets a flat `price` for the transfer order.

```
1. Validate reseller is accepted for this event
2. Get reseller's TicketHolder
3. Check available ticket count ≥ quantity
4. Get B2B ticket type for event
5. Create PENDING order (status=pending, lock_expires_at=now+30min, price=X)
6. Lock tickets (FIFO, lock_reference_type="transfer")
7. Create Razorpay payment link (notes.internal_order_id = order.id)
8. Update order with gateway_order_id + short_url
9. Send payment link via SMS/WhatsApp/Email
10. Return B2BTransferResponse(status=pending_payment, payment_url, mode=PAID)
    (No allocation created — webhook handles that on payment confirmation)
```

**Price:** Flat price per order, not per ticket. `final_amount = price` (not `price * quantity`).

### Phase 4B: Organizer → Customer (Paid)

**Endpoint:** `POST /organizers/{id}/customer-transfer`
**Flow:** Similar to 4A but customer may not have a TicketHolder — resolved by phone/email.

```
1. Validate organizer owns event
2. Validate event_day_id belongs to event
3. Get organizer's TicketHolder
4. Check available ticket count ≥ quantity
5. Resolve customer TicketHolder (phone+email → existing or create new)
6. Get B2B ticket type
7. Create PENDING order (price=X)
8. Lock tickets (transfer lock)
9. Create Razorpay payment link
10. Send payment link to customer
11. Return CustomerTransferResponse(status=pending_payment, payment_url, mode=PAID)
```

### Phase 4C: Reseller → Customer (Paid)

**Endpoint:** `POST /resellers/me/customer-transfer`
**Flow:** Reseller transfers B2B tickets to end customer.

```
1. Validate user is reseller for this event
2. Validate event_day_id belongs to event
3. Get reseller's TicketHolder
4. Check available count ≥ quantity
5. Resolve customer TicketHolder
6. Create PENDING order (price=X)
7. Lock tickets
8. Create Razorpay payment link
9. Send payment link to customer
10. Return CustomerTransferResponse(status=pending_payment, payment_url, mode=PAID)
```

### Key Design Decision: Flat Price

Price is **flat per order** (`final_amount = price`), not per-ticket. This means:

```python
# Order creation in paid flow:
order = OrderModel(
    subtotal_amount=total_price,   # flat price from request
    discount_amount=0.0,
    final_amount=total_price,      # same as subtotal
)
```

This differs from how you'd price per ticket — the organizer sets one price for the entire transfer, regardless of quantity.

### Bug Fixes in Phase 4

**Bug 1: `datetime.utcnow()` deprecation** (fixed in `lock_tickets_for_transfer`)
```python
# Before (deprecated):
expires_at = datetime.utcnow() + timedelta(minutes=lock_ttl_minutes)

# After (timezone-aware):
expires_at = datetime.now(timezone.utc) + timedelta(minutes=lock_ttl_minutes)
```

**Bug 2: `clear_locks_for_order` only handling `"order"` type** (fixed in both repos)
```python
# Before (only clears "order" locks, misses "transfer" locks):
WHERE lock_reference_type = 'order'

# After (clears both):
WHERE lock_reference_type IN ('order', 'transfer')
```

---

## Phase 5: Testing ✅

**Plan:** `docs/superpowers/plans/2026-05-04-payment-gateway-phase5-testing.md`
**Completed:** 2026-05-04

### Tests Written

| File | Tests | What It Covers |
|------|-------|----------------|
| `tests/apps/payment_gateway/test_webhook_handler_edge_cases.py` | 7 | Handler edge cases: amount mismatch, already-paid idempotency, gateway_order_id mismatch, duplicate event IntegrityError dedup, non-pending orders, order-not-found |
| `tests/apps/allocation/test_allocation_repository.py` | 1 | UNIQUE(order_id) constraint prevents double allocation on duplicate webhook |
| `tests/apps/organizer/test_organizer_service.py` | 8 | `create_b2b_transfer` + `create_customer_transfer` with PAID mode: returns pending_payment + payment_url, no allocation created |
| `tests/apps/resellers/test_reseller_customer_transfer.py` | 6 | `create_reseller_customer_transfer` with PAID mode: same behavior |

### Test Coverage Summary

| Component | Covered By |
|-----------|------------|
| Signature verification routing | ✅ existing |
| Event type routing (order.paid, payment.failed, etc.) | ✅ existing |
| Parse order.paid extracts internal_order_id | ✅ existing |
| Parse payment.failed structure | ✅ existing |
| Parse payment_link.expired structure | ✅ existing |
| cancel_payment_link success + already-cancelled | ✅ existing |
| create_payment_link correct payload + notes | ✅ existing |
| Factory returns correct gateway | ✅ existing |
| **Amount mismatch → failed** | ✅ new (edge cases) |
| **Already-paid order idempotency** | ✅ new (edge cases) |
| **gateway_order_id mismatch → skip** | ✅ new (edge cases) |
| **Duplicate event (IntegrityError) → skip** | ✅ new (edge cases) |
| **payment.failed on non-pending → skip** | ✅ new (edge cases) |
| **payment_link.expired not found → skip** | ✅ new (edge cases) |
| **payment_link.cancelled non-pending → skip** | ✅ new (edge cases) |
| **Allocation UNIQUE constraint prevents double-create** | ✅ new |
| **create_b2b_transfer PAID returns pending_payment** | ✅ new (organizer service) |
| **create_customer_transfer PAID returns pending_payment** | ✅ new (organizer service) |
| **create_reseller_customer_transfer PAID returns pending_payment** | ✅ new (reseller service) |

### Running Tests

```bash
# Phase 5 specific tests
uv run pytest tests/apps/payment_gateway/test_webhook_handler_edge_cases.py tests/apps/allocation/test_allocation_repository.py -v

# Organizer service paid transfer tests
uv run pytest tests/apps/organizer/test_organizer_service.py -v

# Reseller service paid transfer tests
uv run pytest tests/apps/resellers/test_reseller_customer_transfer.py -v

# Full payment gateway suite
uv run pytest tests/apps/payment_gateway/ -v → 35 passed
```

**Total: 73 tests passing across payment_gateway + organizer + reseller + allocation test suites.**

---

## File Inventory

### New Files Created (feat-payments branch)

```
src/apps/queues/                          # NEW APP
src/apps/payment_gateway/                 # NEW APP
src/apps/allocation/models.py             # Modified (added payment fields)
src/apps/allocation/enums.py              # Modified (added TransferMode)
src/apps/ticketing/repository.py          # Modified (fixed lock types + datetime)
src/apps/queues/repository.py             # Modified (fixed lock types)
src/apps/organizer/request.py             # Modified (added mode + price)
src/apps/organizer/response.py            # Modified (added mode + payment_url)
src/apps/organizer/service.py             # Modified (paid transfer flows)
src/apps/resellers/request.py            # Modified (added mode + price)
src/apps/resellers/response.py            # Modified (added payment_url)
src/apps/resellers/service.py             # Modified (paid transfer flow)
src/apps/payment_gateway/repositories/order.py  # Modified (implemented)
src/apps/payment_gateway/handlers/razorpay.py  # Modified (allocation creation)
tests/apps/queues/                        # NEW
tests/apps/payment_gateway/               # NEW
tests/apps/organizer/test_organizer_service.py  # Modified (added paid mode tests)
tests/apps/resellers/test_reseller_customer_transfer.py  # Modified
tests/apps/allocation/test_allocation_repository.py  # NEW
tests/apps/payment_gateway/test_webhook_handler_edge_cases.py  # NEW
```

### Migration Files

```
migrations/versions/2026-05-02_XXXXXXXXXXXXXXXX_add_payment_fields_to_orders.py
migrations/versions/2026-05-02_XXXXXXXXXXXXXXXX_add_payment_gateway_events_table.py
migrations/versions/2026-05-03_XXXXXXXXXXXXXXXX_add_lock_type_fix.py
```

---

## Commit History

| Date | Commit | Description |
|------|--------|-------------|
| 2026-05-03 | `feat(queues): add expiration handler with scheduler-based worker` | Phase 1: ExpiryWorker, OrderExpiryRepository |
| 2026-05-03 | `feat(payment-gateway): add Phase 1 foundation` | Phase 2: App scaffold, ABC, factory |
| 2026-05-03 | `feat(payment-gateway): add webhook handler with 4-layer idempotency` | Phase 3: handle_order_paid + handlers |
| 2026-05-04 | `feat: Phase 4 paid transfers complete — organizer/reseller/customer flows + price field` | Phase 4: All 3 paid flows + TransferMode enum + bug fixes |
| 2026-05-04 | `test: add webhook handler edge case tests` | Phase 5: 7 edge case tests |
| 2026-05-04 | `test: add allocation repository UNIQUE constraint test` | Phase 5: IntegrityError test |
| 2026-05-04 | `test: add Phase 5 paid transfer flow tests` | Phase 5: Service tests for paid modes |

---

## What's Left

**Nothing from the tech spec is left undone.** All 5 phases are complete:

1. ✅ Expiration handler (scheduler-based, clears both lock types)
2. ✅ Payment gateway app scaffold
3. ✅ Webhook handler with 4-layer idempotency
4. ✅ All 3 paid transfer flows (O→R, O→C, R→C) + flat price support
5. ✅ Tests (73 tests passing)

### Future Work (Out of Scope for V1)

- **Online checkout** — customer buys directly from event page (not B2B transfer)
- **Refund handling** — Razorpay refund webhooks
- **Multi-gateway support** — Stripe or other gateways
- **Payment retry** — automatic retry for failed payments
- **Partial payment** — paying in installments

---

*Last updated: 2026-05-04 (Phase 5 complete)*