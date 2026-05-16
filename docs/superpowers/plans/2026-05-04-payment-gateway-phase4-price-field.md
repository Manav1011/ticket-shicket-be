# Payment Gateway Phase 4 — Add Price Field to Paid Transfers

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a `price: float` field to all paid transfer request schemas so organizers can set a dynamic order total at runtime. The price is a flat amount per order (not per ticket) — any quantity of tickets can be transferred for that fixed price.

**Architecture:** The organizer sets `price` when initiating a paid transfer. This becomes `subtotal_amount`, `discount_amount=0`, and `final_amount` on the order. The payment link amount is `int(price * 100)` (converted to paise). The webhook handler validates the paid amount against `final_amount * 100`.

**Tech Stack:** Pydantic, SQLAlchemy async, Razorpay SDK.

**Dependencies:** Phase 4 plans 4A, 4B, 4C must be complete first.

---

## File Structure

**Files modified:**
- `src/apps/organizer/request.py` — add `price` to `CreateB2BTransferRequest` and `CreateCustomerTransferRequest`
- `src/apps/resellers/request.py` — add `price` to `CreateResellerCustomerTransferRequest`
- `src/apps/organizer/service.py` — update paid flows to use `price` for order amounts
- `src/apps/resellers/service.py` — update paid flow to use `price` for order amounts

**Files created:**
- `tests/apps/organizer/test_request.py` (extend existing)
- `tests/apps/resellers/test_request.py` (extend existing)

---

### Task 1: Add `price` to Organizer request schemas

**Files:**
- Modify: `src/apps/organizer/request.py` (add `price` to both request models)
- Test: `tests/apps/organizer/test_request.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/apps/organizer/test_request.py
import pytest
from apps.organizer.request import CreateB2BTransferRequest, CreateCustomerTransferRequest
from apps.allocation.enums import TransferMode


def test_b2b_transfer_request_has_price_field():
    req = CreateB2BTransferRequest(
        reseller_id="00000000-0000-0000-0000-000000000001",
        quantity=5,
        mode=TransferMode.PAID,
        price=250.0,
    )
    assert req.price == 250.0


def test_customer_transfer_request_has_price_field():
    req = CreateCustomerTransferRequest(
        phone="+919999999999",
        quantity=3,
        event_day_id="00000000-0000-0000-0000-000000000001",
        mode=TransferMode.PAID,
        price=100.0,
    )
    assert req.price == 100.0


def test_b2b_transfer_request_price_defaults_to_none():
    req = CreateB2BTransferRequest(
        reseller_id="00000000-0000-0000-0000-000000000001",
        quantity=5,
    )
    assert req.price is None


def test_customer_transfer_request_price_defaults_to_none():
    req = CreateCustomerTransferRequest(
        phone="+919999999999",
        quantity=3,
        event_day_id="00000000-0000-0000-0000-000000000001",
    )
    assert req.price is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/apps/organizer/test_request.py -v`
Expected: FAIL — `price` field not found

- [ ] **Step 3: Write implementation**

In `src/apps/organizer/request.py`:

```python
class CreateB2BTransferRequest(CamelCaseModel):
    reseller_id: UUID
    quantity: int = Field(gt=0)
    event_day_id: UUID | None = None
    mode: TransferMode = TransferMode.FREE
    price: float | None = None  # Flat order price in rupees. Required when mode=PAID.


class CreateCustomerTransferRequest(CamelCaseModel):
    phone: str | None = None
    email: str | None = None
    quantity: int = Field(gt=0)
    event_day_id: UUID
    mode: TransferMode = TransferMode.FREE
    price: float | None = None  # Flat order price in rupees. Required when mode=PAID.

    @model_validator(mode='after')
    def must_have_phone_or_email(self):
        if not self.phone and not self.email:
            raise ValueError('Either phone or email must be provided')
        return self
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/apps/organizer/test_request.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/apps/organizer/request.py tests/apps/organizer/test_request.py
git commit -m "feat(organizer): add price field to B2B and customer transfer requests"
```

---

### Task 2: Add `price` to Reseller request schema

**Files:**
- Modify: `src/apps/resellers/request.py`
- Test: `tests/apps/resellers/test_request.py` (create if not exists)

