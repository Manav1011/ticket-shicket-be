# feat-payments Branch — Implementation Progress

> Track what was built on the `feat-payments` branch, from payment gateway integration to B2B paid transfers with Razorpay.

**Branch:** `feat-payments`
**Started:** 2026-05-02
**Current Status:** 🚧 Payment Gateway Foundation — Starting

---

## Current Focus: Expiration Handling (Queues App) — ✅ COMPLETE

**Spec:** `docs/superpowers/specs/2026-05-02-payment-gateway-design.md`
**Plan:** `docs/superpowers/plans/2026-05-02-expiration-handler.md`
**Branch:** `feat-payments`
**Completed:** 2026-05-03

### Architecture Decision: Scheduler-Based vs Message-Driven

**Why NOT message-driven?**
- NATS `NATS-Deliver-Time` headers don't work reliably in nats-py version
- **Scheduler approach (implemented):**
  - ✅ Single SQL UPDATE query scans all expired orders (efficient)
  - ✅ Deterministic latency: max 30s from expiry time
  - ✅ No complex retry logic needed
  - ✅ Atomic with RETURNING clause

### What Was Built

```
src/apps/queues/                   # New app for async message handling
├── __init__.py                    # Exports: STREAMS, NATSClient, OrderExpiryRepository
├── config.py                      # StreamConfig + STREAMS dict
├── repository.py                  # OrderExpiryRepository (moved from allocation)
├── clients/
│   ├── __init__.py
│   └── nats.py                    # NATSClient singleton + publish_order_created()
└── workers/
    ├── __init__.py
    └── expiry.py                  # ExpiryWorker (scheduler-based, 30s interval)

scripts/
└── run_expiry_worker.py           # Entry point for systemd/supervisor (executable)

tests/
└── apps/queues/test_expiry_worker.py  # 10 unit tests (all passing)
```

## How the Expiration Handler Works

### Order Lifecycle

```
[PENDING] ──pay──▶ [PAID/COMPLETED]          (normal flow)
     ▲
     │
     └──expiry── [EXPIRED]                   (failed to pay in time)
```

An order starts in `pending` status with a `lock_expires_at` timestamp. If the user
completes payment before that time, the order moves to `completed`. If the timer
fires and the order is still `pending` + past `lock_expires_at`, it is atomically
expired.

### Flow Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                  EXPIRY WORKER (every 30s)                  │
└──────────────────────────┬────────────────────────────────┘
                           │
                           ▼
              ┌────────────────────────────┐
              │  bulk_expire_pending_orders │          ◄── Single SQL UPDATE
              │  WHERE status='pending'     │              with RETURNING
              │  AND lock_expires_at < now  │
              └──────────────┬───────────────┘
                             │  returns list of expired orders
                             ▼
              ┌────────────────────────────┐
              │  For EACH expired order:    │
              │  clear_ticket_locks(order)  │          ◄── Unlocks held tickets
              └──────────────┬───────────────┘
                             │
                    ┌────────┴────────┐
                    │ gateway_type == │          ◄── Commented out for now
                    │ RAZORPAY_       │              (payment gateway not
                    │ PAYMENT_LINK ?  │              yet integrated)
                    └────────┬────────┘
                             │  YES (future)
                             ▼
                   cancel_payment_link()
                   (fire-and-forget, retry 3x)
```

### Before vs After Order States

| Field | Before Expiry | After Expiry |
|-------|-------------|--------------|
| `status` | `pending` | `expired` |
| `lock_expires_at` | `2026-05-03 15:40:00+00` | unchanged |
| `expired_at` | `NULL` | `2026-05-03 15:40:15+00` (when expiry runs) |
| `gateway_order_id` | `"plan_abc123"` | unchanged |
| Ticket locks | Tickets held for this order | Tickets released (lock ref cleared) |

### Partial Index

The query uses a partial index on `(status, lock_expires_at)`:

```sql
CREATE INDEX ix_orders_pending_lock_expiry
  ON orders (status, lock_expires_at)
  WHERE status = 'pending';
