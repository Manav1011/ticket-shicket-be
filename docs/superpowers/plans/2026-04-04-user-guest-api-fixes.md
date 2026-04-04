# User and Guest API Fixes Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the User and Guest auth APIs secure, consistent, and schema-compatible without changing the intended client flows.

**Architecture:** We will fix shared primitives first so every model and request schema behaves predictably. Then we will harden the User and Guest services at the boundary where business rules meet persistence: normalize emails, hash passwords before storage, serialize only public response fields, lock user-by-id endpoints to the current principal, and clean up dependent rows before deletion.

**Tech Stack:** FastAPI, Pydantic, SQLAlchemy 2.0 async, PostgreSQL, pytest, unittest.mock/AsyncMock

---

## File Structure

- `src/db/base.py`: fix UUID primary key generation so each row gets its own UUID.
- `src/auth/schemas.py`: make refresh/logout payloads accept camelCase and snake_case like the rest of the API.
- `src/apps/user/repository.py`: normalize email lookups, return both email and phone for duplicate checks, and add guest-link cleanup for user deletion.
- `src/apps/user/service.py`: hash passwords on creation, normalize email before lookup/storage, distinguish duplicate email vs duplicate phone, and revoke related records before delete.
- `src/apps/user/urls.py`: enforce self-only access for by-id endpoints and explicitly serialize public user DTOs.
- `src/apps/user/exceptions.py`: add a dedicated duplicate-phone exception.
- `src/apps/guest/service.py`: hash passwords during guest-to-user conversion and normalize email before duplicate checks.
- `src/apps/guest/repository.py`: keep guest-side lookups aligned with normalized email behavior.
- `tests/unit/db/test_uuid_primary_key.py`: regression tests for UUID generation.
- `tests/unit/auth/test_refresh_request_schema.py`: regression tests for refresh body parsing.
- `tests/apps/user/test_user_service.py`: service-level tests for normalization, hashing, duplicate handling, and delete cleanup.
- `tests/apps/user/test_user_urls.py`: route-level tests for self-only authorization and safe response serialization.
- `tests/apps/guest/test_guest_service.py`: service-level tests for guest conversion hashing and normalized duplicate checks.

## Task 1: Fix Shared UUID Generation and Refresh Schema Parsing

**Files:**
- Modify: `src/db/base.py`
- Modify: `src/auth/schemas.py`
- Create: `tests/unit/db/test_uuid_primary_key.py`
- Create: `tests/unit/auth/test_refresh_request_schema.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/unit/db/test_uuid_primary_key.py
from datetime import datetime, timedelta
from uuid import uuid4

from apps.user.models import RefreshTokenModel


def test_uuid_primary_key_default_generates_distinct_ids():
    now = datetime.utcnow()
    token_a = RefreshTokenModel(
        token_hash="hash-a",
        user_id=uuid4(),
        expires_at=now + timedelta(hours=1),
    )
    token_b = RefreshTokenModel(
        token_hash="hash-b",
        user_id=uuid4(),
        expires_at=now + timedelta(hours=1),
    )

    assert token_a.id != token_b.id
```

```python
# tests/unit/auth/test_refresh_request_schema.py
from auth.schemas import RefreshRequest, RefreshRequestWithJti


def test_refresh_request_accepts_camel_case():
    body = RefreshRequest.model_validate({"refreshToken": "refresh-123"})
    assert body.refresh_token == "refresh-123"


def test_refresh_request_with_jti_accepts_camel_case():
    body = RefreshRequestWithJti.model_validate(
        {"refreshToken": "refresh-123", "accessTokenJti": "jti-456"}
    )
    assert body.refresh_token == "refresh-123"
    assert body.access_token_jti == "jti-456"
```

- [ ] **Step 2: Run the tests and confirm they fail for the right reasons**

Run:

```bash
python3 -m pytest tests/unit/db/test_uuid_primary_key.py tests/unit/auth/test_refresh_request_schema.py -v
```

Expected:

```text
FAIL: RefreshTokenModel instances reuse the same id
FAIL: RefreshRequest rejects refreshToken / accessTokenJti
```

