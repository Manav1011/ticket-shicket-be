# Reseller Module Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement reseller authorization per-event. Organizers can invite users as resellers to their events. Users accept/decline invites to become authorized resellers for specific events.

**Architecture:**
- `invites` table + model/repository/service in `apps/user/invite/` — generic invite system
- `event_resellers` table in `apps/event/models.py` — per-event authorization
- Invite endpoints in `apps/event/urls.py` calling `apps/user/invite/service`
- Invite status flow: pending → accepted/declined/cancelled

**Tech Stack:** Python, SQLAlchemy, FastAPI, PostgreSQL (via existing db.session)

---

## File Structure

**Create:**
- `src/apps/user/invite/__init__.py`
- `src/apps/user/invite/enums.py`
- `src/apps/user/invite/models.py`
- `src/apps/user/invite/repository.py`
- `src/apps/user/invite/service.py`
- `src/apps/user/invite/exceptions.py`
- `src/apps/user/invite/request.py`
- `src/apps/user/invite/response.py`
- `tests/apps/user/invite/test_invite_enums.py`
- `tests/apps/user/invite/test_invite_models.py`
- `tests/apps/user/invite/test_invite_service.py`
- `tests/apps/user/invite/conftest.py`

**Modify:**
- `src/apps/event/models.py` — add EventResellerModel
- `src/apps/event/repository.py` — add event reseller methods
- `src/apps/event/service.py` — add reseller invite methods
- `src/apps/event/urls.py` — add invite endpoints
- `src/apps/event/enums.py` — add InviteStatus enum
- `src/apps/user/repository.py` — add find_by_email, find_by_phone
- `src/server.py` — router registration (invite router from user app)
- `src/migrations/versions/<new_uuid>_add_invites_and_event_resellers_tables.py`

---

### Task 1: Create Invite Enums

**Files:**
- Create: `src/apps/user/invite/enums.py`
- Test: `tests/apps/user/invite/test_invite_enums.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/apps/user/invite/test_invite_enums.py
import pytest
from apps.user.invite.enums import InviteStatus


def test_invite_status_values():
    assert InviteStatus.pending == "pending"
    assert InviteStatus.accepted == "accepted"
    assert InviteStatus.declined == "declined"
    assert InviteStatus.cancelled == "cancelled"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/apps/user/invite/test_invite_enums.py -v`
Expected: FAIL — ImportError: cannot import 'apps.user.invite'

- [ ] **Step 3: Write minimal implementation**

```python
# src/apps/user/invite/enums.py
from enum import Enum


class InviteStatus(str, Enum):
    pending = "pending"
    accepted = "accepted"
    declined = "declined"
    cancelled = "cancelled"
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/apps/user/invite/test_invite_enums.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/apps/user/invite/enums.py tests/apps/user/invite/test_invite_enums.py
git commit -m "feat: add invite status enum"
```

---

### Task 2: Create Invite Model

**Files:**
- Create: `src/apps/user/invite/models.py`
- Test: `tests/apps/user/invite/test_invite_models.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/apps/user/invite/test_invite_models.py
import pytest
import uuid
from datetime import datetime
from apps.user.invite.models import InviteModel


def test_invite_model_creation():
    invite = InviteModel(
        id=uuid.uuid4(),
        target_user_id=uuid.uuid4(),
        created_by_id=uuid.uuid4(),
        status="pending",
        metadata={"event_id": str(uuid.uuid4())},
    )
    assert invite.status == "pending"
    assert isinstance(invite.metadata, dict)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/apps/user/invite/test_invite_models.py -v`
Expected: FAIL — cannot import 'apps.user.invite.models'

- [ ] **Step 3: Write minimal implementation**

```python
# src/apps/user/invite/models.py
import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from db.base import Base, TimeStampMixin, UUIDPrimaryKeyMixin


class InviteModel(Base, UUIDPrimaryKeyMixin, TimeStampMixin):
    __tablename__ = "invites"

    target_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True
    )
    created_by_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True
    )
    status: Mapped[str] = mapped_column(
        String(20), default="pending", nullable=False, index=True
    )
    metadata: Mapped[dict] = mapped_column(
        JSONB, default=dict, nullable=False, server_default="{}"
    )
    expires_at: Mapped[datetime | None] = mapped_column(nullable=True)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/apps/user/invite/test_invite_models.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/apps/user/invite/models.py tests/apps/user/invite/test_invite_models.py
git commit -m "feat: add invite model"
```

