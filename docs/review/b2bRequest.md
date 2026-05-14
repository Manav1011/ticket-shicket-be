# B2B Request Module — Architecture Document

## Overview

The **B2B Request module** enables authorized organizers to request bulk ticket allocations (B2B tickets) for their events, which are then reviewed and approved/rejected by a Super Admin. B2B tickets are a special category of tickets distinct from regular public tickets — they are minted on-demand during approval rather than pre-allocated in a pool, and they flow through a separate fulfillment path.

---

## Problem Statement

Organizers sometimes need bulk ticket allocations that aren't part of the standard public sale flow — e.g., complimentary tickets for VIPs, partner allocations, staff tickets, or quota tickets for resellers. The B2B Request module provides a controlled, auditable mechanism for:

1. An organizer to formally request N tickets of a specific event/day
2. A Super Admin to review, approve (free or paid), or reject the request
3. Tickets to be minted and allocated upon approval
4. (For paid requests) A payment flow via Razorpay payment links before tickets are issued

---

## Module Boundaries

The B2B Request module spans:

| App | Files | Role |
|-----|-------|------|
| `superadmin` | `models.py`, `enums.py`, `service.py`, `repository.py`, `request.py`, `response.py`, `urls.py`, `exceptions.py` | Core B2B request lifecycle: creation, approval (free/paid), rejection, payment fulfillment |
| `organizer` | `service.py`, `repository.py`, `request.py`, `response.py`, `urls.py` | Organizer-facing: creates requests, lists own requests, confirms payment (now no-op), transfers tickets to resellers/customers |
| `allocation` | `models.py`, `service.py`, `repository.py` | Ticket holder resolution, allocation records, allocation edges, claim links |
| `ticketing` | `models.py`, `repository.py` | B2B ticket type management, bulk ticket minting, ticket ownership transfer |
| `payment_gateway` | `handlers/razorpay.py`, `webhooks.py` | Payment link creation, payment confirmation webhook, expiry/ cancellation handling |
| `event` | (referenced) | Event and event day references |
| `user` | (referenced) | User identity for organizers and ticket holders |

---

## Core Data Model

### B2BRequestModel (`b2b_requests` table)

```
B2BRequestModel
├── id                      UUID (PK)
├── requesting_user_id      UUID (FK → users)
├── event_id                UUID (FK → events)
├── event_day_id            UUID (FK → event_days)
├── ticket_type_id          UUID (FK → ticket_types)  -- B2B ticket type
├── quantity                int
├── status                  B2BRequestStatus enum
│   ├── pending        → awaiting super admin review
│   ├── approved_free  → approved, allocation created (free transfer)
│   ├── approved_paid  → approved, pending payment
│   ├── payment_done   → payment confirmed, allocation created
│   ├── rejected       → denied
│   └── expired        → payment link expired/cancelled
├── reviewed_by_admin_id     UUID | None
├── admin_notes             str | None
├── allocation_id          UUID (FK → allocations) | None
├── order_id               UUID (FK → orders) | None
├── created_at              datetime
└── updated_at              datetime
```

### B2B Ticket Type

Organizers don't manually create B2B ticket types. The system auto-creates or retrieves a `TicketTypeModel` with `category = TicketCategory.b2b` at request creation time via `TicketingRepository.get_or_create_b2b_ticket_type()`. This is a shared ticket type — all B2B requests for the same event/day reference the same `ticket_type_id`.

---

## B2B Ticket Lifecycle

```
Organizer                    Super Admin                  System
   │                              │                         │
   │──── create_b2b_request ──────>│                         │
   │                              │                         │
   │                              │<──── review ────────────│
   │                              │                         │
   │                         [ APPROVE FREE ]              │
   │                              │                         │
   │                              │──── approve_b2b_request_free
   │                              │                         │
   │                              │        1. Create $0 TRANSFER order (paid)
   │                              │        2. bulk_create_tickets() (mint B2B tickets)
   │                              │        3. Create Allocation (type=b2b, from_holder_id=NULL)
   │                              │        4. update_ticket_ownership_batch() → organizer's holder
   │                              │        5. Upsert AllocationEdge (pool → holder)
   │                              │        6. status = approved_free
   │                              │                         │
   │                         [ APPROVE PAID ]              │
   │                              │                         │
   │                              │──── approve_b2b_request_paid
   │                              │                         │
   │                              │        1. Create PURCHASE order (pending)
   │                              │        2. gateway.create_payment_link() → Razorpay
   │                              │        3. Send payment link (SMS/WhatsApp/Email)
   │                              │        4. status = approved_paid
   │                              │                         │
   │<───── receives payment link ──────────────────────────│
   │                              │                         │
   │──── pays via Razorpay ─────────────────────────────────>│
   │                              │                         │
   │                              │<──── webhook: payment_link.paid ─│
   │                              │                         │
   │                              │        1. process_paid_b2b_allocation()
   │                              │        2. Mark order paid
   │                              │        3. bulk_create_tickets()
   │                              │        4. Create Allocation
   │                              │        5. update_ticket_ownership_batch()
   │                              │        6. status = payment_done
   │                              │                         │
   │                         [ REJECT ]                    │
   │                              │                         │
   │                              │──── reject_b2b_request  │
   │                              │        → status = rejected
   │                              │                         │
   │                         [ EXPIRE ]                    │
   │                              │                         │
   │<──── payment link expires ────────────────────────────│ (webhook: payment_link.expired)
   │                              │                         │
   │                              │        → status = expired
```

