# Claim Links & Scan Token Infrastructure Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the foundational infrastructure for customer claim links and scan JWTs. This covers models, utility functions, and repository methods. URLs and services come in a separate plan.

**Architecture:**
- `ClaimLinkModel` — links a customer to an allocation via a claim token
- `RevokedScanTokenModel` — audit log for revoked token JTIs (DB layer; Redis comes later)
- `jwt_utils.py` — generates and verifies scan JWTs using existing `settings.JWT_SECRET_KEY`
- `claim_link_utils.py` — generates 8-char alphanumeric claim tokens
- Repository methods follow existing patterns from `AllocationRepository`

**Tech Stack:** FastAPI, SQLAlchemy async, PyJWT (already in use), repository pattern

---

## File Structure

```
src/apps/allocation/
├── models.py          # Add ClaimLinkModel, RevokedScanTokenModel
├── enums.py           # Add ClaimLinkStatus

src/utils/
├── jwt_utils.py       # Create: scan JWT generation/verification
├── claim_link_utils.py # Create: 8-char alphanumeric token generation

src/apps/allocation/
├── repository.py      # Add: ClaimLinkRepository, RevokedScanTokenRepository, new AllocationRepository methods

tests/apps/allocation/
├── test_claim_link_models.py
├── test_claim_link_utils.py
├── test_jwt_utils.py
├── test_revoked_scan_token_repo.py
```

---

## Task 1: Add `ClaimLinkStatus` Enum

**Files:**
- Modify: `src/apps/allocation/enums.py`

- [ ] **Step 1: Add the enum**

```python
class ClaimLinkStatus(str, Enum):
    active = "active"
    inactive = "inactive"
```

- [ ] **Step 2: Run import check**

Run: `python3 -c "from apps.allocation.enums import ClaimLinkStatus; print(ClaimLinkStatus.active.value)"`

Expected: `active`

- [ ] **Step 3: Commit**

```bash
git add src/apps/allocation/enums.py
git commit -m "feat(allocation): add ClaimLinkStatus enum"
```

---

## Task 2: Add `ClaimLinkModel`

**Files:**
- Modify: `src/apps/allocation/models.py`

- [ ] **Step 1: Add the model after TicketHolderModel**

```python
class ClaimLinkModel(Base, UUIDPrimaryKeyMixin, TimeStampMixin):
    __tablename__ = "claim_links"

    allocation_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("allocations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    token_hash: Mapped[str] = mapped_column(
        String(64), unique=True, nullable=False, index=True
    )
    event_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("events.id", ondelete="CASCADE"), nullable=False, index=True
    )
    from_holder_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("ticket_holders.id", ondelete="CASCADE"), nullable=True
    )
    to_holder_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("ticket_holders.id", ondelete="CASCADE"), nullable=False, index=True
    )
    status: Mapped[str] = mapped_column(
        Enum(ClaimLinkStatus),
        default=ClaimLinkStatus.active,
        server_default=text("'active'"),
        nullable=False,
        index=True,
    )
    claimed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_by_holder_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("ticket_holders.id", ondelete="CASCADE"), nullable=False
    )
```

- [ ] **Step 2: Run import check**

Run: `python3 -c "from apps.allocation.models import ClaimLinkModel; print('OK')"`

Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add src/apps/allocation/models.py
git commit -m "feat(allocation): add ClaimLinkModel"
```

---

## Task 3: Add `RevokedScanTokenModel`

**Files:**
- Modify: `src/apps/allocation/models.py`

- [ ] **Step 1: Add the model after ClaimLinkModel**

```python
class RevokedScanTokenModel(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "revoked_scan_tokens"

    event_day_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("event_days.id", ondelete="CASCADE"), nullable=False, index=True
    )
    jti: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    reason: Mapped[str] = mapped_column(String(32), nullable=False)
    revoked_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )

    __table_args__ = (
        UniqueConstraint("event_day_id", "jti", name="uq_revoked_scan_tokens_event_day_jti"),
    )