- [ ] **Step 3: Implement the minimal fix**

```python
# src/db/base.py
class UUIDPrimaryKeyMixin:
    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4,
        nullable=False,
    )
```

```python
# src/auth/schemas.py
from utils.schema import CamelCaseModel


class RefreshRequest(CamelCaseModel):
    refresh_token: str


class RefreshRequestWithJti(CamelCaseModel):
    refresh_token: str
    access_token_jti: str | None = None
```

- [ ] **Step 4: Re-run the tests and confirm they pass**

Run:

```bash
python3 -m pytest tests/unit/db/test_uuid_primary_key.py tests/unit/auth/test_refresh_request_schema.py -v
```

Expected:

```text
PASS
```

- [ ] **Step 5: Commit**

```bash
git add src/db/base.py src/auth/schemas.py tests/unit/db/test_uuid_primary_key.py tests/unit/auth/test_refresh_request_schema.py
git commit -m "fix: repair uuid defaults and refresh schema parsing"
```

## Task 2: Harden User Signup, Login, and Public Response Serialization

**Files:**
- Modify: `src/apps/user/repository.py`
- Modify: `src/apps/user/service.py`
- Modify: `src/apps/user/urls.py`
- Modify: `src/apps/user/exceptions.py`
- Create: `tests/apps/user/test_user_service.py`
- Create: `tests/apps/user/test_user_urls.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/apps/user/test_user_service.py
from datetime import datetime, timedelta
from types import SimpleNamespace
from uuid import uuid4
from unittest.mock import AsyncMock, patch

import pytest

from apps.user.exceptions import DuplicatePhoneException
from apps.user.models import UserModel
from apps.user.repository import UserRepository
from apps.user.service import UserService
from auth.blocklist import TokenBlocklist


@pytest.mark.asyncio
async def test_create_user_hashes_password_and_normalizes_email():
    session = AsyncMock()
    session.flush = AsyncMock()
    session.refresh = AsyncMock()
    repo = AsyncMock(spec=UserRepository)
    repo.get_by_email_or_phone.return_value = None
    repo.session = session
    blocklist = AsyncMock(spec=TokenBlocklist)
    service = UserService(repo, blocklist)

    with patch("apps.user.service.hash_password", AsyncMock(return_value="hashed-password")):
        user = await service.create_user(
            first_name="Jane",
            last_name="Doe",
            email=" Jane@Example.COM ",
            phone="1234567890",
            password="Secret123!",
        )

    assert user.email == "jane@example.com"
    assert user.password == "hashed-password"
    assert repo.add.call_count == 1


@pytest.mark.asyncio
async def test_login_user_looks_up_normalized_email():
    session = AsyncMock()
    repo = AsyncMock(spec=UserRepository)
    repo.get_by_email.return_value = UserModel(
        id=uuid4(),
        first_name="Jane",
        last_name="Doe",
        email="jane@example.com",
        phone="1234567890",
        password="hashed-password",
    )
    repo.session = session
    blocklist = AsyncMock(spec=TokenBlocklist)
    service = UserService(repo, blocklist)

    with patch("apps.user.service.verify_password", AsyncMock(return_value=True)):
        with patch("apps.user.service.create_tokens", AsyncMock(return_value={"access_token": "a", "refresh_token": "r"})):
            await service.login_user(" JANE@EXAMPLE.COM ", "Secret123!")

    repo.get_by_email.assert_awaited_once_with("jane@example.com")


@pytest.mark.asyncio
async def test_create_user_raises_duplicate_phone():
    session = AsyncMock()
    repo = AsyncMock(spec=UserRepository)
    repo.get_by_email_or_phone.return_value = SimpleNamespace(email=None, phone="1234567890")
    repo.session = session
    blocklist = AsyncMock(spec=TokenBlocklist)
    service = UserService(repo, blocklist)

    with pytest.raises(DuplicatePhoneException):
        await service.create_user(
            first_name="Jane",
            last_name="Doe",
            email="jane@example.com",
            phone="1234567890",
            password="Secret123!",
        )
```