---

### Task 3: Create Invite Exceptions

**Files:**
- Create: `src/apps/user/invite/exceptions.py`
- Test: `tests/apps/user/invite/test_invite_exceptions.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/apps/user/invite/test_invite_exceptions.py
import pytest
from apps.user.invite.exceptions import InviteNotFound, InviteAlreadyProcessed, NotInviteRecipient


def test_invite_not_found():
    exc = InviteNotFound()
    assert exc.message == "Invite not found."


def test_invite_already_processed():
    exc = InviteAlreadyProcessed()
    assert exc.message == "Invite has already been processed."


def test_not_invite_recipient():
    exc = NotInviteRecipient()
    assert exc.message == "You are not the recipient of this invite."
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/apps/user/invite/test_invite_exceptions.py -v`
Expected: FAIL — cannot import 'apps.user.invite.exceptions'

- [ ] **Step 3: Write minimal implementation**

```python
# src/apps/user/invite/exceptions.py
from exceptions import NotFoundError, ConflictError, ForbiddenError


class InviteNotFound(NotFoundError):
    message = "Invite not found."


class InviteAlreadyProcessed(ConflictError):
    message = "Invite has already been processed."


class NotInviteRecipient(ForbiddenError):
    message = "You are not the recipient of this invite."
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/apps/user/invite/test_invite_exceptions.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/apps/user/invite/exceptions.py tests/apps/user/invite/test_invite_exceptions.py
git commit -m "feat: add invite exceptions"
```

---

### Task 4: Create Invite Repository

**Files:**
- Create: `src/apps/user/invite/repository.py`
- Test: `tests/apps/user/invite/test_invite_repository.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/apps/user/invite/test_invite_repository.py
import pytest
import uuid
from apps.user.invite.models import InviteModel
from apps.user.invite.repository import InviteRepository


@pytest.fixture
def invite_repository(session):
    return InviteRepository(session)


def test_add_invite(invite_repository):
    invite = InviteModel(
        id=uuid.uuid4(),
        target_user_id=uuid.uuid4(),
        created_by_id=uuid.uuid4(),
        status="pending",
        metadata={"event_id": str(uuid.uuid4())},
    )
    invite_repository.add(invite)
    assert invite.id is not None
    assert invite.status == "pending"


async def test_get_invite_by_id(invite_repository, sample_invite):
    invite = await invite_repository.get_invite_by_id(sample_invite.id)
    assert invite is not None
    assert invite.id == sample_invite.id


async def test_list_pending_invites_for_user(invite_repository, sample_invite, another_user_id):
    invites = await invite_repository.list_pending_invites_for_user(another_user_id)
    assert len(invites) >= 1
    assert any(i.id == sample_invite.id for i in invites)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/apps/user/invite/test_invite_repository.py -v`
Expected: FAIL — cannot import 'apps.user.invite.repository'

- [ ] **Step 3: Write minimal implementation**

```python
# src/apps/user/invite/repository.py
from typing import Optional
from uuid import UUID

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from .models import InviteModel


class InviteRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    @property
    def session(self) -> AsyncSession:
        return self._session

    def add(self, entity) -> None:
        self._session.add(entity)

    async def get_invite_by_id(self, invite_id: UUID) -> Optional[InviteModel]:
        return await self._session.scalar(
            select(InviteModel).where(InviteModel.id == invite_id)
        )

    async def list_pending_invites_for_user(self, user_id: UUID) -> list[InviteModel]:
        result = await self._session.scalars(
            select(InviteModel)
            .where(
                and_(
                    InviteModel.target_user_id == user_id,
                    InviteModel.status == "pending",
                )
            )
            .order_by(InviteModel.created_at.desc())
        )
        return list(result.all())

    async def update_invite_status(self, invite: InviteModel, status: str) -> None:
        invite.status = status
        await self._session.flush()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/apps/user/invite/test_invite_repository.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/apps/user/invite/repository.py tests/apps/user/invite/test_invite_repository.py
git commit -m "feat: add invite repository"
```

