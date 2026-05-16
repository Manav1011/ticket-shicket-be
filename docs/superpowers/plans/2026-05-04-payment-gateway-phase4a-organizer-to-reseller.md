# Payment Gateway Phase 4A — Organizer → Reseller B2B Transfer

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement `is_paid=True` branch in `OrganizerService.create_b2b_transfer` so that when an organizer transfers to a reseller with `mode=TransferMode.PAID`, a Razorpay payment link is created, the buyer is notified, and allocation is deferred to the `order.paid` webhook.

**Architecture:** Paid branch diverges from free flow: creates `OrderModel` with `status=pending`, locks tickets with 30-min TTL, generates payment link via `gateway.create_payment_link()`, sends notifications, returns `payment_url` in response. No allocation created yet — webhook handles that on payment confirmation.

**Tech Stack:** Razorpay SDK, SQLAlchemy async, FastAPI, notification services.

**Prerequisite:** Complete `docs/superpowers/plans/2026-05-04-payment-gateway-phase4-shared.md` first.

---

## File Structure

**Files modified:**
- `src/apps/organizer/service.py` — implement paid branch in `create_b2b_transfer`

**Files created:**
- `tests/apps/organizer/test_service.py` (extend existing)

**Dependencies already in place (Phase 4-Shared):**
- `TransferMode` enum in `allocation/enums.py`
- `OrderPaymentRepository.update_pending_order_on_payment_link_created()`
- `B2BTransferResponse.payment_url` field
- `gateway.create_payment_link()` implemented in Phase 2
- `gateway = get_gateway("razorpay")` factory
- `GatewayType.RAZORPAY_PAYMENT_LINK` in `allocation/enums.py`

---

### Task: Implement paid flow in `OrganizerService.create_b2b_transfer`

**Files:**
- Modify: `src/apps/organizer/service.py` (replace `mode == "paid"` stub with real implementation)
- Test: `tests/apps/organizer/test_service.py` (add `test_create_b2b_transfer_paid_mode`)

**Pre-execution checklist:**
- [ ] Verify OrganizerService uses `self.repository.session` (not `self._repo._session`)
- [ ] Verify `UserRepository` import path is `from apps.allocation.repositories.user import UserRepository`
- [ ] Check `tests/apps/organizer/test_service.py` exists — add test to it, don't create new file

- [ ] **Step 1: Write the failing test**

```python
# tests/apps/organizer/test_service.py
import pytest
from uuid import uuid4
from unittest.mock import AsyncMock, MagicMock, patch


@pytest.mark.asyncio
async def test_create_b2b_transfer_paid_mode_creates_pending_order():
    """Paid mode creates a pending order, generates payment link, returns payment_url."""
    from apps.organizer.service import OrganizerService
    from apps.ticketing.enums import OrderStatus
    from apps.allocation.enums import TransferMode

    mock_repo = AsyncMock()
    mock_session = AsyncMock()
    mock_session.add = MagicMock()
    mock_session.flush = AsyncMock()
    mock_session.refresh = AsyncMock()
    mock_repo.session = mock_session

    service = OrganizerService(mock_repo)
    service._ticketing_repo = AsyncMock()
    service._allocation_repo = AsyncMock()
    service._allocation_service = AsyncMock()

    # Mock allocation_repo methods
    org_holder = MagicMock(id=uuid4())
    reseller_holder = MagicMock(id=uuid4())
    reseller_user = MagicMock(id=uuid4(), name="Reseller Co", email="reseller@co.in", phone="+919999999999")

    service._allocation_repo.get_holder_by_user_id = AsyncMock(
        side_effect=[org_holder, reseller_holder]
    )
    service._allocation_repo.list_b2b_tickets_by_holder = AsyncMock(return_value=[
        {"event_day_id": uuid4(), "count": 5}
    ])
    service._allocation_repo.get_holder_by_email = AsyncMock(return_value=None)
    service._allocation_repo.get_holder_by_phone = AsyncMock(return_value=None)

    service._ticketing_repo.get_b2b_ticket_type_for_event = AsyncMock(
        return_value=MagicMock(id=uuid4())
    )
    service._ticketing_repo.lock_tickets_for_transfer = AsyncMock(return_value=[uuid4(), uuid4()])

    # Mock gateway
    with patch("apps.organizer.service.get_gateway") as mock_get_gateway:
        mock_gateway = MagicMock()
        mock_gateway.create_payment_link = AsyncMock(
            return_value=MagicMock(
                gateway_order_id="plink_test123",
                short_url="https://razorpay.in/test",
                gateway_response={"id": "plink_test123"},
            )
        )
        mock_get_gateway.return_value = mock_gateway

        with patch("apps.organizer.service.OrderModel") as mock_order_model:
            order_instance = MagicMock()
            order_instance.id = uuid4()
            mock_order_model.return_value = order_instance

            with patch("apps.organizer.service.UserRepository") as mock_user_repo_cls:
                mock_user_repo = MagicMock()
                mock_user_repo.find_by_id = AsyncMock(return_value=reseller_user)
                mock_user_repo_cls.return_value = mock_user_repo

                result = await service.create_b2b_transfer(
                    user_id=uuid4(),
                    event_id=uuid4(),
                    reseller_id=uuid4(),
                    quantity=2,
                    event_day_id=uuid4(),
                    mode=TransferMode.PAID,
                )

    assert result.status == "pending_payment"
    assert result.mode == TransferMode.PAID
    assert result.payment_url == "https://razorpay.in/test"
    assert result.ticket_count == 2
    mock_gateway.create_payment_link.assert_called_once()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/apps/organizer/test_service.py::test_create_b2b_transfer_paid_mode -v`
