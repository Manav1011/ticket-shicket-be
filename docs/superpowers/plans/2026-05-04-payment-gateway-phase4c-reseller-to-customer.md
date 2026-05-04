# Payment Gateway Phase 4C — Reseller → Customer Transfer

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement `is_paid=True` branch in `ResellerService.create_reseller_customer_transfer` so that when a reseller transfers to a customer with `mode=TransferMode.PAID`, a Razorpay payment link is created, the customer is notified, and allocation is deferred to the `order.paid` webhook.

**Architecture:** Paid branch diverges from free flow: creates `OrderModel` with `status=pending`, locks tickets with 30-min TTL, generates payment link via `gateway.create_payment_link()`, sends notifications to customer's phone/email, returns `payment_url` in response. No allocation created yet — webhook handles that on payment confirmation.

**Tech Stack:** Razorpay SDK, SQLAlchemy async, FastAPI, notification services.

**Prerequisite:** Complete `docs/superpowers/plans/2026-05-04-payment-gateway-phase4-shared.md` first.

---

## File Structure

**Files modified:**
- `src/apps/resellers/service.py` — implement paid branch in `create_reseller_customer_transfer`

**Files created:**
- `tests/apps/resellers/test_service.py` (extend existing)

**Dependencies already in place (Phase 4-Shared):**
- `TransferMode` enum in `allocation/enums.py`
- `OrderPaymentRepository.update_pending_order_on_payment_link_created()`
- `CustomerTransferResponse.payment_url` field
- `gateway.create_payment_link()` implemented in Phase 2
- `GatewayType.RAZORPAY_PAYMENT_LINK` in `allocation/enums.py`

---

### Task: Implement paid flow in `ResellerService.create_reseller_customer_transfer`

**Files:**
- Modify: `src/apps/resellers/service.py` (replace `mode == "paid"` stub with real implementation)
- Test: `tests/apps/resellers/test_service.py` (add `test_create_reseller_customer_transfer_paid_mode`)

**Pre-execution checklist:**
- [ ] Verify ResellerService uses `self._repo._session` (not `self.repository.session`)
- [ ] Verify `UserRepository` import path if needed
- [ ] Check `tests/apps/resellers/test_service.py` exists — add test to it

- [ ] **Step 1: Write the failing test**

```python
# tests/apps/resellers/test_service.py
import pytest
from uuid import uuid4
from unittest.mock import AsyncMock, MagicMock, patch
from apps.allocation.enums import TransferMode


@pytest.mark.asyncio
async def test_create_reseller_customer_transfer_paid_mode():
    """Paid mode creates pending order, generates payment link, returns payment_url."""
    from apps.resellers.service import ResellerService
    from apps.organizer.response import CustomerTransferResponse

    mock_repo = AsyncMock()
    mock_session = AsyncMock()
    mock_repo._session = mock_session
    mock_session.add = MagicMock()
    mock_session.flush = AsyncMock()
    mock_session.refresh = AsyncMock()

    service = ResellerService(mock_repo)
    service._allocation_repo = AsyncMock()
    service._ticketing_repo = AsyncMock()

    customer_holder = MagicMock(id=uuid4())
    reseller_holder = MagicMock(id=uuid4())

    service._repo.is_accepted_reseller = AsyncMock(return_value=True)
    service._repo.get_my_holder_for_event = AsyncMock(return_value=reseller_holder)
    service._allocation_repo.get_holder_by_phone = AsyncMock(return_value=None)
    service._allocation_repo.get_holder_by_email = AsyncMock(return_value=None)
    service._allocation_repo.create_holder = AsyncMock(return_value=customer_holder)
    service._allocation_repo.list_b2b_tickets_by_holder = AsyncMock(return_value=[{"count": 5}])
    service._ticketing_repo.get_b2b_ticket_type_for_event = AsyncMock(
        return_value=MagicMock(id=uuid4())
    )
    service._ticketing_repo.lock_tickets_for_transfer = AsyncMock(return_value=[uuid4(), uuid4()])

    with patch("apps.resellers.service.get_gateway") as mock_get_gateway:
        mock_gateway = MagicMock()
        mock_gateway.create_payment_link = AsyncMock(
            return_value=MagicMock(
                gateway_order_id="plink_reseller123",
                short_url="https://razorpay.in/reseller",
                gateway_response={"id": "plink_reseller123"},
            )
        )
        mock_get_gateway.return_value = mock_gateway

        with patch("apps.resellers.service.OrderModel") as mock_order_model:
            order_instance = MagicMock()
            order_instance.id = uuid4()
            mock_order_model.return_value = order_instance

            result = await service.create_reseller_customer_transfer(
                user_id=uuid4(),
                event_id=uuid4(),
                phone="+919999999999",
                email=None,
                quantity=2,
                event_day_id=uuid4(),
                mode=TransferMode.PAID,
            )

    assert result.status == "pending_payment"
    assert result.mode == TransferMode.PAID
    assert result.payment_url == "https://razorpay.in/reseller"
    assert result.ticket_count == 2
    mock_gateway.create_payment_link.assert_called_once()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/apps/resellers/test_service.py::test_create_reseller_customer_transfer_paid_mode -v`
Expected: FAIL — paid mode returns stub `"not_implemented"`

- [ ] **Step 3: Write implementation**

Replace the `if mode == TransferMode.PAID` stub in `ResellerService.create_reseller_customer_transfer` with:

