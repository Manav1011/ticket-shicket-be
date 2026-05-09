# Online Ticket Purchase — Technical Specification

> **Status:** Implemented ✅ — All phases complete

---

## 1. Overview

### 1.1 Goal

Enable logged-in customers to purchase tickets directly from an event page via an online checkout flow. Uses Razorpay Checkout (Orders API) — different from the B2B Payment Link flow. The system polls an order status API while waiting for the `order.paid` webhook, after which the customer receives a claim link via email/WhatsApp/SMS.

### 1.2 Background

The system completed B2B paid transfers (organizer→reseller, organizer→customer, reseller→customer) using Razorpay Payment Links. That infrastructure is reusable: `OrderModel`, `AllocationModel`, ticket locking, webhook idempotency, and claim link generation all apply here.

Online purchase differs in two key ways:
- **Razorpay flow**: Checkout modal (`client.order.create()`) instead of Payment Link
- **Polling**: Frontend polls a status API while waiting for webhook confirmation

### 1.3 Scope

**In Scope:**
- `POST /api/purchase/orders` — Create purchase order with Razorpay checkout
- `POST /api/purchase/orders/preview` — Preview price breakdown before ordering
- `GET /api/purchase/orders/{order_id}/status` — Poll order payment status
- Razorpay `client.order.create()` integration
- Coupon code validation and discount application
- Ticket locking during pending state (FIFO, 30-min TTL)
- `order.paid` webhook → create allocation + claim link + send notifications
- `payment.failed` / `order.failed` webhook → clear locks, mark failed
- Polling API returns scan JWT once order is paid
- Notification delivery (email, WhatsApp, SMS) with claim URL

**Out of Scope:**
- Refund handling
- Multi-ticket-type in single order (single ticket type per order)
- Partial payment
- Guest checkout (must be logged-in user)

---

## 2. Architecture

### 2.1 How Online Purchase Compares to B2B

| Aspect | B2B Transfer (Payment Link) | Online Purchase (Checkout) |
|--------|-----------------------------|----------------------------|
| Gateway type | `RAZORPAY_PAYMENT_LINK` | `RAZORPAY_ORDER` |
| Razorpay API | `payment_link.create()` | `client.order.create()` |
| Buyer experience | Receives payment link via SMS/WhatsApp | Opens Razorpay modal on our site, pays there |
| Source of truth | Webhook only | Webhook only |
| Frontend polling | No | Yes — `GET /orders/{id}/status` |
| Coupon support | No | Yes |
| Price formula | `allocation.price` (organizer-set) | `ticket_type.price × quantity - coupon_discount` |
| Buyer must be | Reseller/Customer TicketHolder | Logged-in User → TicketHolder |

## 2.2 Gateway Interface Method — `create_checkout_order`

Already defined in `PaymentGateway` base class, stub exists at `RazorpayPaymentGateway.create_checkout_order()`. Needs implementation:

```python
# src/apps/payment_gateway/services/razorpay.py — already has stub, needs implementation
async def create_checkout_order(
    self,
    order_id: UUID,
    amount: int,       # in paise
    currency: str,
    event_id: UUID,
) -> CheckoutOrderResult:
    """
    Create a Razorpay checkout order via client.order.create().
    receipt = our internal order UUID (for webhook lookup via receipt field)
    notes = { internal_order_id, event_id, flow_type: "online_purchase" }
    Returns razorpay_order_id + key_id for frontend Razorpay modal.
    """
    response = self._client.order.create(data={
        "amount": amount,
        "currency": currency,
        "receipt": str(order_id),  # our order UUID as receipt — webhook delivers receipt field
        "payment_capture": 1,
        "notes": {
            "internal_order_id": str(order_id),
            "event_id": str(event_id),
            "flow_type": "online_purchase",
        },
    })
    return CheckoutOrderResult(
        gateway_order_id=response["id"],
        razorpay_key_id=settings.RAZORPAY_KEY_ID,
        gateway_response=response,
    )
```

