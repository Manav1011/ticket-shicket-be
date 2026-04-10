# Increase Ticket Allocation Quantity Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add an API endpoint to increase ticket allocation quantities before scanning starts, with proper validations to prevent decreases.

**Architecture:** Extend the existing ticketing service layer with an update operation that validates ownership, checks quantity constraints, bulk-creates new tickets for the increase, and updates the allocation in the database. The endpoint follows the same authorization and error-handling patterns as existing ticketing endpoints.

**Tech Stack:** FastAPI, SQLAlchemy async ORM, Pydantic request/response models

---

## File Structure

**Files to create:**
- None (all changes to existing files)

**Files to modify:**
- `src/apps/ticketing/exceptions.py` — Add new exception for quantity decrease attempts
- `src/apps/ticketing/request.py` — Add request model for quantity updates
- `src/apps/ticketing/repository.py` — Add method to fetch allocation by ID
- `src/apps/ticketing/service.py` — Add service method with all validations and quantity update logic
- `src/apps/ticketing/urls.py` — Add PATCH endpoint for quantity updates
- `tests/apps/ticketing/test_service.py` — Add test cases for update operation
- `tests/apps/ticketing/test_endpoints.py` — Add endpoint integration tests

---

## Task 1: Add CannotDecreaseQuantity Exception

**Files:**
- Modify: `src/apps/ticketing/exceptions.py`

- [ ] **Step 1: Add the new exception class**

Open `src/apps/ticketing/exceptions.py` and add after the `InvalidAllocation` class:

```python
class CannotDecreaseQuantity(BadRequestError):
    message = "Ticket quantity can only be increased, not decreased."
```

- [ ] **Step 2: Commit**

```bash
git add src/apps/ticketing/exceptions.py
git commit -m "feat: add CannotDecreaseQuantity exception"
```

---

## Task 2: Add UpdateTicketAllocationQuantityRequest Model

**Files:**
- Modify: `src/apps/ticketing/request.py`

- [ ] **Step 1: Add the new request model**

Open `src/apps/ticketing/request.py` and add after the `AllocateTicketTypeRequest` class:

```python
class UpdateTicketAllocationQuantityRequest(CamelCaseModel):
    quantity: int
```

- [ ] **Step 2: Commit**

```bash
git add src/apps/ticketing/request.py
git commit -m "feat: add UpdateTicketAllocationQuantityRequest model"
```

---

## Task 3: Add Repository Method to Get Allocation by ID

**Files:**
- Modify: `src/apps/ticketing/repository.py`

- [ ] **Step 1: Add the get_allocation_by_id method**

Open `src/apps/ticketing/repository.py` and add this method after `list_allocations_for_event`:

```python
async def get_allocation_by_id(
    self, allocation_id: UUID
) -> Optional[DayTicketAllocationModel]:
    return await self._session.scalar(
        select(DayTicketAllocationModel).where(
            DayTicketAllocationModel.id == allocation_id
        )
    )
```

- [ ] **Step 2: Commit**

```bash
git add src/apps/ticketing/repository.py
git commit -m "feat: add get_allocation_by_id repository method"
```

---

## Task 4: Add Service Method to Update Allocation Quantity

**Files:**
- Modify: `src/apps/ticketing/service.py`

- [ ] **Step 1: Import the new exception at the top of the file**

Open `src/apps/ticketing/service.py` and update the exceptions import to include `CannotDecreaseQuantity`:

```python
from .exceptions import (
    CannotDecreaseQuantity,
    DuplicateAllocation,
    InvalidAllocation,
    InvalidPrice,
    InvalidQuantity,
    OpenEventDoesNotSupportTickets,
    TicketTypeNotFound,
)
```

- [ ] **Step 2: Add the update service method**

Add this method to the `TicketingService` class after the `allocate_ticket_type_to_day` method:

```python
async def update_allocation_quantity(
    self, owner_user_id, event_id, allocation_id, new_quantity
):
    # C1: Verify event ownership
    event = await self.event_repository.get_by_id_for_owner(event_id, owner_user_id)
    if event is None:
        raise InvalidAllocation("Event not found or access denied")

    # C1: Verify allocation exists
    allocation = await self.repository.get_allocation_by_id(allocation_id)
    if allocation is None:
        raise InvalidAllocation("Allocation not found")

    # C1: Verify allocation belongs to this event
    day = await self.event_day_repository.get_event_day_for_owner(
        allocation.event_day_id, owner_user_id
    )
    if day is None or day.event_id != event_id:
        raise InvalidAllocation("Allocation does not belong to this event")

    # I1: Validate new quantity > 0
    if new_quantity <= 0:
        raise InvalidQuantity

    # I1: Prevent quantity decrease
    if new_quantity < allocation.quantity:
        raise CannotDecreaseQuantity

    # C4: If no change, return allocation as-is (idempotent)
    if new_quantity == allocation.quantity:
        return allocation

    # C4: Calculate quantity increase and bulk-create new tickets
    quantity_increase = new_quantity - allocation.quantity
    await self.repository.bulk_create_tickets(
        event_id,
        allocation.event_day_id,
        allocation.ticket_type_id,
        start_index=day.next_ticket_index,
        quantity=quantity_increase,
    )

    # C4: Update allocation and day state
    allocation.quantity = new_quantity
    day.next_ticket_index += quantity_increase
    await self.repository.session.flush()
    await self.repository.session.refresh(allocation)
    return allocation
```

- [ ] **Step 3: Commit**

```bash
git add src/apps/ticketing/service.py
git commit -m "feat: add update_allocation_quantity service method with validations"
```

---

## Task 5: Add API Endpoint for Quantity Update

**Files:**
- Modify: `src/apps/ticketing/urls.py`

- [ ] **Step 1: Import the new request model**

Open `src/apps/ticketing/urls.py` and update the request imports:

```python
from .request import (
    AllocateTicketTypeRequest,
    CreateTicketTypeRequest,
    UpdateTicketAllocationQuantityRequest,
)
```

- [ ] **Step 2: Add the PATCH endpoint**

Add this endpoint after the `create_ticket_allocation` endpoint:

```python
@router.patch("/{event_id}/ticket-allocations/{allocation_id}")
async def update_ticket_allocation_quantity(
    event_id: UUID,
    allocation_id: UUID,
    request: Request,
    body: Annotated[UpdateTicketAllocationQuantityRequest, Body()],
    service: Annotated[TicketingService, Depends(get_ticketing_service)],
) -> BaseResponse[DayTicketAllocationResponse]:
    allocation = await service.update_allocation_quantity(
        request.state.user.id, event_id, allocation_id, body.quantity
    )
    return BaseResponse(data=DayTicketAllocationResponse.model_validate(allocation))
```

- [ ] **Step 3: Commit**

```bash
git add src/apps/ticketing/urls.py
git commit -m "feat: add PATCH endpoint to update ticket allocation quantity"
```

---

## Task 6: Write Service Layer Tests

**Files:**
- Modify: `tests/apps/ticketing/test_service.py`

- [ ] **Step 1: Add test for successful quantity increase**

Create or open `tests/apps/ticketing/test_service.py` and add:

```python
@pytest.mark.asyncio
async def test_update_allocation_quantity_increase_success(
    ticketing_service, owner_user_id, event, event_day, ticket_type
):
    """Test that we can increase quantity before scanning starts."""
    # Create initial allocation with quantity 50
    allocation = await ticketing_service.allocate_ticket_type_to_day(
        owner_user_id, event.id, event_day.id, ticket_type.id, 50
    )
    initial_quantity = allocation.quantity
    initial_next_index = event_day.next_ticket_index

    # Update quantity to 75 (increase of 25)
    updated = await ticketing_service.update_allocation_quantity(
        owner_user_id, event.id, allocation.id, 75
    )

    assert updated.quantity == 75
    assert event_day.next_ticket_index == initial_next_index + 25
```

