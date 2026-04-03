# Guest Module Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement a guest authentication module that allows anonymous users to browse and add tickets to cart without signup friction, then convert to a full User at checkout.

**Architecture:** Guest identified by server-generated device_id (UUID) stored client-side. JWT tokens contain `type: "guest"` claim for differentiation. Single `/refresh` endpoint handles both User and Guest token rotation. On conversion, Guest record links to new User and is marked as converted.

**Tech Stack:** FastAPI, SQLAlchemy 2.0 async, PostgreSQL, Redis (existing)

---

## File Structure

```
src/apps/guest/                    # NEW - Guest app module
├── __init__.py                    # Exports guest_router
├── models.py                      # GuestModel, GuestRefreshTokenModel
├── repository.py                  # GuestRepository with device_id lookup
├── service.py                     # GuestService with token + conversion logic
├── request.py                     # GuestLoginRequest, GuestConvertRequest
├── response.py                    # GuestLoginResponse, GuestResponse
├── exceptions.py                  # Guest-specific exceptions
├── urls.py                        # Guest endpoints (login, logout, refresh, convert)
├── dependencies.py                # get_current_guest dependency

src/auth/jwt.py                    # MODIFY - create_guest_tokens() adding type claim
src/server.py                      # MODIFY - register guest_router
src/apps/__init__.py               # MODIFY - export guest_router
```

---

## Task 1: Create Guest App Structure

**Files:**
- Create: `src/apps/guest/__init__.py`
- Create: `src/apps/guest/models.py`
- Create: `src/apps/guest/repository.py`
- Create: `src/apps/guest/service.py`
- Create: `src/apps/guest/request.py`
- Create: `src/apps/guest/response.py`
- Create: `src/apps/guest/exceptions.py`
- Create: `src/apps/guest/urls.py`
- Create: `src/apps/guest/dependencies.py`

- [ ] **Step 1: Create all guest app files**

```python
# src/apps/guest/__init__.py
from .urls import router as guest_router

__all__ = ["guest_router"]
```

```python
# src/apps/guest/models.py
from __future__ import annotations
import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from db.base import Base, TimeStampMixin, UUIDPrimaryKeyMixin


class GuestModel(Base, UUIDPrimaryKeyMixin, TimeStampMixin):
    """
    Guest user model for anonymous browsing.
    Identified by device_id (UUID generated on first login).
    Converted to User at checkout.
    """
    __tablename__ = "guests"

    device_id: Mapped[uuid.UUID] = mapped_column(index=True, unique=True)
    # User fields captured at conversion
    email: Mapped[str | None] = mapped_column(String(320), index=True, nullable=True)
    phone: Mapped[str | None] = mapped_column(index=True, nullable=True)
    # Conversion tracking
    is_converted: Mapped[bool] = mapped_column(default=False, nullable=False)
    converted_user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id"), nullable=True
    )

    @classmethod
    def create(cls, device_id: uuid.UUID) -> Self:
        return cls(id=uuid.uuid4(), device_id=device_id)


class GuestRefreshTokenModel(Base, UUIDPrimaryKeyMixin, TimeStampMixin):
    """
    Refresh tokens for guest users.
    Token hash is stored (never plain text).
    """
    __tablename__ = "guest_refresh_tokens"

    token_hash: Mapped[str] = mapped_column(index=True, unique=True)
    guest_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("guests.id"), index=True
    )
    expires_at: Mapped[datetime] = mapped_column(nullable=False)
    revoked: Mapped[bool] = mapped_column(default=False, nullable=False)

    @property
    def is_expired(self) -> bool:
        return datetime.utcnow() > self.expires_at

    @property
    def is_active(self) -> bool:
        return not self.revoked and not self.is_expired
```