Expected: FAIL — paid mode returns stub `"not_implemented"`

- [ ] **Step 3: Write implementation**

Replace the `if mode == "paid"` stub in `OrganizerService.create_b2b_transfer` with:

```python
if mode == TransferMode.PAID:
    from apps.payment_gateway.services.factory import get_gateway
    from apps.payment_gateway.services.base import BuyerInfo
    from apps.payment_gateway.repositories.order import OrderPaymentRepository
    from apps.allocation.enums import GatewayType
    from apps.allocation.repositories.user import UserRepository
    from datetime import datetime, timedelta, timezone

    # Determine reseller contact info for BuyerInfo
    reseller_user_repo = UserRepository(self.repository.session)
    reseller_user = await reseller_user_repo.find_by_id(reseller_id)
    reseller_name = getattr(reseller_user, 'name', None) or 'Reseller'
    reseller_email = getattr(reseller_user, 'email', None)
    reseller_phone = getattr(reseller_user, 'phone', None)

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
    self.repository.session.add(order)
    await self.repository.session.flush()
    await self.repository.session.refresh(order)

    # 2. Lock tickets (FIFO, 30-min TTL)
    locked_ticket_ids = await self._ticketing_repo.lock_tickets_for_transfer(
        owner_holder_id=org_holder.id,
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
        name=reseller_name,
        email=reseller_email,
        phone=reseller_phone or "",
    )
    payment_result = await gateway.create_payment_link(
        order_id=order.id,
        amount=int(0.0 * 100),  # TODO (Phase 5): use actual ticket price in paise
        currency="INR",
        buyer=buyer_info,
        description=f"B2B Transfer - {event.name}",
        event_id=event_id,
        flow_type="b2b_transfer",
        transfer_type="organizer_to_reseller",
        buyer_holder_id=reseller_holder.id,
    )

    # 4. Update order with gateway details
    order_payment_repo = OrderPaymentRepository(self.repository.session)
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

    message = f"Complete your B2B ticket purchase: {payment_result.short_url}"
    if reseller_phone:
        mock_send_sms(reseller_phone, message, template="b2b_paid_transfer")
        mock_send_whatsapp(reseller_phone, message, template="b2b_paid_transfer")
    if reseller_email:
        mock_send_email(reseller_email, "Complete Your B2B Ticket Purchase", message)

    # NO allocation created here — webhook creates it on payment

    return B2BTransferResponse(
        transfer_id=order.id,
        status="pending_payment",
        ticket_count=len(locked_ticket_ids),
        reseller_id=reseller_id,
        mode=TransferMode.PAID,
        payment_url=payment_result.short_url,
    )
```

Also update the existing free-flow return to use `TransferMode.FREE`:

```python
# In the free-flow return (around line 448-455):
return B2BTransferResponse(
    transfer_id=transfer_id,
    status="completed",
    ticket_count=quantity,
    reseller_id=reseller_id,
    mode=TransferMode.FREE,  # <-- was: mode="free"
    message="B2B transfer completed",
)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/apps/organizer/test_service.py::test_create_b2b_transfer_paid_mode -v`
Expected: PASS

- [ ] **Step 5: Run existing tests to check for regressions**

Run: `uv run pytest tests/apps/organizer/test_service.py -v --ignore=tests/apps/organizer/test_service.py::test_create_b2b_transfer_paid_mode`
Expected: All existing free-flow tests PASS

- [ ] **Step 6: Commit**

```bash
git add src/apps/organizer/service.py tests/apps/organizer/test_service.py
git commit -m "feat(organizer): implement paid mode in create_b2b_transfer with Razorpay payment link"
```

---

## Self-Review

**1. Spec coverage:**
- `OrganizerService.create_b2b_transfer` with `is_paid=True` ✅ (spec Section 8.2)
- Payment link creation via `gateway.create_payment_link()` ✅
- Notification via SMS/WhatsApp/Email ✅ (spec Section 3.3)
- Allocation deferred until webhook ✅
- `payment_url` in response ✅
- `lock_reference_type="transfer"` set by `lock_tickets_for_transfer` ✅
- `clear_locks_for_order` fix in Phase 4-Shared handles both lock types ✅

**2. Placeholder scan:**
- `TODO (Phase 5)` for `final_amount` / ticket price derivation — explicitly out of scope, acceptable for Phase 4
- No other placeholders

**3. Type consistency:**
- `TransferMode.PAID` used consistently ✅ (matches `CreateB2BTransferRequest.mode`)
- `GatewayType.RAZORPAY_PAYMENT_LINK` ✅
- `OrderStatus.pending` ✅
- `gateway.create_payment_link()` → `PaymentLinkResult` ✅
- `BuyerInfo(name, email, phone)` ✅
- `OrderPaymentRepository.update_pending_order_on_payment_link_created()` ✅

**4. `final_amount=0.0` note:** Spec says amount comes from `final_amount`. Phase 4 uses `0.0` because ticket price derivation is Phase 5 scope. The webhook handler validates amount and will fail if it doesn't match — correctly surfaces the issue.

Plan complete and saved to `docs/superpowers/plans/2026-05-04-payment-gateway-phase4a-organizer-to-reseller.md`.