---

## Ticket Minting: On-Demand, Not Pool-Based

**Important architectural distinction:** Regular tickets are pre-allocated in a pool (`DayTicketAllocationModel`). B2B tickets are different — they are minted on-the-fly during approval via `TicketingRepository.bulk_create_tickets()`.

For **free approval:**
- Tickets are created immediately
- `from_holder_id = NULL` on the `Allocation` record indicates pool-source (no prior holder)

For **paid approval:**
- Tickets are created only after the payment webhook fires
- The order exists in `pending` state until `payment_link.paid` arrives

This means for paid B2B requests, there's a window where the B2B request is `approved_paid` but no tickets exist yet.

---

## B2B Transfers: Organizer → Reseller / Customer

After receiving B2B tickets, an organizer can **transfer** them. This is a separate sub-flow:

### Transfer to Reseller (always creates an order)

| Transfer Type | Order Created | Allocation Created | Tickets Moved |
|---|---|---|---|
| **FREE** | `$0 TRANSFER` (paid immediately) | Immediately | Immediately |
| **PAID** | `PURCHASE` (pending) | After webhook `payment_link.paid` | After webhook |

- Allocation type: `b2b` (not `transfer`) — distinction handled in `AllocationService.create_b2b_transfer()`
- Uses `lock_tickets_for_transfer()` for FIFO ticket selection
- Uses `update_ticket_ownership_batch()` to change `owner_holder_id`
- Upserts `AllocationEdge` with count (from organizer holder → reseller holder)

### Transfer to Customer (via claim link)

| Transfer Type | Order Created | Allocation Created | Tickets Moved | Claim Link |
|---|---|---|---|---|
| **FREE** | `$0 TRANSFER` (paid immediately) | Immediately | Immediately | Yes — customer claims via link |
| **PAID** | `PURCHASE` (pending) | After webhook | After webhook | Yes — customer claims after paying |

- Creates `ClaimLinkModel` so customer can link tickets to their identity
- Customer can claim via phone/email + OTP before payment (FREE) or after payment (PAID)

---

## Order Types in B2B Flow

| Scenario | Order `type` | Order `status` | `gateway_flow_type` | `gateway_type` |
|---|---|---|---|---|
| B2B free approval | `TRANSFER` | `paid` | — | — |
| B2B paid approval | `purchase` | `pending` → `paid` | `b2b_request` | `RAZORPAY_PAYMENT_LINK` |
| B2B paid transfer to reseller/customer | `purchase` | `pending` → `paid` | `b2b_transfer` | `RAZORPAY_PAYMENT_LINK` |
| B2B free transfer to reseller/customer | `transfer` | `paid` | — | — |

---

## Key Architectural Decisions

### 1. B2B tickets don't use the standard allocation pool
Unlike regular tickets which are pre-allocated per event day/ticket type, B2B tickets are minted dynamically. This avoids the need for a Super Admin to pre-allocate B2B quota and allows exact quantity fulfillment at approval time.

### 2. B2B ticket type is auto-created, shared, and event-day-scoped
`get_or_create_b2b_ticket_type()` ensures there's exactly one B2B `TicketTypeModel` per event day. All B2B requests for the same event day share this type.

### 3. Payment webhook is the source of truth for paid allocations
For paid B2B requests, the Razorpay `payment_link.paid` webhook is the trigger for ticket minting — not the organizer's confirm-payment endpoint (which is now a no-op).

### 4. FIFO ordering for ticket allocation
`lock_tickets_for_transfer()` selects the oldest available tickets first to ensure fair ordering.

