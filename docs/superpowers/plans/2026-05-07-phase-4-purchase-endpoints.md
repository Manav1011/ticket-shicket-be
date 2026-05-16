# Phase 4: Purchase Endpoints — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the `purchase` endpoints inside `src/apps/event/` — preview, create order, and poll status. These are used by the frontend to enable online ticket purchase via Razorpay Checkout.

**Architecture:** Purchase service lives inside the events app (per spec §7 note). Three endpoints: preview (no side effects), create (locks tickets + creates order + calls Razorpay), poll (returns status + jwt when paid). `create_order` acquires locks BEFORE creating the order to prevent over-selling; if order creation fails, locks are released via `clear_locks_for_order`.

**Tech Stack:** FastAPI, SQLAlchemy async, Pydantic, Razorpay Checkout API, JWT.

---

## File Map

| Action | File |
|--------|------|
| Modify | `src/apps/event/service.py` — add `PurchaseService` class with `preview_order`, `create_order`, `poll_order_status` |
| Modify | `src/apps/event/request.py` — add `PreviewOrderRequest`, `CreateOrderRequest` |
| Modify | `src/apps/event/response.py` — add `PreviewOrderResponse`, `CreateOrderResponse`, `PollStatusResponse` |
| Modify | `src/apps/event/urls.py` — add purchase routes and `get_purchase_service` factory |

**Important context:**
- `CouponRepository` already exists at `apps/allocation/repository.py` (Phase 1)
- `calculate_discount` and `validate_coupon` already exist on `PurchaseService` in `event/service.py` (Phase 1)
- `AllocationRepository` already has `get_holder_by_user_id` and `resolve_holder` (Phase 1)
- `GatewayType.RAZORPAY_ORDER` already defined in `allocation/enums.py`
- `OrderStatus` already defined in `ticketing/enums.py`
- `generate_scan_jwt` already exists in `utils/jwt_utils.py`
- `lock_tickets_for_purchase` already exists in `TicketingRepository` (Phase 3)
- `clear_locks_for_order` already exists in `TicketingRepository` (Phase 3)
- `ClaimLinkRepository` already has `get_active_by_to_holder` method

**Schema addition needed:** `ClaimLinkModel.token` — add a `token` column (String, nullable) to store the raw claim token alongside `token_hash`. This lets `poll_order_status` return `claim_url`. Phase 5's webhook will populate this field when creating the claim link. Add via inline column addition in Task 5 (no full migration needed for dev).

---

## Context: Existing Infrastructure

### OrderModel fields used in purchase flow
```
event_id, user_id, type=PURCHASE, gateway_type=RAZORPAY_ORDER,
receiver_holder_id, sender_holder_id=None, event_day_id,
subtotal_amount, discount_amount, final_amount,
status (pending/paid/failed/expired),
lock_expires_at, gateway_order_id, gateway_response
```

### Lock flow for create_order
1. `lock_tickets_for_purchase(event_id, event_day_id, ticket_type_id, qty, order_id)` → sets `lock_reference_type='order'`, `lock_reference_id=order_id`, `lock_expires_at=now+30min`
2. Create `OrderModel` with `status=pending`
3. Call `razorpay.create_checkout_order(order_id, amount_paise, "INR", event_id)` → returns `gateway_order_id`
4. If any step fails → `clear_locks_for_order(order_id)`

### poll_status — claim_url generation
When order is `paid`, look up `ClaimLink` via `order.receiver_holder_id`. The claim_url format is `/claim/{raw_token}` where `raw_token` is reconstructed from the claim link's token_hash (the public claim endpoint at `/claim/{token}` looks up by token_hash, so passing token_hash as the URL segment works).

---

## Tasks

### Task 1: Add Request Schemas

**Files:**
- Modify: `src/apps/event/request.py` — add schemas at end of file

- [ ] **Step 1: Add request schemas**

Add after the existing request classes in `event/request.py`:

```python
class PreviewOrderRequest(CamelCaseModel):
    event_id: UUID
    event_day_id: UUID
    ticket_type_id: UUID
    quantity: int = Field(ge=1)
    coupon_code: str | None = None


class CreateOrderRequest(CamelCaseModel):
    event_id: UUID
    event_day_id: UUID
    ticket_type_id: UUID
    quantity: int = Field(ge=1)
    coupon_code: str | None = None
```

- [ ] **Step 2: Commit**

```bash
git add src/apps/event/request.py
git commit -m "feat(purchase): add PreviewOrderRequest and CreateOrderRequest schemas"
```

---

### Task 2: Add Response Schemas

**Files:**
- Modify: `src/apps/event/response.py` — add schemas at end of file

