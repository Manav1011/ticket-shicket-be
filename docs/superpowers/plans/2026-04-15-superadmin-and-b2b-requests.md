# Super Admin & B2B Request System — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the super admin app with `SuperAdminModel` + `B2BRequestModel`, along with the B2B request lifecycle from organizer submission → super admin approval → allocation.

**Architecture:**
- `SuperAdminModel` in `superadmin` app — links a user to super admin privileges
- `B2BRequestModel` in `superadmin` app — request queue + fulfillment record
- `get_current_super_admin` auth dependency lives in `src/auth/dependencies.py` (with other auth deps), applied at router level
- Organizer endpoints live in `organizer/urls.py` (create request, confirm payment)
- Super admin endpoints live in `superadmin/urls.py` (review, approve, reject)
- `from_holder_id = NULL` (pool) for all B2B allocations
- Payment gateway mocked — organizer confirms payment → allocation created

**Tech Stack:** FastAPI, SQLAlchemy async, Alembic, Pydantic, pytest

---

## File Map

### New App Module (superadmin)
- `src/apps/superadmin/__init__.py` — created by `startapp`
- `src/apps/superadmin/enums.py` — B2BRequestStatus enum
- `src/apps/superadmin/models.py` — SuperAdminModel, B2BRequestModel
- `src/apps/superadmin/repository.py` — data access for both models
- `src/apps/superadmin/service.py` — business logic
- `src/apps/superadmin/urls.py` — API routes (super admin only)
- `src/apps/superadmin/request.py` — Pydantic request schemas
- `src/apps/superadmin/response.py` — Pydantic response schemas

### Modified Files
- `src/auth/dependencies.py` — add `get_current_super_admin` here
- `src/apps/organizer/urls.py` — add B2B request endpoints (organizer side)
- `src/apps/organizer/request.py` — add B2B request schemas
- `src/apps/organizer/service.py` — add B2B request creation + payment confirmation
- `src/apps/organizer/repository.py` — add B2B request data access
- `src/server.py` — register superadmin router
- `src/db/model_registry.py` — register new models

### Auto-Generated (by `makemigrations`)
- `src/migrations/versions/<auto>_add_superadmin_and_b2b_tables.py`

---

## Task 1: Scaffold Super Admin App

**Files:**
- Run: `uv run main.py startapp superadmin`

- [ ] **Step 1: Create the superadmin app**

```bash
uv run main.py startapp superadmin
```

- [ ] **Step 2: Create `src/apps/superadmin/enums.py`**

```python
from enum import Enum


class B2BRequestStatus(str, Enum):
    pending = "pending"           # Awaiting super admin review
    approved_free = "approved_free"   # Approved, allocation created (free transfer)
    approved_paid = "approved_paid"    # Approved, pending payment
    rejected = "rejected"         # Denied by super admin
    expired = "expired"           # Order payment timeout
```

- [ ] **Step 3: Create `src/apps/superadmin/models.py`**

```python
import uuid

from sqlalchemy import Enum, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from db.base import Base, TimeStampMixin, UUIDPrimaryKeyMixin
from .enums import B2BRequestStatus


class SuperAdminModel(Base, UUIDPrimaryKeyMixin, TimeStampMixin):
    """
    Links a User account to super admin privileges.
    """
    __tablename__ = "super_admins"

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), unique=True, index=True, nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)


class B2BRequestModel(Base, UUIDPrimaryKeyMixin, TimeStampMixin):
    """
    B2B ticket request from an organizer.
    Serves as both request queue and fulfillment record.
    """
    __tablename__ = "b2b_requests"

    # Who submitted this request
    requesting_organizer_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizer_pages.id", ondelete="CASCADE"), index=True, nullable=False
    )
    requesting_user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )

    # Which event/day/ticket type
    event_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("events.id", ondelete="CASCADE"), index=True, nullable=False
    )
    event_day_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("event_days.id", ondelete="CASCADE"), nullable=False
    )
    ticket_type_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("ticket_types.id", ondelete="CASCADE"), nullable=False
    )

    # How many tickets
    quantity: Mapped[int] = mapped_column(nullable=False)

    # Contact of the recipient (organizer receives these tickets)
    recipient_phone: Mapped[str | None] = mapped_column(String(32), nullable=True)
    recipient_email: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Request status
    status: Mapped[str] = mapped_column(
        Enum(B2BRequestStatus),
        default=B2BRequestStatus.pending,
        nullable=False,
        index=True,
    )

    # Admin response
    reviewed_by_admin_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("super_admins.id", ondelete="SET NULL"), nullable=True
    )
    admin_notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Fulfillment links (filled when allocation is created)
    allocation_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("allocations.id", ondelete="SET NULL"), nullable=True
    )
    order_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("orders.id", ondelete="SET NULL"), nullable=True
    )

    # Metadata for audit
    metadata_: Mapped[dict] = mapped_column(
        JSONB, default=dict, nullable=False
    )
```

- [ ] **Step 4: Commit**

```bash
git add src/apps/superadmin/
git commit -m "feat(superadmin): scaffold superadmin app with SuperAdminModel and B2BRequestModel"
```

