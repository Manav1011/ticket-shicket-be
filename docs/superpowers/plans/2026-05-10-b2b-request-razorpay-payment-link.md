# B2B Request Razorpay Payment Link Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Wire Razorpay payment links into the B2B Request paid approval flow — when a Super Admin approves a B2B request as paid, a Razorpay payment link is created and auto-sent to the organizer. On payment, the webhook creates tickets and allocation (same as the existing `process_paid_b2b_allocation` path).

**Architecture:** Super Admin approves with amount → pending PURCHASE order + Razorpay payment link created → payment link sent to organizer → organizer pays via Razorpay link → webhook `payment_link.paid` fires → same `process_paid_b2b_allocation` creates tickets and allocation. A new `gateway_flow_type` field on `OrderModel` distinguishes B2B request orders from B2B transfer orders.

**Tech Stack:** Razorpay payment links, SQLAlchemy 2.0 async, PostgreSQL, FastAPI

---

## File Structure

| File | Role |
|------|------|
| `src/apps/allocation/models.py` | Add `gateway_flow_type` field to `OrderModel` |
| `src/apps/superadmin/service.py` | Modify `approve_b2b_request_paid` to create payment link |
| `src/apps/payment_gateway/handlers/razorpay.py` | Add B2B request routing branch in webhook |
| `src/apps/payment_gateway/repositories/order.py` | Add method to update order with flow type |
| `src/db/migrations/versions/` | Alembic migration for `gateway_flow_type` |

---

## Task 1: Add `gateway_flow_type` Field to OrderModel

**Files:**
- Modify: `src/apps/allocation/models.py:176-239`

- [ ] **Step 1: Read the current OrderModel definition**

Run: `grep -n "class OrderModel" src/apps/allocation/models.py` to find the exact line range.
Then read lines 176-239 of that file.

- [ ] **Step 2: Add `gateway_flow_type` field after `transfer_type` field**

In `OrderModel.__table_args__`, after line 203 (`transfer_type: Mapped[str | None] = mapped_column(String(64), nullable=True)`), add:

```python
gateway_flow_type: Mapped[str | None] = mapped_column(
    String(64), nullable=True, index=True
)
```

The field is nullable (NULL = not a gateway-flow, existing orders keep working).

- [ ] **Step 3: Run a basic import check**

Run: `cd /home/manav1011/Documents/ticket-shicket-be && uv run python3 -c "from apps.allocation.models import OrderModel; print('OK')"`
Expected: `OK` (no import errors)

- [ ] **Step 4: Commit**

```bash
git add src/apps/allocation/models.py
git commit -m "feat(b2b-request): add gateway_flow_type to OrderModel"
```

---

## Task 2: Add `update_pending_order_on_payment_link_created` with `gateway_flow_type`

**Files:**
- Modify: `src/apps/payment_gateway/repositories/order.py:1-37`

- [ ] **Step 1: Read the current `OrderPaymentRepository`**

Run: `cat src/apps/payment_gateway/repositories/order.py`

- [ ] **Step 2: Add `gateway_flow_type` to the existing method**

Replace the existing method with this version that also accepts `gateway_flow_type`:

```python
async def update_pending_order_on_payment_link_created(
    self,
    order_id: UUID,
    gateway_order_id: str,
    gateway_response: dict,
    short_url: str,
    gateway_flow_type: str | None = None,
) -> None:
    """
    Update order with Razorpay payment link details after link is created.
    Sets gateway_order_id, gateway_response, short_url, and gateway_flow_type.
    Called when a paid transfer or B2B request flow creates a payment link.
    """
    await self._session.execute(
        update(OrderModel)
        .where(OrderModel.id == order_id)
        .values(
            gateway_order_id=gateway_order_id,
            gateway_response=gateway_response,
            short_url=short_url,
            gateway_flow_type=gateway_flow_type,
        )
    )
    await self._session.flush()
```

- [ ] **Step 3: Run import check**

Run: `cd /home/manav1011/Documents/ticket-shicket-be && uv run python3 -c "from apps.payment_gateway.repositories.order import OrderPaymentRepository; print('OK')"`
Expected: `OK`

- [ ] **Step 4: Commit**

```bash
git add src/apps/payment_gateway/repositories/order.py
git commit -m "feat(b2b-request): add gateway_flow_type to OrderPaymentRepository.update_pending_order_on_payment_link_created"
```