- [ ] **Step 1: Add response schemas**

Add after the existing response classes in `event/response.py`:

```python
class CouponAppliedResponse(CamelCaseModel):
    code: str
    type: str
    value: float
    max_discount: float | None


class PreviewOrderResponse(CamelCaseModel):
    subtotal_amount: str
    discount_amount: str
    final_amount: str
    coupon_applied: CouponAppliedResponse | None


class CreateOrderResponse(CamelCaseModel):
    order_id: UUID
    razorpay_order_id: str
    razorpay_key_id: str
    amount: int
    currency: str
    subtotal_amount: str
    discount_amount: str
    final_amount: str
    status: str


class PollStatusResponse(CamelCaseModel):
    order_id: UUID
    status: str
    ticket_count: int
    jwt: str | None = None
    claim_url: str | None = None
    failure_reason: str | None = None
```

- [ ] **Step 2: Commit**

```bash
git add src/apps/event/response.py
git commit -m "feat(purchase): add PreviewOrderResponse, CreateOrderResponse, PollStatusResponse schemas"
```

---

### Task 3: Add PurchaseService Methods

**Files:**
- Modify: `src/apps/event/service.py` — add methods to `PurchaseService` class

- [ ] **Step 1: Write failing tests for `preview_order`**

Create `tests/test_purchase_service.py`:

```python
import pytest
from uuid import uuid4
from datetime import datetime, timezone
from apps.ticketing.models import TicketModel, TicketTypeModel, DayTicketAllocationModel
from apps.ticketing.enums import TicketCategory
from apps.allocation.models import CouponModel, OrderModel
from apps.allocation.enums import CouponType, GatewayType, OrderType, OrderStatus
from apps.allocation.repository import CouponRepository
from apps.event.service import PurchaseService


@pytest.fixture
async def purchase_service(db_session):
    from apps.event.repository import EventRepository
    return PurchaseService(
        coupon_repository=CouponRepository(db_session),
        repository=EventRepository(db_session),
    )


@pytest.fixture
async def published_event_setup(db_session, test_event):
    """Published event with ticket type, allocation, and 5 pool tickets."""
    # Set event to published state (required for purchase)
    test_event.is_published = True
    test_event.status = "published"
    await db_session.flush()

    from apps.event.models import EventDayModel
    day = EventDayModel(
        id=uuid4(),
        event_id=test_event.id,
        day_index=1,
        date=datetime(2026, 6, 15).date(),
    )
    db_session.add(day)

    ticket_type = TicketTypeModel(
        id=uuid4(),
        event_id=test_event.id,
        name="General Admission",
        category=TicketCategory.public,
        price=499.0,
        currency="INR",
    )
    db_session.add(ticket_type)

    allocation = DayTicketAllocationModel(
        id=uuid4(),
        event_day_id=day.id,
        ticket_type_id=ticket_type.id,
        quantity=5,
    )
    db_session.add(allocation)

    tickets = [
        TicketModel(
            id=uuid4(),
            event_id=test_event.id,
            event_day_id=day.id,
            ticket_type_id=ticket_type.id,
            ticket_index=i,
            owner_holder_id=None,
            status="active",
        )
        for i in range(5)
    ]
    db_session.add_all(tickets)
    await db_session.flush()
    return {
        "event": test_event,
        "day": day,
        "ticket_type": ticket_type,
        "tickets": tickets,
    }


@pytest.mark.asyncio
async def test_preview_order_returns_price_breakdown(published_event_setup, purchase_service):
    """Preview returns subtotal, discount, final without creating an order."""
    result = await purchase_service.preview_order(
        event_id=published_event_setup["event"].id,
        event_day_id=published_event_setup["day"].id,
        ticket_type_id=published_event_setup["ticket_type"].id,
        quantity=2,
        coupon_code=None,
    )
    assert result["subtotal_amount"] == "998.00"
    assert result["discount_amount"] == "0.00"
    assert result["final_amount"] == "998.00"
    assert result["coupon_applied"] is None


@pytest.mark.asyncio
async def test_preview_order_with_coupon(published_event_setup, purchase_service, db_session):
    """Preview applies a valid FLAT coupon."""
    coupon = CouponModel(
        id=uuid4(),
        code="FLAT100",
        type=CouponType.FLAT,
        value=100.0,
        max_discount=None,
        min_order_amount=0.0,
        usage_limit=100,
        per_user_limit=10,
        used_count=0,
        valid_from=datetime(2026, 1, 1, tzinfo=timezone.utc),
        valid_until=datetime(2026, 12, 31, tzinfo=timezone.utc),
        is_active=True,
    )
    db_session.add(coupon)
    await db_session.flush()

    result = await purchase_service.preview_order(
        event_id=published_event_setup["event"].id,
        event_day_id=published_event_setup["day"].id,
        ticket_type_id=published_event_setup["ticket_type"].id,
        quantity=2,
        coupon_code="FLAT100",
    )
    assert result["subtotal_amount"] == "998.00"
    assert result["discount_amount"] == "100.00"
    assert result["final_amount"] == "898.00"
    assert result["coupon_applied"]["code"] == "FLAT100"


@pytest.mark.asyncio
async def test_preview_order_quantity_exceeds_available(published_event_setup, purchase_service):
    """Preview raises BadRequestError when quantity > available pool."""
    from exceptions import BadRequestError
    with pytest.raises(BadRequestError) as exc_info:
        await purchase_service.preview_order(
            event_id=published_event_setup["event"].id,
            event_day_id=published_event_setup["day"].id,
            ticket_type_id=published_event_setup["ticket_type"].id,
            quantity=10,  # only 5 in pool
            coupon_code=None,
        )
    assert "Only 5 tickets available" in str(exc_info.value)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_purchase_service.py::test_preview_order_returns_price_breakdown -v`