---

### Task 5: Create Invite Service

**Files:**
- Create: `src/apps/user/invite/service.py`
- Test: `tests/apps/user/invite/test_invite_service.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/apps/user/invite/test_invite_service.py
import pytest
import uuid
from unittest.mock import MagicMock
from apps.user.invite.service import InviteService


@pytest.fixture
def mock_user_repo():
    return MagicMock()


@pytest.fixture
def mock_invite_repo():
    return MagicMock()


@pytest.fixture
def invite_service(mock_user_repo, mock_invite_repo):
    return InviteService(repository=mock_invite_repo, user_repository=mock_user_repo)


async def test_list_pending_invites(invite_service, mock_user_repo):
    mock_user_repo.list_pending_invites_for_user = MagicMock(return_value=[])
    result = await invite_service.list_pending_invites_for_user(uuid.uuid4())
    assert isinstance(result, list)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/apps/user/invite/test_invite_service.py -v`
Expected: FAIL — cannot import 'apps.user.invite.service'

- [ ] **Step 3: Write minimal implementation**

```python
# src/apps/user/invite/service.py
from uuid import UUID

from .exceptions import InviteNotFound, InviteAlreadyProcessed, NotInviteRecipient
from .models import InviteModel
from .enums import InviteStatus


class InviteService:
    def __init__(self, repository, user_repository) -> None:
        self.repository = repository
        self.user_repository = user_repository

    async def create_invite(
        self,
        target_user_id: UUID,
        created_by_id: UUID,
        metadata: dict,
    ) -> InviteModel:
        invite = InviteModel(
            target_user_id=target_user_id,
            created_by_id=created_by_id,
            status=InviteStatus.pending.value,
            metadata=metadata,
        )
        self.repository.add(invite)
        await self.repository.session.flush()
        await self.repository.session.refresh(invite)
        return invite

    async def list_pending_invites_for_user(self, user_id: UUID) -> list[InviteModel]:
        return await self.repository.list_pending_invites_for_user(user_id)

    async def get_invite_by_id(self, invite_id: UUID) -> InviteModel:
        invite = await self.repository.get_invite_by_id(invite_id)
        if not invite:
            raise InviteNotFound
        return invite

    async def accept_invite(self, user_id: UUID, invite_id: UUID) -> dict:
        invite = await self.get_invite_by_id(invite_id)

        if invite.target_user_id != user_id:
            raise NotInviteRecipient

        if invite.status != InviteStatus.pending.value:
            raise InviteAlreadyProcessed

        await self.repository.update_invite_status(invite, InviteStatus.accepted.value)

        metadata = invite.metadata or {}
        return {
            "invite": invite,
            "event_id": metadata.get("event_id"),
            "permissions": metadata.get("permissions", []),
        }

    async def decline_invite(self, user_id: UUID, invite_id: UUID) -> None:
        invite = await self.get_invite_by_id(invite_id)

        if invite.target_user_id != user_id:
            raise NotInviteRecipient

        if invite.status != InviteStatus.pending.value:
            raise InviteAlreadyProcessed

        await self.repository.update_invite_status(invite, InviteStatus.declined.value)

    async def cancel_invite(self, creator_id: UUID, invite_id: UUID) -> None:
        invite = await self.get_invite_by_id(invite_id)

        if invite.created_by_id != creator_id:
            from exceptions import ForbiddenError
            raise ForbiddenError("Only the invite creator can cancel it")

        if invite.status != InviteStatus.pending.value:
            raise InviteAlreadyProcessed

        await self.repository.update_invite_status(invite, InviteStatus.cancelled.value)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/apps/user/invite/test_invite_service.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/apps/user/invite/service.py tests/apps/user/invite/test_invite_service.py
git commit -m "feat: add invite service"
```

---

### Task 6: Create Invite Request/Response Schemas