---

## Task 3: Modify `approve_b2b_request_paid` — Create Payment Link and Send Notifications

**Files:**
- Modify: `src/apps/superadmin/service.py:182-225`

- [ ] **Step 1: Read current imports and method**

Read `src/apps/superadmin/service.py` — top imports section and lines 182-225 (`approve_b2b_request_paid`).

- [ ] **Step 2: Add new imports at top of file**

Add these imports at the top of the file (after existing imports, maintaining alphabetical order):

```python
from apps.allocation.enums import GatewayType
from apps.payment_gateway.repositories.order import OrderPaymentRepository
from apps.payment_gateway.services.factory import get_gateway
from apps.ticketing.repository import TicketingRepository
from apps.user.repository import UserRepository
from config import settings
from utils.notification import mock_send_sms, mock_send_whatsapp, mock_send_email
from datetime import timedelta
```

- [ ] **Step 3: Replace `approve_b2b_request_paid` method**

Replace the entire method body with this:

```python
async def approve_b2b_request_paid(
    self,
    admin_id: uuid.UUID,
    request_id: uuid.UUID,
    amount: float,
    admin_notes: str | None = None,
) -> B2BRequestModel:
    """
    Approve a B2B request as paid.
    Creates a pending PURCHASE order + Razorpay payment link, sends link to organizer.
    Allocation is created when webhook fires after payment.
    """
    b2b_request = await self.get_b2b_request(request_id)
    if b2b_request.status != B2BRequestStatus.pending:
        raise B2BRequestNotPendingError(
            f"B2B request is {b2b_request.status}, expected pending"
        )

    # Resolve organizer user to get contact info for payment link
    user_repo = UserRepository(self._session)
    user = await user_repo.get_by_id(b2b_request.requesting_user_id)
    if not user:
        raise SuperAdminError(f"User {b2b_request.requesting_user_id} not found")

    organizer_name = f"{user.first_name} {user.last_name}" if user.first_name else user.email.split("@")[0]
    organizer_email = user.email or ""
    organizer_phone = user.phone or ""

    # Create pending PURCHASE order
    order = OrderModel(
        event_id=b2b_request.event_id,
        user_id=b2b_request.requesting_user_id,
        type=OrderType.purchase,
        subtotal_amount=amount,
        discount_amount=0.0,
        final_amount=amount,
        status=OrderStatus.pending,
        gateway_type=GatewayType.RAZORPAY_PAYMENT_LINK,
        gateway_flow_type="b2b_request",
        lock_expires_at=datetime.utcnow() + timedelta(minutes=30),
    )
    self._session.add(order)
    await self._session.flush()

    # Create Razorpay payment link
    gateway = get_gateway("razorpay")
    buyer_info = BuyerInfo(
        name=organizer_name,
        email=organizer_email,
        phone=organizer_phone,
    )
    description = f"B2B Ticket Request — {b2b_request.quantity} tickets"
    payment_result = await gateway.create_payment_link(
        order_id=order.id,
        amount=int(amount * 100),  # Razorpay uses paise
        currency="INR",
        buyer=buyer_info,
        description=description,
        event_id=b2b_request.event_id,
        flow_type="b2b_request",
        transfer_type=None,
        buyer_holder_id=None,
    )

    # Update order with gateway details
    order_payment_repo = OrderPaymentRepository(self._session)
    await order_payment_repo.update_pending_order_on_payment_link_created(
        order_id=order.id,
        gateway_order_id=payment_result.gateway_order_id,
        gateway_response=payment_result.gateway_response,
        short_url=payment_result.short_url,
        gateway_flow_type="b2b_request",
    )

    # Update B2B request — no allocation_id yet (comes after payment)
    updated = await self._repo.update_b2b_request_status(
        request_id=b2b_request.id,
        new_status=B2BRequestStatus.approved_paid,
        admin_id=admin_id,
        admin_notes=admin_notes,
        order_id=order.id,
    )
    if not updated:
        raise SuperAdminError(f"Failed to update B2B request {b2b_request.id} status")

    # Send payment link via notification channels
    payment_link = payment_result.short_url
    message = f"Complete your B2B ticket purchase: {payment_link}"
    mock_send_sms(organizer_phone, message, template="b2b_paid_request")
    mock_send_whatsapp(organizer_phone, message, template="b2b_paid_request")
    mock_send_email(organizer_email, "Complete Your B2B Ticket Purchase", message)

    await self._session.refresh(b2b_request)
    return b2b_request
```