---

## Task 2: Register Models & Add SuperAdmin Router to Server

**Files:**
- Modify: `src/db/model_registry.py`
- Modify: `src/server.py`

- [ ] **Step 1: Update `src/db/model_registry.py`**

Add to imports:
```python
from apps.superadmin.models import B2BRequestModel, SuperAdminModel
```

Add to `__all__`:
```python
    "SuperAdminModel",
    "B2BRequestModel",
```

- [ ] **Step 2: Update `src/server.py`**

Add import:
```python
from apps.superadmin.urls import router as superadmin_router
```

Add to base_router include:
```python
base_router.include_router(superadmin_router)
```

- [ ] **Step 3: Commit**

```bash
git add src/db/model_registry.py src/server.py
git commit -m "feat(superadmin): register superadmin router and models"
```

---

## Task 3: Add get_current_super_admin to Auth Dependencies

**Files:**
- Modify: `src/auth/dependencies.py`

- [ ] **Step 1: Add `get_current_super_admin` to `src/auth/dependencies.py`**

Add this after the existing `get_current_user_or_guest` function:

```python
async def get_current_super_admin(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    session: AsyncSession = Depends(db_session),
) -> "SuperAdminModel":
    """
    Dependency that validates Bearer token and returns the current super admin.
    Raises 401 if no valid token, 403 if token is valid but user is not a super admin.
    """
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )

    try:
        payload = access.decode(credentials.credentials)
        if payload.get("user_type") != "user":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token type",
            )
        user_id = UUID(payload["sub"])
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )

    from apps.superadmin.models import SuperAdminModel

    admin = await session.scalar(
        select(SuperAdminModel).where(SuperAdminModel.user_id == user_id)
    )

    if not admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not a super admin",
        )

    return admin
```

- [ ] **Step 2: Commit**

```bash
git add src/auth/dependencies.py
git commit -m "feat(superadmin): add get_current_super_admin auth dependency"
```

---

## Task 4: Create B2B Request Repository in SuperAdmin App

**Files:**
- Create: `src/apps/superadmin/repository.py`

- [ ] **Step 1: Create `src/apps/superadmin/repository.py`**

```python
from typing import Optional
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from .enums import B2BRequestStatus
from .models import B2BRequestModel, SuperAdminModel


class SuperAdminRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    @property
    def session(self) -> AsyncSession:
        return self._session

    # --- SuperAdmin ---

    async def get_super_admin_by_user_id(self, user_id: UUID) -> Optional[SuperAdminModel]:
        return await self._session.scalar(
            select(SuperAdminModel).where(SuperAdminModel.user_id == user_id)
        )

    async def create_super_admin(self, user_id: UUID, name: str) -> SuperAdminModel:
        admin = SuperAdminModel(user_id=user_id, name=name)
        self._session.add(admin)
        await self._session.flush()
        await self._session.refresh(admin)
        return admin

    # --- B2B Request ---

    async def get_b2b_request_by_id(self, request_id: UUID) -> Optional[B2BRequestModel]:
        return await self._session.scalar(
            select(B2BRequestModel).where(B2BRequestModel.id == request_id)
        )

    async def list_b2b_requests(
        self,
        status: B2BRequestStatus | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[B2BRequestModel]:
        query = select(B2BRequestModel).order_by(B2BRequestModel.created_at.desc())
        if status:
            query = query.where(B2BRequestModel.status == status.value)
        query = query.limit(limit).offset(offset)
        result = await self._session.scalars(query)
        return list(result.all())

    async def list_b2b_requests_by_organizer(
        self,
        organizer_id: UUID,
        status: B2BRequestStatus | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[B2BRequestModel]:
        query = (
            select(B2BRequestModel)
            .where(B2BRequestModel.requesting_organizer_id == organizer_id)
            .order_by(B2BRequestModel.created_at.desc())
        )
        if status:
            query = query.where(B2BRequestModel.status == status.value)
        query = query.limit(limit).offset(offset)
        result = await self._session.scalars(query)
        return list(result.all())

    async def create_b2b_request(
        self,
        requesting_organizer_id: UUID,
        requesting_user_id: UUID,
        event_id: UUID,
        event_day_id: UUID,
        ticket_type_id: UUID,
        quantity: int,
        recipient_phone: str | None = None,
        recipient_email: str | None = None,
        metadata: dict | None = None,
    ) -> B2BRequestModel:
        request = B2BRequestModel(
            requesting_organizer_id=requesting_organizer_id,
            requesting_user_id=requesting_user_id,
            event_id=event_id,
            event_day_id=event_day_id,
            ticket_type_id=ticket_type_id,
            quantity=quantity,
            recipient_phone=recipient_phone,
            recipient_email=recipient_email,
            metadata_=metadata or {},
        )
        self._session.add(request)
        await self._session.flush()
        await self._session.refresh(request)
        return request

    async def update_b2b_request_status(
        self,
        request_id: UUID,
        new_status: B2BRequestStatus,
        admin_id: UUID,
        admin_notes: str | None = None,
        allocation_id: UUID | None = None,
        order_id: UUID | None = None,
    ) -> bool:
        result = await self._session.execute(
            update(B2BRequestModel)
            .where(B2BRequestModel.id == request_id)
            .values(
                status=new_status.value,
                reviewed_by_admin_id=admin_id,
                admin_notes=admin_notes,
                allocation_id=allocation_id,
                order_id=order_id,
            )
        )
        return result.rowcount > 0
```