```python
# tests/apps/user/test_user_urls.py
from types import SimpleNamespace
from uuid import uuid4
from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException

from apps.user.models import UserModel
from apps.user.request import GetUserByIdRequest, SignUpRequest
from apps.user.urls import create_user, get_user_by_id


@pytest.mark.asyncio
async def test_create_user_returns_only_public_fields():
    user = UserModel(
        id=uuid4(),
        first_name="Jane",
        last_name="Doe",
        email="jane@example.com",
        phone="1234567890",
        password="hashed-password",
    )
    service = AsyncMock()
    service.create_user.return_value = user
    body = SignUpRequest(
        first_name="Jane",
        last_name="Doe",
        email="jane@example.com",
        phone="1234567890",
        password="Secret123!",
    )

    response = await create_user(body=body, service=service)

    assert response.data.model_dump() == {
        "id": user.id,
        "first_name": "Jane",
        "last_name": "Doe",
    }


@pytest.mark.asyncio
async def test_get_user_by_id_rejects_other_user():
    current_user = SimpleNamespace(id=uuid4())
    request = SimpleNamespace(state=SimpleNamespace(user=current_user))
    query = GetUserByIdRequest(user_id=uuid4())
    service = AsyncMock()

    with pytest.raises(HTTPException) as excinfo:
        await get_user_by_id(query=query, request=request, service=service)

    assert excinfo.value.status_code == 403
    service.get_user_by_id.assert_not_awaited()
```

- [ ] **Step 2: Run the tests and confirm they fail**

Run:

```bash
python3 -m pytest tests/apps/user/test_user_service.py tests/apps/user/test_user_urls.py -v
```

Expected:

```text
FAIL: user email lookups are not normalized
FAIL: user signup still stores plaintext password
FAIL: duplicate phone is treated as duplicate email or not handled
FAIL: create_user response still exposes raw ORM data instead of a public DTO
FAIL: by-id route does not reject a different authenticated user
```

- [ ] **Step 3: Implement the minimal fix**

```python
# src/apps/user/exceptions.py
class DuplicatePhoneException(BadRequestError):
    message = "Phone number already exists."
```

```python
# src/apps/user/repository.py
from apps.guest.models import GuestModel
from sqlalchemy import func, or_, select, update


async def get_by_id(self, user_id: UUID) -> Optional[UserModel]:
    return await self._session.scalar(
        select(UserModel).where(UserModel.id == user_id)
    )


async def get_by_email(self, email: str) -> Optional[UserModel]:
    normalized_email = email.strip().lower()
    return await self._session.scalar(
        select(UserModel).where(func.lower(UserModel.email) == normalized_email)
    )


async def get_by_email_or_phone(self, email: str, phone: str) -> Optional[UserModel]:
    normalized_email = email.strip().lower()
    return await self._session.scalar(
        select(UserModel).where(
            or_(
                func.lower(UserModel.email) == normalized_email,
                UserModel.phone == phone,
            )
        )
    )


async def clear_guest_conversion_links(self, user_id: UUID) -> None:
    await self._session.execute(
        update(GuestModel)
        .where(GuestModel.converted_user_id == user_id)
        .values(converted_user_id=None)
    )
    await self._session.flush()
```

```python
# src/apps/user/service.py
from .exceptions import DuplicateEmailException, DuplicatePhoneException
from auth.password import hash_password, verify_password


async def login_user(self, email: str, password: str) -> dict[str, str]:
    normalized_email = email.strip().lower()
    user = await self.repository.get_by_email(normalized_email)
    if not user:
        raise InvalidCredentialsException
    if not await verify_password(hashed_password=user.password, plain_password=password):
        raise InvalidCredentialsException
    return await create_tokens(user_id=user.id, type="user")


async def create_user(
    self,
    first_name: str,
    last_name: str,
    email: str,
    phone: str,
    password: str,
) -> UserModel:
    normalized_email = email.strip().lower()
    existing = await self.repository.get_by_email_or_phone(normalized_email, phone)
    if existing:
        if existing.email and existing.email.strip().lower() == normalized_email:
            raise DuplicateEmailException
        if existing.phone == phone:
            raise DuplicatePhoneException

    user = UserModel.create(
        first_name=first_name,
        last_name=last_name,
        phone=phone,
        password=await hash_password(password),
        email=normalized_email,
    )
    self.repository.add(user)
    await self.repository.session.flush()
    await self.repository.session.refresh(user)
    return user
```

