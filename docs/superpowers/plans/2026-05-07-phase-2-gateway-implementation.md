# Phase 2: Razorpay Gateway — `create_checkout_order`

> **For agentic workers:** Use superpowers:subagent-driven-development or superpowers:executing-plans to implement task-by-task.

**Goal:** Replace the `NotImplementedError` stub in `RazorpayPaymentGateway.create_checkout_order()` with the actual Razorpay `client.order.create()` call.

**Architecture:** Razorpay `client.order.create()` maps directly to `CheckoutOrderResult` — no schema changes needed. The existing `CheckoutOrderResult` already has `gateway_order_id, amount, currency, key_id, gateway_response`.

---

## File Map

| Action | File |
|--------|------|
| Modify | `src/apps/payment_gateway/services/razorpay.py` |

---

## Tasks

### Task 1: Implement `create_checkout_order`

**File:** `src/apps/payment_gateway/services/razorpay.py` (line 69)

- [ ] **Step 1: Replace `raise NotImplementedError` with actual implementation**

Replace line 69-70 with:

```python
async def create_checkout_order(self, order_id, amount: int, currency: str, event_id) -> CheckoutOrderResult:
    """Create a Razorpay checkout order for online ticket purchase."""
    response = self._client.order.create(data={
        "amount": amount,
        "currency": currency,
        "receipt": str(order_id),
        "payment_capture": 1,
        "notes": {
            "internal_order_id": str(order_id),
            "event_id": str(event_id),
            "flow_type": "online_purchase",
        },
    })
    return CheckoutOrderResult(
        gateway_order_id=response["id"],
        amount=amount,
        currency=currency,
        key_id=settings.RAZORPAY_KEY_ID,
        gateway_response=response,
    )
```

- [ ] **Step 2: Verify `CheckoutOrderResult` fields match**

From `src/apps/payment_gateway/services/base.py`:
- `gateway_order_id: str`
- `amount: int`
- `currency: str`
- `key_id: str`
- `gateway_response: Optional[dict]`

All fields are covered by the implementation above.

- [ ] **Step 3: Verify settings import**

Confirm `settings.RAZORPAY_KEY_ID` is accessible in `razorpay.py`. If not, add the import.

- [ ] **Step 4: Verify no type errors**

```bash
uv run mypy src/apps/payment_gateway/services/razorpay.py --ignore-missing-imports
```

Expected: no errors.

- [ ] **Step 5: Commit**

```bash
git add src/apps/payment_gateway/services/razorpay.py
git commit -m "feat(gateway): implement create_checkout_order for RAZORPAY_ORDER"
```

---

## Verification

1. `uv run main.py` — no import errors
2. `uv run mypy src/apps/payment_gateway/services/razorpay.py --ignore-missing-imports` — clean
3. Code review: method signature, response mapping, notes fields are correct