- [ ] **Step 2: Commit**

```bash
git add src/apps/superadmin/repository.py
git commit -m "feat(superadmin): add repository for SuperAdminModel and B2BRequestModel"
```

---

## Task 5: Create SuperAdmin Service

**Files:**
- Create: `src/apps/superadmin/service.py`
- Create: `src/apps/superadmin/exceptions.py`

- [ ] **Step 1: Create `src/apps/superadmin/exceptions.py`**

```python
class SuperAdminError(Exception):
    """Base exception for super admin errors."""
    pass


class B2BRequestNotFoundError(SuperAdminError):
    """Raised when a B2B request cannot be found."""
    pass


class B2BRequestNotPendingError(SuperAdminError):
    """Raised when a B2B request is not in pending status."""
    pass


class InsufficientTicketsError(SuperAdminError):
    """Raised when not enough tickets are available."""

    def __init__(self, requested: int, available: int):
        self.requested = requested
        self.available = available
        super().__init__(f"Requested {requested} tickets, only {available} available")
```

- [ ] **Step 2: Create `src/apps/superadmin/service.py`**

```python
"""
Super admin service — handles B2B request lifecycle.
All B2B operations are wrapped in a single database transaction.
"""
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.allocation.enums import AllocationStatus
from apps.allocation.models import AllocationModel, OrderModel
from apps.allocation.repository import AllocationRepository
from apps.allocation.service import AllocationService
from apps.ticketing.enums import OrderStatus, OrderType
from apps.ticketing.models import TicketModel

from .enums import B2BRequestStatus
from .exceptions import (
    B2BRequestNotFoundError,
    B2BRequestNotPendingError,
    InsufficientTicketsError,
)
from .models import B2BRequestModel, SuperAdminModel
from .repository import SuperAdminRepository


class SuperAdminService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = SuperAdminRepository(session)
        self._allocation_repo = AllocationRepository(session)

    @property
    def repo(self) -> SuperAdminRepository:
        return self._repo

    async def get_b2b_request(self, request_id: uuid.UUID) -> B2BRequestModel:
        request = await self._repo.get_b2b_request_by_id(request_id)
        if not request:
            raise B2BRequestNotFoundError(f"B2B request {request_id} not found")
        return request

    async def list_pending_b2b_requests(
        self, limit: int = 50, offset: int = 0
    ) -> list[B2BRequestModel]:
        return await self._repo.list_b2b_requests(
            status=B2BRequestStatus.pending, limit=limit, offset=offset
        )

    async def list_all_b2b_requests(
        self,
        status: B2BRequestStatus | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[B2BRequestModel]:
        return await self._repo.list_b2b_requests(status=status, limit=limit, offset=offset)

    async def approve_b2b_request_free(
        self,
        admin_id: uuid.UUID,
        request_id: uuid.UUID,
        admin_notes: str | None = None,
    ) -> B2BRequestModel:
        """
        Approve a B2B request with free transfer (no payment).
        Creates allocation directly with a $0 TRANSFER order.
        """
        b2b_request = await self.get_b2b_request(request_id)
        if b2b_request.status != B2BRequestStatus.pending:
            raise B2BRequestNotPendingError(
                f"B2B request is {b2b_request.status}, expected pending"
            )

        # Resolve recipient holder
        allocation_service = AllocationService(self._session)
        to_holder = await allocation_service.resolve_holder(
            phone=b2b_request.recipient_phone,
            email=b2b_request.recipient_email,
            create_if_missing=True,
        )

        async with self._session.begin():
            # Create $0 TRANSFER order (free = immediately paid)
            order = OrderModel(
                event_id=b2b_request.event_id,
                user_id=b2b_request.requesting_user_id,
                type=OrderType.transfer,
                subtotal_amount=0.0,
                discount_amount=0.0,
                final_amount=0.0,
                status=OrderStatus.paid,
            )
            self._session.add(order)
            await self._session.flush()

            # Select + lock + allocate tickets (FIFO from pool)
            ticket_ids = await self._select_and_lock_tickets_fifo(
                event_day_id=b2b_request.event_day_id,
                ticket_type_id=b2b_request.ticket_type_id,
                quantity=b2b_request.quantity,
                order_id=order.id,
            )

            if len(ticket_ids) < b2b_request.quantity:
                raise InsufficientTicketsError(
                    requested=b2b_request.quantity,
                    available=len(ticket_ids),
                )

            # Create allocation (from_holder_id=NULL means pool)
            allocation = await self._allocation_repo.create_allocation(
                event_id=b2b_request.event_id,
                from_holder_id=None,
                to_holder_id=to_holder.id,
                order_id=order.id,
                ticket_count=len(ticket_ids),
                metadata_={
                    "b2b_request_id": str(b2b_request.id),
                    "approved_by_admin_id": str(admin_id),
                    "source": "b2b_free",
                },
            )

            # Add tickets to allocation
            await self._allocation_repo.add_tickets_to_allocation(allocation.id, ticket_ids)

            # Update ticket ownership
            await self._update_ticket_ownership(ticket_ids, to_holder.id)

            # Upsert edge (pool → holder)
            await self._allocation_repo.upsert_edge(
                event_id=b2b_request.event_id,
                from_holder_id=None,
                to_holder_id=to_holder.id,
                ticket_count=len(ticket_ids),
            )

            # Mark allocation completed
            await self._allocation_repo.transition_allocation_status(
                allocation.id,
                AllocationStatus.pending,
                AllocationStatus.completed,
            )

            # Update B2B request
            await self._repo.update_b2b_request_status(
                request_id=b2b_request.id,
                new_status=B2BRequestStatus.approved_free,
                admin_id=admin_id,
                admin_notes=admin_notes,
                allocation_id=allocation.id,
                order_id=order.id,
            )

        await self._session.refresh(b2b_request)
        return b2b_request

    async def approve_b2b_request_paid(
        self,
        admin_id: uuid.UUID,
        request_id: uuid.UUID,
        amount: float,
        admin_notes: str | None = None,
    ) -> B2BRequestModel:
        """
        Approve a B2B request with paid order.
        Creates a pending PURCHASE order. Organizer pays via payment gateway.
        Allocation is created later when organizer confirms payment.
        """
        b2b_request = await self.get_b2b_request(request_id)
        if b2b_request.status != B2BRequestStatus.pending:
            raise B2BRequestNotPendingError(
                f"B2B request is {b2b_request.status}, expected pending"
            )

        async with self._session.begin():
            # Create PURCHASE order with pending status
            order = OrderModel(
                event_id=b2b_request.event_id,
                user_id=b2b_request.requesting_user_id,
                type=OrderType.purchase,
                subtotal_amount=amount,
                discount_amount=0.0,
                final_amount=amount,
                status=OrderStatus.pending,
            )
            self._session.add(order)
            await self._session.flush()

            # Update B2B request — no allocation_id yet (allocation comes after payment)
            await self._repo.update_b2b_request_status(
                request_id=b2b_request.id,
                new_status=B2BRequestStatus.approved_paid,
                admin_id=admin_id,
                admin_notes=admin_notes,
                order_id=order.id,
            )

            await self._session.refresh(b2b_request)

        return b2b_request

    async def reject_b2b_request(
        self,
        admin_id: uuid.UUID,
        request_id: uuid.UUID,
        reason: str | None = None,
    ) -> B2BRequestModel:
        """Reject a B2B request."""
        b2b_request = await self.get_b2b_request(request_id)
        if b2b_request.status != B2BRequestStatus.pending:
            raise B2BRequestNotPendingError(
                f"B2B request is {b2b_request.status}, expected pending"
            )

        await self._repo.update_b2b_request_status(
            request_id=b2b_request.id,
            new_status=B2BRequestStatus.rejected,
            admin_id=admin_id,
            admin_notes=reason,
        )
        await self._session.refresh(b2b_request)
        return b2b_request

    async def process_paid_b2b_allocation(
        self,
        request_id: uuid.UUID,
    ) -> B2BRequestModel:
        """
        Called after payment succeeds. Creates the actual allocation using the existing paid order.
        This method is called from the organizer's confirm-payment endpoint.
        admin_id is pulled from b2b_request.reviewed_by_admin_id (the super admin who approved it).
        """
        b2b_request = await self.get_b2b_request(request_id)
        if b2b_request.status != B2BRequestStatus.approved_paid:
            raise B2BRequestNotPendingError(
                f"B2B request is {b2b_request.status}, expected approved_paid"
            )
        if not b2b_request.order_id:
            raise SuperAdminError(f"No order_id found for B2B request {request_id}")

        admin_id = b2b_request.reviewed_by_admin_id

        # Get the existing pending order
        order = await self._session.scalar(
            select(OrderModel).where(OrderModel.id == b2b_request.order_id)
        )
        if not order:
            raise SuperAdminError(f"Order {b2b_request.order_id} not found")

        # Mark order as paid
        order.status = OrderStatus.paid

        # Resolve recipient holder
        allocation_service = AllocationService(self._session)
        to_holder = await allocation_service.resolve_holder(
            phone=b2b_request.recipient_phone,
            email=b2b_request.recipient_email,
            create_if_missing=True,
        )

        # Select + lock + allocate tickets
        ticket_ids = await self._select_and_lock_tickets_fifo(
            event_day_id=b2b_request.event_day_id,
            ticket_type_id=b2b_request.ticket_type_id,
            quantity=b2b_request.quantity,
            order_id=order.id,
        )

        if len(ticket_ids) < b2b_request.quantity:
            raise InsufficientTicketsError(
                requested=b2b_request.quantity,
                available=len(ticket_ids),
            )

        # Create allocation (from_holder_id=NULL means pool)
        allocation = await self._allocation_repo.create_allocation(
            event_id=b2b_request.event_id,
            from_holder_id=None,
            to_holder_id=to_holder.id,
            order_id=order.id,
            ticket_count=len(ticket_ids),
            metadata_={
                "b2b_request_id": str(b2b_request.id),
                "approved_by_admin_id": str(admin_id),
                "source": "b2b_paid",
            },
        )

        # Add tickets to allocation
        await self._allocation_repo.add_tickets_to_allocation(allocation.id, ticket_ids)

        # Update ticket ownership
        await self._update_ticket_ownership(ticket_ids, to_holder.id)

        # Upsert edge
        await self._allocation_repo.upsert_edge(
            event_id=b2b_request.event_id,
            from_holder_id=None,
            to_holder_id=to_holder.id,
            ticket_count=len(ticket_ids),
        )

        # Mark allocation completed
        await self._allocation_repo.transition_allocation_status(
            allocation.id,
            AllocationStatus.pending,
            AllocationStatus.completed,
        )

        # Update B2B request with allocation_id
        await self._repo.update_b2b_request_status(
            request_id=b2b_request.id,
            new_status=B2BRequestStatus.approved_paid,
            admin_id=admin_id,
            allocation_id=allocation.id,
        )

        await self._session.refresh(b2b_request)
        return b2b_request

    async def _select_and_lock_tickets_fifo(
        self,
        event_day_id: uuid.UUID,
        ticket_type_id: uuid.UUID,
        quantity: int,
        order_id: uuid.UUID,
    ) -> list[uuid.UUID]:
        """
        Select the oldest unallocated tickets (FIFO by ticket_index) and lock them.
        Uses SELECT + UPDATE in a single atomic operation.
        """
        from sqlalchemy import update
        from sqlalchemy import select as sa_select

        # Subquery: select ticket IDs ordered by ticket_index (FIFO), limited by quantity
        subq = (
            sa_select(TicketModel.id)
            .where(
                TicketModel.event_day_id == event_day_id,
                TicketModel.ticket_type_id == ticket_type_id,
                TicketModel.owner_holder_id.is_(None),
                TicketModel.lock_reference_id.is_(None),
                TicketModel.status == "active",
            )
            .order_by(TicketModel.ticket_index.asc())
            .limit(quantity)
            .with_for_update()
        )

        # Update selected tickets with lock
        result = await self._session.execute(
            update(TicketModel)
            .where(TicketModel.id.in_(subq.scalar_subquery()))
            .values(
                lock_reference_type="order",
                lock_reference_id=order_id,
            )
            .returning(TicketModel.id)
        )
        return list(result.scalars().all())

    async def _update_ticket_ownership(
        self, ticket_ids: list[uuid.UUID], to_holder_id: uuid.UUID
    ) -> None:
        """Update ticket ownership and clear locks."""
        from sqlalchemy import update

        await self._session.execute(
            update(TicketModel)
            .where(TicketModel.id.in_(ticket_ids))
            .values(
                owner_holder_id=to_holder_id,
                lock_reference_type=None,
                lock_reference_id=None,
            )
        )
```