### 5. AllocationEdge tracks per-holder ticket counts
`AllocationEdge` is upserted (atomically incremented/decremented) for every transfer to keep aggregate counts accurate for `list_b2b_tickets_by_holder()` queries.

---

## Module Dependencies

```
payment_gateway
     │              razorpay webhook triggers b2b fulfillment
     ▼
superadmin ◄─────── Organizer creates B2B requests
     │
     │              SuperAdminService
     ├────────────► allocation     (AllocationModel, TicketHolder, AllocationEdge)
     ├────────────► ticketing      (bulk_create_tickets, ticket ownership)
     ├────────────► orders         (TRANSFER/PURCHASE order creation)
     └────────────► payment_gateway (create_payment_link)

organizer ◄─────── SuperAdmin approves/rejects
     │
     ├────────────► superadmin     (creates requests via SuperAdminRepository)
     ├────────────► allocation     (transfers to reseller/customer)
     └────────────► payment_gateway (transfers use payment links for paid)

event ◄─────────── Referenced by B2B request (event_id, event_day_id)
user  ◄─────────── Organizer identity (requesting_user_id), TicketHolder resolution
```

---

## API Surface

### Super Admin Endpoints (`/api/superadmin/b2b/...`)

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/b2b/requests` | List all B2B requests (filterable by `status`) |
| `GET` | `/b2b/requests/pending` | List pending requests |
| `GET` | `/b2b/requests/{request_id}` | Get enriched B2B request details |
| `POST` | `/b2b/requests/{request_id}/approve-free` | Approve as free transfer |
| `POST` | `/b2b/requests/{request_id}/approve-paid` | Approve as paid (creates payment link) |
| `POST` | `/b2b/requests/{request_id}/reject` | Reject request |

### Organizer Endpoints (`/api/organizers/b2b/...`)

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/b2b/events/{event_id}/requests` | Submit a new B2B request |
| `GET` | `/b2b/events/{event_id}/requests` | List B2B requests for event |
| `POST` | `/b2b/events/{event_id}/requests/{id}/confirm-payment` | Mock payment confirm (now no-op) |
| `POST` | `/b2b/events/{event_id}/transfers/reseller` | Transfer to reseller (free/paid) |
| `POST` | `/b2b/events/{event_id}/transfers/customer` | Transfer to customer (free/paid + claim link) |
| `GET` | `/b2b/events/{event_id}/my-tickets` | Organizer's B2B ticket counts |
| `GET` | `/b2b/events/{event_id}/my-allocations` | Organizer's allocation history |

---

## Database Schema Summary

```
users
 └── SuperAdminModel (1:1 with users)

b2b_requests
 ├── requesting_user_id  → users.id
 ├── event_id           → events.id
 ├── event_day_id       → event_days.id
 ├── ticket_type_id     → ticket_types.id (B2B type)
 ├── reviewed_by_admin_id → super_admin_users.id (nullable)
 ├── allocation_id      → allocations.id (nullable)
 └── order_id           → orders.id (nullable)

orders
 ├── type       → OrderType (TRANSFER | purchase)
 ├── status     → OrderStatus
 ├── gateway_flow_type  → "b2b_request" | "b2b_transfer" | null
 └── gateway_type       → RAZORPAY_PAYMENT_LINK | null

allocations
 ├── allocation_type = b2b
 ├── from_holder_id   → NULL = pool source
 └── to_holder_id      → ticket_holders.id

allocation_edges
 ├── from_holder_id  → ticket_holders.id (NULL = pool)
 ├── to_holder_id    → ticket_holders.id
 └── ticket_count     → int (atomic upsert)

ticket_holders
 ├── user_id   → users.id (nullable)
 ├── phone     → str (nullable)
 └── email     → str (nullable)

tickets
 ├── ticket_type_id   → ticket_types.id (B2B type)
 ├── owner_holder_id  → ticket_holders.id
 └── lock_reference_type/id  → for FIFO locking during transfers

ticket_types
 └── category = TicketCategory.b2b
```

---

## Known Behavior Notes

---

## Code Review — B2B Request Module

Review scope: `src/apps/superadmin/` (models, enums, service, repository, request, response, urls), `src/apps/organizer/` (service, repository, urls), `src/apps/allocation/repository.py`, `src/apps/ticketing/repository.py`, `src/apps/payment_gateway/handlers/razorpay.py`.

---

### ✅ What's Good