```python
# src/apps/guest/repository.py
from datetime import datetime
from typing import Optional
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import load_only

from .models import GuestModel, GuestRefreshTokenModel


class GuestRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    @property
    def session(self) -> AsyncSession:
        return self._session

    async def get_by_id(self, guest_id: UUID) -> Optional[GuestModel]:
        return await self._session.scalar(
            select(GuestModel).where(GuestModel.id == guest_id)
        )

    async def get_by_device_id(self, device_id: UUID) -> Optional[GuestModel]:
        return await self._session.scalar(
            select(GuestModel).where(GuestModel.device_id == device_id)
        )

    async def get_by_email(self, email: str) -> Optional[GuestModel]:
        return await self._session.scalar(
            select(GuestModel).where(GuestModel.email == email)
        )

    async def get_by_phone(self, phone: str) -> Optional[GuestModel]:
        return await self._session.scalar(
            select(GuestModel).where(GuestModel.phone == phone)
        )

    async def create(self, guest: GuestModel) -> GuestModel:
        self._session.add(guest)
        await self._session.flush()
        return guest

    async def update_conversion(
        self,
        guest_id: UUID,
        email: str,
        phone: str,
        converted_user_id: UUID,
    ) -> None:
        await self._session.execute(
            update(GuestModel)
            .where(GuestModel.id == guest_id)
            .values(
                email=email,
                phone=phone,
                is_converted=True,
                converted_user_id=converted_user_id,
            )
        )
        await self._session.flush()

    async def create_refresh_token(
        self, token_hash: str, guest_id: UUID, expires_at: datetime
    ) -> GuestRefreshTokenModel:
        token = GuestRefreshTokenModel(
            token_hash=token_hash,
            guest_id=guest_id,
            expires_at=expires_at,
        )
        self._session.add(token)
        await self._session.flush()
        return token

    async def get_refresh_token(self, token_hash: str) -> Optional[GuestRefreshTokenModel]:
        return await self._session.scalar(
            select(GuestRefreshTokenModel).where(
                GuestRefreshTokenModel.token_hash == token_hash,
                GuestRefreshTokenModel.revoked == False,
            )
        )

    async def revoke_refresh_token(self, token_hash: str) -> None:
        token = await self._session.scalar(
            select(GuestRefreshTokenModel).where(
                GuestRefreshTokenModel.token_hash == token_hash
            )
        )
        if token:
            token.revoked = True
            await self._session.flush()

    async def revoke_all_guest_tokens(self, guest_id: UUID) -> None:
        await self._session.execute(
            update(GuestRefreshTokenModel)
            .where(GuestRefreshTokenModel.guest_id == guest_id)
            .values(revoked=True)
        )
        await self._session.flush()
```