- [ ] **Step 3: Commit**

```bash
git add src/apps/superadmin/service.py src/apps/superadmin/exceptions.py
git commit -m "feat(superadmin): add service with approve/reject flows and process_paid_b2b_allocation"
```

---

## Task 6: SuperAdmin API Routes (Router-Level Auth)

**Files:**
- Create: `src/apps/superadmin/request.py`
- Create: `src/apps/superadmin/response.py`
- Create: `src/apps/superadmin/urls.py`

- [ ] **Step 1: Create `src/apps/superadmin/request.py`**

```python
from pydantic import BaseModel, Field


class ApproveB2BRequestFreeBody(BaseModel):
    admin_notes: str | None = None


class ApproveB2BRequestPaidBody(BaseModel):
    amount: float = Field(gt=0)
    admin_notes: str | None = None


class RejectB2BRequestBody(BaseModel):
    reason: str | None = None
```

- [ ] **Step 2: Create `src/apps/superadmin/response.py`**

```python
from pydantic import BaseModel


class B2BRequestResponse(BaseModel):
    id: str
    requesting_organizer_id: str
    requesting_user_id: str
    event_id: str
    event_day_id: str
    ticket_type_id: str
    quantity: int
    recipient_phone: str | None
    recipient_email: str | None
    status: str
    reviewed_by_admin_id: str | None
    admin_notes: str | None
    allocation_id: str | None
    order_id: str | None
    metadata: dict = Field(validation_alias="metadata_", serialization_alias="metadata")
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True
```