```

This means the expiry scan only touches `pending` orders — it never hits
`completed`, `expired`, or `failed` rows.

---

## How Ticket Locking Works

### Ticket Model Lock Fields

| Field | Type | Description |
|-------|------|-------------|
| `lock_reference_type` | `VARCHAR(32) \| NULL` | What kind of thing locked this ticket (`'order'`) |
| `lock_reference_id` | `UUID \| NULL` | The `Order.id` that locked this ticket |
| `lock_expires_at` | `DATETIME \| NULL` | When the lock auto-releases if unpaid |

### Lock Flow

**Step 1 — Order Created:** When a purchase order is created, for each reserved ticket:

```
ticket.lock_reference_type = "order"
ticket.lock_reference_id   = order.id
ticket.lock_expires_at    = order.lock_expires_at   # e.g. now + 15 min
```

**Step 2 — Pending Order (waiting for payment):**

```
Order(id=abc, status=pending, lock_expires_at=15:40)
  │
  └──▶ Ticket_1 (lock_ref=order:abc, lock_expires_at=15:40)
  └──▶ Ticket_2 (lock_ref=order:abc, lock_expires_at=15:40)
  └──▶ Ticket_3 (lock_ref=order:abc, lock_expires_at=15:40)
```

User has ~15 minutes to pay. Nobody else can buy/claim these tickets while locked.

**Step 3a — User pays in time → Order completed**

Payment succeeds → order status becomes `completed`. Tickets remain linked to the
order (lock is now stale but irrelevant since order is done).

**Step 3b — No payment in time → Expiry worker runs (every 30s)**

```
ExpiryWorker:
  1. bulk_expire_pending_orders()
       UPDATE orders SET status='expired', expired_at=NOW()
       WHERE status='pending' AND lock_expires_at < NOW()
       RETURNING id, gateway_type, gateway_order_id

  2. For each expired order:
       clear_ticket_locks(order_id)
         UPDATE tickets
         SET lock_reference_type=NULL,
             lock_reference_id=NULL,
             lock_expires_at=NULL
         WHERE lock_reference_type='order'
           AND lock_reference_id=<expired_order_id>
```

**After expiry:**

```
Order(id=abc, status=expired, expired_at=15:40)
  │
  └──▶ Ticket_1 (lock_ref=NULL)  ←─ released, now free
  └──▶ Ticket_2 (lock_ref=NULL)  ←─ released, now free
  └──▶ Ticket_3 (lock_ref=NULL)  ←─ released, now free