```python
# src/apps/guest/service.py
import hashlib
import uuid
from datetime import datetime, timedelta

from .exceptions import (
    GuestNotFoundException,
    GuestAlreadyConvertedException,
    DuplicateEmailException,
    DuplicatePhoneException,
)
from .models import GuestModel
from .repository import GuestRepository
from apps.user.models import UserModel
from apps.user.repository import UserRepository
from apps.user.service import UserService
from auth.jwt import create_tokens
from exceptions import UnauthorizedError
from config import settings


class GuestService:
    def __init__(
        self,
        repository: GuestRepository,
        user_repository: UserRepository,
    ) -> None:
        self.repository = repository
        self.user_repository = user_repository

    async def login_guest(self, device_id: uuid.UUID) -> dict:
        """
        Login or create guest by device_id.
        Returns tokens and guest info including device_id for client storage.
        """
        guest = await self.repository.get_by_device_id(device_id)

        if not guest:
            guest = GuestModel.create(device_id=device_id)
            await self.repository.create(guest)
            await self.repository.session.flush()
            await self.repository.session.refresh(guest)

        if guest.is_converted:
            raise GuestAlreadyConvertedException

        tokens = await create_tokens(guest_id=guest.id, type="guest")

        # Store refresh token
        token_hash = self._hash_token(tokens["refresh_token"])
        await self.repository.create_refresh_token(
            token_hash=token_hash,
            guest_id=guest.id,
            expires_at=datetime.utcnow() + timedelta(seconds=int(settings.REFRESH_TOKEN_EXP)),
        )
        await self.repository.session.flush()

        return {
            "guest_id": str(guest.id),
            "device_id": str(guest.device_id),
            "access_token": tokens["access_token"],
            "refresh_token": tokens["refresh_token"],
        }

    async def refresh_guest(self, refresh_token: str) -> dict:
        """
        Validate refresh token and rotate: revoke old, issue new pair.
        For guests only - raises UnauthorizedError for converted guests.
        """
        token_hash = self._hash_token(refresh_token)
        token_record = await self.repository.get_refresh_token(token_hash)

        if not token_record:
            raise UnauthorizedError(message="Invalid refresh token")

        if not token_record.is_active:
            raise UnauthorizedError(message="Refresh token expired or revoked")

        guest = await self.repository.get_by_id(token_record.guest_id)
        if not guest:
            raise UnauthorizedError(message="Guest not found")

        if guest.is_converted:
            raise GuestAlreadyConvertedException

        # Revoke old token
        await self.repository.revoke_refresh_token(token_hash)

        # Issue new tokens
        new_tokens = await create_tokens(guest_id=guest.id, type="guest")

        # Store new refresh token
        await self.repository.create_refresh_token(
            token_hash=self._hash_token(new_tokens["refresh_token"]),
            guest_id=guest.id,
            expires_at=datetime.utcnow() + timedelta(seconds=int(settings.REFRESH_TOKEN_EXP)),
        )
        await self.repository.session.commit()

        return new_tokens

    async def logout_guest(self, refresh_token: str) -> None:
        """Revoke guest refresh token."""
        token_hash = self._hash_token(refresh_token)
        await self.repository.revoke_refresh_token(token_hash)
        await self.repository.session.commit()

    async def convert_guest(
        self,
        guest_id: uuid.UUID,
        email: str,
        phone: str,
        password: str,
        first_name: str,
        last_name: str,
    ) -> dict:
        """
        Convert guest to user at checkout.
        Creates new User, marks Guest as converted, revokes guest tokens.
        """
        guest = await self.repository.get_by_id(guest_id)
        if not guest:
            raise GuestNotFoundException

        if guest.is_converted:
            raise GuestAlreadyConvertedException

        # Check email/phone uniqueness in User table
        existing = await self.user_repository.get_by_email_or_phone(email, phone)
        if existing:
            if existing.email == email.lower():
                raise DuplicateEmailException
            if existing.phone == phone:
                raise DuplicatePhoneException

        # Create user
        user = UserModel.create(
            first_name=first_name,
            last_name=last_name,
            email=email,
            phone=phone,
            password=password,
        )
        self.user_repository.add(user)
        await self.user_repository.session.flush()
        await self.user_repository.session.refresh(user)

        # Update guest record
        await self.repository.update_conversion(
            guest_id=guest_id,
            email=email,
            phone=phone,
            converted_user_id=user.id,
        )

        # Revoke all guest tokens
        await self.repository.revoke_all_guest_tokens(guest_id)

        await self.repository.session.commit()

        # Issue new user tokens
        tokens = await create_tokens(user_id=user.id, type="user")

        return {
            "user_id": str(user.id),
            "access_token": tokens["access_token"],
            "refresh_token": tokens["refresh_token"],
        }

    async def get_guest(self, guest_id: uuid.UUID) -> GuestModel:
        guest = await self.repository.get_by_id(guest_id)
        if not guest:
            raise GuestNotFoundException
        return guest

    @staticmethod
    def _hash_token(token: str) -> str:
        return hashlib.sha256(token.encode()).hexdigest()
```

```python
# src/apps/guest/request.py
import uuid
from utils.schema import CamelCaseModel


class GuestLoginRequest(CamelCaseModel):
    """Empty request - device_id extracted from header."""


class GuestConvertRequest(CamelCaseModel):
    """Request body for converting guest to user at checkout."""
    email: str
    phone: str
    password: str
    first_name: str
    last_name: str
```