- [ ] **Step 2: Add test for idempotent no-op**

Add:

```python
@pytest.mark.asyncio
async def test_update_allocation_quantity_no_change_is_idempotent(
    ticketing_service, owner_user_id, event, event_day, ticket_type
):
    """Test that same quantity returns allocation unchanged."""
    allocation = await ticketing_service.allocate_ticket_type_to_day(
        owner_user_id, event.id, event_day.id, ticket_type.id, 50
    )

    # Update with same quantity
    updated = await ticketing_service.update_allocation_quantity(
        owner_user_id, event.id, allocation.id, 50
    )

    assert updated.quantity == 50
```

- [ ] **Step 3: Add test for decrease rejection**

Add:

```python
@pytest.mark.asyncio
async def test_update_allocation_quantity_rejects_decrease(
    ticketing_service, owner_user_id, event, event_day, ticket_type
):
    """Test that decreasing quantity raises CannotDecreaseQuantity."""
    allocation = await ticketing_service.allocate_ticket_type_to_day(
        owner_user_id, event.id, event_day.id, ticket_type.id, 50
    )

    with pytest.raises(CannotDecreaseQuantity):
        await ticketing_service.update_allocation_quantity(
            owner_user_id, event.id, allocation.id, 30
        )
```

- [ ] **Step 4: Add test for invalid quantity (zero/negative)**

Add:

```python
@pytest.mark.asyncio
async def test_update_allocation_quantity_rejects_zero_or_negative(
    ticketing_service, owner_user_id, event, event_day, ticket_type
):
    """Test that zero or negative quantities are rejected."""
    allocation = await ticketing_service.allocate_ticket_type_to_day(
        owner_user_id, event.id, event_day.id, ticket_type.id, 50
    )

    with pytest.raises(InvalidQuantity):
        await ticketing_service.update_allocation_quantity(
            owner_user_id, event.id, allocation.id, 0
        )

    with pytest.raises(InvalidQuantity):
        await ticketing_service.update_allocation_quantity(
            owner_user_id, event.id, allocation.id, -10
        )
```

- [ ] **Step 5: Add test for non-existent allocation**

Add:

```python
@pytest.mark.asyncio
async def test_update_allocation_quantity_rejects_nonexistent_allocation(
    ticketing_service, owner_user_id, event, event_day
):
    """Test that updating non-existent allocation raises InvalidAllocation."""
    fake_allocation_id = uuid4()

    with pytest.raises(InvalidAllocation):
        await ticketing_service.update_allocation_quantity(
            owner_user_id, event.id, fake_allocation_id, 50
        )
```

- [ ] **Step 6: Add test for ownership check**

Add:

```python
@pytest.mark.asyncio
async def test_update_allocation_quantity_requires_event_ownership(
    ticketing_service, owner_user_id, event, event_day, ticket_type, another_user_id
):
    """Test that non-owner cannot update allocation."""
    allocation = await ticketing_service.allocate_ticket_type_to_day(
        owner_user_id, event.id, event_day.id, ticket_type.id, 50
    )

    with pytest.raises(InvalidAllocation):
        await ticketing_service.update_allocation_quantity(
            another_user_id, event.id, allocation.id, 75
        )
```

- [ ] **Step 7: Run tests to verify they all pass**

```bash
pytest tests/apps/ticketing/test_service.py -v
```

Expected: All 6 new tests PASS

- [ ] **Step 8: Commit**

```bash
git add tests/apps/ticketing/test_service.py
git commit -m "test: add service tests for update_allocation_quantity"
```

---

## Task 7: Write Endpoint Integration Tests

**Files:**
- Modify: `tests/apps/ticketing/test_endpoints.py`

- [ ] **Step 1: Add test for successful endpoint call**

Create or open `tests/apps/ticketing/test_endpoints.py` and add:

```python
@pytest.mark.asyncio
async def test_patch_ticket_allocation_quantity_success(
    client, owner_user_token, event, event_day, ticket_type, db_session
):
    """Test PATCH endpoint for increasing allocation quantity."""
    # First allocate
    allocation = await allocate_helper(db_session, event_day.id, ticket_type.id, 50)

    # Then update quantity via endpoint
    response = client.patch(
        f"/api/events/{event.id}/ticket-allocations/{allocation.id}",
        json={"quantity": 75},
        headers={"Authorization": f"Bearer {owner_user_token}"},
    )

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["quantity"] == 75
```

- [ ] **Step 2: Add test for decrease rejection at endpoint**

Add:

```python
@pytest.mark.asyncio
async def test_patch_ticket_allocation_quantity_rejects_decrease(
    client, owner_user_token, event, event_day, ticket_type, db_session
):
    """Test that endpoint rejects quantity decrease."""
    allocation = await allocate_helper(db_session, event_day.id, ticket_type.id, 50)

    response = client.patch(
        f"/api/events/{event.id}/ticket-allocations/{allocation.id}",
        json={"quantity": 30},
        headers={"Authorization": f"Bearer {owner_user_token}"},
    )

    assert response.status_code == 400
    assert "cannot" in response.json()["message"].lower()
```

- [ ] **Step 3: Add test for invalid allocation at endpoint**

Add:

```python
@pytest.mark.asyncio
async def test_patch_ticket_allocation_quantity_nonexistent(
    client, owner_user_token, event
):
    """Test that endpoint returns 422 for non-existent allocation."""
    fake_allocation_id = uuid4()

    response = client.patch(
        f"/api/events/{event.id}/ticket-allocations/{fake_allocation_id}",
        json={"quantity": 75},
        headers={"Authorization": f"Bearer {owner_user_token}"},
    )

    assert response.status_code == 422
```

- [ ] **Step 4: Add test for unauthorized access at endpoint**

Add:

```python
@pytest.mark.asyncio
async def test_patch_ticket_allocation_quantity_requires_auth(
    client, event, event_day, ticket_type, db_session
):
    """Test that endpoint requires authentication."""
    allocation = await allocate_helper(db_session, event_day.id, ticket_type.id, 50)

    response = client.patch(
        f"/api/events/{event.id}/ticket-allocations/{allocation.id}",
        json={"quantity": 75},
    )

    assert response.status_code == 401
```

- [ ] **Step 5: Run tests to verify they all pass**

```bash
pytest tests/apps/ticketing/test_endpoints.py -v
```

Expected: All 4 new tests PASS

- [ ] **Step 6: Commit**

```bash
git add tests/apps/ticketing/test_endpoints.py
git commit -m "test: add endpoint integration tests for update_allocation_quantity"
```

---

## Task 8: Run Full Test Suite and Verify No Regressions

**Files:**
- None (verification only)

- [ ] **Step 1: Run all ticketing tests**

```bash
pytest tests/apps/ticketing/ -v
```

Expected: All tests PASS with no regressions

- [ ] **Step 2: Run full test suite if time allows**

```bash
pytest tests/ -v --tb=short
```

Expected: No new failures introduced

---

## Verification Checklist

- [ ] All validations are in place:
  - Event ownership verified
  - Allocation exists and belongs to event
  - New quantity ≥ old quantity (no decreases)
  - New quantity > 0
  - Idempotent behavior (no-op on same quantity)
- [ ] New tickets are bulk-created for quantity increase
- [ ] `next_ticket_index` is updated correctly
- [ ] All exceptions are raised with appropriate error messages
- [ ] Tests cover happy path, validation failures, and edge cases
- [ ] No scanning_started_at check (as requested)
- [ ] All commits are atomic with clear messages

---

## Next Steps After Implementation

1. **Manual testing** — Use your API client (Postman/curl) to verify endpoint behavior
2. **Frontend integration** — Wire up UI to call the new PATCH endpoint
3. **Future work** — Add scanning_started_at check in a separate task when ready
4. **Documentation** — Update API docs to include the new PATCH endpoint

