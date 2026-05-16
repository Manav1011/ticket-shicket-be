# Fix: OrderCoupon FK Violation in Zero-Amount Order

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix the `order_coupons` FK violation in `create_order` when `final_amount == 0` by using SQLAlchemy ORM relationships instead of manual FK insertion order coordination.

**Architecture:** Add `relationship()` on `OrderModel` for `coupon_application` (uselist=False, cascade delete-orphan) and corresponding back_populates on `OrderCouponModel`. Update `create_order` to assign `order.coupon_application = OrderCouponModel(...)` so SQLAlchemy handles insertion order. This ensures `orders` row is inserted before `order_coupons` references it.

**Tech Stack:** SQLAlchemy ORM, asyncpg, Python

---

## Context

When `create_order` is called with a 100% coupon (zero final_amount), the code:
1. Adds `OrderModel` to session
2. Adds `OrderCouponModel` to session (same transaction)
3. Calls `flush()`

SQLAlchemy's UnitOfWork may batch both inserts and execute them in wrong order — `order_coupons` before `orders`. Since `order_coupons.order_id` FK references `orders.id`, and the `orders` row doesn't exist yet, FK constraint violation occurs.

**Affected file:** `src/apps/event/service.py` (zero-amount branch in `create_order`)
**Root model file:** `src/apps/allocation/models.py`

---

## Pre-Flight Check

- [ ] **Read current models** — verify OrderModel and OrderCouponModel definitions before modifying
- [ ] **Run existing tests** — confirm baseline passes before changes

```bash
cd /home/manav1011/Documents/ticket-shicket-be
uv run pytest tests/ -v --tb=short -x -q 2>&1 | head -50
```

Expected: Tests pass (or fail for unrelated reasons)

---

## Task 1: Add SQLAlchemy `relationship` to OrderModel

**File:** `src/apps/allocation/models.py:176-234`

- [ ] **Step 1: Read OrderModel section**

```bash
grep -n "class OrderModel" src/apps/allocation/models.py
```

Expected output: `176`

- [ ] **Step 2: Add relationship import**

Find the import line in `models.py`:
```python
from sqlalchemy.orm import Mapped, mapped_column
```

Change to:
```python
from sqlalchemy.orm import Mapped, mapped_column, relationship
```

- [ ] **Step 3: Add coupon_application relationship to OrderModel**

After the `captured_at` column (line ~232, before `__table_args__`), add:

```python
    coupon_application: Mapped["OrderCouponModel | None"] = relationship(
        back_populates="order",
        cascade="all, delete-orphan",
        uselist=False,
        lazy="selectin",
    )
```

This creates a one-to-one child relationship on `OrderModel` with cascade delete.

---

## Task 2: Add back_populates relationship to OrderCouponModel

**File:** `src/apps/allocation/models.py:274-285`

- [ ] **Step 1: Add back_populates to OrderCouponModel**

After `discount_applied` column (line ~284, after `Numeric()`), add:

```python
    order: Mapped["OrderModel"] = relationship(
        back_populates="coupon_application",
        lazy="selectin",
    )
    coupon: Mapped["CouponModel"] = relationship(
        lazy="selectin",
    )
```

---

## Task 3: Update create_order zero-amount path to use relationship

**File:** `src/apps/event/service.py:247-260`

- [ ] **Step 1: Read current zero-amount block (lines 247-260)**

Current code (approx):
```python
# Save coupon application
if coupon_record and discount > 0:
    order_coupon = OrderCouponModel(
        order_id=order_id,
        coupon_id=coupon_record.id,
        discount_applied=discount,
    )
    self.repository.session.add(order_coupon)

# Ensure order is persisted before zero-amount block (allocations FK)
await self.repository.session.flush()

# Zero-amount order: coupon fully covers cost — skip Razorpay, mark paid immediately
if final_amount == 0:
```

Change to:
```python
# Save coupon application via relationship (ensures correct insert order)
if coupon_record and discount > 0:
    order.coupon_application = OrderCouponModel(
        coupon_id=coupon_record.id,
        discount_applied=discount,
    )

# Ensure order is persisted before zero-amount block (allocations FK)
await self.repository.session.flush()

# Zero-amount order: coupon fully covers cost — skip Razorpay, mark paid immediately
if final_amount == 0:
```