```python
# src/apps/guest/response.py
import uuid
from utils.schema import CamelCaseModel


class GuestLoginResponse(CamelCaseModel):
    guest_id: uuid.UUID
    device_id: uuid.UUID
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class GuestResponse(CamelCaseModel):
    id: uuid.UUID
    device_id: uuid.UUID
    is_converted: bool
    converted_user_id: uuid.UUID | None = None
```

```python
# src/apps/guest/exceptions.py
import constants
from exceptions import CustomException, NotFoundError, UnauthorizedError, BadRequestError


class GuestNotFoundException(NotFoundError):
    message = "Guest not found"


class GuestAlreadyConvertedException(UnauthorizedError):
    message = "Guest has already been converted to a user"


class DuplicateEmailException(BadRequestError):
    message = "Email already registered"


class DuplicatePhoneException(BadRequestError):
    message = "Phone number already registered"
```

```python
# src/apps/guest/urls.py
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Body, Depends, Header, Request, status
from fastapi.responses import JSONResponse

from .dependencies import get_current_guest
from .exceptions import GuestAlreadyConvertedException
from .models import GuestModel
from .request import GuestConvertRequest, GuestLoginRequest
from .response import GuestLoginResponse, GuestResponse
from .service import GuestService
from .repository import GuestRepository
from apps.user.repository import UserRepository
from db.session import db_session
from auth.schemas import RefreshRequest
from utils.schema import BaseResponse
from utils.cookies import set_auth_cookies
from constants import SUCCESS
from config import settings


router = APIRouter(prefix="/api/guest", tags=["Guest"])
protected_router = APIRouter(
    prefix="/api/guest", tags=["Guest"], dependencies=[Depends(get_current_guest)]
)


def get_guest_service(session: Annotated, Depends(db_session)]) -> GuestService:
    return GuestService(
        GuestRepository(session),
        UserRepository(session),
    )


# PUBLIC ROUTES

@router.post("/login", status_code=status.HTTP_200_OK, operation_id="guest_login")
async def guest_login(
    device_id_header: Annotated[str, Header(alias="X-Device-ID")],
    service: Annotated[GuestService, Depends(get_guest_service)],
) -> JSONResponse:
    """
    Login or register guest by device_id.
    Device ID is sent in X-Device-ID header (generated client-side).
    Server generates guest_id and returns tokens.
    """
    device_id = UUID(device_id_header)
    result = await service.login_guest(device_id)

    data = {"status": SUCCESS, "code": status.HTTP_200_OK, "data": result}
    response = JSONResponse(content=data)
    # Set cookies for web clients
    response = set_auth_cookies(
        response,
        {"access_token": result["access_token"], "refresh_token": result["refresh_token"]},
    )
    return response


@router.post("/logout", status_code=status.HTTP_200_OK, operation_id="guest_logout")
async def guest_logout(
    body: RefreshRequest,
    service: Annotated[GuestService, Depends(get_guest_service)],
) -> BaseResponse:
    """Logout guest by revoking refresh token."""
    await service.logout_guest(body.refresh_token)
    return BaseResponse(message="Logged out successfully")


# PROTECTED ROUTES (require valid guest token)

@protected_router.post(
    "/convert", status_code=status.HTTP_200_OK, operation_id="convert_guest_to_user"
)
async def convert_guest(
    request: Request,
    body: GuestConvertRequest,
    service: Annotated[GuestService, Depends(get_guest_service)],
) -> JSONResponse:
    """
    Convert guest to user at checkout.
    Requires valid guest token.
    Creates User record, links to Guest, returns new user tokens.
    """
    guest: GuestModel = request.state.guest

    result = await service.convert_guest(
        guest_id=guest.id,
        email=body.email,
        phone=body.phone,
        password=body.password,
        first_name=body.first_name,
        last_name=body.last_name,
    )

    data = {"status": SUCCESS, "code": status.HTTP_200_OK, "data": result}
    response = JSONResponse(content=data)
    response = set_auth_cookies(
        response,
        {"access_token": result["access_token"], "refresh_token": result["refresh_token"]},
    )
    return response


@protected_router.get("/self", status_code=status.HTTP_200_OK, operation_id="get_guest_self")
async def get_guest_self(
    request: Request,
    service: Annotated[GuestService, Depends(get_guest_service)],
) -> BaseResponse[GuestResponse]:
    """Get current guest info."""
    guest: GuestModel = request.state.guest
    return BaseResponse(data=GuestResponse(
        id=guest.id,
        device_id=guest.device_id,
        is_converted=guest.is_converted,
        converted_user_id=guest.converted_user_id,
    ))
```