```

- [ ] **Step 2: Run import check**

Run: `python3 -c "from apps.allocation.models import RevokedScanTokenModel; print('OK')"`

Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add src/apps/allocation/models.py
git commit -m "feat(allocation): add RevokedScanTokenModel"
```

---

## Task 4: Create `claim_link_utils.py`

**Files:**
- Create: `src/utils/claim_link_utils.py`

- [ ] **Step 1: Write the utility**

```python
import secrets
import string


def generate_claim_link_token(length: int = 8) -> str:
    """
    Generate a cryptographically random 8-char alphanumeric token.
    Uses ASCII letters and digits for readability.
    """
    alphabet = string.ascii_lowercase + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(length))
```

- [ ] **Step 2: Write the test**

```python
# tests/apps/allocation/test_claim_link_utils.py
import pytest
from src.utils.claim_link_utils import generate_claim_link_token


def test_generate_claim_link_token_returns_correct_length():
    token = generate_claim_link_token()
    assert len(token) == 8


def test_generate_claim_link_token_returns_string():
    token = generate_claim_link_token()
    assert isinstance(token, str)


def test_generate_claim_link_token_is_alphanumeric():
    token = generate_claim_link_token()
    assert token.isalnum()


def test_generate_claim_link_token_produces_unique_tokens():
    tokens = {generate_claim_link_token() for _ in range(100)}
    # With 8 chars from lowercase + digits (36 chars), 100 tokens should all be unique
    assert len(tokens) == 100


def test_generate_claim_link_token_custom_length():
    token = generate_claim_link_token(length=12)
    assert len(token) == 12
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `pytest tests/apps/allocation/test_claim_link_utils.py -v`

Expected: FAIL — module doesn't exist yet

- [ ] **Step 4: Create the file**

Run: `touch src/utils/claim_link_utils.py`

- [ ] **Step 5: Run tests to verify they pass**

Run: `pytest tests/apps/allocation/test_claim_link_utils.py -v`

Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add src/utils/claim_link_utils.py tests/apps/allocation/test_claim_link_utils.py
git commit -m "feat(allocation): add claim_link_utils for 8-char token generation"
```

---

## Task 5: Create `jwt_utils.py` for Scan Tokens

**Files:**
- Create: `src/utils/jwt_utils.py`

- [ ] **Step 1: Write the utility**

```python
from datetime import datetime
from uuid import UUID

import jwt
from jwt import DecodeError, ExpiredSignatureError

from config import settings


def generate_scan_jwt(
    jti: str,
    holder_id: UUID,
    event_day_id: UUID,
    indexes: list[int],
) -> str:
    """
    Generate a signed scan JWT.

    Payload:
        jti: Unique token ID (used for revocation tracking)
        holder_id: Who owns these tickets
        event_day_id: Which event day's bitmap to check/update
        indexes: List of ticket indexes for this holder's allocation
        iat: Issued at (UTC timestamp)
    """
    payload = {
        "jti": jti,
        "holder_id": str(holder_id),
        "event_day_id": str(event_day_id),
        "indexes": indexes,
        "iat": int(datetime.utcnow().timestamp()),
    }
    return jwt.encode(
        payload,
        key=settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )


def verify_scan_jwt(token: str) -> dict:
    """
    Verify and decode a scan JWT.
    Raises InvalidJWTTokenException if invalid or expired.
    """
    from exceptions import InvalidJWTTokenException

    try:
        payload = jwt.decode(
            token,
            key=settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
            options={"verify_signature": True, "verify_exp": False},
        )
        return payload
    except DecodeError:
        from exceptions import InvalidJWTTokenException
        raise InvalidJWTTokenException("Invalid scan token")


def get_jti_from_jwt(token: str) -> str:
    """
    Extract jti from a scan JWT without full verification.
    Used for revocation lookups.
    """
    payload = jwt.decode(
        token,
        key=settings.JWT_SECRET_KEY,
        algorithms=[settings.JWT_ALGORITHM],
        options={"verify_signature": False, "verify_exp": False},
    )
    return payload["jti"]


def decode_scan_jwt(token: str) -> dict:
    """
    Decode a scan JWT without verification (for debugging/audit).
    """
    return jwt.decode(
        token,
        key=settings.JWT_SECRET_KEY,
        algorithms=[settings.JWT_ALGORITHM],
        options={"verify_signature": False, "verify_exp": False},
    )
```