Expected: FAIL — `preview_order` method not defined

- [ ] **Step 3: Implement `preview_order` in `PurchaseService`**

Add to the existing `PurchaseService` class in `event/service.py`. The class already exists with `calculate_discount` and `validate_coupon` from Phase 1.

**First, update `__init__`** to accept `repository` (EventRepository) in addition to `coupon_repository`:

```python
def __init__(self, coupon_repository: CouponRepository, repository: EventRepository) -> None:
    self._coupon_repo = coupon_repository
    self.repository = repository
```

Then add the new methods:

```python
async def preview_order(
    self,
    event_id: UUID,
    event_day_id: UUID,
    ticket_type_id: UUID,
    quantity: int,
    coupon_code: str | None = None,
) -> dict:
    """
    Validate and return price breakdown without creating an order or locking tickets.
    Raises BadRequestError if validation fails.
    """
    from apps.ticketing.repository import TicketingRepository
    from apps.allocation.repository import AllocationRepository
    from apps.event.models import EventModel, EventDayModel
    from sqlalchemy import select
    from exceptions import BadRequestError

    # Validate event exists and is published
    event_result = await self.repository.session.execute(
        select(EventModel).where(EventModel.id == event_id)
    )
    event = event_result.scalar_one_or_none()
    if not event:
        raise BadRequestError("Event not found")
    if not event.is_published or event.status != "published":
        raise BadRequestError("Event is not available for purchase")

    # Validate event_day belongs to event
    day_result = await self.repository.session.execute(
        select(EventDayModel).where(
            EventDayModel.id == event_day_id,
            EventDayModel.event_id == event_id,
        )
    )
    day = day_result.scalar_one_or_none()
    if not day:
        raise BadRequestError("Event day not found")

    # Validate ticket_type belongs to event
    ticket_type_repo = TicketingRepository(self.repository.session)
    ticket_type = await ticket_type_repo.get_ticket_type_for_event(ticket_type_id, event_id)
    if not ticket_type:
        raise BadRequestError("Ticket type not found")

    # Check pool availability
    available_count = await self._count_available_pool_tickets(
        event_id, event_day_id, ticket_type_id
    )
    if quantity > available_count:
        raise BadRequestError(f"Only {available_count} tickets available, requested {quantity}")

    # Calculate pricing
    subtotal = float(ticket_type.price) * quantity
    coupon_applied = None
    discount = 0.0

    if coupon_code:
        coupon = await self.validate_coupon(coupon_code, subtotal)
        discount = self.calculate_discount(coupon, subtotal)
        coupon_applied = {
            "code": coupon.code,
            "type": coupon.type.value if hasattr(coupon.type, 'value') else coupon.type,
            "value": float(coupon.value),
            "max_discount": float(coupon.max_discount) if coupon.max_discount else None,
        }

    final = subtotal - discount

    return {
        "subtotal_amount": f"{subtotal:.2f}",
        "discount_amount": f"{discount:.2f}",
        "final_amount": f"{final:.2f}",
        "coupon_applied": coupon_applied,
    }


async def _count_available_pool_tickets(
    self,
    event_id: UUID,
    event_day_id: UUID,
    ticket_type_id: UUID,
) -> int:
    """Count pool tickets that are available for purchase (not owned, not locked)."""
    from apps.ticketing.models import TicketModel
    from sqlalchemy import select, func

    result = await self.repository.session.execute(
        select(func.count(TicketModel.id)).where(
            TicketModel.event_id == event_id,
            TicketModel.event_day_id == event_day_id,
            TicketModel.ticket_type_id == ticket_type_id,
            TicketModel.owner_holder_id.is_(None),
            TicketModel.lock_reference_id.is_(None),
        )
    )
    return result.scalar_one()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_purchase_service.py::test_preview_order_returns_price_breakdown tests/test_purchase_service.py::test_preview_order_with_coupon tests/test_purchase_service.py::test_preview_order_quantity_exceeds_available -v`