The `receipt` field in Razorpay order is our order UUID. When `order.paid` webhook fires, `event.receipt` will contain our order UUID — already used in webhook handler for order lookup (see [razorpay.py:112](src/apps/payment_gateway/handlers/razorpay.py#L112)).

### 2.3 New Locking Method: Pool Ticket Locking

B2B transfers use `lock_tickets_for_transfer()` which requires `owner_holder_id`. Online purchases lock tickets from the **pool** (unowned, `owner_holder_id=None`).

**Needed:** `lock_tickets_for_purchase()` in `TicketingRepository`:

```python
async def lock_tickets_for_purchase(
    self,
    event_id: UUID,
    event_day_id: UUID,
    ticket_type_id: UUID,
    quantity: int,
    order_id: UUID,
    lock_ttl_minutes: int = 30,
) -> list[UUID]:
    """
    Atomically lock `quantity` tickets from the pool for a purchase order.
    Selects tickets where owner_holder_id=None and lock_reference_id=None (FIFO by ticket_index).
    Sets lock_reference_type='order', lock_reference_id=order_id, lock_expires_at.
    Returns locked ticket IDs.
    Raises ValueError if fewer than `quantity` tickets available.
    """
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=lock_ttl_minutes)

    subq = (
        select(TicketModel.id)
        .where(
            TicketModel.event_id == event_id,
            TicketModel.event_day_id == event_day_id,
            TicketModel.ticket_type_id == ticket_type_id,
            TicketModel.owner_holder_id.is_(None),  # Pool tickets only
            TicketModel.lock_reference_id.is_(None),
        )
        .order_by(TicketModel.ticket_index.asc())
        .limit(quantity)
        .with_for_update()
    )

    result = await self._session.execute(
        update(TicketModel)
        .where(TicketModel.id.in_(subq))
        .values(
            lock_reference_type="order",
            lock_reference_id=order_id,
            lock_expires_at=expires_at,
        )
        .returning(TicketModel.id)
    )
    locked_ids = list(result.scalars().all())

    if len(locked_ids) < quantity:
        raise ValueError(f"Only {len(locked_ids)} tickets available, requested {quantity}")

    return locked_ids
```

### 2.4 Webhook Handler Extension: `RAZORPAY_ORDER` Branch

The existing `handle_order_paid` at [razorpay.py:109](src/apps/payment_gateway/handlers/razorpay.py#L109) has B2B-specific logic (reseller vs customer split based on `transfer_type`). For `RAZORPAY_ORDER`, the flow is simpler:

- All tickets go to the buyer (the user who placed the order)
- `allocation_type = AllocationType.purchase` (not B2B)
- Lock reference type is `'order'` (not `'transfer'`)
- Claim link is ALWAYS created for the buyer

New section added to `handle_order_paid`:

```python
# In handle_order_paid, after gateway_type check:
elif order.gateway_type == GatewayType.RAZORPAY_ORDER:
    # Online purchase: create allocation + claim link for buyer
    # Order.sender_holder_id = buyer (the user who placed the order)
    # Order.event_day_id is set at order creation
    raw_token = generate_claim_link_token(length=8)
    token_hash = hashlib.sha256(raw_token.encode()).hexdigest()

    allocation, claim_link = await self._allocation_repo.create_allocation_with_claim_link(
        event_id=order.event_id,
        event_day_id=order.event_day_id,
        from_holder_id=None,  # From pool (no previous owner)
        to_holder_id=order.receiver_holder_id,  # Buyer
        order_id=order.id,
        allocation_type=AllocationType.purchase,
        ticket_count=len(locked_ticket_ids),
        token_hash=token_hash,
        created_by_holder_id=order.receiver_holder_id,
        jwt_jti=secrets.token_hex(8),
        metadata_={"source": "online_purchase"},
    )
    # Transfer ownership to buyer, add claim_link_id to tickets
    await self._ticketing_repo.update_ticket_ownership_batch(
        ticket_ids=locked_ticket_ids,
        new_owner_holder_id=order.receiver_holder_id,
        claim_link_id=claim_link.id,
    )
    # Send claim link notifications to buyer
    await send_claim_link_notifications(order, claim_link, raw_token)
```

### 2.6 Zero-Amount Orders (Coupon-Fully-Covered)

When a coupon fully covers the order (`final_amount == 0`), Razorpay is skipped entirely — it requires minimum 1 paise. The flow mirrors B2B free transfers:

1. Tickets are still locked (30-min TTL, standard flow)
2. Order is created with `status = paid` and `captured_at = now` — no Razorpay call
3. Post-payment steps run inline: allocation + claim link created, ownership transferred, notifications sent, locks cleared
4. Response returns `status: "paid"`, `is_free: true`, and the `claim_url` directly

```python
# In create_order, after final_amount calculation:
if final_amount == 0:
    order.status = OrderStatus.paid
    order.captured_at = datetime.utcnow()
    # ... create allocation + claim link, transfer ownership, send notifications
    return {
        "status": "paid",
        "is_free": True,
        "claim_url": f"/claim/{raw_token}",
    }
```

The frontend checks `is_free: true` to skip the Razorpay checkout modal and instead show a success screen immediately.

### 2.5 Data Flow

```
Customer (logged-in) selects ticket type + quantity + event_day
         │
         ▼
POST /api/purchase/orders
{
  "event_id": "uuid",
  "event_day_id": "uuid",
  "ticket_type_id": "uuid",
  "quantity": 3,
  "coupon_code": "SAVE20" (optional)
}
         │
         ▼
Validate: event is published, tickets available, user is logged-in
         │
         ▼
Resolve user's TicketHolder (via AllocationService.resolve_holder)
         │
         ▼
Validate coupon (if provided) → calculate discount
subtotal = quantity × ticket_type.price
discount = apply_coupon(coupon_code, subtotal, user_id)
final_amount = subtotal - discount
         │
         ▼
Lock tickets: quantity tickets from pool (FIFO, owner_holder_id=None, lock_ref=order.id, lock_ref_type='order')
         │
         ▼
Create OrderModel:
  - status = pending
  - type = PURCHASE
  - gateway_type = RAZORPAY_ORDER
  - receiver_holder_id = buyer's TicketHolder
  - subtotal_amount, discount_amount, final_amount
  - lock_expires_at = now + 30 min
         │
         ▼
Call razorpay.client.order.create({
  amount: final_amount × 100,  # paise
  currency: "INR",
  receipt: order.id,  # our order UUID as receipt for lookup
  payment_capture: 1,
  notes: { internal_order_id, event_id, flow_type: "online_purchase" }
})
         │
         ▼
Save gateway_order_id (razorpay order_id) to OrderModel
         │
         ▼
Return { razorpay_order_id, razorpay_key_id, order_id } to frontend
         │
         ▼
[FRONTEND] Opens Razorpay modal with order_id + key_id
         │
         ▼
[POLLING] GET /api/purchase/orders/{order_id}/status every N seconds
  → Returns { status: "pending" } until webhook fires
         │
         ▼
[WEBHOOK] Razorpay sends order.paid
         │
         ▼
handle_order_paid:
  1. Find order by gateway_order_id
  2. L1: skip if not pending
  3. Validate amount, currency, payment status
  4. L4: Insert PaymentGatewayEvent (unique constraint dedup)
  5. L3: Atomic UPDATE status=paid WHERE status=pending
  6. Create Allocation (type=PURCHASE)
  7. Create ClaimLink + ClaimLinkToken
  8. Transfer ticket ownership to buyer
  9. Clear ticket locks
  10. Send notifications: claim URL via email/WhatsApp/SMS
         │
         ▼
[POLLING] Next status call → { status: "paid", jwt, claim_url, ticket_count }
         │
         ▼
Frontend displays QR code with jwt
```

---

## 3. API Endpoints

### 3.1 Create Purchase Order

**Endpoint:** `POST /api/purchase/orders`

**Auth Required:** Yes (Bearer token — logged-in user only, no guests)

**Request:**
```json
{
  "event_id": "uuid",
  "event_day_id": "uuid",
  "ticket_type_id": "uuid",
  "quantity": 3,
  "coupon_code": "SAVE20"  // optional
}
```

**Validation rules:**
- `event_id` must exist and be published
- `event_day_id` must belong to the event
- `ticket_type_id` must belong to the event
- `quantity` must be ≥ 1
- `quantity` must not exceed available tickets in pool (owner_holder_id=None, not locked)
- Coupon code valid (if provided): active, not expired, not exceeded usage limits, per-user limit not exceeded, min_order_amount satisfied

**Response (201 Created):**
```json
{
  "success": true,
  "data": {
    "order_id": "uuid",
    "razorpay_order_id": "razorpay_order_id",
    "razorpay_key_id": "rzp_test_xxx",
    "amount": 149700,
    "currency": "INR",
    "subtotal_amount": "1497.00",
    "discount_amount": "0.00",
    "final_amount": "1497.00",
    "status": "pending"
  }
}
```

**Error cases:**
- 400: Invalid ticket type, quantity exceeds availability, coupon invalid/expired/limit reached
- 401: Not authenticated
- 404: Event, event day, or ticket type not found

---

### 3.2 Poll Order Status

**Endpoint:** `GET /api/purchase/orders/{order_id}/status`

**Auth Required:** Yes (Bearer token)

**Response (200 OK):**

*While pending:*
```json
{
  "success": true,
  "data": {
    "order_id": "uuid",
    "status": "pending",
    "ticket_count": 3
  }
}
```

*When paid:*
```json
{
  "success": true,
  "data": {
    "order_id": "uuid",
    "status": "paid",
    "ticket_count": 3,
    "jwt": "eyJ...",
    "claim_url": "/claim/abc123"
  }
}
```

*When failed:*
```json
{
  "success": true,
  "data": {
    "order_id": "uuid",
    "status": "failed",
    "ticket_count": 0,
    "failure_reason": "Payment failed or was rejected"
  }
}
```

*When expired:*
```json
{
  "success": true,
  "data": {
    "order_id": "uuid",
    "status": "expired",
    "ticket_count": 0
  }
}
```

**Note:** `jwt` and `claim_url` are only present when `status == "paid"`. The `jwt` is the scan JWT for entry (same format as B2B claim redemption). The `claim_url` is the URL sent via notifications.

**Error cases:**
- 401: Not authenticated
- 403: Order does not belong to the authenticated user
- 404: Order not found

---

### 3.3 Preview Order Price

**Endpoint:** `POST /api/purchase/orders/preview`

**Auth Required:** Yes (Bearer token)

**Purpose:** Validate inputs and return the price breakdown (subtotal, discount, final_amount) without locking tickets or creating an order. Allows the frontend to show the user the final amount before committing to payment.

**Request:**
```json
{
  "event_id": "uuid",
  "event_day_id": "uuid",
  "ticket_type_id": "uuid",
  "quantity": 3,
  "coupon_code": "SAVE20"  // optional
}
```

**Validation rules:** (same as Create Purchase Order — ticket availability, coupon validity)
- Does NOT lock tickets or create an order
- Returns error if any validation fails

**Response (200 OK):**

*With valid coupon:*
```json
{
  "success": true,
  "data": {
    "subtotal_amount": "1497.00",
    "discount_amount": "299.40",
    "final_amount": "1197.60",
    "coupon_applied": {
      "code": "SAVE20",
      "type": "PERCENTAGE",
      "value": 20,
      "max_discount": null
    }
  }
}
```

*Without coupon or invalid coupon:*
```json
{
  "success": true,
  "data": {
    "subtotal_amount": "1497.00",
    "discount_amount": "0.00",
    "final_amount": "1497.00",
    "coupon_applied": null
  }
}
```

**Error cases:**
- 400: Invalid ticket type, quantity exceeds availability, coupon invalid/expired/limit reached, min_order_amount not met
- 401: Not authenticated
- 404: Event, event day, or ticket type not found

---

## 4. Coupon System

### 4.1 Coupon Model — New Migration Required

Coupon models exist only in schema (`docs/schemas/base.md`). They need to be implemented via new migration.

**Migration: `xxxx_add_coupons.py`**

```python
# src/migrations/versions/xxxx_add_coupons.py
op.create_table('coupons',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('code', sa.String(length=64), nullable=False, unique=True),
    sa.Column('type', sa.Enum('FLAT', 'PERCENTAGE', name='coupontype'), nullable=False),
    sa.Column('value', sa.Numeric(), nullable=False),
    sa.Column('max_discount', sa.Numeric(), nullable=True),
    sa.Column('min_order_amount', sa.Numeric(), nullable=False, server_default='0'),
    sa.Column('usage_limit', sa.Integer(), nullable=False),
    sa.Column('per_user_limit', sa.Integer(), nullable=False, server_default='1'),
    sa.Column('used_count', sa.Integer(), nullable=False, server_default='0'),
    sa.Column('valid_from', sa.DateTime(), nullable=False),
    sa.Column('valid_until', sa.DateTime(), nullable=False),
    sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
    sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
    sa.PrimaryKeyConstraint('id')
)

op.create_table('order_coupons',
    sa.Column('order_id', sa.Uuid(), nullable=False, primary_key=True),
    sa.Column('coupon_id', sa.Uuid(), nullable=False),
    sa.Column('discount_applied', sa.Numeric(), nullable=False),
    sa.ForeignKeyConstraint(['coupon_id'], ['coupons.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['order_id'], ['orders.id'], ondelete='CASCADE'),
)
```

**Per-user limit tracking:** The `order_coupons` table links order→coupon. To enforce `per_user_limit`, count how many `order_coupons` rows exist for the given `coupon_id` where the order's `user_id` matches. This requires a JOIN through OrderModel. Implementation is TODO for v1 — coupon codes used in v1 are assumed to have `per_user_limit` set very high or unlimited.

### 4.2 Coupon Discount Calculation

```python
def calculate_discount(coupon: CouponModel, subtotal: float, user_id: UUID) -> float:
    """
    Apply coupon to subtotal and return discount amount.
    Returns 0 if coupon is invalid or cannot be applied.
    """
    # 1. Check active
    if not coupon.is_active:
        return 0.0

    # 2. Check date range
    now = datetime.utcnow()
    if not (coupon.valid_from <= now <= coupon.valid_until):
        return 0.0

    # 3. Check usage limit
    if coupon.used_count >= coupon.usage_limit:
        return 0.0

    # 4. Check per-user limit (count orders using this coupon for this user)
    # TODO: implement per_user usage tracking via order_coupons table
    # if user_usage >= coupon.per_user_limit:
    #     return 0.0

    # 5. Check min_order_amount
    if subtotal < float(coupon.min_order_amount):
        return 0.0

    # 6. Calculate discount
    if coupon.type == CouponType.FLAT:
        discount = float(coupon.value)
    else:  # PERCENTAGE
        discount = subtotal * (float(coupon.value) / 100)
        if coupon.max_discount is not None:
            discount = min(discount, float(coupon.max_discount))

    # Cap at subtotal
    return min(discount, subtotal)
```

### 4.3 Coupon Validation in Create Order

```python
async def validate_coupon(code: str, subtotal: float, user_id: UUID) -> CouponModel:
    """
    Validate coupon code and return coupon if valid.
    Raises BadRequestError if invalid.
    """
    coupon = await coupon_repo.get_by_code(code)
    if not coupon:
        raise BadRequestError("Invalid coupon code")

    discount = calculate_discount(coupon, subtotal, user_id)
    if discount == 0.0:
        # Determine reason for error message
        if coupon.used_count >= coupon.usage_limit:
            raise BadRequestError("Coupon usage limit reached")
        raise BadRequestError("Coupon cannot be applied to this order")

    return coupon
```

---

## 5. Webhook Handling

### 5.1 Events to Handle

| Event | Action |
|-------|--------|
| `order.paid` | Create allocation + claim link + transfer ownership + send notifications |
| `payment.failed` | Mark order failed, clear ticket locks, cancel razorpay order |
| `payment.captured` | **Ignored** — `order.paid` is the authoritative event for RAZORPAY_ORDER |
| `payment.authorized` | **Ignored** — wait for captured |
| `order.failed` | **Razorpay does NOT send `order.failed` webhook** — derive from `payment.failed` |

> Note: For `RAZORPAY_ORDER`, the authoritative payment event is `order.paid` (razorpay fires this when payment is captured). `payment.captured` is ignored to avoid double-processing. The `parse_webhook_event` method in razorpay.py already routes `order.paid` for `RAZORPAY_ORDER` separately from payment link flows.

### 5.2 `handle_order_paid` (Same 4-Layer Idempotency as B2B)

```python
async def handle_order_paid(event: WebhookEvent):
    # Layer 1: Find order by razorpay order_id in gateway_order_id
    order = await order_payment_repo.get_by_gateway_order_id(event.razorpay_order_id)
    if not order:
        return  # Unknown order, ignore

    # Layer 1 (continued): skip if not pending
    if order.status != OrderStatus.pending:
        return  # Already paid/failed/expired

    # Validations (same as B2B)
    payment_entity = event.raw_payload["payload"]["payment"]["entity"]
    payment_amount = payment_entity["amount"]
    expected_amount = int(float(order.final_amount) * 100)

    if payment_amount != expected_amount:
        await mark_order_failed(order, "amount_mismatch")
        return

    if payment_entity["currency"] != "INR":
        await mark_order_failed(order, "currency_mismatch")
        return

    if payment_entity["status"] != "captured":
        return  # Wait for captured

    payment_id = payment_entity["id"]

    # Layer 4: Attempt insert into payment_gateway_events (dedup via constraint)
    try:
        await gateway_event_repo.create(order_id=order.id, ...)
    except IntegrityError:
        return  # Duplicate event

    # Layer 3: Atomic update
    updated = await order_payment_repo.mark_order_paid(order.id, payment_id, event.raw_payload)
    if not updated:
        return  # Another thread already processed

    # Create allocation + claim link (same as B2B webhook)
    await create_allocation_with_claim_link(order, ...)
    await ticketing_repo.update_ticket_ownership_batch(...)
    await ticketing_repo.clear_locks_for_order(order.id)

    # Notifications (fire-and-forget)
    asyncio.create_task(send_claim_link_notifications(order))
```

### 5.3 Notifications After Paid

When `order.paid` webhook is processed, send notifications to buyer:
- **Email**: Claim link URL
- **WhatsApp**: Claim link URL
- **SMS**: Claim link URL

Same notification pattern as B2B, but the claim link generated here is for direct purchase (not transfer). The claim link uses `AllocationType.purchase`.

---

## 6. Ticket Locking

**Online purchase uses a different lock path than B2B transfers:**

| Aspect | B2B Transfer | Online Purchase |
|--------|-------------|-----------------|
| Locking method | `lock_tickets_for_transfer()` | `lock_tickets_for_purchase()` (new) |
| Source of tickets | From organizer's holder pool | From shared pool (`owner_holder_id=None`) |
| `lock_reference_type` | `'transfer'` | `'order'` |
| `lock_reference_id` | `order.id` | `order.id` |
| TTL | 30 min | 30 min |

The expiry worker already handles `lock_reference_type in ('order', 'transfer')` in `clear_locks_for_order()`. No changes needed to expiry worker.

On `payment.failed`: `clear_locks_for_order(order.id)` clears locks — same as B2B.

On `order.paid` webhook: `clear_locks_for_order(order.id)` called after ownership transfer.

---

## 7. New Files Structure

> **Note:** Online purchase endpoints live as a separate router in the **events app** (`src/apps/event/`), not a standalone purchase app. This keeps related event functionality together and avoids a separate app just for one feature.

```
src/apps/event/
├── service.py                 # Add: PurchaseService (create_order, preview_order, poll_status)
├── repository.py             # Add: PurchaseRepository, CouponRepository
├── urls.py                   # Add: purchase_router (POST /orders, POST /orders/preview, GET /orders/{id}/status)
├── request.py                # Add: CreateOrderRequest, PreviewOrderRequest, OrderStatusRequest
└── response.py               # Add: CreateOrderResponse, PreviewOrderResponse, OrderStatusResponse

src/apps/allocation/
└── models.py                  # Add: CouponModel, OrderCouponModel

src/migrations/versions/
└── xxxx_add_coupons.py       # New migration for coupons + order_coupons tables
```

---

## 8. Testing Requirements

- Unit tests for coupon validation and discount calculation
- Unit tests for `create_order` service method
- Unit tests for `preview_order` service method
- Unit tests for `poll_status` service method
- Integration tests for full purchase flow:
  - Create order → verify pending → webhook fires → verify paid → poll returns jwt
  - Create order with invalid coupon → 400 error
  - Create order quantity > available → 400 error
  - Webhook fires twice → only one allocation created (idempotency)
  - Order expires → locks cleared → next purchase gets those tickets

---

## 9. Out of Scope for This Spec

- Multi-ticket-type cart (one ticket type per order)
- Guest checkout
- Refund flow
- Partial payment
- Payment retry mechanism
- Organizer-managed coupon creation (coupon codes come from external/offline campaigns)
- Per-user coupon limit enforcement (v1: assume high or unlimited per-user limits; full tracking via `order_coupons` JOIN is TODO)

---

## 10. Implementation Phases

**Phase 1 — Coupon Infrastructure** ✅ DONE
- Create `coupons` + `order_coupons` migration
- Add `CouponModel` + `OrderCouponModel` to `allocation/models.py`
- Add `CouponRepository` (get_by_code, increment_used_count)
- Implement `PurchaseService.calculate_discount()` + `PurchaseService.validate_coupon()` in event service layer

**Phase 2 — Gateway Implementation** ✅ DONE
- Implement `RazorpayPaymentGateway.create_checkout_order()` (stub → actual Razorpay `client.order.create()` call)

**Phase 3 — Ticket Locking** ✅ DONE
- Add `lock_tickets_for_purchase()` to `TicketingRepository` — FIFO from pool (`owner_holder_id=None`), `lock_reference_type='order'`

**Phase 4 — Purchase Endpoints (Events App)** ✅ DONE
- Integrate into `src/apps/event/` (not a separate app)
- Add `PurchaseService` with `preview_order`, `create_order`, `poll_order_status`
- `POST /api/events/purchase/preview` — price breakdown, no side effects
- `POST /api/events/purchase/create` — validate → lock → create order → call gateway → return razorpay order details
- `GET /api/events/purchase/orders/{order_id}/status` — poll, return jwt + claim_url when paid (with ownership check)
- `ClaimLinkModel.token` column added for claim URL reconstruction

**Phase 5 — Webhook Handler Extension** ✅ DONE
- Add `RAZORPAY_ORDER` branch inside `handle_order_paid()` — simpler than B2B (no split logic, single allocation, single claim link)
- Add `payment.failed` handling for `RAZORPAY_ORDER` (mark failed + clear locks)
- Notifications to buyer (email/WhatsApp/SMS) via existing mock utilities
- `ClaimLinkRepository.create()` and `create_allocation_with_claim_link()` now accept optional `token` param to store raw claim token

**Phase 6 — Testing**
- Unit tests for coupon logic, create/preview/poll service methods
- Integration: full happy path, idempotency, lock expiry

**Dependencies:** Phase 1 and 2 are independent. Phase 3–5 must run sequentially (each builds on the previous).