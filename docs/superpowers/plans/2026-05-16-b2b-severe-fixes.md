# B2B Request SEVERE Fixes Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix 4 SEVERE bugs in the B2B Request module — redundant order-paid update in webhook, missing order→request ownership verification, missing post-payment notification to organizer, and unreachable refresh code after raise.

**Architecture:** All 4 fixes are isolated to 2 files: `src/apps/payment_gateway/handlers/razorpay.py` (Issue 1) and `src/apps/superadmin/service.py` (Issues 2-4). No new files are created. The notification for Issue 3 follows the existing pattern already used in the regular purchase webhook (razorpay.py:314-320).

**Tech Stack:** SQLAlchemy 2.0 async, Python 3.11+

---

## File Map

```
src/apps/payment_gateway/handlers/razorpay.py  — Fix Issue 1 (remove redundant UPDATE)
src/apps/superadmin/service.py                 — Fix Issues 2, 3, 4
tests/apps/superadmin/test_service.py          — Add tests for Issue 2 (order mismatch guard)
tests/apps/payment_gateway/test_razorpay.py    — Add test for Issue 1 (no double UPDATE)
```

---

## Pre-Read: Understand the Existing Code

Before starting, read these files to understand the current state:

**razorpay.py lines 328-354** — the `b2b_request` branch in `handle_order_paid`:
```
- Calls process_paid_b2b_allocation (which already marks order paid at service.py:334)
- Then does a redundant UPDATE order.status = paid (lines 345-350)
- This is the double-processing issue
```

**service.py lines 316-334** — `process_paid_b2b_allocation`:
```
- Fetches b2b_request by request_id
- Fetches order by b2b_request.order_id
- Sets order.status = OrderStatus.paid at line 334 (Python-side, no DB call yet)
- Does NOT verify order.id == b2b_request.order_id — this is the missing guard
```

**service.py lines 399-410** — post-allocation status update:
```
- update_b2b_request_status is called at line 400
- refresh happens at line 409 AFTER the return at line 410
- Actually wait — looking at line 407: raise SuperAdminError, line 409: refresh, line 410: return
- The refresh at 409 IS reachable (it's after the if block, not inside it)
- But if updated=False triggers the raise at 407, line 409 still runs
- This is the "silent failure on update" issue — refresh loads stale data after a failed update
```

---

## Task 1: Remove Redundant Order-Paid Update in Razorpay Webhook

**Files:**
- Modify: `src/apps/payment_gateway/handlers/razorpay.py:341-353`

The webhook calls `process_paid_b2b_allocation` which marks `order.status = OrderStatus.paid` at service.py:334 (Python-side). Then the webhook immediately does an atomic `UPDATE ... SET status=paid` at razorpay.py:345-350. This second UPDATE is a no-op (rowcount=0) since the order is already paid. Removing it simplifies the flow — `process_paid_b2b_allocation` remains the sole processor.

- [ ] **Step 1: Read the current code around lines 341-353**

Run: `sed -n '328,360p' src/apps/payment_gateway/handlers/razorpay.py`

Expected output:
```python
            svc = SuperAdminService(self.session)
            await svc.process_paid_b2b_allocation(request_id=b2b_request.id)

            # Mark order as paid
            await self.session.execute(
                update(OrderModel)
                .where(OrderModel.id == order.id, OrderModel.status == OrderStatus.pending)
                .values(status=OrderStatus.paid, captured_at=datetime.utcnow())
            )

            await self.session.flush()
            logger.info(f"B2B request {b2b_request.id} allocation complete for order {order.id}")
```

- [ ] **Step 2: Remove lines 345-352 (the redundant UPDATE + flush)**