Expected: PASS

- [ ] **Step 5: Write failing tests for `create_order`**

Add to `tests/test_purchase_service.py`:

```python
@pytest.fixture
async def buyer_holder(db_session, test_user):
    """TicketHolder for the buying user."""
    from apps.allocation.models import TicketHolderModel
    holder = TicketHolderModel(
        id=uuid4(),
        user_id=test_user.id,
        email="buyer@example.com",
        status="active",
    )
    db_session.add(holder)
    await db_session.flush()
    return holder


@pytest.mark.asyncio
async def test_create_order_happy_path(published_event_setup, buyer_holder, purchase_service, db_session, test_user):
    """create_order creates order and returns razorpay details."""
    from apps.ticketing.repository import TicketingRepository
    from apps.allocation.models import OrderModel
    from apps.allocation.enums import OrderStatus
    from apps.payment_gateway.services.base import CheckoutOrderResult
    from unittest.mock import AsyncMock, patch

    order_id = uuid4()

    with patch.object(TicketingRepository, 'lock_tickets_for_purchase', new_callable=AsyncMock) as mock_lock:
        mock_lock.return_value = [t.id for t in published_event_setup["tickets"][:2]]

        with patch('apps.event.service.get_gateway', new_callable=AsyncMock) as mock_gateway:
            mock_gateway.return_value.create_checkout_order = AsyncMock(return_value=CheckoutOrderResult(
                gateway_order_id="razorpay_order_123",
                amount=99800,
                currency="INR",
                key_id="rzp_test_xxx",
                gateway_response={},
            ))

            result = await purchase_service.create_order(
                user_id=test_user.id,
                event_id=published_event_setup["event"].id,
                event_day_id=published_event_setup["day"].id,
                ticket_type_id=published_event_setup["ticket_type"].id,
                quantity=2,
                coupon_code=None,
                order_id=order_id,
            )

    assert result["order_id"] == order_id
    assert result["razorpay_order_id"] == "razorpay_order_123"
    assert result["status"] == "pending"

    # Verify order was created in DB
    await db_session.expire_all()
    order = await db_session.get(OrderModel, order_id)
    assert order.status == OrderStatus.pending
    assert order.type == OrderType.purchase
    assert order.gateway_type.value == "razorpay_order"


@pytest.mark.asyncio
async def test_create_order_locks_are_cleared_on_failure(published_event_setup, buyer_holder, purchase_service, db_session, test_user):
    """If order creation fails after locking, locks are released."""
    from apps.ticketing.repository import TicketingRepository
    from unittest.mock import AsyncMock, patch

    order_id = uuid4()

    with patch.object(TicketingRepository, 'lock_tickets_for_purchase', new_callable=AsyncMock) as mock_lock:
        mock_lock.return_value = [t.id for t in published_event_setup["tickets"][:2]]

        # Simulate gateway failure
        with patch('apps.event.service.get_gateway', new_callable=AsyncMock) as mock_gateway:
            mock_gateway.return_value.create_checkout_order = AsyncMock(side_effect=Exception("Razorpay error"))

            with patch.object(TicketingRepository, 'clear_locks_for_order', new_callable=AsyncMock) as mock_clear:
                with pytest.raises(Exception):
                    await purchase_service.create_order(
                        user_id=test_user.id,
                        event_id=published_event_setup["event"].id,
                        event_day_id=published_event_setup["day"].id,
                        ticket_type_id=published_event_setup["ticket_type"].id,
                        quantity=2,
                        coupon_code=None,
                        order_id=order_id,
                    )

                # Verify locks were cleared after failure
                mock_clear.assert_called_once_with(order_id)
```

- [ ] **Step 6: Run create_order tests to verify they fail**

Run: `pytest tests/test_purchase_service.py::test_create_order_happy_path -v`
Expected: FAIL — `create_order` method not defined

- [ ] **Step 7: Implement `create_order` in `PurchaseService`**

Add to `PurchaseService` class:

```python
async def create_order(
    self,
    user_id: UUID,
    event_id: UUID,
    event_day_id: UUID,
    ticket_type_id: UUID,
    quantity: int,
    coupon_code: str | None = None,
    order_id: UUID | None = None,
) -> dict:
    """
    Create a purchase order: validate → resolve buyer holder → lock tickets →
    create order → call Razorpay → return razorpay checkout details.

    If order creation fails after locking, clears locks before re-raising.

    Raises BadRequestError on validation failure.
    Raises exception on gateway/DB failure (after cleanup).
    """
    import uuid as uuid_lib
    from apps.ticketing.repository import TicketingRepository
    from apps.allocation.models import OrderModel, OrderCouponModel
    from apps.allocation.enums import GatewayType, OrderType, OrderStatus
    from apps.allocation.repository import AllocationRepository
    from apps.payment_gateway.services.factory import get_gateway
    from apps.ticketing.enums import TicketCategory
    from sqlalchemy import select
    from exceptions import BadRequestError

    if order_id is None:
        order_id = uuid_lib.uuid4()

    # Validate event (published)
    event_result = await self.repository.session.execute(
        select(EventModel).where(EventModel.id == event_id)
    )
    event = event_result.scalar_one_or_none()
    if not event:
        raise BadRequestError("Event not found")
    if not event.is_published or event.status != "published":
        raise BadRequestError("Event is not available for purchase")

    # Validate event_day
    day_result = await self.repository.session.execute(
        select(EventDayModel).where(
            EventDayModel.id == event_day_id,
            EventDayModel.event_id == event_id,
        )
    )
    day = day_result.scalar_one_or_none()
    if not day:
        raise BadRequestError("Event day not found")

    # Validate ticket_type (must be public/online category)
    ticketing_repo = TicketingRepository(self.repository.session)
    ticket_type = await ticketing_repo.get_ticket_type_for_event(ticket_type_id, event_id)
    if not ticket_type:
        raise BadRequestError("Ticket type not found")
    if ticket_type.category == TicketCategory.b2b:
        raise BadRequestError("Cannot purchase B2B ticket type directly")
    if ticket_type.category == TicketCategory.public or ticket_type.category == TicketCategory.online or ticket_type.category == TicketCategory.vip:
        pass  # allowed

    # Resolve buyer TicketHolder
    allocation_repo = AllocationRepository(self.repository.session)
    buyer_holder = await allocation_repo.resolve_holder(user_id=user_id)

    # Validate coupon and calculate discount (if provided)
    subtotal = float(ticket_type.price) * quantity
    discount = 0.0
    coupon_record = None
    coupon_applied_info = None

    if coupon_code:
        coupon_record = await self.validate_coupon(coupon_code, subtotal)
        discount = self.calculate_discount(coupon_record, subtotal)
        coupon_applied_info = {
            "code": coupon_record.code,
            "type": coupon_record.type.value if hasattr(coupon_record.type, 'value') else coupon_record.type,
            "value": float(coupon_record.value),
            "max_discount": float(coupon_record.max_discount) if coupon_record.max_discount else None,
        }

    final_amount = subtotal - discount

    # Lock tickets BEFORE creating order (prevents over-selling)
    locked_ticket_ids = await ticketing_repo.lock_tickets_for_purchase(
        event_id=event_id,
        event_day_id=event_day_id,
        ticket_type_id=ticket_type_id,
        quantity=quantity,
        order_id=order_id,
        lock_ttl_minutes=30,
    )

    try:
        # Create OrderModel
        order = OrderModel(
            id=order_id,
            event_id=event_id,
            user_id=user_id,
            receiver_holder_id=buyer_holder.id,
            sender_holder_id=None,
            event_day_id=event_day_id,
            type=OrderType.purchase,
            subtotal_amount=subtotal,
            discount_amount=discount,
            final_amount=final_amount,
            status=OrderStatus.pending,
            lock_expires_at=datetime.utcnow() + timedelta(minutes=30),
            gateway_type=GatewayType.RAZORPAY_ORDER,
        )
        self.repository.session.add(order)

        # Save coupon application
        if coupon_record and discount > 0:
            order_coupon = OrderCouponModel(
                order_id=order_id,
                coupon_id=coupon_record.id,
                discount_applied=discount,
            )
            self.repository.session.add(order_coupon)

        await self.repository.session.flush()

        # Call Razorpay to create checkout order
        gateway = get_gateway("razorpay")
        razorpay_result = await gateway.create_checkout_order(
            order_id=order_id,
            amount=int(final_amount * 100),  # paise
            currency=ticket_type.currency or "INR",
            event_id=event_id,
        )

        # Update order with gateway order_id
        order.gateway_order_id = razorpay_result.gateway_order_id
        order.gateway_response = razorpay_result.gateway_response
        await self.repository.session.flush()

        return {
            "order_id": order_id,
            "razorpay_order_id": razorpay_result.gateway_order_id,
            "razorpay_key_id": razorpay_result.key_id,
            "amount": razorpay_result.amount,
            "currency": razorpay_result.currency,
            "subtotal_amount": f"{subtotal:.2f}",
            "discount_amount": f"{discount:.2f}",
            "final_amount": f"{final_amount:.2f}",
            "status": "pending",
        }

    except Exception as e:
        # Clear locks before re-raising — order creation failed
        await ticketing_repo.clear_locks_for_order(order_id)
        raise e
```

