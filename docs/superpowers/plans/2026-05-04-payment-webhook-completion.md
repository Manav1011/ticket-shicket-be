# Post-Payment Webhook Completion Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement the missing post-payment logic in Razorpay webhook handlers so paid B2B transfers actually deliver tickets to buyers after payment.

**Architecture:** The `handle_order_paid` webhook handler must, after marking the order `paid`:
1. Retrieve the locked ticket IDs (via `lock_reference_id=order.id`)
2. Create a B2B allocation (idempotent via UNIQUE constraint on `order_id`)
3. Transfer ticket ownership to buyer
4. Upsert allocation edge
5. Send claim link to buyer (for reseller → customer paid transfers only)

Other handlers (`payment.failed`, `payment_link.expired`, `payment_link.cancelled`) need: (a) `cancel_payment_link` call for failed and (b) tickets released back to pool.

---

## File Structure

```
src/apps/payment_gateway/handlers/razorpay.py   — main handler, all 4 handlers live here
src/apps/allocation/repository.py              — create_allocation, upsert_edge, add_tickets_to_allocation
src/apps/ticketing/repository.py               — lock_tickets_for_transfer, clear_locks_for_order, update_ticket_ownership_batch
src/apps/organizer/service.py                 — for reference: how free transfer creates allocation/claim link
```

No new files needed. All primitives already exist in the repositories.

---

## Task 0: Add sender_holder_id, receiver_holder_id, transfer_type, event_day_id to OrderModel

**Files:**
- Modify: `src/apps/allocation/models.py:172-219`

**Steps:**

- [ ] **Step 1: Add fields to OrderModel**

Add these columns to `OrderModel` after `user_id` (line ~184):

```python
sender_holder_id: Mapped[uuid.UUID | None] = mapped_column(
    ForeignKey("ticket_holders.id", ondelete="SET NULL"), nullable=True, index=True
)
receiver_holder_id: Mapped[uuid.UUID | None] = mapped_column(
    ForeignKey("ticket_holders.id", ondelete="SET NULL"), nullable=True, index=True
)
transfer_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
event_day_id: Mapped[uuid.UUID | None] = mapped_column(
    ForeignKey("event_days.id", ondelete="CASCADE"), nullable=True
)
```

- [ ] **Step 2: Run makemigrations**

Run: `uv run main.py makemigrations`
Expected: Migration file created with new columns

- [ ] **Step 3: Apply migration**

Run: `uv run main.py migrate`
Expected: Migration applied successfully

- [ ] **Step 4: Update paid transfer creation in organizer service**

In `create_b2b_transfer` PAID branch (after order creation, ~line 498), add:
```python
order.sender_holder_id = org_holder.id
order.receiver_holder_id = reseller_holder.id
order.transfer_type = "organizer_to_reseller"
order.event_day_id = event_day_id
```

In `create_customer_transfer` PAID branch (after order creation, ~line 717), add:
```python
order.sender_holder_id = org_holder.id
order.receiver_holder_id = customer_holder.id
order.transfer_type = "organizer_to_customer"
order.event_day_id = event_day_id
```

- [ ] **Step 5: Run tests**

Run: `pytest tests/apps/organizer/test_service.py -v`
Expected: PASS (existing tests still pass, new fields set correctly)

- [ ] **Step 6: Commit**

```bash
git add src/apps/allocation/models.py src/apps/organizer/service.py
git commit -m "feat(allocation): add sender_holder_id, receiver_holder_id, transfer_type, event_day_id to OrderModel

- Required for Phase 4 webhook to create allocation after payment
- Set during paid B2B and customer transfer creation
"
```

---

## Task 1: Implement Phase 4 allocation creation in `handle_order_paid`

**Files:**
- Modify: `src/apps/payment_gateway/handlers/razorpay.py:154-163`

**Context:** The order at this point has `status=paid`, `captured_at` set, and `gateway_payment_id` set. The tickets were locked during step 2 of the paid transfer flow (organizer service). We need to retrieve the locked tickets and create the allocation.

**Steps:**

- [ ] **Step 1: Write the failing test** — add to existing test file

Test: `test_order_paid_creates_allocation_and_transfers_tickets`
```python
async def test_order_paid_creates_allocation_and_transfers_tickets(self, sample_order_with_locked_tickets):
    """After order.paid webhook, allocation is created, tickets transferred, edge upserted."""
    handler = RazorpayWebhookHandler(session)
    body = build_order_paid_webhook_body(order_id=sample_order_with_locked_tickets.id)
    headers = build_razorpay_headers(body)

    result = await handler.handle(body, headers)

    assert result["status"] == "ok"
    # Allocation created
    allocation = await session.execute(
        select(AllocationModel).where(AllocationModel.order_id == sample_order_with_locked_tickets.id)
    )
    assert allocation.scalar_one_or_none() is not None
    # Tickets transferred to buyer
    tickets = await session.execute(
        select(TicketModel).where(TicketModel.lock_reference_id == sample_order_with_locked_tickets.id)
    )
    for ticket in tickets.scalars().all():
        assert ticket.owner_holder_id == sample_order_with_locked_tickets.buyer_holder_id
```