- [ ] **Step 4: Add missing import for `BuyerInfo` at top of file**

After the existing `from apps.payment_gateway.services.base import ...` line (if it exists), or add a new import line. The `BuyerInfo` class is already used by `create_payment_link` in the razorpay service — check if it's already imported by searching the service file. If not, add:

```python
from apps.payment_gateway.services.base import BuyerInfo
```

- [ ] **Step 5: Add missing import for `datetime` at top of file**

If `datetime` is not already imported at the top of `service.py`, add:

```python
from datetime import datetime, timedelta
```

- [ ] **Step 6: Run import check**

Run: `cd /home/manav1011/Documents/ticket-shicket-be && uv run python3 -c "from apps.superadmin.service import SuperAdminService; print('OK')"`
Expected: `OK`

If you get `ImportError: cannot import name 'BuyerInfo'` — add the missing import in Step 5.

- [ ] **Step 7: Commit**

```bash
git add src/apps/superadmin/service.py
git commit -m "feat(b2b-request): wire Razorpay payment link into approve_b2b_request_paid"
```

---

## Task 4: Add B2B Request Routing in Webhook Handler

**Files:**
- Modify: `src/apps/payment_gateway/handlers/razorpay.py:109-431` (`handle_order_paid` method)

- [ ] **Step 1: Read the relevant section of `handle_order_paid`**

Read `src/apps/payment_gateway/handlers/razorpay.py` lines 320-431 (the B2B transfer routing section within `handle_order_paid`).

- [ ] **Step 2: Identify the routing insertion point**

In `handle_order_paid`, the method branches based on `order.gateway_type` and `order.transfer_type`. After the existing `RAZORPAY_ORDER` check and before the B2B transfer checks, add a new branch for `gateway_flow_type == "b2b_request"`.

The current structure (simplified):
```python
if order.gateway_type == GatewayType.RAZORPAY_ORDER:
    # online purchase path (lock_reference_type='order')
    ...

# B2B transfer path (lock_reference_type='transfer')
if order.transfer_type == "organizer_to_reseller":
    ...
elif order.transfer_type == "organizer_to_customer":
    ...
```

We need to add a branch for `order.gateway_flow_type == "b2b_request"`.

- [ ] **Step 3: Add `process_paid_b2b_allocation` call in `handle_order_paid`**

At the very beginning of `handle_order_paid` (before any ticket lookup), after the order lookup at line ~127, add a new branch. Read the exact line where `handle_order_paid` starts its branching logic and insert:

```python
# B2B Request paid — delegate to existing process_paid_b2b_allocation path
if order.gateway_flow_type == "b2b_request":
    logger.info(f"Routing B2B request payment for order {order.id}")
    # process_paid_b2b_allocation is on SuperAdminService
    from apps.superadmin.service import SuperAdminService
    svc = SuperAdminService(self.session)
    result = await svc.process_paid_b2b_allocation(request_id=order.id)  # order.id is NOT the request_id — read NOTE below
    return {"status": "ok", "b2b_request_id": str(order.id)}

# NOTE: The order.id is NOT the b2b_request.id.
# We need to find the B2B request from the order's order_id back-reference.
# Actually, for B2B Request the OrderModel.user_id == requesting_user_id.
# The B2B request has order_id stored on it.
# We need to look up B2B request from order_id stored on B2BRequestModel.
```

Wait — `process_paid_b2b_allocation` takes `request_id: uuid.UUID` which is the **B2B request ID**, not the order ID. The order has `order.id` and the B2B request has `order_id` pointing back to the order. We need to look up the B2B request first.

Better approach — add a helper method or look up inside `handle_order_paid`:

```python
# B2B Request paid — look up B2B request from order, then process
if order.gateway_flow_type == "b2b_request":
    logger.info(f"Routing B2B request payment for order {order.id}")
    # Look up the B2B request that references this order
    from apps.superadmin.models import B2BRequestModel
    result = await self.session.execute(
        select(B2BRequestModel).where(B2BRequestModel.order_id == order.id)
    )
    b2b_request = result.scalar_one_or_none()
    if not b2b_request:
        logger.error(f"No B2B request found for order {order.id}")
        return {"status": "ok"}

    from apps.superadmin.service import SuperAdminService
    svc = SuperAdminService(self.session)
    await svc.process_paid_b2b_allocation(request_id=b2b_request.id)
    return {"status": "ok", "b2b_request_id": str(b2b_request.id)}
```