- [ ] **Step 3: Create `src/apps/superadmin/urls.py`**

```python
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Body, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from auth.dependencies import get_current_super_admin
from apps.superadmin.models import SuperAdminModel
from apps.superadmin.request import (
    ApproveB2BRequestFreeBody,
    ApproveB2BRequestPaidBody,
    RejectB2BRequestBody,
)
from apps.superadmin.response import B2BRequestResponse
from apps.superadmin.service import SuperAdminService
from db.session import db_session
from utils.schema import BaseResponse

# Router-level auth: all routes require super admin
router = APIRouter(
    prefix="/api/superadmin",
    tags=["SuperAdmin"],
    dependencies=[Depends(get_current_super_admin)],
)


def get_super_admin_service(
    session: Annotated[AsyncSession, Depends(db_session)],
) -> SuperAdminService:
    return SuperAdminService(session)


@router.get("/b2b-requests")
async def list_b2b_requests(
    admin: SuperAdminModel,
    service: Annotated[SuperAdminService, Depends(get_super_admin_service)],
    status_filter: str | None = Query(None, alias="status"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
) -> BaseResponse[list[B2BRequestResponse]]:
    """
    [Super Admin] List all B2B requests, optionally filtered by status.
    """
    from apps.superadmin.enums import B2BRequestStatus

    status_enum = B2BRequestStatus(status_filter) if status_filter else None
    requests = await service.list_all_b2b_requests(
        status=status_enum, limit=limit, offset=offset
    )
    return BaseResponse(data=[B2BRequestResponse.model_validate(r) for r in requests])


@router.get("/b2b-requests/pending")
async def list_pending_b2b_requests(
    admin: SuperAdminModel,
    service: Annotated[SuperAdminService, Depends(get_super_admin_service)],
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
) -> BaseResponse[list[B2BRequestResponse]]:
    """
    [Super Admin] List pending B2B requests awaiting review.
    """
    requests = await service.list_pending_b2b_requests(limit=limit, offset=offset)
    return BaseResponse(data=[B2BRequestResponse.model_validate(r) for r in requests])


@router.get("/b2b-requests/{request_id}")
async def get_b2b_request(
    request_id: UUID,
    admin: SuperAdminModel,
    service: Annotated[SuperAdminService, Depends(get_super_admin_service)],
) -> BaseResponse[B2BRequestResponse]:
    """
    [Super Admin] Get a single B2B request by ID.
    """
    b2b_request = await service.get_b2b_request(request_id)
    return BaseResponse(data=B2BRequestResponse.model_validate(b2b_request))


@router.post("/b2b-requests/{request_id}/approve-free")
async def approve_b2b_request_free(
    request_id: UUID,
    admin: SuperAdminModel,
    service: Annotated[SuperAdminService, Depends(get_super_admin_service)],
    body: Annotated[ApproveB2BRequestFreeBody, Body()],
) -> BaseResponse[B2BRequestResponse]:
    """
    [Super Admin] Approve B2B request as free transfer.
    Creates allocation immediately with $0 TRANSFER order.
    """
    b2b_request = await service.approve_b2b_request_free(
        admin_id=admin.id,
        request_id=request_id,
        admin_notes=body.admin_notes,
    )
    return BaseResponse(data=B2BRequestResponse.model_validate(b2b_request))


@router.post("/b2b-requests/{request_id}/approve-paid")
async def approve_b2b_request_paid(
    request_id: UUID,
    admin: SuperAdminModel,
    service: Annotated[SuperAdminService, Depends(get_super_admin_service)],
    body: Annotated[ApproveB2BRequestPaidBody, Body()],
) -> BaseResponse[B2BRequestResponse]:
    """
    [Super Admin] Approve B2B request as paid.
    Sets the amount and creates a pending PURCHASE order.
    Organizer then pays via the organizer app's confirm-payment endpoint.
    """
    b2b_request = await service.approve_b2b_request_paid(
        admin_id=admin.id,
        request_id=request_id,
        amount=body.amount,
        admin_notes=body.admin_notes,
    )
    return BaseResponse(data=B2BRequestResponse.model_validate(b2b_request))


@router.post("/b2b-requests/{request_id}/reject")
async def reject_b2b_request(
    request_id: UUID,
    admin: SuperAdminModel,
    service: Annotated[SuperAdminService, Depends(get_super_admin_service)],
    body: Annotated[RejectB2BRequestBody, Body()],
) -> BaseResponse[B2BRequestResponse]:
    """
    [Super Admin] Reject a B2B request.
    """
    b2b_request = await service.reject_b2b_request(
        admin_id=admin.id,
        request_id=request_id,
        reason=body.reason,
    )
    return BaseResponse(data=B2BRequestResponse.model_validate(b2b_request))
```