- [ ] **Step 1: Write the failing test**

```python
# tests/apps/resellers/test_request.py
import pytest
from apps.resellers.request import CreateResellerCustomerTransferRequest
from apps.allocation.enums import TransferMode


def test_reseller_customer_transfer_request_has_price_field():
    req = CreateResellerCustomerTransferRequest(
        phone="+919999999999",
        quantity=2,
        event_day_id="00000000-0000-0000-0000-000000000001",
        mode=TransferMode.PAID,
        price=150.0,
    )
    assert req.price == 150.0


def test_reseller_customer_transfer_request_price_defaults_to_none():
    req = CreateResellerCustomerTransferRequest(
        phone="+919999999999",
        quantity=2,
        event_day_id="00000000-0000-0000-0000-000000000001",
    )
    assert req.price is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/apps/resellers/test_request.py -v`
Expected: FAIL — `price` field not found

- [ ] **Step 3: Write implementation**

In `src/apps/resellers/request.py`:

```python
class CreateResellerCustomerTransferRequest(CamelCaseModel):
    phone: str | None = None
    email: str | None = None
    quantity: int = Field(gt=0)
    event_day_id: UUID
    mode: TransferMode = TransferMode.FREE
    price: float | None = None  # Flat order price in rupees. Required when mode=PAID.

    @model_validator(mode='after')
    def must_have_phone_or_email(self):
        if not self.phone and not self.email:
            raise ValueError('Either phone or email must be provided')
        return self
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/apps/resellers/test_request.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/apps/resellers/request.py tests/apps/resellers/test_request.py
git commit -m "feat(reseller): add price field to customer transfer request"
```

---

### Task 3: Wire `price` into Organizer paid flows

**Files:**
- Modify: `src/apps/organizer/service.py` — `create_b2b_transfer` and `create_customer_transfer`
- Test: `tests/apps/organizer/test_organizer_service.py`

**Three changes needed per method:**
1. Accept `price: float | None` from the request
2. Set `order.subtotal_amount = price`, `order.discount_amount = 0.0`, `order.final_amount = price`
3. Pass `amount=int(price * 100)` to `create_payment_link()`

- [ ] **Step 1: Write the failing test**