**Files:**
- Create: `src/apps/user/invite/request.py`
- Create: `src/apps/user/invite/response.py`
- Test: `tests/apps/user/invite/test_invite_schemas.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/apps/user/invite/test_invite_schemas.py
import pytest
from uuid import uuid4
from apps.user.invite.request import CreateInviteRequest, ResellerMetadata
from apps.user.invite.response import InviteResponse


def test_create_invite_request():
    request = CreateInviteRequest(
        lookup_type="email",
        lookup_value="test@example.com",
        metadata=ResellerMetadata(event_id=uuid4()),
    )
    assert request.lookup_type == "email"


def test_invite_response():
    response = InviteResponse(
        id=uuid4(),
        target_user_id=uuid4(),
        created_by_id=uuid4(),
        status="pending",
        metadata={},
    )
    assert response.status == "pending"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/apps/user/invite/test_invite_schemas.py -v`
Expected: FAIL — cannot import 'apps.user.invite.request'

- [ ] **Step 3: Write minimal implementation**

```python
# src/apps/user/invite/request.py
from uuid import UUID
from utils.schema import CamelCaseModel


class ResellerMetadata(CamelCaseModel):
    event_id: UUID
    permissions: list[str] = []


class CreateInviteRequest(CamelCaseModel):
    lookup_type: str  # "email" or "phone"
    lookup_value: str
    metadata: ResellerMetadata | None = None
```

```python
# src/apps/user/invite/response.py
from datetime import datetime
from uuid import UUID
from utils.schema import CamelCaseModel


class InviteResponse(CamelCaseModel):
    id: UUID
    target_user_id: UUID
    created_by_id: UUID
    status: str
    metadata: dict
    expires_at: datetime | None = None
    created_at: datetime
    updated_at: datetime
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/apps/user/invite/test_invite_schemas.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/apps/user/invite/request.py src/apps/user/invite/response.py tests/apps/user/invite/test_invite_schemas.py
git commit -m "feat: add invite request/response schemas"
```

---

### Task 7: Add User Repository Lookup Methods

**Files:**
- Modify: `src/apps/user/repository.py`
- Test: `tests/apps/user/test_user_repository.py` (existing or new)

- [ ] **Step 1: Write the failing test**

```python
# tests/apps/user/test_user_repository.py
import pytest
from apps.user.repository import UserRepository


async def test_find_by_email(user_repo, sample_user):
    user = await user_repo.find_by_email(sample_user.email)
    assert user is not None
    assert user.email == sample_user.email


async def test_find_by_email_not_found(user_repo):
    user = await user_repo.find_by_email("nonexistent@example.com")
    assert user is None


async def test_find_by_phone(user_repo, sample_user):
    user = await user_repo.find_by_phone(sample_user.phone)
    assert user is not None
    assert user.phone == sample_user.phone
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/apps/user/test_user_repository.py -v -k "find_by"`
Expected: FAIL — find_by_email method doesn't exist

- [ ] **Step 3: Add methods to UserRepository**

```python
# In src/apps/user/repository.py, add:

async def find_by_email(self, email: str) -> Optional[UserModel]:
    return await self._session.scalar(
        select(UserModel).where(UserModel.email == email.lower())
    )

async def find_by_phone(self, phone: str) -> Optional[UserModel]:
    return await self._session.scalar(
        select(UserModel).where(UserModel.phone == phone)
    )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/apps/user/test_user_repository.py -v -k "find_by"`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/apps/user/repository.py
git commit -m "feat: add email/phone lookup to user repository"
```

---

### Task 8: Add Event Reseller Model

**Files:**
- Modify: `src/apps/event/models.py`
- Modify: `src/apps/event/enums.py`
- Test: `tests/apps/event/test_event_reseller_model.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/apps/event/test_event_reseller_model.py
import pytest
import uuid
from apps.event.models import EventResellerModel


def test_event_reseller_model_creation():
    reseller = EventResellerModel(
        id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        event_id=uuid.uuid4(),
        invited_by_id=uuid.uuid4(),
        permissions={},
    )
    assert reseller.user_id is not None
    assert reseller.event_id is not None
    assert reseller.permissions == {}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/apps/event/test_event_reseller_model.py -v`
Expected: FAIL — EventResellerModel doesn't exist

- [ ] **Step 3: Write minimal implementation**

```python
# In src/apps/event/enums.py, add:

class ResellerPermissions(str, Enum):
    sell_tickets = "sell_tickets"
    view_sales = "view_sales"
```

```python
# In src/apps/event/models.py, add at end of file:

class EventResellerModel(Base, UUIDPrimaryKeyMixin, TimeStampMixin):
    __tablename__ = "event_resellers"
    __table_args__ = (
        UniqueConstraint("user_id", "event_id", name="uq_event_reseller_user_event"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True
    )
    event_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("events.id"), nullable=False, index=True
    )
    invited_by_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    permissions: Mapped[dict] = mapped_column(
        JSONB, default=dict, nullable=False, server_default="{}"
    )
    accepted_at: Mapped[datetime | None] = mapped_column(nullable=True)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/apps/event/test_event_reseller_model.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/apps/event/models.py src/apps/event/enums.py tests/apps/event/test_event_reseller_model.py
git commit -m "feat: add event reseller model"
```

---

### Task 9: Add Event Reseller Repository Methods

**Files:**
- Modify: `src/apps/event/repository.py`
- Test: `tests/apps/event/test_event_repository.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/apps/event/test_event_repository.py
import pytest
import uuid
from apps.event.models import EventResellerModel


async def test_create_event_reseller(event_repo, user_id, event_id, organizer_user_id):
    reseller = await event_repo.create_event_reseller(
        user_id=user_id,
        event_id=event_id,
        invited_by_id=organizer_user_id,
        permissions={},
    )
    assert reseller.user_id == user_id
    assert reseller.event_id == event_id


async def test_get_reseller_for_event(event_repo, event_reseller):
    reseller = await event_repo.get_reseller_for_event(
        event_reseller.user_id, event_reseller.event_id
    )
    assert reseller is not None


async def test_list_resellers_for_event(event_repo, event_reseller):
    resellers = await event_repo.list_resellers_for_event(event_reseller.event_id)
    assert len(resellers) >= 1
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/apps/event/test_event_repository.py -v -k "reseller"`
Expected: FAIL — method doesn't exist

- [ ] **Step 3: Add methods to EventRepository**

```python
# In src/apps/event/repository.py, add:

async def create_event_reseller(
    self,
    user_id: UUID,
    event_id: UUID,
    invited_by_id: UUID,
    permissions: dict,
) -> EventResellerModel:
    from datetime import datetime
    reseller = EventResellerModel(
        user_id=user_id,
        event_id=event_id,
        invited_by_id=invited_by_id,
        permissions=permissions,
        accepted_at=datetime.utcnow(),
    )
    self._session.add(reseller)
    await self._session.flush()
    await self._session.refresh(reseller)
    return reseller

async def get_reseller_for_event(
    self, user_id: UUID, event_id: UUID
) -> Optional[EventResellerModel]:
    return await self._session.scalar(
        select(EventResellerModel).where(
            and_(
                EventResellerModel.user_id == user_id,
                EventResellerModel.event_id == event_id,
            )
        )
    )

async def list_resellers_for_event(self, event_id: UUID) -> list[EventResellerModel]:
    result = await self._session.scalars(
        select(EventResellerModel)
        .where(EventResellerModel.event_id == event_id)
        .order_by(EventResellerModel.created_at.desc())
    )
    return list(result.all())
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/apps/event/test_event_repository.py -v -k "reseller"`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/apps/event/repository.py
git commit -m "feat: add event reseller repository methods"
```

---

### Task 10: Add Reseller Invite Endpoints

**Files:**
- Modify: `src/apps/event/urls.py`
- Test: `tests/apps/event/test_reseller_endpoints.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/apps/event/test_reseller_endpoints.py
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_create_reseller_invite(client, auth_headers, event_id):
    response = await client.post(
        f"/api/events/{event_id}/reseller-invites",
        json={"lookup_type": "email", "lookup_value": "test@example.com"},
        headers=auth_headers,
    )
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_list_event_resellers(client, auth_headers, event_id):
    response = await client.get(
        f"/api/events/{event_id}/resellers",
        headers=auth_headers,
    )
    assert response.status_code == 200
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/apps/event/test_reseller_endpoints.py -v`
Expected: FAIL — endpoint doesn't exist