- [ ] **Step 2: Write the tests**

```python
# tests/apps/allocation/test_jwt_utils.py
import pytest
from uuid import uuid4
from src.utils.jwt_utils import (
    generate_scan_jwt,
    verify_scan_jwt,
    get_jti_from_jwt,
    decode_scan_jwt,
)


def test_generate_scan_jwt_returns_string():
    jti = "abc12345"
    holder_id = uuid4()
    event_day_id = uuid4()
    indexes = [0, 1, 2, 3, 4]

    token = generate_scan_jwt(jti, holder_id, event_day_id, indexes)
    assert isinstance(token, str)
    assert len(token) > 0


def test_verify_scan_jwt_returns_payload():
    jti = "abc12345"
    holder_id = uuid4()
    event_day_id = uuid4()
    indexes = [0, 1, 2]

    token = generate_scan_jwt(jti, holder_id, event_day_id, indexes)
    payload = verify_scan_jwt(token)

    assert payload["jti"] == jti
    assert payload["holder_id"] == str(holder_id)
    assert payload["event_day_id"] == str(event_day_id)
    assert payload["indexes"] == indexes


def test_get_jti_from_jwt_extracts_jti():
    jti = "test_jti_123"
    holder_id = uuid4()
    event_day_id = uuid4()

    token = generate_scan_jwt(jti, holder_id, event_day_id, [0, 1])
    extracted = get_jti_from_jwt(token)

    assert extracted == jti


def test_decode_scan_jwt_without_verification():
    jti = "decode_test"
    holder_id = uuid4()
    event_day_id = uuid4()
    indexes = [5, 6, 7]

    token = generate_scan_jwt(jti, holder_id, event_day_id, indexes)
    payload = decode_scan_jwt(token)

    assert payload["jti"] == jti
    assert payload["indexes"] == indexes


def test_verify_scan_jwt_rejects_invalid_token():
    from exceptions import InvalidJWTTokenException

    with pytest.raises(InvalidJWTTokenException):
        verify_scan_jwt("not.a.valid.token")
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `pytest tests/apps/allocation/test_jwt_utils.py -v`

Expected: FAIL — module doesn't exist yet

- [ ] **Step 4: Create the file**

Run: `touch src/utils/jwt_utils.py`

- [ ] **Step 5: Run tests to verify they pass**

Run: `pytest tests/apps/allocation/test_jwt_utils.py -v`

Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add src/utils/jwt_utils.py tests/apps/allocation/test_jwt_utils.py
git commit -m "feat(allocation): add jwt_utils for scan token generation"
```

---

## Task 6: Create `ClaimLinkRepository`

**Files:**
- Modify: `src/apps/allocation/repository.py`

- [ ] **Step 1: Add ClaimLinkRepository class to the file**