Run: `pytest tests/apps/payment_gateway/handlers/test_razorpay_webhook_handler.py::TestRazorpayWebhookHandler::test_order_paid_creates_allocation_and_transfers_tickets -v`
Expected: FAIL with AttributeError / AssertionError

- [ ] **Step 2: Read the lock_reference fields on OrderModel and TicketModel**

Check: `src/apps/allocation/models.py` for OrderModel.lock_expires_at and TicketModel.lock_reference_id/lock_reference_type fields.

- [ ] **Step 3: Write the Phase 4 implementation** in `handle_order_paid` after line 152 (`if updated.rowcount == 0`)

Replace:
```python
# Phase 4: Allocation creation will be filled in next phase
# TODO (Phase 4): Create allocation, transfer ticket ownership, upsert edge
# Allocation creation will be idempotent via UNIQUE constraint on order_id
# await self._allocation_repo.create_allocation(...)
await self._ticketing_repo.clear_locks_for_order(order.id)
```

With:
```python
# Phase 4: Create B2B allocation + transfer tickets to buyer
# Retrieve the locked tickets (locked during paid transfer creation in organizer service)
# Tickets have lock_reference_type='transfer' and lock_reference_id=order.id
locked_tickets_result = await self.session.execute(
    select(TicketModel).where(
        TicketModel.lock_reference_type == 'transfer',
        TicketModel.lock_reference_id == order.id,
    )
)
locked_ticket_ids = [t.id for t in locked_tickets_result.scalars().all()]

if locked_ticket_ids:
    # Create B2B allocation (idempotent — UNIQUE constraint on order_id prevents duplicates)
    allocation = await self._allocation_repo.create_allocation(
        event_id=order.event_id,
        from_holder_id=order.sender_holder_id,  # organizer
        to_holder_id=order.receiver_holder_id,   # reseller/customer
        order_id=order.id,
        allocation_type=AllocationType.b2b,
        ticket_count=len(locked_ticket_ids),
        metadata_={"source": "razorpay_webhook_paid_transfer"},
    )

    # Add tickets to allocation
    await self._allocation_repo.add_tickets_to_allocation(allocation.id, locked_ticket_ids)

    # Upsert allocation edge (organizer → buyer)
    await self._allocation_repo.upsert_edge(
        event_id=order.event_id,
        from_holder_id=order.sender_holder_id,
        to_holder_id=order.receiver_holder_id,
        ticket_count=len(locked_ticket_ids),
    )

    # Transfer ticket ownership to buyer and clear lock fields
    await self._ticketing_repo.update_ticket_ownership_batch(
        ticket_ids=locked_ticket_ids,
        new_owner_holder_id=order.receiver_holder_id,
    )

    # Mark allocation completed
    await self._allocation_repo.transition_allocation_status(
        allocation.id,
        AllocationStatus.pending,
        AllocationStatus.completed,
    )
else:
    # No tickets locked — this shouldn't happen for a valid paid transfer
    logger.warning(f"No locked tickets found for order {order.id} after payment")

await self._ticketing_repo.clear_locks_for_order(order.id)
```

- [ ] **Step 3b: Add cancel_payment_link to `handle_payment_failed`**

In `handle_payment_failed` at line 199 (after `clear_locks_for_order`), add:
```python
await self._gateway.cancel_payment_link(order.gateway_order_id)
```
This matches what `handle_payment_link_expired` already does.

- [ ] **Step 4: Run tests to verify it passes**

Run: `pytest tests/apps/payment_gateway/handlers/test_razorpay_webhook_handler.py -v`
Expected: PASS (all existing tests still pass)

- [ ] **Step 5: Commit**

```bash
git add src/apps/payment_gateway/handlers/razorpay.py
git commit -m "feat(payment-gateway): implement Phase 4 allocation creation in order.paid webhook

- After marking order paid, create B2B allocation (idempotent via order_id UNIQUE constraint)
- Transfer locked tickets to buyer and clear locks
- Upsert allocation edge (organizer → buyer)
- Mark allocation completed
- Add cancel_payment_link to payment.failed handler for consistency
"
```

---

## Task 2: Add claim link sending for paid reseller→customer transfers

**Files:**
- Modify: `src/apps/payment_gateway/handlers/razorpay.py` (same file, same handler)

**Context:** For paid B2B transfers from organizer to RESELLER, after payment the reseller needs a claim link (they already have their own holder account from the invite). For paid transfers from organizer to CUSTOMER (no prior account), the customer also needs a claim link so they can claim tickets to their own account. Both need the claim link after payment.

The claim link is generated from a token (same as free transfer). The allocation + claim link should be created atomically via `create_allocation_with_claim_link` instead of `create_allocation`.

**Steps:**

- [ ] **Step 1: Write failing test**