- [ ] **Step 4: Commit**

```bash
git add src/apps/superadmin/urls.py src/apps/superadmin/request.py src/apps/superadmin/response.py
git commit -m "feat(superadmin): add API routes with router-level super admin auth"
```

---

## Task 7: Add B2B Request Endpoints to Organizer App

**Files:**
- Modify: `src/apps/organizer/request.py` — add B2B schemas
- Modify: `src/apps/organizer/service.py` — add B2B methods
- Modify: `src/apps/organizer/repository.py` — add B2B repo methods
- Modify: `src/apps/organizer/urls.py` — add B2B routes

- [ ] **Step 1: Add to `src/apps/organizer/request.py`**

```python
class CreateB2BRequestBody(BaseModel):
    event_id: str
    event_day_id: str
    ticket_type_id: str
    quantity: int = Field(gt=0)
    recipient_phone: str | None = None
    recipient_email: str | None = None


class ConfirmB2BPaymentBody(BaseModel):
    pass  # No body needed; b2b_request_id comes from path parameter
```

- [ ] **Step 2: Add to `src/apps/organizer/repository.py`**

Add import:
```python
from apps.superadmin.enums import B2BRequestStatus
from apps.superadmin.models import B2BRequestModel
from apps.superadmin.repository import SuperAdminRepository
```