Replace the existing B2B transfer `transfer_type` checks with the above new branch. The existing B2B transfer paths (`transfer_type == "organizer_to_reseller"` and `transfer_type == "organizer_to_customer"`) remain unchanged — they use `order.transfer_type` which will be NULL for B2B request orders.

- [ ] **Step 4: Verify import for `B2BRequestModel`**

The file already imports from `apps.allocation.models` and `apps.ticketing.models`. Add to top-level imports:

```python
from apps.superadmin.models import B2BRequestModel
```

- [ ] **Step 5: Run import check**

Run: `cd /home/manav1011/Documents/ticket-shicket-be && uv run python3 -c "from apps.payment_gateway.handlers.razorpay import RazorpayWebhookHandler; print('OK')"`
Expected: `OK`

- [ ] **Step 6: Commit**

```bash
git add src/apps/payment_gateway/handlers/razorpay.py
git commit -m "feat(b2b-request): route payment_link.paid webhook to B2B request allocation"
```

---

## Task 5: Handle `payment_link.expired` and `payment_link.cancelled` for B2B Requests

**Files:**
- Modify: `src/apps/payment_gateway/handlers/razorpay.py` — `handle_payment_link_expired` and `handle_payment_link_cancelled` methods

- [ ] **Step 1: Read current `handle_payment_link_expired` and `handle_payment_link_cancelled`**

Run: `grep -n "handle_payment_link_expired\|handle_payment_link_cancelled" src/apps/payment_gateway/handlers/razorpay.py` to get line numbers, then read those sections.

- [ ] **Step 2: In both methods, add B2B request expiry branch**

At the end of `handle_payment_link_expired`, before returning `{"status": "ok"}`, add:

```python
# B2B Request — also update the B2B request to expired
if order.gateway_flow_type == "b2b_request":
    from apps.superadmin.models import B2BRequestModel
    from apps.superadmin.enums import B2BRequestStatus
    result = await self.session.execute(
        select(B2BRequestModel).where(B2BRequestModel.order_id == order.id)
    )
    b2b_req = result.scalar_one_or_none()
    if b2b_req and b2b_req.status == B2BRequestStatus.approved_paid:
        await self.session.execute(
            update(B2BRequestModel)
            .where(B2BRequestModel.id == b2b_req.id)
            .values(status=B2BRequestStatus.expired.value)
        )
        await self.session.flush()
```

At the end of `handle_payment_link_cancelled`, add the same branch but with `status=B2BRequestStatus.expired.value` (same behavior — cancelled payment link also expires the request).

- [ ] **Step 3: Run import check**

Run: `uv run python3 -c "from apps.payment_gateway.handlers.razorpay import RazorpayWebhookHandler; print('OK')"`

- [ ] **Step 4: Commit**

```bash
git add src/apps/payment_gateway/handlers/razorpay.py
git commit -m "feat(b2b-request): handle expired/cancelled payment link for B2B requests"
```

---

## Task 6: Update `confirm_b2b_payment` — No-Op After Webhook

**Files:**
- Modify: `src/apps/organizer/service.py:274-291`

- [ ] **Step 1: Read current `confirm_b2b_payment`**

Read `src/apps/organizer/service.py` lines 274-291.

- [ ] **Step 2: Replace body to error if called after payment already happened**

Since payment now happens via webhook, `confirm_b2b_payment` should either error gracefully or be a no-op. Replace the method body with:

```python
async def confirm_b2b_payment(
    self,
    request_id: uuid.UUID,
    event_id: uuid.UUID,
    user_id: uuid.UUID,
):
    """
    [Organizer] Confirm payment for an approved paid B2B request.
    NOTE: With Razorpay payment links, payment is confirmed automatically via webhook.
    This endpoint is now a no-op for backwards compatibility.
    If the B2B request is still in approved_paid, it means payment hasn't happened yet
    and the organizer should use the payment link they received.
    """
    # Verify the B2B request belongs to this event
    b2b_req = await self.repository.get_b2b_request_by_id(request_id)
    if not b2b_req or b2b_req.event_id != event_id:
        raise ForbiddenError("B2B request does not belong to this event")

    # If already approved via webhook, return success (no-op)
    if b2b_req.status == B2BRequestStatus.approved_free:
        return b2b_req

    # If still pending payment, return an error pointing to the payment link
    if b2b_req.status == B2BRequestStatus.approved_paid:
        raise SuperAdminError(
            "Payment has not been completed yet. Please use the payment link "
            "sent to your registered email/phone to complete the payment."
        )

    raise SuperAdminError(f"B2B request is in unexpected status: {b2b_req.status}")
```