```

### The Connection (how tickets know which order locked them)

```
Ticket  ──lock_reference_id──▶  Order.id
Ticket  ──lock_reference_type──▶  "order"
```

`clear_ticket_locks(order_id)` finds locked tickets with:
`WHERE lock_reference_id = order_id AND lock_reference_type = 'order'`

### Stream Design

| Entity | Config |
|--------|--------|
| Stream | `ORDERS_EXPIRY` — workqueue retention, 1hr max age, 10MB |
| Subject | `orders.expiry` |
| Purpose | Audit/tracing only (worker doesn't consume from it) |

---

## What's Done

✅ **Phase 1: Expiration Handler (Queues App)** — COMPLETED 2026-05-03

- [x] GatewayType enum added to allocation/enums.py
- [x] OrderModel payment fields added (lock_expires_at, gateway_type, gateway_order_id, etc.)
- [x] queues app scaffolded with proper structure
- [x] NATS client singleton with Jetstream support
- [x] OrderExpiryRepository with bulk_expire_pending_orders() + clear_ticket_locks()
- [x] ExpiryWorker — scheduler-based (30s interval), NOT message-driven
  - Rationale: NATS Deliver-Time headers unreliable in nats-py version; bulk scan is simpler, faster (1 query), deterministic latency
- [x] Payment link cancellation **commented out** — to be enabled once payment gateway is integrated
- [x] 10 comprehensive unit tests (all passing ✅)
- [x] scripts/run_expiry_worker.py entry point (executable)
- [x] Commit: `feat(queues): add expiration handler with scheduler-based worker`

---

## What's Done

✅ **Phase 1: Expiration Handler (Queues App)** — COMPLETED 2026-05-03

- [x] GatewayType enum added to allocation/enums.py
- [x] OrderModel payment fields added (lock_expires_at, gateway_type, gateway_order_id, etc.)
- [x] queues app scaffolded with proper structure
- [x] NATS client singleton with Jetstream support
- [x] OrderExpiryRepository with bulk_expire_pending_orders() + clear_ticket_locks()
- [x] ExpiryWorker — scheduler-based (30s interval), NOT message-driven
  - Rationale: NATS Deliver-Time headers unreliable in nats-py version; bulk scan is simpler, faster (1 query), deterministic latency
- [x] Fire-and-forget payment link cancellation (commented out — payment gateway pending)
- [x] 10 comprehensive unit tests (all passing ✅)
- [x] scripts/run_expiry_worker.py entry point (executable)
- [x] Commit: `feat(queues): add expiration handler with scheduler-based worker`

**Tests:** `uv run pytest tests/apps/queues/test_expiry_worker.py -v` → 10 passed
**To Run Worker:** `uv run scripts/run_expiry_worker.py`

---

## What's NOT Done (Next Phase)

**Phase 2: Gateway Implementation** (planned — from tech spec Section 12)

- [x] `payment_gateway` app scaffold (client, enums, exceptions, schemas, services, handlers, repositories)
- [x] Razorpay `Client` singleton (`RazorpayClient` in `client.py`)
- [x] `PaymentGateway` ABC interface + `BuyerInfo`, `PaymentLinkResult`, `CheckoutOrderResult` dataclasses
- [x] `RazorpayPaymentGateway` stub — raises `NotImplementedError` (filled in Phase 2)
- [x] `get_gateway("razorpay")` factory
- [x] Razorpay settings added to `config.py` (`RAZORPAY_KEY_ID`, `RAZORPAY_KEY_SECRET`, `RAZORPAY_WEBHOOK_SECRET`)
- [x] 8 unit tests (all passing ✅)
- [x] Commit: `feat(payment-gateway): add Phase 1 foundation`

**Tests:** `uv run pytest tests/apps/payment_gateway/ -v` → 8 passed

**Spec:** `docs/superpowers/specs/2026-05-02-payment-gateway-design.md`
**Goal:** Scaffold `payment_gateway` app — all foundation needed before B2B paid flows

### Step 1: Create `payment_gateway` App Structure

```
src/apps/payment_gateway/
├── __init__.py                         # App export
├── client.py                           # razorpay.Client singleton
├── enums.py                            # GatewayType enum
├── exceptions.py                       # PaymentGatewayError, WebhookVerificationError
├── schemas/
│   ├── __init__.py
│   ├── base.py                        # BaseWebhookPayload
│   └── razorpay.py                    # Razorpay Pydantic schemas (order.paid, payment.failed, etc.)
├── services/
│   ├── __init__.py
│   ├── base.py                        # PaymentGateway ABC interface
│   ├── razorpay.py                    # RazorpayPaymentGateway implementation
│   └── factory.py                    # get_gateway("razorpay") factory
├── handlers/
│   ├── __init__.py
│   └── razorpay.py                   # RazorpayWebhookHandler
├── repositories/
│   ├── __init__.py
│   └── order.py                      # OrderPaymentRepository
└── models.py                          # PaymentGatewayEventModel (append-only audit log)
```

### Step 2: Add Settings (new env vars for Razorpay)

```python
razorpay_key_id: str
razorpay_key_secret: str
razorpay_webhook_secret: str
```

### Step 3: Create PaymentGatewayEventModel Migration

```sql
CREATE TABLE payment_gateway_events (
    id UUID PRIMARY KEY,
    order_id UUID REFERENCES orders(id),
    event_type VARCHAR(64),
    gateway_event_id VARCHAR(128),
    payload JSONB,
    gateway_payment_id VARCHAR(128),
    created_at TIMESTAMP,
    updated_at TIMESTAMP,
    UNIQUE(order_id, event_type, gateway_event_id)
);
```

**Phase 2: Gateway Implementation** (from tech spec Section 12):

- [ ] Razorpay Pydantic schemas for all webhook events (`OrderPaidPayload`, `PaymentFailedPayload`, etc.)
- [ ] Implement `RazorpayPaymentGateway.create_payment_link()`
- [ ] Implement `verify_webhook_signature()`
- [ ] Implement `parse_webhook_event()`
- [ ] `get_gateway()` factory — ✅ done in Phase 1

---

*Last updated: 2026-05-03 (Phase 1 complete)*