In `OrganizerRepository.__init__`:
```python
self._super_admin_repo = SuperAdminRepository(session)
```

Add method:
```python
    async def create_b2b_request(
        self,
        requesting_organizer_id: UUID,
        requesting_user_id: UUID,
        event_id: UUID,
        event_day_id: UUID,
        ticket_type_id: UUID,
        quantity: int,
        recipient_phone: str | None = None,
        recipient_email: str | None = None,
    ) -> B2BRequestModel:
        return await self._super_admin_repo.create_b2b_request(
            requesting_organizer_id=requesting_organizer_id,
            requesting_user_id=requesting_user_id,
            event_id=event_id,
            event_day_id=event_day_id,
            ticket_type_id=ticket_type_id,
            quantity=quantity,
            recipient_phone=recipient_phone,
            recipient_email=recipient_email,
        )

    async def get_b2b_request_by_id(
        self, request_id: UUID
    ) -> Optional[B2BRequestModel]:
        return await self._super_admin_repo.get_b2b_request_by_id(request_id)

    async def list_b2b_requests_by_organizer(
        self,
        organizer_id: UUID,
        status: Optional = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[B2BRequestModel]:
        return await self._super_admin_repo.list_b2b_requests_by_organizer(
            organizer_id=organizer_id,
            status=status,
            limit=limit,
            offset=offset,
        )
```

- [ ] **Step 3: Add to `src/apps/organizer/service.py`**

Add import:
```python
from apps.superadmin.service import SuperAdminService
from apps.superadmin.enums import B2BRequestStatus
```

In `OrganizerService.__init__`:
```python
self._super_admin_service = SuperAdminService(session)
```

Add methods:
```python
    async def create_b2b_request(
        self,
        organizer_id: uuid.UUID,
        user_id: uuid.UUID,
        event_id: uuid.UUID,
        event_day_id: uuid.UUID,
        ticket_type_id: uuid.UUID,
        quantity: int,
        recipient_phone: str | None = None,
        recipient_email: str | None = None,
    ):
        """[Organizer] Submit a B2B ticket request."""
        return await self._repo.create_b2b_request(
            requesting_organizer_id=organizer_id,
            requesting_user_id=user_id,
            event_id=event_id,
            event_day_id=event_day_id,
            ticket_type_id=ticket_type_id,
            quantity=quantity,
            recipient_phone=recipient_phone,
            recipient_email=recipient_email,
        )

    async def get_my_b2b_requests(
        self,
        organizer_id: uuid.UUID,
    ) -> list:
        """[Organizer] List B2B requests submitted by this organizer."""
        return await self._repo.list_b2b_requests_by_organizer(organizer_id)

    async def confirm_b2b_payment(
        self,
        request_id: uuid.UUID,
    ):
        """
        [Organizer] Confirm payment for an approved paid B2B request.
        Triggers full allocation after mock payment success.
        admin_id is read from b2b_request.reviewed_by_admin_id (the approving super admin).
        """
        return await self._super_admin_service.process_paid_b2b_allocation(
            request_id=request_id,
        )
```

Note: `process_paid_b2b_allocation` is called with `admin_id` for audit trail (stored in allocation metadata). The organizer's super admin account is the approving admin.

- [ ] **Step 4: Add to `src/apps/organizer/urls.py`**

Add routes to the existing `router` (which already has `get_current_user` auth):

```python
@router.post("/{organizer_id}/b2b-requests")
async def create_b2b_request(
    organizer_id: UUID,
    request: Request,
    body: Annotated[CreateB2BRequestBody, Body()],
    service: Annotated[OrganizerService, Depends(get_organizer_service)],
) -> BaseResponse[B2BRequestResponse]:
    """
    [Organizer] Submit a B2B ticket request.
    """
    b2b_req = await service.create_b2b_request(
        organizer_id=organizer_id,
        user_id=request.state.user.id,
        event_id=UUID(body.event_id),
        event_day_id=UUID(body.event_day_id),
        ticket_type_id=UUID(body.ticket_type_id),
        quantity=body.quantity,
        recipient_phone=body.recipient_phone,
        recipient_email=body.recipient_email,
    )
    return BaseResponse(data=B2BRequestResponse.model_validate(b2b_req))


@router.get("/{organizer_id}/b2b-requests")
async def list_my_b2b_requests(
    organizer_id: UUID,
    request: Request,
    service: Annotated[OrganizerService, Depends(get_organizer_service)],
) -> BaseResponse[list[B2BRequestResponse]]:
    """
    [Organizer] List B2B requests submitted by this organizer.
    """
    b2b_reqs = await service.get_my_b2b_requests(
        organizer_id=organizer_id,
    )
    return BaseResponse(data=[B2BRequestResponse.model_validate(r) for r in b2b_reqs])


@router.post("/{organizer_id}/b2b-requests/{b2b_request_id}/confirm-payment")
async def confirm_b2b_payment(
    organizer_id: UUID,
    b2b_request_id: UUID,
    request: Request,
    service: Annotated[OrganizerService, Depends(get_organizer_service)],
    body: Annotated[ConfirmB2BPaymentBody, Body()],
) -> BaseResponse[B2BRequestResponse]:
    """
    [Organizer] Confirm payment for an approved paid B2B request.
    Mock payment success — triggers allocation creation.
    The admin_id for audit is read from b2b_request.reviewed_by_admin_id.
    """
    b2b_req = await service.confirm_b2b_payment(
        request_id=b2b_request_id,
    )
    return BaseResponse(data=B2BRequestResponse.model_validate(b2b_req))
```