- [ ] **Step 8: Run create_order tests to verify they pass**

Run: `pytest tests/test_purchase_service.py::test_create_order_happy_path tests/test_purchase_service.py::test_create_order_locks_are_cleared_on_failure -v`
Expected: PASS

- [ ] **Step 9: Write failing tests for `poll_order_status`**

Add to `tests/test_purchase_service.py`:

```python
@pytest.mark.asyncio
async def test_poll_status_pending(published_event_setup, buyer_holder, purchase_service, db_session, test_user):
    """Poll returns pending status with ticket count."""
    from apps.allocation.models import OrderModel
    from apps.allocation.enums import OrderStatus, OrderType, GatewayType

    order = OrderModel(
        id=uuid4(),
        event_id=published_event_setup["event"].id,
        user_id=test_user.id,
        receiver_holder_id=buyer_holder.id,
        event_day_id=published_event_setup["day"].id,
        type=OrderType.purchase,
        subtotal_amount=998.0,
        discount_amount=0.0,
        final_amount=998.0,
        status=OrderStatus.pending,
        gateway_type=GatewayType.RAZORPAY_ORDER,
    )
    db_session.add(order)
    await db_session.flush()

    result = await purchase_service.poll_order_status(order.id, test_user.id)
    assert result["status"] == "pending"
    assert result["ticket_count"] == 0
    assert result["jwt"] is None
    assert result["claim_url"] is None


@pytest.mark.asyncio
async def test_poll_status_paid_returns_jwt_and_claim_url(published_event_setup, buyer_holder, purchase_service, db_session, test_user):
    """Poll returns paid status with jwt and claim_url."""
    from apps.allocation.models import OrderModel, AllocationModel, ClaimLinkModel
    from apps.allocation.enums import OrderStatus, OrderType, GatewayType, AllocationType, ClaimLinkStatus
    import hashlib

    order = OrderModel(
        id=uuid4(),
        event_id=published_event_setup["event"].id,
        user_id=test_user.id,
        receiver_holder_id=buyer_holder.id,
        event_day_id=published_event_setup["day"].id,
        type=OrderType.purchase,
        subtotal_amount=998.0,
        discount_amount=0.0,
        final_amount=998.0,
        status=OrderStatus.paid,
        gateway_type=GatewayType.RAZORPAY_ORDER,
    )
    db_session.add(order)

    allocation = AllocationModel(
        id=uuid4(),
        event_id=published_event_setup["event"].id,
        to_holder_id=buyer_holder.id,
        order_id=order.id,
        allocation_type=AllocationType.purchase,
        ticket_count=2,
        status="completed",
    )
    db_session.add(allocation)

    raw_token = "abc123xy"
    token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
    claim_link = ClaimLinkModel(
        id=uuid4(),
        allocation_id=allocation.id,
        token=raw_token,  # raw token for URL; token_hash is stored separately
        token_hash=token_hash,
        event_id=published_event_setup["event"].id,
        event_day_id=published_event_setup["day"].id,
        to_holder_id=buyer_holder.id,
        status=ClaimLinkStatus.active,
        created_by_holder_id=buyer_holder.id,
        jwt_jti="jti_abc123",
    )
    db_session.add(claim_link)
    await db_session.flush()

    result = await purchase_service.poll_order_status(order.id, test_user.id)
    assert result["status"] == "paid"
    assert result["ticket_count"] == 2
    assert result["jwt"] is not None
    assert result["claim_url"] == f"/claim/{raw_token}"


@pytest.mark.asyncio
async def test_poll_status_forbidden_for_other_user(published_event_setup, purchase_service, db_session):
    """Poll returns 403 if order belongs to a different user."""
    from apps.allocation.models import OrderModel
    from apps.allocation.enums import OrderStatus, OrderType, GatewayType
    from exceptions import ForbiddenError

    other_user_id = uuid4()
    order = OrderModel(
        id=uuid4(),
        event_id=published_event_setup["event"].id,
        user_id=other_user_id,
        receiver_holder_id=uuid4(),
        event_day_id=published_event_setup["day"].id,
        type=OrderType.purchase,
        subtotal_amount=998.0,
        discount_amount=0.0,
        final_amount=998.0,
        status=OrderStatus.pending,
        gateway_type=GatewayType.RAZORPAY_ORDER,
    )
    db_session.add(order)
    await db_session.flush()

    with pytest.raises(ForbiddenError):
        await purchase_service.poll_order_status(order.id, test_user.id)
```