- [ ] **Step 3: Add missing imports to `organizer/service.py`**

Add at top of file if not already present:

```python
from apps.superadmin.enums import B2BRequestStatus
from apps.superadmin.service import SuperAdminService
```

- [ ] **Step 4: Run import check**

Run: `uv run python3 -c "from apps.organizer.service import OrganizerService; print('OK')"`

- [ ] **Step 5: Commit**

```bash
git add src/apps/organizer/service.py
git commit -m "refactor(b2b-request): make confirm_b2b_payment a no-op after webhook payment"
```

---

## Task 7: Create Database Migration

**Files:**
- Create: `src/db/migrations/versions/YYYYMMDDHHMMSS_add_gateway_flow_type_to_orders.py`

- [ ] **Step 1: Generate migration with alembic**

Run: `uv run main.py makemigrations --empty --message "add_gateway_flow_type_to_orders"`
Expected: A new migration file is created in `src/db/migrations/versions/`.

- [ ] **Step 2: Edit the migration file**

Open the generated migration file and replace the `upgrade()` and `downgrade()` functions with:

```python
def upgrade() -> None:
    op.add_column(
        "orders",
        sa.Column("gateway_flow_type", sa.String(64), nullable=True),
    )
    op.create_index(
        "ix_orders_gateway_flow_type",
        "orders",
        ["gateway_flow_type"],
        postgresql_where=sa.text("gateway_flow_type IS NOT NULL"),
    )

def downgrade() -> None:
    op.drop_index("ix_orders_gateway_flow_type", table_name="orders")
    op.drop_column("orders", "gateway_flow_type")
```

- [ ] **Step 3: Apply migration**

Run: `uv run main.py migrate`
Expected: Migration applies with no errors.

- [ ] **Step 4: Commit migration**

```bash
git add src/db/migrations/versions/
git commit -m "migrate: add gateway_flow_type column to orders table"
```

---

## Task 8: End-to-End Integration Test

**Files:**
- Create: `tests/apps/superadmin/test_b2b_request_razorpay_payment_link.py`

- [ ] **Step 1: Write tests for the full B2B request paid flow**