```python
# tests/apps/organizer/test_organizer_service.py
import pytest
from uuid import uuid4
from unittest.mock import AsyncMock, MagicMock, patch
from apps.allocation.enums import TransferMode


@pytest.mark.asyncio
async def test_create_b2b_transfer_paid_mode_uses_price_for_amount():
    """Paid mode uses price as final_amount and passes price*100 (paise) to gateway."""
    from apps.organizer.service import OrganizerService

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

    org_holder = MagicMock(id=uuid4())
    reseller_holder = MagicMock(id=uuid4())
    reseller_user = MagicMock(id=uuid4(), name="Reseller Co", email="reseller@co.in", phone="+919999999999")

    service._allocation_repo.get_holder_by_user_id = AsyncMock(
        side_effect=[org_holder, reseller_holder]
    )
    service._allocation_repo.list_b2b_tickets_by_holder = AsyncMock(return_value=[{"event_day_id": uuid4(), "count": 5}])
    service._allocation_repo.get_holder_by_email = AsyncMock(return_value=None)
    service._allocation_repo.get_holder_by_phone = AsyncMock(return_value=None)
    service._ticketing_repo.get_b2b_ticket_type_for_event = AsyncMock(
        return_value=MagicMock(id=uuid4())
    )
    service._ticketing_repo.lock_tickets_for_transfer = AsyncMock(return_value=[uuid4(), uuid4()])

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
                    price=250.0,
                )

    assert result.status == "pending_payment"
    # Verify amount passed to gateway was price*100 in paise
    mock_gateway.create_payment_link.assert_called_once()
    call_kwargs = mock_gateway.create_payment_link.call_args.kwargs
    assert call_kwargs["amount"] == int(250.0 * 100)  # 25000 paise = ₹250


@pytest.mark.asyncio
async def test_create_customer_transfer_paid_mode_uses_price_for_amount():
    """Paid mode uses price as final_amount and passes price*100 (paise) to gateway."""
    from apps.organizer.service import OrganizerService

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

    customer_holder = MagicMock(id=uuid4())
    org_holder = MagicMock(id=uuid4())

    service._allocation_repo.get_holder_by_user_id = AsyncMock(return_value=org_holder)
    service._allocation_repo.get_holder_by_phone_and_email = AsyncMock(return_value=None)
    service._allocation_repo.get_holder_by_phone = AsyncMock(return_value=None)
    service._allocation_repo.get_holder_by_email = AsyncMock(return_value=None)
    service._allocation_repo.create_holder = AsyncMock(return_value=customer_holder)
    service._allocation_repo.list_b2b_tickets_by_holder = AsyncMock(return_value=[{"count": 5}])
    service._ticketing_repo.get_b2b_ticket_type_for_event = AsyncMock(
        return_value=MagicMock(id=uuid4())
    )
    service._ticketing_repo.lock_tickets_for_transfer = AsyncMock(return_value=[uuid4()])

    with patch("apps.organizer.service.get_gateway") as mock_get_gateway:
        mock_gateway = MagicMock()
        mock_gateway.create_payment_link = AsyncMock(
            return_value=MagicMock(
                gateway_order_id="plink_cust123",
                short_url="https://razorpay.in/cust",
                gateway_response={"id": "plink_cust123"},
            )
        )
        mock_get_gateway.return_value = mock_gateway

        with patch("apps.organizer.service.OrderModel") as mock_order_model:
            order_instance = MagicMock()
            order_instance.id = uuid4()
            mock_order_model.return_value = order_instance

            with patch("apps.organizer.service.EventRepository") as mock_event_repo_cls:
                mock_event_repo = MagicMock()
                target_event_id = uuid4()
                mock_event_repo.get_by_id_for_owner = AsyncMock(return_value=MagicMock(name="Test Event"))
                mock_event_repo.get_event_day_by_id = AsyncMock(return_value=MagicMock(event_id=target_event_id))
                mock_event_repo_cls.return_value = mock_event_repo

                result = await service.create_customer_transfer(
                    user_id=uuid4(),
                    event_id=target_event_id,
                    phone="+919999999999",
                    email=None,
                    quantity=3,
                    event_day_id=uuid4(),
                    mode=TransferMode.PAID,
                    price=100.0,
                )

    assert result.status == "pending_payment"
    mock_gateway.create_payment_link.assert_called_once()
    call_kwargs = mock_gateway.create_payment_link.call_args.kwargs
    assert call_kwargs["amount"] == int(100.0 * 100)  # 10000 paise = ₹100
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/apps/organizer/test_organizer_service.py::test_create_b2b_transfer_paid_mode_uses_price_for_amount tests/apps/organizer/test_organizer_service.py::test_create_customer_transfer_paid_mode_uses_price_for_amount -v`
Expected: FAIL — `create_b2b_transfer` doesn't accept `price` keyword arg

- [ ] **Step 3: Write implementation**

**Change 1:** In `create_b2b_transfer`, add `price: float | None = None` to the method signature.

**Change 2:** In the paid-flow `OrderModel` creation, replace the hardcoded amounts:

```python
# OLD (in create_b2b_transfer paid flow):
subtotal_amount=0.0,  # TODO (Phase 5): derive from ticket type price
discount_amount=0.0,
final_amount=0.0,  # TODO (Phase 5): derive from ticket type price

# NEW:
subtotal_amount=price or 0.0,
discount_amount=0.0,
final_amount=price or 0.0,
```

**Change 3:** In the `create_payment_link()` call, replace hardcoded amount:

```python
# OLD:
amount=int(0.0 * 100),  # TODO (Phase 5): use actual ticket price in paise

# NEW:
amount=int((price or 0.0) * 100),
```