```python
# src/apps/user/urls.py
from fastapi import HTTPException


@router.post("/create", status_code=status.HTTP_201_CREATED, operation_id="create_user")
async def create_user(
    body: Annotated[SignUpRequest, Body()],
    service: Annotated[UserService, Depends(get_user_service)],
) -> BaseResponse[BaseUserResponse]:
    user = await service.create_user(**body.model_dump())
    return BaseResponse(data=BaseUserResponse.model_validate(user))
```

- [ ] **Step 4: Re-run the tests and confirm they pass**

Run:

```bash
python3 -m pytest tests/apps/user/test_user_service.py tests/apps/user/test_user_urls.py -v
```

Expected:

```text
PASS
```

- [ ] **Step 5: Commit**

```bash
git add src/apps/user/repository.py src/apps/user/service.py src/apps/user/urls.py src/apps/user/exceptions.py tests/apps/user/test_user_service.py tests/apps/user/test_user_urls.py
git commit -m "fix: harden user auth and response handling"
```

## Task 3: Hash Guest Conversion Passwords and Normalize Guest Conversion Lookups

**Files:**
- Modify: `src/apps/guest/repository.py`
- Modify: `src/apps/guest/service.py`
- Create: `tests/apps/guest/test_guest_service.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/apps/guest/test_guest_service.py
from types import SimpleNamespace
from uuid import uuid4
from unittest.mock import AsyncMock, patch

import pytest

from apps.guest.exceptions import DuplicateEmailException
from apps.guest.models import GuestModel
from apps.guest.repository import GuestRepository
from apps.guest.service import GuestService
from apps.user.models import UserModel
from auth.blocklist import TokenBlocklist


@pytest.mark.asyncio
async def test_convert_guest_hashes_password_and_normalizes_email():
    guest_repo = AsyncMock(spec=GuestRepository)
    guest_repo.session = AsyncMock()
    guest_repo.session.flush = AsyncMock()
    guest_repo.session.refresh = AsyncMock()
    guest = GuestModel.create(device_id=uuid4())
    guest_repo.get_by_id.return_value = guest
    user_repo = AsyncMock()
    user_repo.get_by_email_or_phone.return_value = None
    user_repo.session = AsyncMock()
    user_repo.session.flush = AsyncMock()
    user_repo.session.refresh = AsyncMock()
    blocklist = AsyncMock(spec=TokenBlocklist)
    service = GuestService(guest_repo, user_repo, blocklist)

    with patch("apps.guest.service.hash_password", AsyncMock(return_value="hashed-password")):
        with patch("apps.guest.service.create_tokens", AsyncMock(return_value={"access_token": "a", "refresh_token": "r"})):
            result = await service.convert_guest(
                guest_id=guest.id,
                email=" Guest@Example.COM ",
                phone="1234567890",
                password="Secret123!",
                first_name="Jane",
                last_name="Doe",
            )

    created_user = user_repo.add.call_args.args[0]
    assert created_user.email == "guest@example.com"
    assert created_user.password == "hashed-password"
    assert result["user_id"]


@pytest.mark.asyncio
async def test_convert_guest_raises_duplicate_email_case_insensitively():
    guest_repo = AsyncMock(spec=GuestRepository)
    guest = GuestModel.create(device_id=uuid4())
    guest_repo.get_by_id.return_value = guest
    user_repo = AsyncMock()
    user_repo.get_by_email_or_phone.return_value = SimpleNamespace(
        email="guest@example.com",
        phone=None,
    )
    user_repo.session = AsyncMock()
    blocklist = AsyncMock(spec=TokenBlocklist)
    service = GuestService(guest_repo, user_repo, blocklist)

    with pytest.raises(DuplicateEmailException):
        await service.convert_guest(
            guest_id=guest.id,
            email="GUEST@example.com",
            phone="1234567890",
            password="Secret123!",
            first_name="Jane",
            last_name="Doe",
        )
```

