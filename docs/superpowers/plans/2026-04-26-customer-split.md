# Customer → Customer (Split) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement `POST /api/open/claim/{token}/split` — a public endpoint allowing Customer A to split tickets to Customer B. Customer A identifies via claim token, revokes old JWT, transfers tickets, and gets a new JWT.

**Architecture:** The split endpoint is under `/api/open/` (no auth required). Customer A provides claim token + email + ticket count. System locks tickets, creates allocation, revokes old claim link and JWT, reissues new JWT to Customer A, creates claim link for Customer B, sends notifications.

**Tech Stack:** FastAPI, SQLAlchemy async, Pydantic

---

## Request/Response Schemas

### Request Schema: `SplitClaimRequest`
```python
class SplitClaimRequest(BaseModel):
    to_email: str                      # Customer B's email (required)
    ticket_count: int                   # Number of tickets to transfer
```

### Response Schema: `SplitClaimResponse`
```python
class SplitClaimResponse(BaseModel):
    status: str                        # "completed"
    tickets_transferred: int           # Count transferred to Customer B
    remaining_ticket_count: int        # Customer A's remaining count
    new_jwt: str                       # Customer A's new JWT with remaining tickets
    message: str                       # "Your previous QR code is no longer valid..."
```

---

## File Structure

| File | Change |
|------|--------|
| `src/apps/event/request.py` | Add `SplitClaimRequest` |
| `src/apps/event/response.py` | Add `SplitClaimResponse` |
| `src/apps/event/public_urls.py` | Add `POST /api/open/claim/{token}/split` endpoint |
| `src/apps/event/claim_service.py` | Add `split_claim()` method |
| `src/apps/allocation/repository.py` | Add `revoke_claim_link()` method |
| `src/apps/allocation/repository.py` | Add `add_revoked_jti()` method |
| `src/apps/ticketing/repository.py` | (already has methods needed) |
| `src/utils/notifications/` | Already has mock SMS/WhatsApp/Email |

---

## Tasks

### Task 1: Add `SplitClaimRequest` Schema

**Files:**
- Modify: `src/apps/event/request.py`

- [ ] **Step 1: Read current request.py**

Find the imports and existing request classes to follow the same pattern.

- [ ] **Step 2: Add SplitClaimRequest**

```python
class SplitClaimRequest(BaseModel):
    to_email: str
    ticket_count: int
```

---

### Task 2: Add `SplitClaimResponse` Schema

**Files:**
- Modify: `src/apps/event/response.py`

- [ ] **Step 1: Read current response.py**

Find where `ClaimRedemptionResponse` was added and follow same pattern.

- [ ] **Step 2: Add SplitClaimResponse**

```python
class SplitClaimResponse(CamelCaseModel):
    status: str
    tickets_transferred: int
    remaining_ticket_count: int
    new_jwt: str
    message: str
```

---

### Task 3: Add `revoke_claim_link()` Method in AllocationRepository

**Files:**
- Modify: `src/apps/allocation/repository.py`

- [ ] **Step 1: Read current allocation/repository.py**

Find the `ClaimLinkRepository` class. Note the existing methods.

- [ ] **Step 2: Add `revoke_claim_link()` method**

In `ClaimLinkRepository` class:

```python
async def revoke_claim_link(self, claim_link_id: UUID) -> None:
    """
    Revoke a claim link by setting its status to inactive.
    Used when Customer A splits tickets — old claim link becomes invalid.
    """
    await self._session.execute(
        update(ClaimLinkModel)
        .where(ClaimLinkModel.id == claim_link_id)
        .values(status=ClaimLinkStatus.inactive)
    )
```

- [ ] **Step 3: Run import check**

Run: `uv run python -c "from apps.allocation.repository import ClaimLinkRepository; print('OK')"`
Expected: No errors

---

### Task 4: Add `add_revoked_jti()` Method in RevokedScanTokenRepository

**Files:**
- Modify: `src/apps/allocation/repository.py`

- [ ] **Step 1: Find RevokedScanTokenRepository**

Check if `RevokedScanTokenRepository` class exists. If not, find where `add_revoked_jti` should go.

- [ ] **Step 2: Add `add_revoked_jti()` method**

```python
async def add_revoked_jti(
    self,
    event_day_id: UUID,
    jti: str,
    reason: str = "split",
) -> None:
    """
    Add a JTI to the revoked list.
    Called during split to invalidate Customer A's old JWT.
    """
    revoked = RevokedScanTokenModel(
        event_day_id=event_day_id,
        jti=jti,
        reason=reason,
    )
    self._session.add(revoked)
    await self._session.flush()
```

- [ ] **Step 3: Run import check**

Run: `uv run python -c "from apps.allocation.repository import RevokedScanTokenRepository; print('OK')"`
Expected: No errors

---

### Task 5: Add `split_claim()` Method in ClaimService

**Files:**
- Modify: `src/apps/event/claim_service.py`

- [ ] **Step 1: Read current claim_service.py**

Note existing imports and `ClaimService` class structure.

- [ ] **Step 2: Add imports**