```python
# src/apps/guest/dependencies.py
from typing import Annotated
from uuid import UUID

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from auth.jwt import access
from db.session import db_session
from exceptions import UnauthorizedError, InvalidJWTTokenException
from .models import GuestModel
from .repository import GuestRepository


security = HTTPBearer()


async def get_current_guest(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    session: AsyncSession = Depends(db_session),
) -> GuestModel:
    """
    Dependency that validates Bearer token and returns the current guest.
    Validates token has type="guest".
    Raises 401 if no valid guest token is provided.
    """
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )

    try:
        payload = access.decode(credentials.credentials)
        if payload.get("type") != "guest":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token type - expected guest",
            )
        guest_id = UUID(payload["sub"])
    except (UnauthorizedError, InvalidJWTTokenException, ValueError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )

    guest = await session.scalar(
        select(GuestModel).where(GuestModel.id == guest_id)
    )

    if not guest:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Guest not found",
        )

    if guest.is_converted:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Guest has been converted",
        )

    request.state.guest = guest
    return guest
```

- [ ] **Step 2: Run `python main.py startapp guest` to verify structure**

---

## Task 2: Modify JWT to Support Type Claim

**Files:**
- Modify: `src/auth/jwt.py`

- [ ] **Step 1: Update create_tokens to accept type parameter**

```python
# In src/auth/jwt.py, modify create_tokens:

async def create_tokens(
    user_id: UUID = None,
    guest_id: UUID = None,
    type: Literal["user", "guest"] = "user",
) -> dict[str, str]:
    """
    Create access-token and refresh-token.
    Only one of user_id or guest_id should be provided based on type.
    """
    if type == "user" and user_id is None:
        raise ValueError("user_id required for user tokens")
    if type == "guest" and guest_id is None:
        raise ValueError("guest_id required for guest tokens")

    sub = str(user_id) if type == "user" else str(guest_id)

    access_token = access.encode(
        payload={"sub": sub, "type": type},
        expire_period=int(settings.ACCESS_TOKEN_EXP),
    )
    refresh_token = refresh.encode(
        payload={"sub": sub, "type": type},
        expire_period=int(settings.REFRESH_TOKEN_EXP),
    )
    return {"access_token": access_token, "refresh_token": refresh_token}
```

- [ ] **Step 2: Verify existing user tests still pass**

Run: `pytest tests/ -v -k "user" --tb=short`
Expected: All user auth tests pass

---

## Task 3: Update Server to Register Guest Router

**Files:**
- Modify: `src/server.py`
- Modify: `src/apps/__init__.py`

- [ ] **Step 1: Update server.py to import and register guest_router**

```python
# In src/server.py, add:
from apps.guest import guest_router

# In create_app(), after base_router.include_router(protected_user_router):
base_router.include_router(guest_router)
```

- [ ] **Step 2: Update apps/__init__.py to export guest_router**

```python
# src/apps/__init__.py
from apps.user import user_router, protected_user_router
from apps.guest import guest_router

__all__ = ["user_router", "protected_user_router", "guest_router"]
```

- [ ] **Step 3: Verify app starts without errors**

Run: `python -c "from server import create_app; app = create_app(); print('OK')"`
Expected: Output "OK" with no errors

---

## Task 4: Create Guest Database Migration

- [ ] **Step 1: Generate migration**

Run: `python main.py makemigrations "add guests table"`
Expected: Migration file created in src/migrations/versions/

- [ ] **Step 2: Apply migration**

Run: `python main.py migrate`
Expected: Migration applied successfully