**Repeat Changes 1-3 for `create_customer_transfer`** (same pattern: add `price` param, update OrderModel amounts, update `create_payment_link` amount).

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/apps/organizer/test_organizer_service.py::test_create_b2b_transfer_paid_mode_uses_price_for_amount tests/apps/organizer/test_organizer_service.py::test_create_customer_transfer_paid_mode_uses_price_for_amount -v`
Expected: PASS

- [ ] **Step 5: Run regression tests**

Run: `uv run pytest tests/apps/organizer/test_organizer_service.py -v`
Expected: All tests PASS

- [ ] **Step 6: Commit**

```bash
git add src/apps/organizer/service.py tests/apps/organizer/test_organizer_service.py
git commit -m "feat(organizer): wire price field into paid transfer flows"
```

---

### Task 4: Wire `price` into Reseller paid flow

**Files:**
- Modify: `src/apps/resellers/service.py` — `create_reseller_customer_transfer`
- Test: `tests/apps/resellers/test_reseller_customer_transfer.py`

**Same three changes as Task 3** — add `price` to method signature, use it in OrderModel, pass `int(price * 100)` to `create_payment_link()`.

- [ ] **Step 1: Write the failing test**

```python
# tests/apps/resellers/test_reseller_customer_transfer.py
import pytest
from uuid import uuid4
from unittest.mock import AsyncMock, MagicMock, patch
from apps.allocation.enums import TransferMode


@pytest.mark.asyncio
async def test_create_reseller_customer_transfer_paid_mode_uses_price_for_amount():
    """Paid mode uses price as final_amount and passes price*100 (paise) to gateway."""
    from apps.resellers.service import ResellerService

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
                price=175.0,
            )

    assert result.status == "pending_payment"
    mock_gateway.create_payment_link.assert_called_once()
    call_kwargs = mock_gateway.create_payment_link.call_args.kwargs
    assert call_kwargs["amount"] == int(175.0 * 100)  # 17500 paise = ₹175
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/apps/resellers/test_reseller_customer_transfer.py::test_create_reseller_customer_transfer_paid_mode_uses_price_for_amount -v`
Expected: FAIL — `create_reseller_customer_transfer` doesn't accept `price` keyword arg

- [ ] **Step 3: Write implementation**

**Change 1:** Add `price: float | None = None` to `create_reseller_customer_transfer` signature.

**Change 2:** In the paid-flow `OrderModel` creation:

```python
# OLD:
subtotal_amount=0.0,  # TODO (Phase 5): derive from ticket type price
discount_amount=0.0,
final_amount=0.0,  # TODO (Phase 5): derive from ticket type price

# NEW:
subtotal_amount=price or 0.0,
discount_amount=0.0,
final_amount=price or 0.0,
```

**Change 3:** In `create_payment_link()`:

```python
# OLD:
amount=int(0.0 * 100),  # TODO (Phase 5): use actual ticket price in paise

# NEW:
amount=int((price or 0.0) * 100),
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/apps/resellers/test_reseller_customer_transfer.py::test_create_reseller_customer_transfer_paid_mode_uses_price_for_amount -v`
Expected: PASS

- [ ] **Step 5: Run regression tests**

Run: `uv run pytest tests/apps/resellers/test_reseller_customer_transfer.py -v`
Expected: All tests PASS

- [ ] **Step 6: Commit**

```bash
git add src/apps/resellers/service.py tests/apps/resellers/test_reseller_customer_transfer.py
git commit -m "feat(reseller): wire price field into customer transfer paid flow"
```

---

## Self-Review

**1. Spec coverage:**
- `price: float | None` field in all 3 request schemas ✅
- `subtotal_amount`, `discount_amount`, `final_amount` all set from `price` ✅
- `amount=int(price * 100)` passed to `create_payment_link()` ✅
- Amount validation in webhook handler (`int(float(order.final_amount) * 100)`) already exists ✅

**2. Placeholder scan:** No "TBD", "TODO" in the actual implementation. `TODO (Phase 5)` comments are removed since this is Phase 5 work being done now.

**3. Type consistency:**
- `price: float | None` in all 3 request schemas ✅
- `price or 0.0` handles `None` gracefully ✅
- `int(price * 100)` for Razorpay paise ✅
- Webhook amount validation uses `int(float(order.final_amount) * 100)` — matches exactly ✅

**4. Amount validation flow (webhook handler):**
```python
# Webhook (already implemented):
payment_amount = raw.get("payload", {}).get("payment", {}).get("entity", {}).get("amount")
expected_amount = int(float(order.final_amount) * 100)
if payment_amount != expected_amount:  # matches int(price * 100) ✅
```

Plan complete and saved to `docs/superpowers/plans/2026-05-04-payment-gateway-phase4-price-field.md`.