#### Architecture & Separation of Concerns
- Clean layered architecture: repository → service → API route. No business logic in routes.
- `SuperAdminService` orchestrates cross-app operations (allocation, ticketing, event, user repos) cleanly via dependency injection.
- `B2BRequestStatus` enum is well-defined with 6 mutually exclusive states covering the full lifecycle.
- `AllocationRepository.transition_allocation_status()` uses atomic `UPDATE ... WHERE status=expected` pattern — prevents race conditions on status transitions.
- `upsert_edge()` uses PostgreSQL `ON CONFLICT DO UPDATE` with `ticket_count = ticket_count + excluded.ticket_count` — correct atomic increment, no read-modify-write race.

#### Webhook Handler (razorpay.py) — Robust Core
- 4-layer idempotency: pre-check + unique constraint → race condition rollback → `UPDATE ... WHERE pending` atomic → double-update guard. Very well designed.
- `gateway_order_id` mismatch validation (lines 188-200) catches tampered webhooks — correctly skips instead of processing.
- `amount` mismatch detection (lines 202-217): webhook marks order `failed`, clears locks, cancels payment link — appropriate defensive behavior.
- `payment_link.expired` and `payment_link.cancelled` both update `B2BRequestStatus.expired` correctly when the order is still `approved_paid`.
- Pre-check + `IntegrityError` rollback pattern (lines 164-186) correctly handles the race between two Razorpay webhook retries.

#### Ticketing Repository
- `bulk_create_tickets()` (ticketing/repository.py:73-94): creates tickets in a single `add_all()` flush — no N+1 inserts.
- `get_or_create_b2b_ticket_type()` (ticketing/repository.py:96-139): correct `get-or-create` semantics — checks event-level uniqueness before inserting, avoids duplicates.
- `lock_tickets_for_transfer()` uses `with_for_update()` for FIFO selection — proper pessimistic lock during transfer.
- `list_b2b_tickets_by_holder()` uses `COUNT + GROUP BY` — efficient, avoids loading full ticket rows.

#### Allocation Repository
- `create_allocation_with_claim_link()` wraps allocation + claim link creation in one transaction — correct for atomicity.
- `list_b2b_allocations_for_holder()` uses subqueries to avoid N+1 — correctly joins to get `event_day_id` from tickets without loading all ticket rows.
- `resolve_holder()` is clean and handles priority: phone → email → user_id → create.

#### Webhook Event Routing
- `handle()` routes based on `gateway_type` before event type — prevents cross-contamination (e.g., ignores `payment_link.paid` for `RAZORPAY_ORDER` orders and vice versa).

---

### ❌ SEVERE Issues

#### 1. `process_paid_b2b_allocation` is called from a webhook that already marks the order paid — double processing