- [ ] **Step 3: Verify tables exist**

Run: `python main.py showmigrations`
Expected: All migrations show ✓

---

## Task 5: Add Guest Refresh Endpoint (No Changes to User Refresh)

**Files:**
- No modifications needed to user refresh - it stays at `/api/user/refresh`
- Guest refresh already defined in `src/apps/guest/urls.py` at `/api/guest/refresh`

- [ ] **Step 1: Verify guest refresh endpoint exists in urls.py**

The guest refresh endpoint is already defined in Task 1's urls.py:
```python
@router.post("/refresh", status_code=status.HTTP_200_OK, operation_id="guest_refresh")
async def guest_refresh(
    body: RefreshRequest,
    service: Annotated[GuestService, Depends(get_guest_service)],
) -> TokenPair:
    return await service.refresh_guest(body.refresh_token)
```

- [ ] **Step 2: Test both refresh endpoints work**

Run: `pytest tests/ -v -k "refresh" --tb=short`
Expected: Both user and guest refresh tests pass

---

## Task 6: Write Unit Tests for Guest Module

**Files:**
- Create: `tests/apps/guest/__init__.py`
- Create: `tests/apps/guest/test_guest_service.py`
- Create: `tests/apps/guest/test_guest_repository.py`
- Create: `tests/apps/guest/test_guest_urls.py`

- [ ] **Step 1: Write tests for GuestService.login_guest**

```python
# tests/apps/guest/test_guest_service.py
import pytest
from uuid import uuid4
from unittest.mock import AsyncMock, MagicMock

from apps.guest.service import GuestService
from apps.guest.repository import GuestRepository
from apps.guest.models import GuestModel


class TestGuestLogin:
    def test_login_creates_new_guest_when_device_id_not_found(self):
        # Arrange
        mock_session = AsyncMock()
        mock_user_repo = AsyncMock()
        mock_guest_repo = AsyncMock()
        mock_guest_repo.get_by_device_id.return_value = None
        mock_guest_repo.create.return_value = GuestModel.create(device_id=uuid4())
        mock_guest_repo.session.flush = AsyncMock()
        mock_guest_repo.session.refresh = AsyncMock()

        service = GuestService(mock_guest_repo, mock_user_repo)
        device_id = uuid4()

        # Act
        # (test implementation)

        # Assert
        mock_guest_repo.create.assert_called_once()
```

- [ ] **Step 2: Write tests for GuestService.convert_guest**

- [ ] **Step 3: Write tests for GuestService.refresh_guest**

- [ ] **Step 4: Run all guest tests**

Run: `pytest tests/apps/guest/ -v --tb=short`
Expected: All tests pass

---

## Task 7: Integration Test - Full Guest Flow

- [ ] **Step 1: Write integration test for complete guest lifecycle**

```python
# tests/apps/guest/test_guest_integration.py
"""
Integration test covering:
1. Guest login - creates guest, returns device_id
2. Guest browse (protected endpoint) - uses guest token
3. Guest convert - creates user, marks guest converted
4. Guest token now invalid after conversion
"""
```

- [ ] **Step 2: Run integration test**

Run: `pytest tests/apps/guest/test_guest_integration.py -v`
Expected: Full flow passes

---

## Self-Review Checklist

- [ ] Guest login returns device_id for client storage
- [ ] Guest token has `type: "guest"` claim
- [ ] `get_current_guest` validates token type and rejects converted guests
- [ ] Conversion creates User record with email/phone/password
- [ ] Conversion links Guest to User via `converted_user_id`
- [ ] Conversion revokes all guest refresh tokens
- [ ] User and Guest refresh endpoints work correctly after separation
- [ ] All existing user tests still pass
- [ ] Migration creates `guests` and `guest_refresh_tokens` tables

---

## Plan Complete

**Two execution options:**

**1. Subagent-Driven (recommended)** - I dispatch a fresh subagent per task, review between tasks, fast iteration

**2. Inline Execution** - Execute tasks in this session using executing-plans, batch execution with checkpoints

**Which approach?**