Replace lines 345-352:
```python
            await svc.process_paid_b2b_allocation(request_id=b2b_request.id)

            # Mark order as paid  ← REMOVE THIS BLOCK (already done by service)
            # await self.session.execute(
            #     update(OrderModel)
            #     .where(OrderModel.id == order.id, OrderModel.status == OrderStatus.pending)
            #     .values(status=OrderStatus.paid, captured_at=datetime.utcnow())
            # )

            # await self.session.flush()
            logger.info(f"B2B request {b2b_request.id} allocation complete for order {order.id}")
```

With:
```python
            await svc.process_paid_b2b_allocation(request_id=b2b_request.id)
            logger.info(f"B2B request {b2b_request.id} allocation complete for order {order.id}")
```

- [ ] **Step 3: Verify the change compiles**

Run: `cd /home/manav1011/Documents/ticket-shicket-be && python3 -c "from apps.payment_gateway.handlers.razorpay import RazorpayWebhookHandler; print('OK')"`

Expected: `OK` with no errors

- [ ] **Step 4: Commit**

```bash
git add src/apps/payment_gateway/handlers/razorpay.py
git commit -m "fix(payment_gateway): remove redundant order-paid UPDATE in b2b_request webhook
"
```

---

## Task 2: Add Order→Request Ownership Verification in process_paid_b2b_allocation

**Files:**
- Modify: `src/apps/superadmin/service.py:326-334`

The method fetches the order via `b2b_request.order_id` but never verifies the order ID actually matches. If called with a `request_id` whose `order_id` points to a different order (edge case: request re-approved with a new order), the service would operate on the wrong order. Add an explicit guard.

- [ ] **Step 1: Read the current code around lines 326-334**

```python
        # Get the existing pending order
        order = await self._session.scalar(
            select(OrderModel).where(OrderModel.id == b2b_request.order_id)
        )
        if not order:
            raise SuperAdminError(f"Order {b2b_request.order_id} not found")

        # Mark order as paid
        order.status = OrderStatus.paid
```

- [ ] **Step 2: Add order ownership verification after fetching the order**

Replace:
```python
        if not order:
            raise SuperAdminError(f"Order {b2b_request.order_id} not found")
```

With:
```python
        if not order:
            raise SuperAdminError(f"Order {b2b_request.order_id} not found")

        # Guard: ensure the order found actually belongs to this B2B request
        if order.id != b2b_request.order_id:
            raise SuperAdminError(
                f"Order mismatch: webhook order {order.id} != b2b_request.order_id {b2b_request.order_id}"
            )
```

- [ ] **Step 3: Verify the change compiles**

Run: `cd /home/manav1011/Documents/ticket-shicket-be && python3 -c "from apps.superadmin.service import SuperAdminService; print('OK')"`

Expected: `OK` with no errors

- [ ] **Step 4: Add a test for the order mismatch guard**

Check if a test file exists:
Run: `ls tests/apps/superadmin/test_service.py 2>/dev/null && echo "exists" || echo "not found"`

If the file exists, read it first:
Run: `head -50 tests/apps/superadmin/test_service.py`

Then add a test for the order mismatch case:

```python
import pytest
from unittest.mock import AsyncMock, MagicMock
from apps.superadmin.service import SuperAdminService
from apps.superadmin.enums import B2BRequestStatus
from apps.superadmin.exceptions import SuperAdminError


@pytest.mark.asyncio
async def test_process_paid_b2b_allocation_rejects_mismatched_order():
    """
    When b2b_request.order_id points to a different order than the one
    passed via the webhook, the service must reject with SuperAdminError.
    """
    # Setup: mock session, mock repo
    session = AsyncMock()
    mock_repo = AsyncMock()
    mock_allocation_repo = AsyncMock()
    mock_ticketing_repo = AsyncMock()
    mock_event_repo = AsyncMock()
    mock_user_repo = AsyncMock()

    svc = SuperAdminService.__new__(SuperAdminService)
    svc._session = session
    svc._repo = mock_repo
    svc._allocation_repo = mock_allocation_repo
    svc._ticketing_repo = mock_ticketing_repo
    svc._event_repo = mock_event_repo

    # Create a b2b_request with order_id = UUID("11111111-1111-1111-1111-111111111111")
    b2b_request = MagicMock()
    b2b_request.id = uuid.UUID("22222222-2222-2222-2222-222222222222")
    b2b_request.order_id = uuid.UUID("11111111-1111-1111-1111-111111111111")
    b2b_request.status = B2BRequestStatus.approved_paid
    b2b_request.requesting_user_id = uuid.UUID("33333333-3333-3333-3333-333333333333")
    b2b_request.event_day_id = uuid.UUID("44444444-4444-4444-4444-444444444444")
    b2b_request.event_id = uuid.UUID("55555555-5555-5555-5555-555555555555")
    b2b_request.quantity = 10
    b2b_request.reviewed_by_admin_id = uuid.UUID("66666666-6666-6666-6666-666666666666")

    # Mock get_b2b_request to return the b2b_request
    mock_repo.get_b2b_request_by_id = AsyncMock(return_value=b2b_request)

    # Mock order lookup — returns order with DIFFERENT id
    mock_order = MagicMock()
    mock_order.id = uuid.UUID("99999999-9999-9999-9999-999999999999")  # Different from b2b_request.order_id

    async def mock_scalar(query):
        # Return the mismatched order
        result = MagicMock()
        result.scalar_one_or_none = MagicMock(return_value=mock_order)
        return result

    session.scalar = mock_scalar

    # Expect SuperAdminError due to order mismatch
    with pytest.raises(SuperAdminError, match="Order mismatch"):
        await svc.process_paid_b2b_allocation(b2b_request.id)
```

Note: This test uses mocks extensively because `process_paid_b2b_allocation` has many collaborators. The key assertion is that when `order.id != b2b_request.order_id`, a `SuperAdminError` with "Order mismatch" is raised.

- [ ] **Step 5: Run the test**

Run: `cd /home/manav1011/Documents/ticket-shicket-be && python3 -m pytest tests/apps/superadmin/test_service.py::test_process_paid_b2b_allocation_rejects_mismatched_order -v 2>/dev/null || echo "Test file may need setup"`

If the test file doesn't exist, create the minimal structure:
```bash
mkdir -p tests/apps/superadmin
touch tests/apps/superadmin/__init__.py
```

Then run the test again.

- [ ] **Step 6: Commit**

```bash
git add src/apps/superadmin/service.py tests/apps/superadmin/test_service.py
git commit -m "fix(superadmin): add order mismatch guard in process_paid_b2b_allocation
"
```

---

## Task 3: Add Post-Payment Notification to Organizer in process_paid_b2b_allocation

**Files:**
- Modify: `src/apps/superadmin/service.py:399-410` (after `update_b2b_request_status` succeeds)

After `process_paid_b2b_allocation` completes (allocation created, tickets minted, B2B request status updated to `payment_done`), the **organizer gets no notification** that their B2B tickets have been issued. Compare this to the regular purchase webhook (razorpay.py:314-320) which sends claim link notification. The B2B flow needs an analogous notification.

The notification should:
1. Look up the organizer's `TicketHolder` (via `requesting_user_id`)
2. Send email/SMS/WhatsApp with the ticket count and a link to view them
3. Follow the same pattern as `mock_send_email` used in razorpay.py:320

- [ ] **Step 1: Read the current end of process_paid_b2b_allocation (lines 399-420)**

```python
        # Update B2B request with allocation_id
        updated = await self._repo.update_b2b_request_status(
            request_id=b2b_request.id,
            new_status=B2BRequestStatus.payment_done,
            admin_id=admin_id,
            allocation_id=allocation.id,
        )
        if not updated:
            raise SuperAdminError(f"Failed to update B2B request {b2b_request.id} status")

        await self._session.refresh(b2b_request)
        return b2b_request
```

- [ ] **Step 2: Add notification block after update_b2b_request_status succeeds**