**Key change:** `self.repository.session.add(order_coupon)` removed — the relationship assignment on `order.coupon_application` handles child tracking. SQLAlchemy's ORM knows to insert `orders` before `order_coupons`.

---

## Task 4: Update create_order normal (paid) path to use relationship

**File:** `src/apps/event/service.py:330-345` (normal flow)

- [ ] **Step 1: Read normal flow coupon block**

```python
# Normal flow: amount > 0, call Razorpay
await self.repository.session.flush()
gateway = get_gateway("razorpay")
```

Current code has the same manual `order_coupon` pattern above flush. Change:

```python
# Save coupon application via relationship
if coupon_record and discount > 0:
    order.coupon_application = OrderCouponModel(
        coupon_id=coupon_record.id,
        discount_applied=discount,
    )

# Normal flow: amount > 0, call Razorpay
await self.repository.session.flush()
```

---

## Task 5: Verify fix — run tests

- [ ] **Step 1: Run tests**

```bash
uv run pytest tests/ -v --tb=short -q 2>&1 | tail -30
```

Expected: All tests pass

- [ ] **Step 2: Manual test — zero-amount order**

```bash
# Login buyer
TOKEN=$(curl -s -X POST http://0.0.0.0:8080/api/user/sign-in \
  -H "Content-Type: application/json" \
  -d '{"email": "buyer@test.com", "password": "Test@1234"}' | \
  python3 -c "import sys,json; print(json.load(sys.stdin)['data']['access_token'])")

# Create free order
curl -s -X POST http://0.0.0.0:8080/api/events/purchase/create \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"event_id": "f031381f-22d9-4104-bf91-f8e07b32e265", "event_day_id": "ffe206f2-4817-42c7-9a64-3a2e800aa63f", "ticket_type_id": "1023ceb6-e6b3-4085-a97e-dce3e2f07fef", "quantity": 2, "coupon_code": "FULL100"}'
```

Expected (200):
```json
{
  "status": "SUCCESS",
  "code": 200,
  "data": {
    "status": "paid",
    "is_free": true,
    "claim_token": "<token>"
  }
}
```

- [ ] **Step 3: Verify DB state**

```bash
# Check order is paid and order_coupon exists
uv run python scripts/db_query_engine.py "SELECT o.id, o.status, o.final_amount, oc.coupon_id FROM orders o LEFT JOIN order_coupons oc ON o.id = oc.order_id WHERE o.event_id = 'f031381f-22d9-4104-bf91-f8e07b32e265' ORDER BY o.created_at DESC LIMIT 1"
```

Expected: order status=paid, final_amount=0, coupon_id=a0000000-0000-0000-0000-000000000001

- [ ] **Step 4: Verify allocation and tickets**

```bash
uv run python scripts/db_query_engine.py "SELECT id, status, ticket_count FROM allocations WHERE order_id = (SELECT id FROM orders WHERE event_id = 'f031381f-22d9-4104-bf91-f8e07b32e265' AND final_amount = 0 LIMIT 1)"
```

Expected: allocation status=completed, ticket_count=2

---

## Task 6: Commit

```bash
git add src/apps/allocation/models.py src/apps/event/service.py
git commit -m "fix: use ORM relationship for order_coupons to fix FK violation in zero-amount purchase

Before: order_coupons.insert() could run before orders.insert() due to
SQLAlchemy batch ordering, causing FK violation (order_id not in orders).

After: order.coupon_application = OrderCouponModel(...) uses ORM relationship
which SQLAlchemy resolves by inserting parent (orders) before child (order_coupons).

Changes:
- Add relationship() to OrderModel.coupon_application
- Add back_populates to OrderCouponModel
- Update create_order (zero-amount and normal paths) to use relationship assignment

Fixes: create_order 500 error with 100% coupon (final_amount=0)"
```

---

## Files Summary

| Action | File | Lines |
|--------|------|-------|
| Modify | `src/apps/allocation/models.py` | ~176-240 (OrderModel), ~274-290 (OrderCouponModel) |
| Modify | `src/apps/event/service.py` | ~247-257 (zero-amount coupon), ~330-345 (normal coupon) |

**Test file:** `tests/test_purchase.py` or `tests/test_coupon_service.py` if existing purchase tests exist.