- [ ] **Step 2: Run the tests and confirm they fail**

Run:

```bash
python3 -m pytest tests/apps/guest/test_guest_service.py -v
```

Expected:

```text
FAIL: guest conversion still stores plaintext password
FAIL: guest conversion still uses an unnormalized email for duplicate checks
```

- [ ] **Step 3: Implement the minimal fix**

```python
# src/apps/guest/service.py
from auth.password import hash_password


async def convert_guest(
    self,
    guest_id: uuid.UUID,
    email: str,
    phone: str,
    password: str,
    first_name: str,
    last_name: str,
) -> dict:
    guest = await self.repository.get_by_id(guest_id)
    if not guest:
        raise GuestNotFoundException
    if guest.is_converted:
        raise GuestAlreadyConvertedException

    normalized_email = email.strip().lower()
    existing = await self.user_repository.get_by_email_or_phone(normalized_email, phone)
    if existing:
        if existing.email and existing.email.strip().lower() == normalized_email:
            raise DuplicateEmailException
        if existing.phone == phone:
            raise DuplicatePhoneException

    user = UserModel.create(
        first_name=first_name,
        last_name=last_name,
        email=normalized_email,
        phone=phone,
        password=await hash_password(password),
    )
    self.user_repository.add(user)
    await self.user_repository.session.flush()
    await self.user_repository.session.refresh(user)

    await self.repository.update_conversion(
        guest_id=guest_id,
        email=normalized_email,
        phone=phone,
        converted_user_id=user.id,
    )
    await self.repository.revoke_all_guest_tokens(guest_id)
    await self.repository.session.commit()

    tokens = await create_tokens(user_id=user.id, type="user")
    return {
        "user_id": str(user.id),
        "access_token": tokens["access_token"],
        "refresh_token": tokens["refresh_token"],
    }
```

```python
# src/apps/guest/repository.py
from sqlalchemy import func, select, update


async def get_by_email(self, email: str) -> Optional[GuestModel]:
    normalized_email = email.strip().lower()
    return await self._session.scalar(
        select(GuestModel).where(func.lower(GuestModel.email) == normalized_email)
    )
```

- [ ] **Step 4: Re-run the tests and confirm they pass**

Run:

```bash
python3 -m pytest tests/apps/guest/test_guest_service.py -v
```

Expected:

```text
PASS
```

- [ ] **Step 5: Commit**

```bash
git add src/apps/guest/repository.py src/apps/guest/service.py tests/apps/guest/test_guest_service.py
git commit -m "fix: secure guest conversion flow"
```

## Task 4: Lock User By-Id Endpoints to the Current Principal and Clean Up Deletions

**Files:**
- Modify: `src/apps/user/repository.py`
- Modify: `src/apps/user/service.py`
- Modify: `src/apps/user/urls.py`
- Create: `tests/apps/user/test_user_urls.py`
- Create: `tests/apps/user/test_user_service.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/apps/user/test_user_urls.py
from types import SimpleNamespace
from uuid import uuid4
from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException

from apps.user.models import UserModel
from apps.user.request import DeleteUserByIdRequest
from apps.user.urls import delete_user_by_id, get_user_by_id


@pytest.mark.asyncio
async def test_delete_user_by_id_rejects_other_user():
    current_user = SimpleNamespace(id=uuid4())
    request = SimpleNamespace(state=SimpleNamespace(user=current_user))
    query = DeleteUserByIdRequest(user_id=uuid4())
    service = AsyncMock()

    with pytest.raises(HTTPException) as excinfo:
        await delete_user_by_id(query=query, request=request, service=service)

    assert excinfo.value.status_code == 403
    service.delete_user_by_id.assert_not_awaited()
```