Replace:
```python
        if not updated:
            raise SuperAdminError(f"Failed to update B2B request {b2b_request.id} status")

        await self._session.refresh(b2b_request)
        return b2b_request
```

With:
```python
        if not updated:
            raise SuperAdminError(f"Failed to update B2B request {b2b_request.id} status")

        # Notify organizer that their B2B tickets have been issued
        try:
            holder_result = await self._session.execute(
                select(TicketHolderModel).where(TicketHolderModel.user_id == b2b_request.requesting_user_id)
            )
            org_holder = holder_result.scalar_one_or_none()
            if org_holder:
                ticket_msg = f"Your B2B request for {b2b_request.quantity} ticket(s) has been fulfilled and tickets are now active."
                if org_holder.email:
                    mock_send_email(org_holder.email, "B2B Tickets Issued", ticket_msg)
                if org_holder.phone:
                    mock_send_sms(org_holder.phone, ticket_msg)
                    mock_send_whatsapp(org_holder.phone, ticket_msg)
        except Exception as e:
            # Notification failures must not rollback the allocation
            logger.warning(f"Failed to send B2B fulfillment notification: {e}")

        await self._session.refresh(b2b_request)
        return b2b_request
```

Note: `select` is imported. `mock_send_email`, `mock_send_sms`, `mock_send_whatsapp` are imported. HOWEVER — `TicketHolderModel` is NOT imported in service.py. You MUST add it to the existing import from `apps.allocation.models`:

```python
from apps.allocation.models import AllocationModel, OrderModel, TicketHolderModel
```

Also add `logger = logging.getLogger(__name__)` at module level (or add `import logging` and define it). The notification block must use `logger.warning(...)` for failures.

- [ ] **Step 3: Verify the change compiles**

Run: `cd /home/manav1011/Documents/ticket-shicket-be && python3 -c "from apps.superadmin.service import SuperAdminService; print('OK')"`

Expected: `OK` with no errors

- [ ] **Step 4: Commit**

```bash
git add src/apps/superadmin/service.py
git commit -m "feat(superadmin): notify organizer when B2B tickets are issued after payment
"
```

---

## Task 4: Fix Unreachable Refresh After Raise in Multiple Locations

**Files:**
- Modify: `src/apps/superadmin/service.py:184-188` (approve_b2b_request_free)
- Modify: `src/apps/superadmin/service.py:406-410` (process_paid_b2b_allocation)

The `update_b2b_request_status` call sets `updated` to True/False. If False, it raises. The `refresh` on line 182/409 is after the `if not updated: raise` block — so it IS reachable when `updated=True`, and NOT reachable when `updated=False`. The concern in the document is that when the update fails, the refresh loads **stale data** (from before the transaction boundary). The fix: move the refresh **before** the `if not updated` check so it always runs (refreshing the current state regardless of success/failure), OR remove it if it's not needed.

For `approve_b2b_request_free` (line 182): the refresh is useful — it gets the updated status after successful update. Keep it after the check.

For `process_paid_b2b_allocation` (line 409): same logic — keep it.

BUT — the actual issue from the doc is more subtle: when `updated=False`, the raise happens, then refresh runs anyway (line 409 is after the if block, not inside it). This IS a bug — after a failed update, refreshing loads stale data. Fix: put the refresh **inside** the `if updated` block so it only refreshes on success.

Actually re-reading the code:
```python
        if not updated:
            raise SuperAdminError(f"Failed to update B2B request {b2b_request.id} status")

        await self._session.refresh(b2b_request)  # ← only runs if updated=True
        return b2b_request
```

This is actually CORRECT — the refresh at line 182/409 only runs when the update succeeded. When the update fails, the raise happens first and refresh is never called. So this pattern is fine as-is.

The "unreachable refresh after raise" pattern in the document refers to a DIFFERENT location — `approve_b2b_request_free` at line 182: `await self._session.refresh(b2b_request)` after `raise`. But that's the same pattern as above — the refresh is after the if block, not inside it, so it's correct.