```python
if mode == TransferMode.PAID:
    from apps.payment_gateway.services.factory import get_gateway
    from apps.payment_gateway.services.base import BuyerInfo
    from apps.payment_gateway.repositories.order import OrderPaymentRepository
    from apps.allocation.enums import GatewayType
    from datetime import datetime, timedelta, timezone

    # Build buyer info from customer contact (customer may not have a user account)
    customer_name = phone or "Customer"
    customer_email = email
    customer_phone = phone or ""

    # 1. Create pending order (no allocation created yet)
    order = OrderModel(
        event_id=event_id,
        user_id=user_id,
        type=OrderType.transfer,
        subtotal_amount=0.0,  # TODO (Phase 5): derive from ticket type price
        discount_amount=0.0,
        final_amount=0.0,  # TODO (Phase 5): derive from ticket type price
        status=OrderStatus.pending,
        payment_gateway="razorpay",
        gateway_type=GatewayType.RAZORPAY_PAYMENT_LINK,
        lock_expires_at=datetime.now(timezone.utc) + timedelta(minutes=30),
    )
    self._repo._session.add(order)
    await self._repo._session.flush()
    await self._repo._session.refresh(order)

    # 2. Lock tickets (FIFO, 30-min TTL)
    locked_ticket_ids = await self._ticketing_repo.lock_tickets_for_transfer(
        owner_holder_id=reseller_holder.id,
        event_id=event_id,
        ticket_type_id=b2b_ticket_type.id,
        event_day_id=event_day_id,
        quantity=quantity,
        order_id=order.id,
        lock_ttl_minutes=30,
    )

    # 3. Create payment link via Razorpay
    gateway = get_gateway("razorpay")
    buyer_info = BuyerInfo(
        name=customer_name,
        email=customer_email,
        phone=customer_phone,
    )
    payment_result = await gateway.create_payment_link(
        order_id=order.id,
        amount=int(0.0 * 100),  # TODO (Phase 5): use actual ticket price in paise
        currency="INR",
        buyer=buyer_info,
        description="Ticket Purchase",
        event_id=event_id,
        flow_type="b2b_transfer",
        transfer_type="reseller_to_customer",
        buyer_holder_id=customer_holder.id,
    )

    # 4. Update order with gateway details
    order_payment_repo = OrderPaymentRepository(self._repo._session)
    await order_payment_repo.update_pending_order_on_payment_link_created(
        order_id=order.id,
        gateway_order_id=payment_result.gateway_order_id,
        gateway_response=payment_result.gateway_response,
        short_url=payment_result.short_url,
    )

    # 5. Send payment link via our notification channels
    from src.utils.notifications.sms import mock_send_sms
    from src.utils.notifications.whatsapp import mock_send_whatsapp
    from src.utils.notifications.email import mock_send_email

    message = f"Complete your ticket purchase: {payment_result.short_url}"
    if customer_phone:
        mock_send_sms(customer_phone, message, template="customer_paid_transfer")
        mock_send_whatsapp(customer_phone, message, template="customer_paid_transfer")
    if customer_email:
        mock_send_email(customer_email, "Complete Your Ticket Purchase", message)

    # NO allocation created here — webhook creates it on payment

    return CustomerTransferResponse(
        transfer_id=order.id,
        status="pending_payment",
        ticket_count=len(locked_ticket_ids),
        mode=TransferMode.PAID,
        payment_url=payment_result.short_url,
    )
```

Also update the existing free-flow return to use `TransferMode.FREE`:

```python
# In the free-flow return (around the existing return statement):
return CustomerTransferResponse(
    transfer_id=transfer_id,
    status="completed",
    ticket_count=quantity,
    mode=TransferMode.FREE,  # <-- was: mode="free"
    message="Transfer completed",
)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/apps/resellers/test_service.py::test_create_reseller_customer_transfer_paid_mode -v`
Expected: PASS

- [ ] **Step 5: Run existing tests to check for regressions**

Run: `uv run pytest tests/apps/resellers/test_service.py -v`
Expected: All existing free-flow tests PASS

- [ ] **Step 6: Commit**

```bash
git add src/apps/resellers/service.py tests/apps/resellers/test_service.py
git commit -m "feat(reseller): implement paid mode in create_reseller_customer_transfer with payment link"
```

---

## Self-Review

**1. Spec coverage:**
- `ResellerService.create_reseller_customer_transfer` with `mode=TransferMode.PAID` ✅ (spec Section 8.2)
- Payment link creation via `gateway.create_payment_link()` ✅
- Notification via SMS/WhatsApp/Email ✅
- Allocation deferred until webhook ✅
- `payment_url` in response ✅
- `transfer_type="reseller_to_customer"` in notes ✅

**2. Placeholder scan:**
- `TODO (Phase 5)` for `final_amount` / ticket price derivation — explicitly out of scope
- No other placeholders

**3. Type consistency:**
- `TransferMode.PAID` used consistently ✅
- `GatewayType.RAZORPAY_PAYMENT_LINK` ✅
- `OrderStatus.pending` ✅
- `gateway.create_payment_link()` → `PaymentLinkResult` ✅
- `BuyerInfo(name, email, phone)` — phone used as name when no name available ✅
- `self._repo._session` used for session access (ResellerService pattern, not `self.repository.session`) ✅

**4. Difference from Plan 4B:**
- Uses `reseller_holder` as the `owner_holder_id` for locking (vs `org_holder` in 4B)
- `transfer_type="reseller_to_customer"` vs `"organizer_to_customer"`

Plan complete and saved to `docs/superpowers/plans/2026-05-04-payment-gateway-phase4c-reseller-to-customer.md`.