- [ ] **Step 3: Write minimal implementation**

```python
# In src/apps/event/urls.py, add imports:
from apps.user.invite.service import InviteService as UserInviteService
from apps.user.invite.repository import InviteRepository as UserInviteRepository
from apps.user.invite.request import CreateInviteRequest
from apps.user.invite.response import InviteResponse

# Add dependency:
def get_user_invite_service(
    session: Annotated[AsyncSession, Depends(db_session)],
) -> UserInviteService:
    return UserInviteService(
        repository=UserInviteRepository(session),
        user_repository=UserRepository(session),
    )


# Add endpoints:
@router.post("/{event_id}/reseller-invites")
async def create_reseller_invite(
    event_id: UUID,
    request: Request,
    body: Annotated[CreateInviteRequest, Body()],
    event_service: Annotated[EventService, Depends(get_event_service)],
    invite_service: Annotated[UserInviteService, Depends(get_user_invite_service)],
) -> BaseResponse[InviteResponse]:
    # Verify organizer owns event
    event = await event_service.repository.get_by_id_for_owner(event_id, request.state.user.id)
    if not event:
        from apps.event.exceptions import OrganizerOwnershipError
        raise OrganizerOwnershipError

    # Find target user by email or phone
    target_user = None
    if body.lookup_type == "email":
        target_user = await invite_service.user_repository.find_by_email(body.lookup_value)
    elif body.lookup_type == "phone":
        target_user = await invite_service.user_repository.find_by_phone(body.lookup_value)

    if not target_user:
        from exceptions import NotFoundError
        raise NotFoundError("User not found")

    # Create invite
    metadata = body.metadata.model_dump() if body.metadata else {}
    metadata["event_id"] = str(event_id)
    invite = await invite_service.create_invite(
        target_user_id=target_user.id,
        created_by_id=request.state.user.id,
        metadata=metadata,
    )
    return BaseResponse(data=InviteResponse.model_validate(invite))


@router.get("/{event_id}/resellers")
async def list_event_resellers(
    event_id: UUID,
    request: Request,
    event_service: Annotated[EventService, Depends(get_event_service)],
) -> BaseResponse[list[ResellerResponse]]:
    # Verify organizer owns event
    event = await event_service.repository.get_by_id_for_owner(event_id, request.state.user.id)
    if not event:
        from apps.event.exceptions import OrganizerOwnershipError
        raise OrganizerOwnershipError

    resellers = await event_service.repository.list_resellers_for_event(event_id)
    return BaseResponse(data=[ResellerResponse.model_validate(r) for r in resellers])
```

```python
# Add ResellerResponse to src/apps/event/response.py:

class ResellerResponse(CamelCaseModel):
    id: UUID
    user_id: UUID
    event_id: UUID
    invited_by_id: UUID
    permissions: dict
    accepted_at: datetime | None = None
    created_at: datetime
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/apps/event/test_reseller_endpoints.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/apps/event/urls.py src/apps/event/response.py tests/apps/event/test_reseller_endpoints.py
git commit -m "feat: add reseller invite endpoints"
```

---

### Task 11: Add Accept/Decline Invite Endpoints

**Files:**
- Modify: `src/apps/event/urls.py`
- Test: `tests/apps/event/test_invite_accept_decline.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/apps/event/test_invite_accept_decline.py
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_accept_invite_creates_reseller(client, auth_headers, sample_invite):
    response = await client.post(
        f"/api/invites/{sample_invite.id}/accept",
        headers=auth_headers,
    )
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_decline_invite(client, auth_headers, sample_invite):
    response = await client.post(
        f"/api/invites/{sample_invite.id}/decline",
        headers=auth_headers,
    )
    assert response.status_code == 200
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/apps/event/test_invite_accept_decline.py -v`
Expected: FAIL — endpoint doesn't exist

- [ ] **Step 3: Write minimal implementation**