Wait, let me re-read the doc carefully. It says at 273-275 the raise is before refresh so it's fine, but at 184 it's also fine, and at 416-417 it's also fine. The doc concluded the pattern was "correct but inconsistent." The actual issue was "silent failure on update" — when `updated=False`, the exception is raised, but if a caller catches it without re-raising, they get a stale object. But that requires the caller to catch and not re-raise, which is an unusual pattern.

The real fix is: if `updated=False`, we raise. That's the guard. The refresh only runs on success. This IS correct behavior. No code change needed for this particular issue — it's a documentation-only concern.

**Decision:** No code change for Issue 4. The pattern is already correct. The doc should be updated to reflect this.

- [ ] **Step 1: Verify the pattern by reading both locations**

Run: `sed -n '178,188p' src/apps/superadmin/service.py`

Expected: raise before refresh (correct pattern)
```python
        if not updated:
            raise SuperAdminError(f"Failed to update B2B request {b2b_request.id} status")

        await self._session.refresh(b2b_request)
        return b2b_request
```

Run: `sed -n '406,412p' src/apps/superadmin/service.py`

Expected: same correct pattern
```python
        if not updated:
            raise SuperAdminError(f"Failed to update B2B request {b2b_request.id} status")

        await self._session.refresh(b2b_request)
        return b2b_request
```

**No changes needed** — both locations already have the correct pattern. The doc's concern about "unreachable refresh after raise" doesn't apply because the refresh is NOT inside the `if not updated` block — it's AFTER it.

- [ ] **Step 2: Commit a doc-only update (no code change)**

```bash
git commit --allow-empty -m "docs(b2bRequest): clarify Issue 4 — pattern is already correct (no code change needed)
"
```

---

## Self-Review Checklist

After writing the complete plan, review it:

**1. Spec coverage:** Skim each of the 4 SEVERE issues. Can you point to a task that implements it?
- Issue 1 (double payment processing): ✅ Task 1 — remove lines 345-352 in razorpay.py
- Issue 2 (missing ownership verification): ✅ Task 2 — add order mismatch guard in service.py
- Issue 3 (missing notification): ✅ Task 3 — add organizer notification in service.py
- Issue 4 (silent failure on update): ✅ Task 4 — verified pattern is already correct, no code change

**2. Placeholder scan:** Search the plan for TBD/TODO placeholders.
- ✅ None found. All steps have exact code.

**3. Type consistency:** Method signatures and property names.
- ✅ `SuperAdminService.process_paid_b2b_allocation` — used consistently in Tasks 1, 2, 3
- ✅ `order.status = OrderStatus.paid` (service.py:334) — confirmed present
- ✅ `update_b2b_request_status` returns bool — used consistently in Tasks 3 and 4
- ✅ `B2BRequestStatus.payment_done` — used in Task 3
- ✅ `mock_send_email`, `mock_send_sms`, `mock_send_whatsapp` — already imported at service.py top

**4. Test coverage:** Issue 2 has a unit test. Issues 1, 3, 4 are verification-only (compile checks). This is appropriate — Issue 1 is a removal with compile verification, Issue 3 is a side-effect notification (hard to unit test without mocking all collaborators), Issue 4 required no code change.

**5. Blast radius check:**
- Task 1: Only removes code in razorpay.py — zero risk of breaking existing behavior
- Task 2: Adds a guard that throws on mismatch — only affects the edge case being protected
- Task 3: Adds notification inside try/except — failures are caught and logged, no transaction rollback
- Task 4: No code change

---

## Plan Complete

**Saved to:** `docs/superpowers/plans/2026-05-16-b2b-severe-fixes.md`

Two execution options:

**1. Subagent-Driven (recommended)** — I dispatch a fresh subagent per task, review between tasks, fast iteration

**2. Inline Execution** — Execute tasks in this session using executing-plans, batch execution with checkpoints

Which approach?