- [ ] **Step 10: Run poll_order_status tests to verify they fail**

Run: `pytest tests/test_purchase_service.py::test_poll_status_pending -v`
Expected: FAIL — `poll_order_status` method not defined

- [ ] **Step 11: Implement `poll_order_status` in `PurchaseService`**

Add to `PurchaseService` class:

```python
async def poll_order_status(
    self,
    order_id: UUID,
    user_id: UUID,
) -> dict:
    """
    Poll order status for a purchase order.
    Returns status + jwt + claim_url when paid.

    Raises ForbiddenError if order does not belong to user.
    Raises NotFoundError if order not found.
    """
    from apps.allocation.models import OrderModel, AllocationModel, ClaimLinkModel
    from apps.allocation.enums import OrderStatus, AllocationType, ClaimLinkStatus
    from sqlalchemy import select
    from exceptions import ForbiddenError, NotFoundError
    from utils.jwt_utils import generate_scan_jwt

    # Fetch order
    result = await self.repository.session.execute(
        select(OrderModel).where(OrderModel.id == order_id)
    )
    order = result.scalar_one_or_none()
    if not order:
        raise NotFoundError(f"Order {order_id} not found")

    # Verify ownership
    if order.user_id != user_id:
        raise ForbiddenError("You do not have access to this order")

    status = order.status.value if hasattr(order.status, 'value') else order.status

    if status == OrderStatus.pending.value:
        return {
            "order_id": order_id,
            "status": "pending",
            "ticket_count": 0,
            "jwt": None,
            "claim_url": None,
            "failure_reason": None,
        }

    elif status == OrderStatus.failed.value:
        return {
            "order_id": order_id,
            "status": "failed",
            "ticket_count": 0,
            "jwt": None,
            "claim_url": None,
            "failure_reason": order.failure_reason or "Payment failed or was rejected",
        }

    elif status == OrderStatus.expired.value:
        return {
            "order_id": order_id,
            "status": "expired",
            "ticket_count": 0,
            "jwt": None,
            "claim_url": None,
            "failure_reason": None,
        }

    elif status == OrderStatus.paid.value:
        # Find the allocation for this order
        alloc_result = await self.repository.session.execute(
            select(AllocationModel).where(
                AllocationModel.order_id == order_id,
                AllocationModel.allocation_type == AllocationType.purchase,
            )
        )
        allocation = alloc_result.scalar_one_or_none()

        ticket_count = allocation.ticket_count if allocation else 0
        jwt = None
        claim_url = None

        if allocation:
            # Find the claim link for this allocation
            claim_result = await self.repository.session.execute(
                select(ClaimLinkModel).where(
                    ClaimLinkModel.allocation_id == allocation.id,
                    ClaimLinkModel.status == ClaimLinkStatus.active,
                )
            )
            claim_link = claim_result.scalar_one_or_none()

            if claim_link and claim_link.jwt_jti:
                # Generate scan JWT
                jwt = generate_scan_jwt(
                    jti=claim_link.jwt_jti,
                    holder_id=order.receiver_holder_id,
                    event_day_id=order.event_day_id,
                    indexes=[],  # Indexes not needed for purchase allocation
                )
                # claim_url uses the raw token stored in claim_link.token (Phase 5)
                # Phase 5 webhook must store raw_token in ClaimLinkModel.token when creating the link
                claim_url = f"/claim/{claim_link.token}" if claim_link.token else None

        return {
            "order_id": order_id,
            "status": "paid",
            "ticket_count": ticket_count,
            "jwt": jwt,
            "claim_url": claim_url,
            "failure_reason": None,
        }

    # Unknown status
    return {
        "order_id": order_id,
        "status": status,
        "ticket_count": 0,
        "jwt": None,
        "claim_url": None,
        "failure_reason": None,
    }
```

- [ ] **Step 12: Run poll_order_status tests to verify they pass**

Run: `pytest tests/test_purchase_service.py::test_poll_status_pending tests/test_purchase_service.py::test_poll_status_paid_returns_jwt_and_claim_url tests/test_purchase_service.py::test_poll_status_forbidden_for_other_user -v`
Expected: PASS