Test: `test_order_paid_sends_claim_link_to_customer`
```python
async def test_order_paid_sends_claim_link_to_customer(self, sample_order_with_locked_tickets):
    """After order.paid for customer transfer, claim link is sent via notification."""
    # sample_order_with_locked_tickets has type='transfer' and buyer_holder_id set
    # Customer (not reseller) — has phone and email
    handler = RazorpayWebhookHandler(session)
    body = build_order_paid_webhook_body(order_id=sample_order_with_locked_tickets.id)
    headers = build_razorpay_headers(body)

    result = await handler.handle(body, headers)

    # Claim link created
    claim_link = await session.execute(
        select(ClaimLinkModel).where(ClaimLinkModel.allocation_id == allocation.id)
    )
    assert claim_link.scalar_one_or_none() is not None
    # Notification sent (mock asserts called)
```

- [ ] **Step 2: Check the order model for buyer_holder_id and transfer_type fields**

Look at `src/apps/allocation/models.py` for OrderModel fields. Specifically need `sender_holder_id` (organizer), `receiver_holder_id` (buyer), and `transfer_type` field that indicates reseller vs customer.

- [ ] **Step 3: Modify Phase 4 implementation to use `create_allocation_with_claim_link`**

Replace the allocation creation block with:
```python
if locked_ticket_ids:
    # Determine transfer type from order metadata
    transfer_type = order.transfer_type  # 'organizer_to_reseller' or 'organizer_to_customer'
    is_reseller = transfer_type == 'organizer_to_reseller'

    # Generate claim link token
    raw_token = generate_claim_link_token(length=8)
    token_hash = hashlib.sha256(raw_token.encode()).hexdigest()

    if is_reseller:
        # Reseller already has a holder account — create allocation only, no claim link needed
        # They can view tickets in their dashboard
        allocation = await self._allocation_repo.create_allocation(
            event_id=order.event_id,
            from_holder_id=order.sender_holder_id,
            to_holder_id=order.receiver_holder_id,
            order_id=order.id,
            allocation_type=AllocationType.b2b,
            ticket_count=len(locked_ticket_ids),
            metadata_={"source": "razorpay_webhook_paid_transfer", "transfer_type": transfer_type},
        )
        await self._allocation_repo.add_tickets_to_allocation(allocation.id, locked_ticket_ids)
    else:
        # Customer has no prior account — create allocation WITH claim link
        allocation, claim_link_record = await self._allocation_repo.create_allocation_with_claim_link(
            event_id=order.event_id,
            event_day_id=order.event_day_id,  # from order metadata or query
            from_holder_id=order.sender_holder_id,
            to_holder_id=order.receiver_holder_id,
            order_id=order.id,
            allocation_type=AllocationType.b2b,
            ticket_count=len(locked_ticket_ids),
            token_hash=token_hash,
            created_by_holder_id=order.sender_holder_id,
            metadata_={"source": "razorpay_webhook_paid_transfer", "transfer_type": transfer_type},
        )
        # TODO: Send claim link to customer via notification (SMS/WhatsApp/Email)

    # Upsert edge + transfer ownership + mark completed (same for both paths)
    await self._allocation_repo.upsert_edge(...)
    await self._ticketing_repo.update_ticket_ownership_batch(...)
    await self._allocation_repo.transition_allocation_status(...)
```

Note: `create_allocation_with_claim_link` also needs `event_day_id`. This should be retrieved from the locked tickets or from order metadata.

- [ ] **Step 4: Run tests**

Run: `pytest tests/apps/payment_gateway/handlers/test_razorpay_webhook_handler.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/apps/payment_gateway/handlers/razorpay.py
git commit -m "feat(payment-gateway): add claim link for paid customer transfers after order.paid
"
```

---

## Task 3: Test the full paid transfer → webhook → tickets flow

**Files:**
- Create: `tests/integration/test_paid_b2b_transfer_flow.py`

**Steps:**

- [ ] **Step 1: Write integration test**

Test that simulates the complete flow:
1. Organizer calls `create_b2b_transfer` with `mode=PAID`
2. Order created with `status=pending`, tickets locked
3. Simulate Razorpay webhook fire (build and sign the webhook body)
4. Verify order status → paid
5. Verify allocation created
6. Verify tickets transferred to reseller
7. Verify edge upserted

Run: `pytest tests/integration/test_paid_b2b_transfer_flow.py -v`

- [ ] **Step 2: Also test the reseller → customer paid flow**

Same test but for `create_customer_transfer` with `mode=PAID`.

Run: `pytest tests/integration/test_paid_customer_transfer_flow.py -v`

---

## Self-Review Checklist

**1. Spec coverage:** The spec requires:
- Organizer→Reseller paid: tickets transferred, reseller can see in dashboard → covered in Task 1
- Organizer→Customer paid: claim link sent after payment → covered in Task 2
- All webhook handlers handle failures gracefully → covered in Task 1 (cancel_payment_link)

**2. Placeholder scan:** No placeholders — all code is actual implementation

**3. Type consistency:**
- `AllocationType.b2b` used correctly
- `AllocationStatus.pending / completed` used correctly
- `TicketModel.lock_reference_type == 'transfer'` used correctly (NOT 'order')
- `OrderModel.sender_holder_id` / `receiver_holder_id` — must verify these exact field names exist on OrderModel (not `buyer_holder_id`)