Add required imports:
```python
from apps.ticketing.repository import TicketingRepository
from apps.allocation.repository import AllocationRepository, ClaimLinkRepository, RevokedScanTokenRepository
from apps.allocation.models import AllocationModel, RevokedScanTokenModel
from src.utils.claim_link_utils import generate_claim_link_token
from src.utils.notifications.whatsapp import mock_send_whatsapp
from src.utils.notifications.email import mock_send_email
```

- [ ] **Step 3: Add `split_claim()` method**

```python
async def split_claim(
    self,
    raw_token: str,
    to_email: str,
    ticket_count: int,
) -> SplitClaimResponse:
    """
    Split tickets from Customer A to Customer B via claim link.

    Flow:
    1. Validate claim token (hash → lookup)
    2. Validate ticket_count (1 to available)
    3. Resolve Customer B by email
    4. Validate Customer B != Customer A
    5. Lock tickets for transfer
    6. Create OrderModel
    7. Create AllocationModel (A → B)
    8. Update ticket ownership (transfer to B)
    9. Revoke Customer A's old claim link (status = inactive)
    10. Revoke Customer A's old JWT (add JTI to revoked list)
    11. Generate new JWT for Customer A (remaining tickets)
    12. Create claim link for Customer B
    13. Send mock notifications to Customer B
    14. Return response with new JWT

    Raises:
        NotFoundError if token invalid
        BadRequestError if validation fails
    """
    # 1. Validate claim token
    token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
    claim_link = await self._claim_link_repo.get_by_token_hash(token_hash)
    if not claim_link:
        raise NotFoundError("Claim link not found")

    if claim_link.status != ClaimLinkStatus.active:
        raise BadRequestError("Claim link has already been used or revoked")

    if claim_link.claimed_at is not None:
        raise BadRequestError("Claim link already claimed")

    customer_a_id = claim_link.to_holder_id
    event_day_id = claim_link.event_day_id
    event_id = claim_link.event_id

    # 2. Validate ticket_count
    if ticket_count <= 0:
        raise BadRequestError("Ticket count must be positive")

    # Get Customer A's tickets
    from apps.ticketing.models import TicketModel
    result = await self._session.scalars(
        select(TicketModel)
        .where(
            TicketModel.owner_holder_id == customer_a_id,
            TicketModel.event_day_id == event_day_id,
            TicketModel.status == "active",
            TicketModel.lock_reference_id.is_(None),
        )
        .order_by(TicketModel.ticket_index.asc())
    )
    customer_a_tickets = list(result.all())
    available_count = len(customer_a_tickets)

    if ticket_count > available_count:
        raise BadRequestError(f"Only {available_count} tickets available")

    # 3. Resolve Customer B by email
    from apps.allocation.models import TicketHolderModel
    customer_b = await self._session.scalar(
        select(TicketHolderModel).where(TicketHolderModel.email == to_email)
    )
    if not customer_b:
        # Create new holder
        customer_b = TicketHolderModel(id=uuid.uuid4(), email=to_email, phone=None)
        self._session.add(customer_b)
        await self._session.flush()

    # 4. Validate Customer B != Customer A
    if customer_b.id == customer_a_id:
        raise BadRequestError("Cannot transfer to yourself")

    # Lock tickets
    ticketing_repo = TicketingRepository(self._session)
    b2b_ticket_type = await ticketing_repo.get_b2b_ticket_type_for_event(event_id)
    if not b2b_ticket_type:
        raise NotFoundError("B2B ticket type not found")

    order_id = uuid.uuid4()
    ticket_ids_to_transfer = [t.id for t in customer_a_tickets[:ticket_count]]

    try:
        await ticketing_repo.lock_tickets_for_transfer(
            owner_holder_id=customer_a_id,
            event_id=event_id,
            ticket_type_id=b2b_ticket_type.id,
            event_day_id=event_day_id,
            quantity=ticket_count,
            order_id=order_id,
        )
    except ValueError as e:
        raise BadRequestError(str(e))

    # Create OrderModel
    from apps.order.models import OrderModel
    order = OrderModel(
        id=order_id,
        from_holder_id=customer_a_id,
        to_holder_id=customer_b.id,
        ticket_count=ticket_count,
        type="transfer",
        status="completed",
        amount=0,
    )
    self._session.add(order)

    # Create AllocationModel
    allocation = AllocationModel(
        from_holder_id=customer_a_id,
        to_holder_id=customer_b.id,
        ticket_count=ticket_count,
        status="completed",
        event_day_id=event_day_id,
    )
    self._session.add(allocation)
    await self._session.flush()

    # Update ticket ownership
    remaining_tickets = customer_a_tickets[ticket_count:]
    remaining_ticket_ids = [t.id for t in remaining_tickets]

    await ticketing_repo.update_ticket_ownership_batch(
        ticket_ids=ticket_ids_to_transfer,
        new_owner_holder_id=customer_b.id,
    )

    # Revoke Customer A's old claim link
    await self._claim_link_repo.revoke_claim_link(claim_link.id)

    # Revoke Customer A's old JWT (add JTI to revoked list)
    if claim_link.jwt_jti:
        revoked_token = RevokedScanTokenModel(
            event_day_id=event_day_id,
            jti=claim_link.jwt_jti,
            reason="split",
        )
        self._session.add(revoked_token)

    # Generate new JWT for Customer A (remaining tickets)
    import secrets
    new_jti = secrets.token_hex(8)
    remaining_indexes = [t.ticket_index for t in remaining_tickets]

    new_jwt = generate_scan_jwt(
        jti=new_jti,
        holder_id=customer_a_id,
        event_day_id=event_day_id,
        indexes=remaining_indexes,
    )

    # Create claim link for Customer B
    from apps.allocation.models import ClaimLinkModel
    raw_token = generate_claim_link_token()
    token_hash = hashlib.sha256(raw_token.encode()).hexdigest()

    new_claim_link = ClaimLinkModel(
        allocation_id=allocation.id,
        token_hash=token_hash,
        event_id=event_id,
        event_day_id=event_day_id,
        from_holder_id=customer_a_id,
        to_holder_id=customer_b.id,
        status=ClaimLinkStatus.active,
        created_by_holder_id=customer_a_id,
    )
    self._session.add(new_claim_link)
    await self._session.flush()

    # Send mock notifications to Customer B
    claim_link_url = f"/claim/{raw_token}"
    await mock_send_whatsapp(to_email, f"Your claim link: {claim_link_url}")
    await mock_send_email(to_email, f"Your claim link: {claim_link_url}")

    # Return response
    return SplitClaimResponse(
        status="completed",
        tickets_transferred=ticket_count,
        remaining_ticket_count=len(remaining_tickets),
        new_jwt=new_jwt,
        message="Your previous QR code is no longer valid. Please use the new QR code for entry.",
    )
```