Also add to the imports in `src/apps/organizer/urls.py`:
```python
from apps.superadmin.response import B2BRequestResponse
from apps.superadmin.request import CreateB2BRequestBody, ConfirmB2BPaymentBody
```

- [ ] **Step 5: Commit**

```bash
git add src/apps/organizer/request.py src/apps/organizer/service.py src/apps/organizer/repository.py src/apps/organizer/urls.py
git commit -m "feat(organizer): add B2B request creation and payment confirmation endpoints"
```

---

## Task 8: Generate & Run Migrations

**Files:**
- Auto-generated: `src/migrations/versions/<auto>_*.py`

- [ ] **Step 1: Generate migrations**

```bash
uv run main.py makemigrations
```

- [ ] **Step 2: Apply migrations**

```bash
uv run main.py migrate
```

- [ ] **Step 3: Verify tables exist**

```bash
docker compose exec -T postgres psql -U testuser -d testdb -c "\dt super_admins"
docker compose exec -T postgres psql -U testuser -d testdb -c "\dt b2b_requests"
```

- [ ] **Step 4: Commit**

```bash
git add src/migrations/versions/
git commit -m "chore(superadmin): add migrations for super_admins and b2b_requests tables"
```

---

## Task 9: Add CLI Command to Create Super Admin

**Files:**
- Modify: `src/cli.py`

- [ ] **Step 1: Add to `src/cli.py`**

Add import:
```python
from apps.superadmin.repository import SuperAdminRepository
```

Add command:
```python
@cli.command()
@click.argument("user_id")
@click.argument("name")
def create_super_admin(user_id: str, name: str) -> None:
    """Create a super admin linked to a user ID (by user UUID)."""
    import asyncio
    from uuid import UUID
    from src.db.session import async_session

    async def _create():
        async with async_session() as session:
            repo = SuperAdminRepository(session)
            admin = await repo.create_super_admin(
                user_id=UUID(user_id),
                name=name,
            )
            await session.commit()
            click.echo(f"Super admin created: {admin.id} ({admin.name})")

    asyncio.run(_create())
```

- [ ] **Step 2: Commit**

```bash
git add src/cli.py
git commit -m "feat(superadmin): add CLI command to create super admin"
```

---

## Self-Review Checklist

- [ ] `get_current_super_admin` is in `src/auth/dependencies.py` (not superadmin app)
- [ ] Super admin auth applied at router level (not per-route)
- [ ] `create_b2b_request` endpoint is in `organizer/urls.py`, not `superadmin/urls.py`
- [ ] `confirm-payment` endpoint is in `organizer/urls.py`, not `superadmin/urls.py`
- [ ] Superadmin endpoints only handle: list, approve-free, approve-paid, reject
- [ ] `SuperAdminModel` has unique FK to `users.id`
- [ ] `B2BRequestModel` stores full request + fulfillment metadata (allocation_id, order_id)
- [ ] `from_holder_id = NULL` for all B2B allocations (pool source)
- [ ] `approve_b2b_request_free` creates allocation + $0 TRANSFER order in one transaction
- [ ] `approve_b2b_request_paid` creates pending PURCHASE order, no allocation yet
- [ ] `process_paid_b2b_allocation` (called from confirm-payment) creates allocation using existing paid order
- [ ] FIFO ticket selection via `ORDER BY ticket_index ASC LIMIT quantity`
- [ ] All status transitions are atomic transactions
- [ ] B2B request status enum covers full lifecycle: pending → approved_free / approved_paid / rejected / expired
- [ ] `makemigrations` generates clean migrations
- [ ] `migrate` applies successfully
- [ ] All new tables have correct FK references

---

## Execution Options

**Plan complete and saved to `docs/superpowers/plans/2026-04-15-superadmin-and-b2b-requests.md`. Two execution options:**

**1. Subagent-Driven (recommended)** - I dispatch a fresh subagent per task, review between tasks, fast iteration

**2. Inline Execution** - Execute tasks in this session using executing-plans, batch execution with checkpoints

Which approach?