```python
# In src/apps/event/urls.py, add endpoints:

@router.post("/invites/{invite_id}/accept")
async def accept_invite(
    invite_id: UUID,
    request: Request,
    event_service: Annotated[EventService, Depends(get_event_service)],
    invite_service: Annotated[UserInviteService, Depends(get_user_invite_service)],
) -> BaseResponse[ResellerResponse]:
    result = await invite_service.accept_invite(request.state.user.id, invite_id)

    # Create event reseller record
    event_id = UUID(result["event_id"])
    permissions = result["permissions"]

    reseller = await event_service.repository.create_event_reseller(
        user_id=request.state.user.id,
        event_id=event_id,
        invited_by_id=result["invite"].created_by_id,
        permissions=permissions,
    )
    return BaseResponse(data=ResellerResponse.model_validate(reseller))


@router.post("/invites/{invite_id}/decline")
async def decline_invite(
    invite_id: UUID,
    request: Request,
    invite_service: Annotated[UserInviteService, Depends(get_user_invite_service)],
) -> BaseResponse[dict]:
    await invite_service.decline_invite(request.state.user.id, invite_id)
    return BaseResponse(data={"declined": True})


@router.delete("/events/{event_id}/reseller-invites/{invite_id}")
async def cancel_reseller_invite(
    event_id: UUID,
    invite_id: UUID,
    request: Request,
    event_service: Annotated[EventService, Depends(get_event_service)],
    invite_service: Annotated[UserInviteService, Depends(get_user_invite_service)],
) -> BaseResponse[dict]:
    # Verify organizer owns event
    event = await event_service.repository.get_by_id_for_owner(event_id, request.state.user.id)
    if not event:
        from apps.event.exceptions import OrganizerOwnershipError
        raise OrganizerOwnershipError

    await invite_service.cancel_invite(request.state.user.id, invite_id)
    return BaseResponse(data={"cancelled": True})
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/apps/event/test_invite_accept_decline.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/apps/event/urls.py tests/apps/event/test_invite_accept_decline.py
git commit -m "feat: add accept/decline/cancel invite endpoints"
```

---

### Task 12: Create Migration

**Files:**
- Create: `src/migrations/versions/<new_uuid>_add_invites_and_event_resellers_tables.py`

- [ ] **Step 1: Generate UUID and get latest revision**

Run: `python -c "import uuid; print(uuid.uuid4())"`
Note the output and use it as `<new_uuid>`

Run: `ls -la src/migrations/versions/*.py | tail -5` to find latest revision

- [ ] **Step 2: Write the migration**

```python
# src/migrations/versions/<new_uuid>_add_invites_and_event_resellers_tables.py
"""Add invites and event_resellers tables

Revision ID: <new_uuid>
Revises: <latest_revision_id>
Create Date: 2026-04-11
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = '<new_uuid>'
down_revision: Union[str, None] = '<latest_revision_id>'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create invites table
    op.create_table(
        "invites",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("target_user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False, index=True),
        sa.Column("created_by_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False, index=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending", index=True),
        sa.Column("metadata", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("expires_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
    )

    # Create event_resellers table
    op.create_table(
        "event_resellers",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False, index=True),
        sa.Column("event_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("events.id"), nullable=False, index=True),
        sa.Column("invited_by_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("permissions", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("accepted_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "event_id", name="uq_event_reseller_user_event"),
    )


def downgrade() -> None:
    op.drop_table("event_resellers")
    op.drop_table("invites")
```

- [ ] **Step 3: Run migration to verify**

Run: `alembic upgrade head`
Expected: Migration completes successfully

- [ ] **Step 4: Commit**

```bash
git add src/migrations/versions/<new_uuid>_add_invites_and_event_resellers_tables.py
git commit -m "feat: add invites and event_resellers migration"
```

---

### Task 13: Add User Invite List Endpoint

**Files:**
- Modify: `src/apps/user/urls.py`
- Test: `tests/apps/user/test_invite_endpoints.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/apps/user/test_invite_endpoints.py
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_list_pending_invites(client, auth_headers, sample_invite):
    response = await client.get(
        "/api/users/me/invites",
        headers=auth_headers,
    )
    assert response.status_code == 200
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/apps/user/test_invite_endpoints.py -v`
Expected: FAIL — endpoint doesn't exist