---

### Task 6: Add Split Endpoint in public_urls.py

**Files:**
- Modify: `src/apps/event/public_urls.py`

- [ ] **Step 1: Read current public_urls.py**

Note the `claim_router` structure.

- [ ] **Step 2: Update imports**

Add `SplitClaimRequest`, `SplitClaimResponse`:

```python
from .request import CreateDraftEventRequest, CreateEventDayRequest, UpdateEventBasicInfoRequest, UpdateEventDayRequest, UpdateMediaAssetMetadataRequest, UpdateShowTicketsRequest, CreateResellerInviteRequest, SplitClaimRequest
from .response import EventInterestResponse, EventSummaryResponse, EventDetailResponse, ClaimRedemptionResponse, SplitClaimResponse
```

- [ ] **Step 3: Add split endpoint**

In `claim_router`:

```python
@claim_router.post("/{token}/split", operation_id="split_claim")
async def split_claim(
    token: str,
    body: Annotated[SplitClaimRequest, Body()],
    service: Annotated[ClaimService, Depends(get_claim_service)],
) -> BaseResponse[SplitClaimResponse]:
    """
    [PUBLIC — No Auth Required]

    Split tickets from Customer A (identified by claim token) to Customer B.
    Customer A's old JWT is revoked, new JWT is issued with remaining tickets.
    Customer B receives a new claim link.

    Request:
        to_email: Customer B's email
        ticket_count: Number of tickets to transfer

    Returns:
        SplitClaimResponse with new JWT for Customer A
    """
    result = await service.split_claim(
        raw_token=token,
        to_email=body.to_email,
        ticket_count=body.ticket_count,
    )
    return BaseResponse(data=result)
```

---

### Task 7: Verify All Imports and Run Tests

- [ ] **Step 1: Import check**

Run: `uv run python -c "from apps.event.claim_service import ClaimService; from apps.event.public_urls import claim_router; print('OK')"`
Expected: No errors

- [ ] **Step 2: Run all event tests**

Run: `uv run pytest tests/apps/event/ -v --tb=short`
Expected: All pass

- [ ] **Step 3: Run allocation tests**

Run: `uv run pytest tests/apps/allocation/ -v --tb=short`
Expected: All pass

---

## Verification

1. **Import check:**
   ```
   uv run python -c "from apps.event.claim_service import ClaimService; print('OK')"
   ```

2. **Tests pass:**
   ```
   uv run pytest tests/apps/event/ tests/apps/allocation/ -v --tb=short
   ```

3. **Manual API test (future):**
   ```
   POST /api/open/claim/{token}/split
   { "to_email": "test@example.com", "ticket_count": 2 }
   ```

---

## Files Modified

| File | Change |
|------|--------|
| `src/apps/event/request.py` | Added `SplitClaimRequest` |
| `src/apps/event/response.py` | Added `SplitClaimResponse` |
| `src/apps/event/public_urls.py` | Added `POST /api/open/claim/{token}/split` |
| `src/apps/event/claim_service.py` | Added `split_claim()` method |
| `src/apps/allocation/repository.py` | Added `revoke_claim_link()`, `add_revoked_jti()` |

---

## Execution Options

**1. Subagent-Driven (recommended)** — I dispatch a fresh subagent per task, review between tasks

**2. Inline Execution** — Execute tasks in this session using executing-plans

**Which approach?**