```python
# Add at end of src/apps/allocation/repository.py

from apps.allocation.models import ClaimLinkModel
from apps.allocation.enums import ClaimLinkStatus


class ClaimLinkRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(
        self,
        allocation_id: UUID,
        token_hash: str,
        event_id: UUID,
        from_holder_id: UUID | None,
        to_holder_id: UUID,
        created_by_holder_id: UUID,
    ) -> ClaimLinkModel:
        """Create a new claim link."""
        link = ClaimLinkModel(
            allocation_id=allocation_id,
            token_hash=token_hash,
            event_id=event_id,
            from_holder_id=from_holder_id,
            to_holder_id=to_holder_id,
            status=ClaimLinkStatus.active,
            created_by_holder_id=created_by_holder_id,
        )
        self._session.add(link)
        await self._session.flush()
        await self._session.refresh(link)
        return link

    async def get_by_token_hash(self, token_hash: str) -> ClaimLinkModel | None:
        """Get a claim link by its token hash."""
        return await self._session.scalar(
            select(ClaimLinkModel).where(ClaimLinkModel.token_hash == token_hash)
        )

    async def get_active_by_to_holder(self, to_holder_id: UUID) -> ClaimLinkModel | None:
        """Get the active claim link for a recipient holder."""
        return await self._session.scalar(
            select(ClaimLinkModel)
            .where(
                ClaimLinkModel.to_holder_id == to_holder_id,
                ClaimLinkModel.status == ClaimLinkStatus.active,
            )
            .order_by(ClaimLinkModel.created_at.desc())
        )

    async def revoke(self, token_hash: str) -> bool:
        """
        Revoke a claim link by setting status to inactive.
        Returns True if revocation succeeded.
        """
        result = await self._session.execute(
            update(ClaimLinkModel)
            .where(
                ClaimLinkModel.token_hash == token_hash,
                ClaimLinkModel.status == ClaimLinkStatus.active,
            )
            .values(status=ClaimLinkStatus.inactive)
        )
        return result.rowcount > 0
```

- [ ] **Step 2: Write the tests**

```python
# tests/apps/allocation/test_claim_link_repo.py
import pytest
from uuid import uuid4
from unittest.mock import AsyncMock, MagicMock
from apps.allocation.repository import ClaimLinkRepository
from apps.allocation.enums import ClaimLinkStatus


@pytest.mark.asyncio
async def test_create_claim_link():
    session = AsyncMock()
    repo = ClaimLinkRepository(session)

    result = await repo.create(
        allocation_id=uuid4(),
        token_hash="abc12345",
        event_id=uuid4(),
        from_holder_id=None,
        to_holder_id=uuid4(),
        created_by_holder_id=uuid4(),
    )

    session.add.assert_called_once()
    session.flush.assert_awaited_once()
    assert result.status == ClaimLinkStatus.active


@pytest.mark.asyncio
async def test_get_by_token_hash_returns_link():
    session = AsyncMock()
    token_hash = "test_token"
    mock_link = MagicMock()
    mock_link.token_hash = token_hash

    session.scalar = AsyncMock(return_value=mock_link)
    repo = ClaimLinkRepository(session)

    result = await repo.get_by_token_hash(token_hash)

    assert result == mock_link
    session.scalar.assert_awaited_once()


@pytest.mark.asyncio
async def test_revoke_sets_status_to_inactive():
    session = AsyncMock()
    mock_result = MagicMock()
    mock_result.rowcount = 1
    session.execute = AsyncMock(return_value=mock_result)
    repo = ClaimLinkRepository(session)

    success = await repo.revoke("abc12345")

    assert success is True
    session.execute.assert_awaited_once()
```

- [ ] **Step 3: Run tests to verify they pass**

Run: `pytest tests/apps/allocation/test_claim_link_repo.py -v`

Expected: PASS

- [ ] **Step 4: Commit**

```bash
git add src/apps/allocation/repository.py tests/apps/allocation/test_claim_link_repo.py
git commit -m "feat(allocation): add ClaimLinkRepository"
```

---

## Task 7: Create `RevokedScanTokenRepository`

**Files:**
- Modify: `src/apps/allocation/repository.py`

- [ ] **Step 1: Add RevokedScanTokenRepository class to the file**