- [ ] **Step 3: Write minimal implementation**

```python
# In src/apps/user/urls.py, add:

from apps.user.invite.service import InviteService as UserInviteService
from apps.user.invite.repository import InviteRepository as UserInviteRepository
from apps.user.invite.response import InviteResponse

def get_user_invite_service(
    session: Annotated[AsyncSession, Depends(db_session)],
) -> UserInviteService:
    return UserInviteService(
        repository=UserInviteRepository(session),
        user_repository=UserRepository(session),
    )


@router.get("/me/invites")
async def list_pending_invites(
    request: Request,
    service: Annotated[UserInviteService, Depends(get_user_invite_service)],
) -> BaseResponse[list[InviteResponse]]:
    invites = await service.list_pending_invites_for_user(request.state.user.id)
    return BaseResponse(data=[InviteResponse.model_validate(i) for i in invites])
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/apps/user/test_invite_endpoints.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/apps/user/urls.py tests/apps/user/test_invite_endpoints.py
git commit -m "feat: add user invite list endpoint"
```

---

### Task 14: Create Conftest with Fixtures

**Files:**
- Create: `tests/apps/user/invite/conftest.py`
- Create: `tests/apps/event/conftest_reseller.py`

- [ ] **Step 1: Write the conftest**

```python
# tests/apps/user/invite/conftest.py
import pytest
import uuid
from datetime import datetime
from apps.user.invite.models import InviteModel


@pytest.fixture
def another_user_id():
    return uuid.uuid4()


@pytest.fixture
def sample_invite(session, another_user_id, organizer_user_id):
    invite = InviteModel(
        id=uuid.uuid4(),
        target_user_id=another_user_id,
        created_by_id=organizer_user_id,
        status="pending",
        metadata={"event_id": str(uuid.uuid4())},
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    session.add(invite)
    session.flush()
    return invite
```

```python
# tests/apps/event/conftest_reseller.py
import pytest
import uuid
from datetime import datetime
from apps.event.models import EventResellerModel


@pytest.fixture
def event_reseller(session, user_id, event_id, organizer_user_id):
    reseller = EventResellerModel(
        id=uuid.uuid4(),
        user_id=user_id,
        event_id=event_id,
        invited_by_id=organizer_user_id,
        permissions={},
        accepted_at=datetime.utcnow(),
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    session.add(reseller)
    session.flush()
    return reseller
```

- [ ] **Step 2: Run tests to verify fixtures work**

Run: `pytest tests/apps/user/invite/ tests/apps/event/ -v --collect-only`
Expected: Tests collected successfully

- [ ] **Step 3: Commit**

```bash
git add tests/apps/user/invite/conftest.py tests/apps/event/conftest_reseller.py
git commit -m "feat: add reseller test fixtures"
```

---

## Self-Review Checklist

1. **Spec coverage:** All spec requirements mapped to tasks
   - ✅ `invites` table in `apps/user/invite/`
   - ✅ `event_resellers` table in `apps/event/`
   - ✅ User lookup by email/phone
   - ✅ Create reseller invite endpoint
   - ✅ List pending invites endpoint
   - ✅ Accept invite creates event_reseller record
   - ✅ Decline invite endpoint
   - ✅ Cancel invite endpoint
   - ✅ List resellers for event endpoint
   - ✅ Auth/permission checks per endpoint

2. **Placeholder scan:** No TBD, TODO, or incomplete steps (except migration UUID which must be generated)

3. **Type consistency:** Method signatures consistent across tasks

4. **Architecture follows user suggestion:**
   - Invite model/service in `apps/user/invite/` (generic)
   - Event reseller model in `apps/event/` (event-specific)
   - Invite endpoints call user invite service from event context

---

**Plan complete and saved to `docs/superpowers/plans/2026-04-11-reseller-module.md`.**

**Two execution options:**

**1. Subagent-Driven (recommended)** - I dispatch a fresh subagent per task, review between tasks, fast iteration

**2. Inline Execution** - Execute tasks in this session using executing-plans, batch execution with checkpoints

**Which approach?**