```python
# tests/apps/user/test_user_service.py
from types import SimpleNamespace
from uuid import uuid4
from unittest.mock import AsyncMock

import pytest

from apps.user.models import UserModel
from apps.user.repository import UserRepository
from apps.user.service import UserService
from auth.blocklist import TokenBlocklist


@pytest.mark.asyncio
async def test_delete_user_revokes_tokens_and_clears_guest_links():
    session = AsyncMock()
    session.commit = AsyncMock()
    repo = AsyncMock()
    repo.get_by_id.return_value = UserModel(
        id=uuid4(),
        first_name="Jane",
        last_name="Doe",
        email="jane@example.com",
        phone="1234567890",
        password="hashed-password",
    )
    repo.session = session
    blocklist = AsyncMock(spec=TokenBlocklist)
    service = UserService(repo, blocklist)

    await service.delete_user_by_id(repo.get_by_id.return_value.id)

    repo.revoke_all_user_tokens.assert_awaited_once()
    repo.clear_guest_conversion_links.assert_awaited_once()
    repo.delete.assert_awaited_once()
    session.commit.assert_awaited_once()
```

- [ ] **Step 2: Run the tests and confirm they fail**

Run:

```bash
python3 -m pytest tests/apps/user/test_user_service.py tests/apps/user/test_user_urls.py -v
```

Expected:

```text
FAIL: by-id routes still allow any authenticated user to fetch/delete arbitrary users
FAIL: delete_user_by_id does not clean up dependent refresh tokens or guest conversion links
```

- [ ] **Step 3: Implement the minimal fix**

```python
# src/apps/user/service.py
async def delete_user_by_id(self, user_id: UUID) -> UserModel:
    user = await self.repository.get_by_id(user_id)
    if not user:
        raise UserNotFoundException

    await self.repository.revoke_all_user_tokens(user_id)
    await self.repository.clear_guest_conversion_links(user_id)
    await self.repository.delete(user_id)
    await self.repository.session.commit()
    return user
```

```python
# src/apps/user/urls.py
from fastapi import HTTPException


@protected_router.get("/", status_code=status.HTTP_200_OK, operation_id="get_user_by_id")
async def get_user_by_id(
    query: Annotated[GetUserByIdRequest, Query()],
    request: Request,
    service: Annotated[UserService, Depends(get_user_service)],
) -> BaseResponse[BaseUserResponse]:
    current_user: UserModel = request.state.user
    if query.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")

    user = await service.get_user_by_id(current_user.id)
    return BaseResponse(data=BaseUserResponse.model_validate(user))


@protected_router.delete("/", status_code=status.HTTP_200_OK, operation_id="delete_user_by_id")
async def delete_user_by_id(
    query: Annotated[DeleteUserByIdRequest, Query()],
    request: Request,
    service: Annotated[UserService, Depends(get_user_service)],
) -> BaseResponse[BaseUserResponse]:
    current_user: UserModel = request.state.user
    if query.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")

    deleted_user = await service.delete_user_by_id(current_user.id)
    return BaseResponse(data=BaseUserResponse.model_validate(deleted_user))
```

```python
# src/apps/user/repository.py
async def clear_guest_conversion_links(self, user_id: UUID) -> None:
    await self._session.execute(
        update(GuestModel)
        .where(GuestModel.converted_user_id == user_id)
        .values(converted_user_id=None)
    )
    await self._session.flush()
```

- [ ] **Step 4: Re-run the tests and confirm they pass**

Run:

```bash
python3 -m pytest tests/apps/user/test_user_service.py tests/apps/user/test_user_urls.py -v
```

Expected:

```text
PASS
```

- [ ] **Step 5: Commit**

```bash
git add src/apps/user/repository.py src/apps/user/service.py src/apps/user/urls.py tests/apps/user/test_user_service.py tests/apps/user/test_user_urls.py
git commit -m "fix: restrict user by-id access and cleanup deletes"
```

## Coverage Check

- The UUID fix covers the refresh-token primary-key collision risk in both user and guest flows.
- The refresh schema fix covers the camelCase payloads used by the current guest and user clients.
- The user service and URL fixes cover the arbitrary-user access bug, the public response leakage risk, email normalization, and duplicate-phone handling.
- The guest service fix covers plaintext password storage during conversion and normalized duplicate email checks.
- The user deletion fix covers dependent refresh-token cleanup and guest conversion-link cleanup before deleting a user.