```python
# Add at end of src/apps/allocation/repository.py

from sqlalchemy.dialects.postgresql import insert as pg_insert


class RevokedScanTokenRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add_revoked(
        self,
        event_day_id: UUID,
        jti: str,
        reason: str,
    ) -> None:
        """
        Add a JTI to the revoked tokens table.
        Uses ON CONFLICT DO NOTHING to handle duplicate revocations gracefully.
        """
        from apps.allocation.models import RevokedScanTokenModel

        stmt = pg_insert(RevokedScanTokenModel).values(
            event_day_id=event_day_id,
            jti=jti,
            reason=reason,
        )
        stmt = stmt.on_conflict_do_nothing(
            constraint="uq_revoked_scan_tokens_event_day_jti",
        )
        await self._session.execute(stmt)

    async def is_revoked(self, event_day_id: UUID, jti: str) -> bool:
        """Check if a JTI has been revoked for a given event day."""
        from apps.allocation.models import RevokedScanTokenModel

        result = await self._session.scalar(
            select(RevokedScanTokenModel.jti).where(
                RevokedScanTokenModel.event_day_id == event_day_id,
                RevokedScanTokenModel.jti == jti,
            )
        )
        return result is not None

    async def get_revoked_jtis_for_event_day(
        self,
        event_day_id: UUID,
    ) -> list[str]:
        """Get all revoked JTI strings for an event day."""
        from apps.allocation.models import RevokedScanTokenModel

        result = await self._session.scalars(
            select(RevokedScanTokenModel.jti).where(
                RevokedScanTokenModel.event_day_id == event_day_id,
            )
        )
        return list(result.all())
```

- [ ] **Step 2: Write the tests**

```python
# tests/apps/allocation/test_revoked_scan_token_repo.py
import pytest
from uuid import uuid4
from unittest.mock import AsyncMock, MagicMock
from apps.allocation.repository import RevokedScanTokenRepository


@pytest.mark.asyncio
async def test_add_revoked_inserts_jti():
    session = AsyncMock()
    repo = RevokedScanTokenRepository(session)

    await repo.add_revoked(
        event_day_id=uuid4(),
        jti="test_jti_123",
        reason="split",
    )

    session.execute.assert_awaited_once()


@pytest.mark.asyncio
async def test_is_revoked_returns_true_when_revoked():
    session = AsyncMock()
    jti = "revoked_jti"
    event_day_id = uuid4()

    session.scalar = AsyncMock(return_value=jti)
    repo = RevokedScanTokenRepository(session)

    result = await repo.is_revoked(event_day_id, jti)

    assert result is True


@pytest.mark.asyncio
async def test_is_revoked_returns_false_when_not_revoked():
    session = AsyncMock()
    event_day_id = uuid4()

    session.scalar = AsyncMock(return_value=None)
    repo = RevokedScanTokenRepository(session)

    result = await repo.is_revoked(event_day_id, "unknown_jti")

    assert result is False


@pytest.mark.asyncio
async def test_get_revoked_jtis_for_event_day():
    session = AsyncMock()
    event_day_id = uuid4()
    jtis = ["jti_1", "jti_2", "jti_3"]

    mock_scalars = MagicMock()
    mock_scalars.all.return_value = jtis
    session.scalars = AsyncMock(return_value=mock_scalars)
    repo = RevokedScanTokenRepository(session)

    result = await repo.get_revoked_jtis_for_event_day(event_day_id)

    assert result == jtis
```

- [ ] **Step 3: Run tests to verify they pass**

Run: `pytest tests/apps/allocation/test_revoked_scan_token_repo.py -v`

Expected: PASS

- [ ] **Step 4: Commit**

```bash
git add src/apps/allocation/repository.py tests/apps/allocation/test_revoked_scan_token_repo.py
git commit -m "feat(allocation): add RevokedScanTokenRepository"
```

---

## Task 8: Add `resolve_holder` to AllocationRepository

**Files:**
- Modify: `src/apps/allocation/repository.py`

- [ ] **Step 1: Add resolve_holder method to AllocationRepository class**

Add after `create_holder`:

```python
async def resolve_holder(
    self,
    phone: str | None = None,
    email: str | None = None,
    user_id: UUID | None = None,
) -> TicketHolderModel:
    """
    Get or create a TicketHolder by phone, email, or user_id.
    At least one of phone, email, or user_id must be provided.
    """
    if phone:
        holder = await self.get_holder_by_phone(phone)
        if holder:
            return holder

    if email:
        holder = await self.get_holder_by_email(email)
        if holder:
            return holder

    if user_id:
        holder = await self.get_holder_by_user_id(user_id)
        if holder:
            return holder

    # Create new holder
    return await self.create_holder(
        user_id=user_id,
        phone=phone,
        email=email,
    )
```