- [ ] **Step 13: Commit**

```bash
git add src/apps/event/service.py tests/test_purchase_service.py
git commit -m "feat(purchase): add PurchaseService with preview_order, create_order, poll_order_status"
```

---

### Task 4: Add Purchase Routes

**Files:**
- Modify: `src/apps/event/urls.py` — add purchase router and endpoints

- [ ] **Step 1: Add purchase router to event/urls.py**

Add at the top of `event/urls.py` (after existing imports):

```python
from apps.allocation.repository import AllocationRepository, CouponRepository
from apps.ticketing.repository import TicketingRepository
from .service import PurchaseService
from .request import PreviewOrderRequest, CreateOrderRequest
from .response import PreviewOrderResponse, CreateOrderResponse, PollStatusResponse
from exceptions import NotFoundError
```

Add after the existing `get_user_invite_service` factory:

```python
def get_purchase_service(
    session: Annotated[AsyncSession, Depends(db_session)],
) -> PurchaseService:
    return PurchaseService(
        coupon_repository=CouponRepository(session),
        repository=EventRepository(session),
    )
```

Add purchase routes at the end of the router (after the existing endpoints):

```python
@router.post("/purchase/orders/preview", response_model=BaseResponse[PreviewOrderResponse])
async def preview_order(
    request: Request,
    body: Annotated[PreviewOrderRequest, Body()],
    service: Annotated[PurchaseService, Depends(get_purchase_service)],
) -> BaseResponse[PreviewOrderResponse]:
    """
    Preview order price breakdown without creating an order or locking tickets.
    Validates event, ticket type, availability, and coupon (if provided).
    """
    result = await service.preview_order(
        event_id=body.event_id,
        event_day_id=body.event_day_id,
        ticket_type_id=body.ticket_type_id,
        quantity=body.quantity,
        coupon_code=body.coupon_code,
    )
    return BaseResponse(data=PreviewOrderResponse.model_validate(result))


@router.post("/purchase/orders", response_model=BaseResponse[CreateOrderResponse])
async def create_order(
    request: Request,
    body: Annotated[CreateOrderRequest, Body()],
    service: Annotated[PurchaseService, Depends(get_purchase_service)],
) -> BaseResponse[CreateOrderResponse]:
    """
    Create a purchase order. Locks tickets atomically, creates order in pending state,
    and returns Razorpay checkout details for the frontend modal.
    """
    result = await service.create_order(
        user_id=request.state.user.id,
        event_id=body.event_id,
        event_day_id=body.event_day_id,
        ticket_type_id=body.ticket_type_id,
        quantity=body.quantity,
        coupon_code=body.coupon_code,
    )
    return BaseResponse(data=CreateOrderResponse.model_validate(result))


@router.get("/purchase/orders/{order_id}/status", response_model=BaseResponse[PollStatusResponse])
async def poll_order_status(
    order_id: UUID,
    request: Request,
    service: Annotated[PurchaseService, Depends(get_purchase_service)],
) -> BaseResponse[PollStatusResponse]:
    """
    Poll the status of a purchase order. Returns status + ticket_count.
    When paid, also returns jwt (scan QR) and claim_url.
    """
    result = await service.poll_order_status(
        order_id=order_id,
        user_id=request.state.user.id,
    )
    return BaseResponse(data=PollStatusResponse.model_validate(result))
```

- [ ] **Step 2: Verify the app starts without import errors**

Run: `uv run main.py run --debug &` (then Ctrl+C after startup check)
Expected: No import errors

- [ ] **Step 3: Commit**

```bash
git add src/apps/event/urls.py
git commit -m "feat(purchase): add purchase order routes to event router"
```

---

## Verification

1. Run `pytest tests/test_purchase_service.py -v` — all pass
2. `uv run main.py run --debug` — no import errors
3. Hit endpoints (manual or via test client):
   - `POST /api/events/purchase/orders/preview` with valid inputs → returns price breakdown
   - `POST /api/events/purchase/orders` → creates order with status=pending, locks tickets
   - `GET /api/events/purchase/orders/{id}/status` → returns pending
4. Verify `create_order` clears locks when Razorpay call fails (tested in unit test)

---

## Follow-up: Phase 5 Webhook

When Phase 5 extends `handle_order_paid` for `RAZORPAY_ORDER`:
1. Create allocation + claim link for buyer (no reseller split)
2. Transfer ticket ownership to buyer
3. Clear locks
4. Send notifications with claim URL

Poll_status will automatically work after Phase 5 — when webhook fires, `poll_order_status` will find the allocation and claim link and return `jwt` + `claim_url`.