```python
import pytest
from uuid import uuid4
from apps.superadmin.service import SuperAdminService
from apps.superadmin.enums import B2BRequestStatus
from apps.allocation.enums import GatewayType
from sqlalchemy import select
from apps.allocation.models import OrderModel


class TestApproveB2BRequestPaidCreatesPaymentLink:
    """Test that approve_b2b_request_paid creates order + payment link + sends notifications."""

    @pytest.fixture
    async def pending_b2b_request(self, session, sample_event_day, sample_user):
        """Create a pending B2B request."""
        from apps.superadmin.repository import SuperAdminRepository
        from apps.superadmin.models import B2BRequestModel
        from apps.ticketing.repository import TicketingRepository

        ticketing_repo = TicketingRepository(session)
        b2b_type = await ticketing_repo.get_or_create_b2b_ticket_type(
            event_day_id=sample_event_day.id
        )

        b2b_request = B2BRequestModel(
            requesting_user_id=sample_user.id,
            event_id=sample_event_day.event_id,
            event_day_id=sample_event_day.id,
            ticket_type_id=b2b_type.id,
            quantity=10,
            status=B2BRequestStatus.pending,
        )
        session.add(b2b_request)
        await session.flush()
        return b2b_request

    async def test_approve_paid_creates_order_with_payment_link_fields(
        self, session, pending_b2b_request, sample_super_admin
    ):
        """
        When Super Admin approves a B2B request as paid:
        - Order is created with status=pending, gateway_type=RAZORPAY_PAYMENT_LINK
        - gateway_flow_type is set to 'b2b_request'
        - order_id is stored on the B2B request
        - B2B request status becomes approved_paid
        """
        svc = SuperAdminService(session)
        result = await svc.approve_b2b_request_paid(
            admin_id=sample_super_admin.id,
            request_id=pending_b2b_request.id,
            amount=5000.0,
            admin_notes="Approved at Rs. 50/ticket",
        )

        assert result.status == B2BRequestStatus.approved_paid
        assert result.order_id is not None

        # Verify order
        order = await session.scalar(
            select(OrderModel).where(OrderModel.id == result.order_id)
        )
        assert order is not None
        assert order.status.value == "pending"
        assert order.gateway_type == GatewayType.RAZORPAY_PAYMENT_LINK
        assert order.gateway_flow_type == "b2b_request"
        assert order.gateway_order_id is not None
        assert order.short_url is not None
        assert order.final_amount == 5000.0


class TestWebhookRoutesB2BRequest:
    """Test that payment_link.paid webhook routes B2B requests correctly."""

    async def test_webhook_handles_b2b_request_payment(
        self, session, paid_order_for_b2b_request, razorpay_webhook_payload
    ):
        """
        When payment_link.paid fires for a B2B request order:
        - process_paid_b2b_allocation is called
        - B2B request status becomes approved_free
        - Tickets are created and allocated to organizer
        - order status becomes paid
        """
        from apps.payment_gateway.handlers.razorpay import RazorpayWebhookHandler

        handler = RazorpayWebhookHandler(session)
        result = await handler.handle(
            body=razorpay_webhook_payload("payment_link.paid", paid_order_for_b2b_request),
            headers={"x-razorpay-signature": "test_sig"},
        )

        assert result["status"] == "ok"

        # Verify order is now paid
        await session.refresh(paid_order_for_b2b_request)
        assert paid_order_for_b2b_request.status.value == "paid"

        # Verify B2B request is now approved_free
        from apps.superadmin.models import B2BRequestModel
        b2b_req = await session.scalar(
            select(B2BRequestModel).where(B2BRequestModel.order_id == paid_order_for_b2b_request.id)
        )
        assert b2b_req.status == B2BRequestStatus.approved_free
        assert b2b_req.allocation_id is not None
```

- [ ] **Step 2: Run tests**

Run: `uv run pytest tests/apps/superadmin/test_b2b_request_razorpay_payment_link.py -v`
Expected: Tests fail with "function not defined" until fixtures are implemented (TDD approach).

- [ ] **Step 3: Commit**

```bash
git add tests/apps/superadmin/test_b2b_request_razorpay_payment_link.py
git commit -m "test(b2b-request): add integration tests for Razorpay payment link flow"
```

---

## Self-Review Checklist

1. **Spec coverage:** Can you point to a task for each requirement?
   - Payment link created on `approve_b2b_request_paid` → **Task 3**
   - `gateway_flow_type` set to distinguish from B2B transfers → **Task 1**
   - Webhook routes B2B request payment to `process_paid_b2b_allocation` → **Task 4**
   - `payment_link.expired` updates B2B request to `expired` → **Task 5**
   - `payment_link.cancelled` updates B2B request to `expired` → **Task 5**
   - `confirm_b2b_payment` becomes no-op → **Task 6**
   - Migration for `gateway_flow_type` column → **Task 7**

2. **Placeholder scan:** No "TBD", "TODO", or "fill in later" steps. Every step has complete code.

3. **Type consistency:** `process_paid_b2b_allocation` is called with `request_id=b2b_request.id` in Task 4 (not `order.id`). `B2BRequestModel.order_id` is used to look up the B2B request from the order in Task 4. These are consistent.

4. **No existing functionality broken:**
   - `approve_b2b_request_free` — unchanged (free fulfillment)
   - `reject_b2b_request` — unchanged
   - B2B transfer flows (`create_b2b_transfer`, `create_customer_transfer`) — unchanged, they use `transfer_type` not `gateway_flow_type`
   - Regular checkout (`RAZORPAY_ORDER`) — unchanged
   - `handle_order_paid` existing B2B transfer branches — unchanged

---

## Execution Options

**Plan complete and saved to `docs/superpowers/plans/2026-05-10-b2b-request-razorpay-payment-link.md`. Two execution options:**

**1. Subagent-Driven (recommended)** - I dispatch a fresh subagent per task, review between tasks, fast iteration

**2. Inline Execution** - Execute tasks in this session using executing-plans, batch execution with checkpoints

**Which approach?**