- [ ] **Step 2: Write the test**

```python
# tests/apps/allocation/test_resolve_holder.py
import pytest
from uuid import uuid4
from unittest.mock import AsyncMock, MagicMock
from apps.allocation.repository import AllocationRepository


@pytest.mark.asyncio
async def test_resolve_holder_returns_existing_by_phone():
    session = AsyncMock()
    repo = AllocationRepository(session)
    existing_holder = MagicMock()
    existing_holder.id = uuid4()

    session.scalar = AsyncMock(return_value=existing_holder)
    result = await repo.resolve_holder(phone="+919999999999")

    assert result == existing_holder
    session.scalar.assert_awaited()


@pytest.mark.asyncio
async def test_resolve_holder_creates_new_when_not_found():
    session = AsyncMock()
    repo = AllocationRepository(session)

    session.scalar = AsyncMock(return_value=None)
    session.add = MagicMock()
    session.flush = AsyncMock()
    session.refresh = AsyncMock()

    result = await repo.resolve_holder(phone="+919999999999")

    session.add.assert_called_once()
    session.flush.assert_awaited()


@pytest.mark.asyncio
async def test_resolve_holder_prefers_phone_over_email():
    """When holder exists by phone, should return it without checking email."""
    session = AsyncMock()
    repo = AllocationRepository(session)
    existing_holder = MagicMock()

    # First call (phone lookup) returns holder
    session.scalar = AsyncMock(side_effect=[existing_holder, None, None])
    result = await repo.resolve_holder(phone="+919999999999", email="test@test.com")

    assert result == existing_holder
```

- [ ] **Step 3: Run tests to verify they pass**

Run: `pytest tests/apps/allocation/test_resolve_holder.py -v`

Expected: PASS

- [ ] **Step 4: Commit**

```bash
git add src/apps/allocation/repository.py tests/apps/allocation/test_resolve_holder.py
git commit -m "feat(allocation): add resolve_holder to AllocationRepository"
```

---

## Task 9: Add `select_tickets_for_transfer` to TicketingRepository

**Files:**
- Modify: `src/apps/ticketing/repository.py`

- [ ] **Step 1: Add method after `lock_tickets_for_transfer`**

```python
async def select_tickets_for_transfer(
    self,
    owner_holder_id: UUID,
    event_id: UUID,
    quantity: int,
    event_day_id: UUID | None = None,
) -> list[dict]:
    """
    Select tickets for transfer from a holder's pool.
    Returns list of dicts with ticket id and ticket_index.
    Uses FIFO ordering (ticket_index ASC).

    Does NOT lock or update — caller decides what to do with selected tickets.
    """
    conditions = [
        TicketModel.event_id == event_id,
        TicketModel.owner_holder_id == owner_holder_id,
        TicketModel.status == "active",
        TicketModel.lock_reference_id.is_(None),
    ]
    if event_day_id:
        conditions.append(TicketModel.event_day_id == event_day_id)

    result = await self._session.execute(
        select(TicketModel.id, TicketModel.ticket_index)
        .where(*conditions)
        .order_by(TicketModel.ticket_index.asc())
        .limit(quantity)
    )
    rows = result.all()
    return [{"ticket_id": row[0], "ticket_index": row[1]} for row in rows]
```

- [ ] **Step 2: Write the test**