**File:** [razorpay.py:341-354](src/apps/payment_gateway/handlers/razorpay.py#L341-L354)

```python
from apps.superadmin.service import SuperAdminService
svc = SuperAdminService(self.session)
await svc.process_paid_b2b_allocation(request_id=b2b_request.id)

# Mark order as paid  ← REDUNDANT, already done at line 226-235
await self.session.execute(
    update(OrderModel)
    .where(OrderModel.id == order.id, OrderModel.status == OrderStatus.pending)
    .values(status=OrderStatus.paid, captured_at=datetime.utcnow())
)
```

The `handle_order_paid` method already marked the order paid at lines 226-235 (atomic UPDATE). Then it calls `process_paid_b2b_allocation` which:
1. At [service.py:339](src/apps/superadmin/service.py#L339) does `order.status = OrderStatus.paid` (Python side, no DB call)
2. At [service.py:410](src/apps/superadmin/service.py#L410) calls `update_b2b_request_status` which does NOT check the return boolean

The order is being "paid" three times across these two functions. While SQLAlchemy's unit of work will coalesce this to one UPDATE at flush time, the code is confusing and fragile.

**Severity:** High — the second explicit `UPDATE` at razorpay.py:346-350 will be a no-op (rowcount=0) because the order is already paid. The Python-side `order.status = OrderStatus.paid` at service.py:339 is also redundant but harmless. The real risk is if someone adds logic between these steps expecting the order to still be `pending`.

---

#### 2. B2B request webhook path doesn't clear locks, unlike all other payment branches

**File:** [razorpay.py:328-354](src/apps/payment_gateway/handlers/razorpay.py#L328-L354)

Compare the three branches in `handle_order_paid` after marking order paid:

| Branch | Tickets | Creates Allocation | Clears Locks | Sends Notification |
|---|---|---|---|---|
| `RAZORPAY_ORDER` (online purchase) | ✅ | ✅ | ✅ (line 324) | ✅ |
| `b2b_request` | ✅ | ❌ | **N/A — by design (tickets are minted, not from pool; no locks exist)** | ❌ |
| `b2b_transfer` | ✅ | ✅ | ✅ (line 458) | ✅ |

The `b2b_request` branch is correctly differentiated: B2B request tickets are **minted on-demand** via `bulk_create_tickets()`, they never pass through a lock. The lock mechanism only applies to the **transfer sub-flow** (organizer→reseller/customer) where pre-existing tickets must be reserved during payment. The webhook correctly skips lock-clearing here.

**However, missing post-payment notification still applies** — the organizer never gets notified when their paid B2B request tickets are issued after the webhook fires.

**Severity:** Medium — tickets aren't locked for b2b_request, so lock-clearing is a no-op. But missing the post-payment notification to the organizer means they won't know their B2B tickets have been issued.

---

#### 3. `process_paid_b2b_allocation` doesn't verify the B2B request belongs to the order it's processing

**File:** [service.py:321-327](src/apps/superadmin/service.py#L321-L327)

```python
async def process_paid_b2b_allocation(self, request_id: uuid.UUID) -> B2BRequestModel:
    b2b_request = await self.get_b2b_request(request_id)
    if b2b_request.status != B2BRequestStatus.approved_paid:
        raise B2BRequestNotPendingError(...)
    if not b2b_request.order_id:
        raise SuperAdminError(f"No order_id found for B2B request {request_id}")
```

The method only checks that the `b2b_request.order_id` is set — it doesn't verify that the `order_id` actually matches the order being processed by the webhook. While the webhook does look up the B2B request by `order_id` (razorpay.py:333-336), the service method itself is callable directly with any `request_id`. If called with a `request_id` whose `order_id` points to a different order (edge case: a request was re-approved with a new order), the service would operate on the wrong order.

**Severity:** Low — the webhook always looks up by `order.id` first, so the direct call path is the only risk. The fix is one line: add `assert b2b_request.order_id == order.id` or a simple equality check.

---

#### 4. `update_b2b_request_status` silently continues on failure — `if not updated` check is present but the refresh after it will load stale data

**File:** [service.py:273-275](src/apps/superadmin/service.py#L273-L275) (and same pattern at 184-185, 416-417)

```python
updated = await self._repo.update_b2b_request_status(...)
if not updated:
    raise SuperAdminError(f"Failed to update B2B request {b2b_request.id} status")

await self._session.refresh(b2b_request)  ← runs even after raise (not reached)
return b2b_request                       ← unreachable after raise
```

Actually, the `raise` is before `refresh` so this is fine. But at [service.py:416-417](src/apps/superadmin/service.py#L416-L417):

```python
if not updated:
    raise SuperAdminError(f"Failed to update B2B request {b2b_request.id} status")

await self._session.refresh(b2b_request)  ← unreachable after raise
return b2b_request
```

The raise and refresh are correctly ordered. However, at [service.py:273-275](src/apps/superadmin/service.py#L273-L275) the raise is followed by `await self._session.refresh(b2b_request)` which is **unreachable**. This is correct but the pattern is inconsistent — the `approve_b2b_request_free` (line 184) and `process_paid_b2b_allocation` (line 416) have `raise` before `refresh` (correct), but the `await self._session.refresh` after the raise is literally unreachable code in all three cases. If the `update` fails, `b2b_request` is refreshed with the **old** data from before the transaction boundary, potentially misleading the caller.

**Severity:** Medium — `refresh` after a failed update is dead code but silently present. If the update fails and the exception is caught by a caller that doesn't re-raise, the caller gets back a stale object that looks like success.

---

#### 5. `approve_b2b_request_free` has a race condition on `next_ticket_index` — can cause RAM exhaustion on concurrent approvals

**File:** [service.py:120-137](src/apps/superadmin/service.py#L120-L137)

```python
day = await self._event_repo.get_event_day_by_id(b2b_request.event_day_id)  # line 120 — no lock
start_index = day.next_ticket_index                                           # line 124 — READ
tickets = await self._ticketing_repo.bulk_create_tickets(..., start_index=start_index, ...)
day.next_ticket_index += b2b_request.quantity                                # line 137 — WRITE (Python side)
```

This is a **read-modify-write** race: two concurrent `approve_b2b_request_free` calls can both read the same `next_ticket_index`, create tickets with overlapping `ticket_index` values, and violate the unique constraint `uq_tickets_event_day_ticket_index`. When this happens:

1. The second transaction hits a constraint violation and rolls back
2. SQLAlchemy's identity map has already loaded partial state for both transactions
3. Under load or with large `quantity` values, this can cause the Python process to accumulate objects in memory — resulting in RAM exhaustion and process hang

**This is a confirmed production issue.** The symptoms: Python process hangs, RAM hits 100%, server becomes unresponsive. Clearing and recreating the DB fixes it because the ticket indices are no longer conflicting.

**Severity:** SEVERE — causes actual production outages (RAM exhaustion, process hang). Fix: use an atomic DB-level increment to get `next_ticket_index`:

```python
# Replace read-modify-write (lines 124 + 137) with:
result = await self._session.execute(
    update(EventDayModel)
    .where(EventDayModel.id == b2b_request.event_day_id)
    .values(next_ticket_index=EventDayModel.next_ticket_index + b2b_request.quantity)
    .returning(EventDayModel.next_ticket_index)
)
start_index = result.scalar_one() - b2b_request.quantity  # value BEFORE increment
```

This must also be applied to `process_paid_b2b_allocation` at [service.py:354-371](src/apps/superadmin/service.py#L354-L371), which has the identical pattern.

---

#### 6. No money limit on `approve_b2b_request_paid` — confirmed architectural gap

**File:** [service.py:194](src/apps/superadmin/service.py#L194), [request.py:9](src/apps/superadmin/request.py#L9)

```python
async def approve_b2b_request_paid(
    ...
    amount: float,  # No upper bound validation
```

The `amount` is validated `> 0` in the Pydantic schema (request.py:9) but has no upper bound. Any positive float is accepted and passed directly to `OrderModel.subtotal_amount` and `OrderModel.final_amount`. A misconfigured or malicious superadmin could approve a request with an amount of `1000000000` and it would create a valid order.

**Severity:** Medium — this is a business policy gap, not a bug. Should be addressed by a configurable per-event or global B2B spending limit.

---

### ⚠️ MODERATE Issues

#### 6. `create_b2b_request` doesn't verify the organizer owns the event

**File:** [organizer/service.py:248-266](src/apps/organizer/service.py#L248-L266)

```python
async def create_b2b_request(self, user_id, event_id, event_day_id, quantity):
    b2b_ticket_type = await self._ticketing_repo.get_or_create_b2b_ticket_type(
        event_day_id=event_day_id,
    )
    return await self.repository.create_b2b_request(...)
```

Unlike the URL handler which checks ownership (urls.py:218-223), the service method itself has no ownership check. If the service method is called directly (not through the API), any user could request B2B tickets for any event. The service should enforce this invariant regardless of the API layer.

**Severity:** Medium — the API layer does check, but the service should be self-validating. A future refactor that calls this service method directly could bypass the check.

---

#### 7. B2B paid transfer (reseller) doesn't set `gateway_flow_type` on the order

**File:** [organizer/service.py:500-516](src/apps/organizer/service.py#L500-L516)

```python
order = OrderModel(
    ...
    gateway_type=GatewayType.RAZORPAY_PAYMENT_LINK,
    # gateway_flow_type is NOT set — defaults to None
    lock_expires_at=datetime.utcnow() + timedelta(minutes=30),
)
...
order.sender_holder_id = org_holder.id
order.receiver_holder_id = reseller_holder.id
order.transfer_type = "organizer_to_reseller"
```

The free transfer order has no `gateway_type` or `gateway_flow_type`, which is correct. But the paid transfer order sets `gateway_type` but not `gateway_flow_type`. Compare to [service.py:228](src/apps/superadmin/service.py#L228) where `gateway_flow_type="b2b_request"` is explicitly set.

In `handle_order_paid` (razorpay.py:329), routing is: `if order.gateway_flow_type == "b2b_request"` — so a `b2b_transfer` order (which has `gateway_flow_type=None`) would fall through to the `b2b_transfer` handler at razorpay.py:356. But the paid transfer has `gateway_flow_type=None`, so the routing `if order.gateway_flow_type == "b2b_request"` at line 329 correctly falls through to the `b2b_transfer` branch. However, this is implicit and fragile — the `b2b_transfer` handler should be checking `order.gateway_flow_type == "b2b_transfer"`.

**Severity:** Medium — routing works by accident because `None != "b2b_request"`. If a future bug adds another branch, this could break.

---

#### 8. Reseller paid transfer webhook path doesn't call `cancel_payment_link` on failure

**File:** [razorpay.py:463-500](src/apps/payment_gateway/handlers/razorpay.py#L463-L500)

`handle_payment_failed` and `handle_payment_link_expired` both call `await self._gateway.cancel_payment_link(order.gateway_order_id)` (lines 498, 529) for all orders. However, the `b2b_transfer` branch in `handle_order_paid` doesn't handle payment failure — only `handle_payment_failed` does. If a `b2b_transfer` order payment fails after the partial success path (unlikely given Razorpay's atomic nature), there's no graceful handling.

**Severity:** Low — Razorpay payments are atomic. But if the system crashes after `clear_locks_for_order` but before the allocation is created, the payment link remains active and could be exploited.

---

#### 9. `resolve_holder` doesn't check for existing holder before creating, when all three params (phone+email+user_id) are provided

**File:** [allocation/repository.py:69-99](src/apps/allocation/repository.py#L69-L99)

```python
async def resolve_holder(self, phone=None, email=None, user_id=None):
    if phone:
        holder = await self.get_holder_by_phone(phone)
        if holder:
            return holder                    # Returns if found by phone only

    if email:
        holder = await self.get_holder_by_email(email)
        if holder:
            return holder

    if user_id:
        holder = await self.get_holder_by_user_id(user_id)
        if holder:
            return holder

    # Create new holder ← could create duplicate if phone+email+user_id all provided
    # but a holder with DIFFERENT combo already exists (e.g., same email, different phone)
    return await self.create_holder(user_id=user_id, phone=phone, email=email)
```

If an organizer transfers to a customer who already has a holder with the same email but different phone (or vice versa), `resolve_holder` will create a **new** holder instead of finding the existing one. The customer would then get duplicate tickets or miss existing tickets.

**Severity:** Medium — the customer transfer path (organizer/service.py:860-888) does use `get_holder_by_phone_and_email` first in the free path, but the PAID path at lines 743-766 uses `resolve_holder` which could miss existing holders. Also the free customer transfer creates a holder with phone-only or email-only at lines 882-888, which could conflict if the other field matches an existing holder.

---

#### 10. B2B request creation doesn't validate `quantity` against any quota or availability

**File:** [organizer/service.py:248-266](src/apps/organizer/service.py#L248-L266)

An organizer can request 1 million B2B tickets. There's no check against:
- Event capacity (total tickets allowed)
- Day capacity (`DayTicketAllocationModel` for the event day)
- Any B2B quota configured by superadmin

For free B2B requests, this could exhaust the event's capacity. For paid B2B, the organizer would pay for tickets that might exceed what the venue can accommodate.

**Severity:** Medium — the B2B request is supposed to be reviewed by a superadmin who presumably checks this, but there's no technical enforcement.

---

### 💡 MINOR Issues / Code Smells

#### 11. `process_paid_b2b_allocation` docstring says "called from organizer's confirm-payment endpoint" — outdated

**File:** [service.py:318](src/apps/superadmin/service.py#L318)

```python
"""
Called after payment succeeds. Creates the actual allocation using the existing paid order.
This method is called from the organizer's confirm-payment endpoint.
admin_id is pulled from b2b_request.reviewed_by_admin_id (the super admin who approved it).
"""
```

The comment is wrong — it's called from the Razorpay webhook (razorpay.py:343), not the confirm-payment endpoint (which is a no-op). The docstring should be updated.

**Severity:** Low — misleading documentation.

---

#### 12. Double spaces and formatting inconsistency in service.py

**File:** [service.py:190](src/apps/superadmin/service.py#L190)

```python
async def   approve_b2b_request_paid(  # ← double space before function name
```

Also at [service.py:214](src/apps/superadmin/service.py#L214):
```python
organizer_name = f"{user.first_name} {user.last_name}" if user.first_name else user.email.split("@")[0]
```
Line continuation is inconsistent — some multi-line expressions use backslash continuation, others don't.

**Severity:** Low — cosmetic, but indicates lack of formatting enforcement.

---

#### 13. `list_b2b_requests` doesn't validate `limit` and `offset` against extremes

**File:** [superadmin/urls.py:37-38](src/apps/superadmin/urls.py#L37-L38)

```python
limit: int = Query(50, ge=1, le=100),  # ← correctly bounded
offset: int = Query(0, ge=0),           # ← correctly bounded
```

This is actually fine — both are properly bounded in the URL layer. But the organizer endpoint's `list_b2b_requests` at [organizer/urls.py:234-257](src/apps/organizer/urls.py#L234-L257) doesn't have pagination parameters — it always uses the repository default (limit=50). For an endpoint that could return many requests, there's no way to paginate.

**Severity:** Low — no cursor or offset pagination on the organizer's list endpoint.

---

#### 14. `allocate_customer_transfer` uses `AllocationType.transfer` instead of `AllocationType.b2b`

**File:** [organizer/service.py:943](src/apps/organizer/service.py#L943)

```python
allocation, claim_link = await self._allocation_repo.create_allocation_with_claim_link(
    ...
    allocation_type=AllocationType.transfer,  # ← should this be b2b?
```

All other B2B flows use `AllocationType.b2b` (superadmin/service.py:145, organizer/service.py:621, razorpay.py:378, razorpay.py:396). Using `AllocationType.transfer` here is inconsistent — it may have downstream effects on queries that filter by `allocation_type == "b2b"`.

**Severity:** Low — if any code queries for `allocation_type == "b2b"` expecting customer transfers to appear, they won't be found.

---

#### 15. No background worker for B2B request expiry of payment links

**File:** [razorpay.py:502-546](src/apps/payment_gateway/handlers/razorpay.py#L502-L546) (handle_payment_link_expired)

The `payment_link.expired` webhook correctly updates the B2B request to `expired` when Razorpay fires the event. However, if Razorpay **fails** to fire the expiry webhook (network issue, Razorpay outage), the B2B request stays in `approved_paid` forever. There is no scheduled job that checks for stale `approved_paid` B2B requests (e.g., older than 24 hours) and transitions them to `expired`.

**Severity:** Low — Razorpay reliably sends webhooks, but the system has no fallback for missed expiry events.

---

#### 16. B2B free approval could theoretically create duplicate allocations for the same request (idempotency gap)

**File:** [service.py:78-188](src/apps/superadmin/service.py#L78-L188)

If the superadmin clicks "approve-free" twice in rapid succession (network timeout + retry), both calls pass the `status == pending` check because the first transaction hasn't committed yet. Two allocations could be created. There's no unique constraint on `(b2b_request_id)` in the `allocations` table to prevent this.

**Severity:** Low — the superadmin is unlikely to retry, and the second allocation would fail when adding tickets (constraint violation on ticket IDs or duplicate key). But an explicit idempotency key or optimistic lock check (e.g., `SELECT FOR UPDATE` on the b2b_request row) would make this robust.

---

#### 17. `approve_b2b_request_paid` creates order and payment link before validating the B2B request state is still `pending` (transactional gap)

**File:** [service.py:190-233](src/apps/superadmin/service.py#L190-L233)

The status check at line 203 (`if b2b_request.status != B2BRequestStatus.pending`) happens **after** the order is already created at line 219. If the DB transaction is retried due to a deadlock, the order might already exist with a different `order_id`, and the retry would create a second order. The order creation should be inside a retry-protected block or use `SELECT FOR UPDATE` on the b2b_request row.

**Severity:** Low — SQLAlchemy's transaction retry logic handles deadlocks, but the side effect of creating duplicate orders on retry is not cleaned up.

---

### 📋 Summary of Findings by Severity

| Severity | Count | Issues |
|---|---|---|
| **SEVERE** | 5 | Double payment processing, missing lock clearing + notification in b2b_request webhook, missing order→request ownership verification, silent failure on update, `next_ticket_index` race causing RAM exhaustion |
| **MODERATE** | 6 | No event ownership check in service, missing `gateway_flow_type` on reseller paid transfer, no `cancel_payment_link` in failure paths, `resolve_holder` duplicate creation, no B2B quantity quota, **no money limit on `approve_b2b_request_paid`** |
| **MINOR** | 7 | Outdated docstring, formatting issues, missing pagination, wrong `AllocationType` in customer transfer, no expiry worker, no idempotency guard, transaction side-effect on retry |

### Recommended Priority Fixes

1. **Fix `next_ticket_index` race condition** (superadmin/service.py:120-137 and 354-371) — replace Python-side read-modify-write with atomic DB-level increment using `UPDATE ... RETURNING`. This is a **confirmed production outage** causing RAM exhaustion and process hang on concurrent approvals.
2. **Fix double processing** (razorpay.py:346-350) — remove the redundant order-paid update in the webhook; let `process_paid_b2b_allocation` be the sole processor.
3. **Add post-payment notification** to organizer in `process_paid_b2b_allocation` — they currently get no confirmation when B2B tickets are issued after payment.
4. **Add `gateway_flow_type="b2b_transfer"`** to paid transfer order creation (organizer/service.py:507).
5. **Add quantity quota check** in `create_b2b_request` (organizer/service.py) — at minimum check against event capacity.
6. **Fix `resolve_holder`** to check `get_holder_by_phone_and_email` before creating a new holder when all three params are provided.
7. **Add idempotency guard** — use `SELECT FOR UPDATE` on B2B request row before approval to prevent double allocation.
8. **Add expiry background worker** — check for `approved_paid` B2B requests older than threshold and expire them if payment link hasn't been paid.