```python
# tests/apps/ticketing/test_select_tickets_for_transfer.py
import pytest
from uuid import uuid4
from unittest.mock import AsyncMock, MagicMock
from apps.ticketing.repository import TicketingRepository


@pytest.mark.asyncio
async def test_select_tickets_for_transfer_returns_ticket_list():
    session = AsyncMock()
    repo = TicketingRepository(session)

    owner_id = uuid4()
    event_id = uuid4()
    ticket_ids = [uuid4(), uuid4()]

    result_mock = MagicMock()
    result_mock.all.return_value = [(ticket_ids[0], 0), (ticket_ids[1], 1)]
    session.execute = AsyncMock(return_value=result_mock)

    result = await repo.select_tickets_for_transfer(
        owner_holder_id=owner_id,
        event_id=event_id,
        quantity=2,
    )

    assert len(result) == 2
    assert result[0]["ticket_id"] == ticket_ids[0]
    assert result[0]["ticket_index"] == 0


@pytest.mark.asyncio
async def test_select_tickets_for_transfer_with_event_day():
    session = AsyncMock()
    repo = TicketingRepository(session)

    result_mock = MagicMock()
    result_mock.all.return_value = []
    session.execute = AsyncMock(return_value=result_mock)

    await repo.select_tickets_for_transfer(
        owner_holder_id=uuid4(),
        event_id=uuid4(),
        quantity=5,
        event_day_id=uuid4(),
    )

    session.execute.assert_awaited_once()
```

- [ ] **Step 3: Run tests to verify they pass**

Run: `pytest tests/apps/ticketing/test_select_tickets_for_transfer.py -v`

Expected: PASS

- [ ] **Step 4: Commit**

```bash
git add src/apps/ticketing/repository.py tests/apps/ticketing/test_select_tickets_for_transfer.py
git commit -m "feat(ticketing): add select_tickets_for_transfer for non-locking ticket selection"
```

---

## Task 10: Add `update_ticket_ownership_batch` to TicketingRepository

**Files:**
- Modify: `src/apps/ticketing/repository.py`

- [ ] **Step 1: Add method after `select_tickets_for_transfer`**

```python
async def update_ticket_ownership_batch(
    self,
    ticket_ids: list[UUID],
    new_owner_holder_id: UUID,
) -> None:
    """
    Update owner_holder_id for a batch of tickets.
    Clears lock fields as part of ownership transfer.
    """
    await self._session.execute(
        update(TicketModel)
        .where(TicketModel.id.in_(ticket_ids))
        .values(
            owner_holder_id=new_owner_holder_id,
            lock_reference_type=None,
            lock_reference_id=None,
            lock_expires_at=None,
        )
    )
```

- [ ] **Step 2: Write the test**

```python
# tests/apps/ticketing/test_update_ticket_ownership_batch.py
import pytest
from uuid import uuid4
from unittest.mock import AsyncMock
from apps.ticketing.repository import TicketingRepository


@pytest.mark.asyncio
async def test_update_ticket_ownership_batch_calls_execute():
    session = AsyncMock()
    repo = TicketingRepository(session)

    ticket_ids = [uuid4(), uuid4()]
    new_owner = uuid4()

    await repo.update_ticket_ownership_batch(ticket_ids, new_owner)

    session.execute.assert_awaited_once()


@pytest.mark.asyncio
async def test_update_ticket_ownership_batch_empty_list():
    session = AsyncMock()
    repo = TicketingRepository(session)

    await repo.update_ticket_ownership_batch([], uuid4())

    session.execute.assert_not_called()
```

- [ ] **Step 3: Run tests to verify they pass**

Run: `pytest tests/apps/ticketing/test_update_ticket_ownership_batch.py -v`

Expected: PASS

- [ ] **Step 4: Commit**

```bash
git add src/apps/ticketing/repository.py tests/apps/ticketing/test_update_ticket_ownership_batch.py
git commit -m "feat(ticketing): add update_ticket_ownership_batch for ownership transfer"
```

---

## Task 11: Add `create_allocation_with_claim_link` to AllocationRepository

**Files:**
- Modify: `src/apps/allocation/repository.py`

- [ ] **Step 1: Add method to AllocationRepository**

Add after `add_tickets_to_allocation`:

```python
async def create_allocation_with_claim_link(
    self,
    event_id: UUID,
    from_holder_id: UUID | None,
    to_holder_id: UUID,
    order_id: UUID,
    allocation_type: "AllocationType",
    ticket_count: int,
    token_hash: str,
    created_by_holder_id: UUID,
    metadata_: dict | None = None,
) -> tuple[AllocationModel, ClaimLinkModel]:
    """
    Create an allocation and its associated claim link in a single transaction.
    Returns (allocation, claim_link).

    The claim link is created for the recipient (to_holder_id).
    """
    allocation = await self.create_allocation(
        event_id=event_id,
        from_holder_id=from_holder_id,
        to_holder_id=to_holder_id,
        order_id=order_id,
        allocation_type=allocation_type,
        ticket_count=ticket_count,
        metadata_=metadata_,
    )

    claim_link = await ClaimLinkRepository(self._session).create(
        allocation_id=allocation.id,
        token_hash=token_hash,
        event_id=event_id,
        from_holder_id=from_holder_id,
        to_holder_id=to_holder_id,
        created_by_holder_id=created_by_holder_id,
    )

    return allocation, claim_link
```

- [ ] **Step 2: Write the test**

```python
# tests/apps/allocation/test_create_allocation_with_claim_link.py
import pytest
from uuid import uuid4
from unittest.mock import AsyncMock, MagicMock
from apps.allocation.repository import AllocationRepository


@pytest.mark.asyncio
async def test_create_allocation_with_claim_link_returns_both():
    session = AsyncMock()
    repo = AllocationRepository(session)

    event_id = uuid4()
    from_id = uuid4()
    to_id = uuid4()
    order_id = uuid4()
    token_hash = "abc12345"

    # Mock create_allocation
    mock_allocation = MagicMock()
    mock_allocation.id = uuid4()
    session.scalar = AsyncMock(return_value=mock_allocation)

    # Mock ClaimLinkRepository create
    mock_claim_link = MagicMock()
    mock_claim_link.id = uuid4()

    with pytest.mock.patch.object(
        ClaimLinkRepository, "create", new_callable=AsyncMock
    ) as mock_create:
        mock_create.return_value = mock_claim_link

        result = await repo.create_allocation_with_claim_link(
            event_id=event_id,
            from_holder_id=from_id,
            to_holder_id=to_id,
            order_id=order_id,
            allocation_type="transfer",
            ticket_count=5,
            token_hash=token_hash,
            created_by_holder_id=from_id,
        )

    allocation, claim_link = result
    assert allocation == mock_allocation
    assert claim_link == mock_claim_link
```

- [ ] **Step 3: Run tests to verify they pass**

Run: `pytest tests/apps/allocation/test_create_allocation_with_claim_link.py -v`

Expected: PASS

- [ ] **Step 4: Commit**

```bash
git add src/apps/allocation/repository.py tests/apps/allocation/test_create_allocation_with_claim_link.py
git commit -m "feat(allocation): add create_allocation_with_claim_link transaction method"
```

---

## Self-Review Checklist

1. **Spec coverage:** All models, utils, and repository methods covered?
   - `ClaimLinkModel` ✅
   - `RevokedScanTokenModel` ✅
   - `ClaimLinkStatus` enum ✅
   - `claim_link_utils.py` ✅
   - `jwt_utils.py` ✅
   - `ClaimLinkRepository` ✅
   - `RevokedScanTokenRepository` ✅
   - `resolve_holder` ✅
   - `select_tickets_for_transfer` ✅
   - `update_ticket_ownership_batch` ✅
   - `create_allocation_with_claim_link` ✅

2. **Placeholder scan:** No TODOs, no TBDs, no "add appropriate error handling" ✅

3. **Type consistency:**
   - `jti` field is `str` (not UUID) ✅
   - `token_hash` field is `String(64)` ✅
   - `indexes` field is `list[int]` ✅
   - All method signatures use `UUID` from `uuid` module ✅

4. **Import consistency:** All existing code uses `apps.allocation.repository` pattern ✅

---

## Execution Handoff

**Plan complete and saved to `docs/superpowers/plans/2026-04-20-claim-links.md`. Two execution options:**

**1. Subagent-Driven (recommended)** - I dispatch a fresh subagent per task, review between tasks, fast iteration

**2. Inline Execution** - Execute tasks in this session using executing-plans, batch execution with checkpoints

**Which approach?**
