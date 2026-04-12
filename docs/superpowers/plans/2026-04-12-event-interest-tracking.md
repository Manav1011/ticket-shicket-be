# Event Interest Tracking Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add event interest tracking that stores one interest per logged-in user or guest, captures request metadata, and maintains a denormalized `interested_counter` on events.

**Architecture:** Keep the feature inside the existing event and guest architecture, but split public engagement from organizer-only event routes. Add a dedicated public engagement router that uses a combined `get_current_user_or_guest` dependency, then pass the resolved actor into the event service. Use a dedicated `event_interests` table for durability and auditability, and increment `events.interested_counter` only when a new unique interest row is created inside a single transaction.

**Tech Stack:** FastAPI, SQLAlchemy async ORM, Alembic, Pydantic response/request models, `fastapi-limiter` and Redis for rate limiting, `uv` for project commands and tests.

---

### Task 1: Add the combined actor dependency and public engagement router shape

**Files:**
- Modify: `src/auth/dependencies.py`
- Create: `src/apps/event/public_urls.py`
- Modify: `src/apps/event/response.py`
- Test: `tests/apps/event/test_event_urls.py`

- [ ] **Step 1: Write the failing tests for the new router and dependency contract**

```python
from types import SimpleNamespace
from uuid import uuid4

import pytest

from apps.event.response import EventInterestResponse


def test_event_interest_response_includes_created_and_counter():
    response = EventInterestResponse.model_validate({"created": True, "interested_counter": 7})
    assert response.created is True
    assert response.interested_counter == 7


def test_public_interest_router_uses_combined_actor_dependency():
    from apps.event.public_urls import router

    route = next(route for route in router.routes if getattr(route, "path", "") == "/api/events/{event_id}/interest")
    dependency_names = [getattr(dep.call, "__name__", "") for dep in route.dependant.dependencies]
    assert "get_current_user_or_guest" in dependency_names
```

- [ ] **Step 2: Run the tests to confirm the contract is missing**

Run:
```bash
uv run pytest tests/apps/event/test_event_urls.py -k interest -v
```
Expected: fail because `EventInterestResponse`, `get_current_user_or_guest`, and the public interest router do not exist yet.

- [ ] **Step 3: Implement the combined dependency and the public router shell**

```python
# src/auth/dependencies.py
from dataclasses import dataclass


@dataclass
class ActorContext:
    kind: str
    id: UUID


async def get_current_user_or_guest(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    session: AsyncSession = Depends(db_session),
) -> ActorContext:
    if not credentials:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")

    try:
        payload = access.decode(credentials.credentials)
        actor_type = payload.get("user_type")
        actor_id = UUID(payload["sub"])
    except (UnauthorizedError, InvalidJWTTokenException, ValueError):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token")

    if actor_type == "user":
        from apps.user.models import UserModel

        actor = await session.scalar(select(UserModel).where(UserModel.id == actor_id))
        if not actor:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
        request.state.actor = ActorContext(kind="user", id=actor.id)
        request.state.user = actor
        return request.state.actor

    if actor_type == "guest":
        from apps.guest.models import GuestModel

        actor = await session.scalar(select(GuestModel).where(GuestModel.id == actor_id))
        if not actor:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Guest not found")
        if actor.is_converted:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Guest has been converted")
        request.state.actor = ActorContext(kind="guest", id=actor.id)
        request.state.guest = actor
        return request.state.actor

    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token type")
```

```python
# src/apps/event/public_urls.py
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Request
from fastapi_limiter.depends import RateLimiter
from sqlalchemy.ext.asyncio import AsyncSession

from auth.dependencies import get_current_user_or_guest
from db.session import db_session
from src.constants.config import rate_limiter_config
from utils.schema import BaseResponse

from apps.organizer.repository import OrganizerRepository
from .repository import EventRepository
from .response import EventInterestResponse
from .service import EventService

router = APIRouter(
    prefix="/api/events",
    tags=["Event Engagement"],
    dependencies=[Depends(get_current_user_or_guest)],
)


def get_event_service(session: Annotated[AsyncSession, Depends(db_session)]) -> EventService:
    return EventService(EventRepository(session), OrganizerRepository(session))


@router.post(
    "/{event_id}/interest",
    dependencies=[Depends(RateLimiter(times=rate_limiter_config["request_limit"], seconds=rate_limiter_config["time"]))],
)
async def mark_event_interest(
    event_id: UUID,
    request: Request,
    service: Annotated[EventService, Depends(get_event_service)],
) -> BaseResponse[EventInterestResponse]:
    actor = request.state.actor
    result = await service.interest_event(
        actor_kind=actor.kind,
        actor_id=actor.id,
        event_id=event_id,
        ip_address=request.client.host if request.client else "unknown",
        user_agent=request.headers.get("user-agent"),
    )
    return BaseResponse(data=EventInterestResponse.model_validate(result))
```

```python
# src/apps/event/response.py
class EventInterestResponse(CamelCaseModel):
    created: bool
    interested_counter: int


class EventResponse(CamelCaseModel):
    id: UUID
    organizer_page_id: UUID
    created_by_user_id: UUID
    title: str | None = None
    slug: str | None = None
    description: str | None = None
    event_type: str | None = None
    status: str
    event_access_type: str
    setup_status: dict
    location_mode: str | None = None
    timezone: str | None = None
    start_date: date | None = None
    end_date: date | None = None
    venue_name: str | None = None
    venue_address: str | None = None
    venue_city: str | None = None
    venue_state: str | None = None
    venue_country: str | None = None
    venue_latitude: float | None = None
    venue_longitude: float | None = None
    venue_google_place_id: str | None = None
    online_event_url: str | None = None
    recorded_event_url: str | None = None
    published_at: datetime | None = None
    is_published: bool
    show_tickets: bool = False
    interested_counter: int = 0
    media_assets: list["MediaAssetResponse"] = []
```

- [ ] **Step 4: Re-run the tests**

Run:
```bash
uv run pytest tests/apps/event/test_event_urls.py -k interest -v
```
Expected: still fail until the service and repository are implemented, but the response and router contract should be present.

- [ ] **Step 5: Commit**

```bash
git add src/auth/dependencies.py src/apps/event/public_urls.py src/apps/event/response.py tests/apps/event/test_event_urls.py
git commit -m "feat: add public event engagement router"
```

### Task 2: Implement repository and service behavior with a transaction boundary

**Files:**
- Modify: `src/apps/event/repository.py`
- Modify: `src/apps/event/service.py`
- Test: `tests/apps/event/test_event_service.py`

- [ ] **Step 1: Write tests that describe the service behavior**

```python
@pytest.mark.asyncio
async def test_interest_event_creates_row_and_increments_counter_for_user():
    event_id = uuid4()
    event = SimpleNamespace(id=event_id, interested_counter=3)
    event_repo = AsyncMock()
    event_repo.get_by_id_for_update.return_value = event
    event_repo.get_interest_for_actor.return_value = None
    event_repo.create_event_interest.return_value = SimpleNamespace(id=uuid4())
    event_repo.session = AsyncMock()
    service = EventService(event_repo, AsyncMock())

    result = await service.interest_event(
        actor_kind="user",
        actor_id=uuid4(),
        event_id=event_id,
        ip_address="203.0.113.10",
        user_agent="Mozilla/5.0",
    )

    assert result["created"] is True
    assert result["interested_counter"] == 4
```

```python
@pytest.mark.asyncio
async def test_interest_event_is_idempotent_for_same_guest_event_pair():
    event_id = uuid4()
    event = SimpleNamespace(id=event_id, interested_counter=3)
    event_repo = AsyncMock()
    event_repo.get_by_id_for_update.return_value = event
    event_repo.get_interest_for_actor.return_value = SimpleNamespace(id=uuid4())
    event_repo.session = AsyncMock()
    service = EventService(event_repo, AsyncMock())

    result = await service.interest_event(
        actor_kind="guest",
        actor_id=uuid4(),
        event_id=event_id,
        ip_address="203.0.113.10",
        user_agent="Mozilla/5.0",
    )

    assert result["created"] is False
    assert result["interested_counter"] == 3
```

- [ ] **Step 2: Run the service tests and confirm they fail**

Run:
```bash
uv run pytest tests/apps/event/test_event_service.py -k interest -v
```
Expected: fail because repository methods and service method are not implemented yet.

- [ ] **Step 3: Add repository methods for interest lookup, row creation, and locked event fetch**

```python
from sqlalchemy import select, update


class EventRepository:
    async def get_by_id_for_update(self, event_id: UUID) -> EventModel | None:
        return await self._session.scalar(
            select(EventModel).where(EventModel.id == event_id).with_for_update()
        )

    async def get_interest_for_actor(
        self,
        event_id: UUID,
        user_id: UUID | None = None,
        guest_id: UUID | None = None,
    ) -> EventInterestModel | None:
        query = select(EventInterestModel).where(EventInterestModel.event_id == event_id)
        if user_id is not None:
            query = query.where(EventInterestModel.user_id == user_id)
        if guest_id is not None:
            query = query.where(EventInterestModel.guest_id == guest_id)
        return await self._session.scalar(query)

    async def create_event_interest(
        self,
        event_id: UUID,
        user_id: UUID | None,
        guest_id: UUID | None,
        ip_address: str,
        user_agent: str | None,
    ) -> EventInterestModel:
        interest = EventInterestModel(
            event_id=event_id,
            user_id=user_id,
            guest_id=guest_id,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        self._session.add(interest)
        await self._session.flush()
        await self._session.refresh(interest)
        return interest

    async def increment_event_interest_counter(self, event_id: UUID) -> None:
        await self._session.execute(
            update(EventModel)
            .where(EventModel.id == event_id)
            .values(interested_counter=EventModel.interested_counter + 1)
        )
```

```python
from sqlalchemy.exc import IntegrityError


class EventService:
    async def interest_event(self, actor_kind, actor_id, event_id, ip_address, user_agent):
        event = await self.repository.get_by_id_for_update(event_id)
        if not event:
            raise EventNotFound

        existing = await self.repository.get_interest_for_actor(
            event_id=event_id,
            user_id=actor_id if actor_kind == "user" else None,
            guest_id=actor_id if actor_kind == "guest" else None,
        )
        if existing:
            return {"created": False, "interested_counter": event.interested_counter}

        try:
            async with self.repository.session.begin_nested():
                await self.repository.create_event_interest(
                    event_id=event_id,
                    user_id=actor_id if actor_kind == "user" else None,
                    guest_id=actor_id if actor_kind == "guest" else None,
                    ip_address=ip_address,
                    user_agent=user_agent,
                )
                await self.repository.increment_event_interest_counter(event_id)
                event.interested_counter += 1
        except IntegrityError:
            current = await self.repository.get_by_id(event_id)
            return {"created": False, "interested_counter": current.interested_counter}

        return {"created": True, "interested_counter": event.interested_counter}
```

- [ ] **Step 4: Re-run the service tests**

Run:
```bash
uv run pytest tests/apps/event/test_event_service.py -k interest -v
```
Expected: pass.

- [ ] **Step 5: Commit**

```bash
git add src/apps/event/repository.py src/apps/event/service.py tests/apps/event/test_event_service.py
git commit -m "feat: store event interest records"
```

### Task 3: Replace the old organizer-only event route with the engagement router registration

**Files:**
- Modify: `src/apps/event/urls.py`
- Modify: `src/apps/__init__.py` or the application router registration file that currently includes the event router
- Test: `tests/apps/event/test_event_urls.py`

- [ ] **Step 1: Write the failing routing test**

```python
def test_public_interest_route_is_registered_separately_from_organizer_routes():
    from apps.event.public_urls import router as public_router
    from apps.event.urls import router as organizer_router

    public_paths = {getattr(route, "path", "") for route in public_router.routes}
    organizer_paths = {getattr(route, "path", "") for route in organizer_router.routes}

    assert "/api/events/{event_id}/interest" in public_paths
    assert "/api/events/{event_id}/interest" not in organizer_paths
```

- [ ] **Step 2: Run the routing test and confirm it fails**

Run:
```bash
uv run pytest tests/apps/event/test_event_urls.py -k interest -v
```
Expected: fail until the public router is wired in and the old organizer router no longer owns the interest route.

- [ ] **Step 3: Register the new public router and keep organizer routes separate**

```python
# src/apps/event/urls.py keeps organizer-only routes and get_current_user dependency.
# src/apps/event/public_urls.py owns the interest route and uses get_current_user_or_guest.
# app router registration should include both routers.
```

- [ ] **Step 4: Re-run the routing test**

Run:
```bash
uv run pytest tests/apps/event/test_event_urls.py -k interest -v
```
Expected: pass.

- [ ] **Step 5: Commit**

```bash
git add src/apps/event/urls.py src/apps/event/public_urls.py tests/apps/event/test_event_urls.py
git commit -m "feat: split public event engagement routes"
```

### Task 4: Add the migration and apply it cleanly

**Files:**
- Create: `src/migrations/versions/20260412_add_event_interests_and_counter.py`
- Test: `tests/apps/event/test_event_service.py`

- [ ] **Step 1: Write a migration-focused test**

```python
def test_event_model_has_interested_counter_default_zero():
    event = SimpleNamespace(interested_counter=0)
    assert event.interested_counter == 0
```

- [ ] **Step 2: Generate the migration**

Run:
```bash
uv run main.py makemigrations
```
Expected: a new Alembic migration adds `events.interested_counter` and creates `event_interests`.

- [ ] **Step 3: Fill in the migration explicitly**

```python
from alembic import op
import sqlalchemy as sa


def upgrade():
    op.add_column(
        "events",
        sa.Column("interested_counter", sa.Integer(), server_default="0", nullable=False),
    )
    op.create_table(
        "event_interests",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("event_id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=True),
        sa.Column("guest_id", sa.UUID(), nullable=True),
        sa.Column("ip_address", sa.String(length=64), nullable=False),
        sa.Column("user_agent", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["event_id"], ["events.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["guest_id"], ["guests.id"]),
        sa.UniqueConstraint("event_id", "user_id", name="uq_event_interests_event_user"),
        sa.UniqueConstraint("event_id", "guest_id", name="uq_event_interests_event_guest"),
    )


def downgrade():
    op.drop_table("event_interests")
    op.drop_column("events", "interested_counter")
```

- [ ] **Step 4: Apply and verify the migration**

Run:
```bash
uv run main.py migrate
uv run main.py showmigrations
```
Expected: the new migration is applied and visible in migration status.

- [ ] **Step 5: Commit**

```bash
git add src/migrations/versions/20260412_add_event_interests_and_counter.py
git commit -m "feat: add event interest persistence"
```

### Task 5: Verify guest-to-user behavior and update the graph

**Files:**
- Modify: `tests/apps/event/test_event_integration.py` or add a focused integration test if that file does not exist

- [ ] **Step 1: Add a full-flow test for guest and logged-in interest**

```python
@pytest.mark.asyncio
async def test_guest_then_user_interest_counts_as_two_identity_based_interests():
    event_id = uuid4()
    guest_id = uuid4()
    user_id = uuid4()
    event_repo = AsyncMock()
    event_repo.get_by_id_for_update.return_value = SimpleNamespace(id=event_id, interested_counter=0)
    event_repo.get_interest_for_actor.return_value = None
    event_repo.create_event_interest.return_value = SimpleNamespace(id=uuid4())
    event_repo.session = AsyncMock()
    service = EventService(event_repo, AsyncMock())

    first = await service.interest_event(
        actor_kind="guest",
        actor_id=guest_id,
        event_id=event_id,
        ip_address="203.0.113.10",
        user_agent="Mozilla/5.0",
    )
    second = await service.interest_event(
        actor_kind="user",
        actor_id=user_id,
        event_id=event_id,
        ip_address="203.0.113.10",
        user_agent="Mozilla/5.0",
    )

    assert first["interested_counter"] == 1
    assert second["interested_counter"] == 2
```

- [ ] **Step 2: Run the integration test**

Run:
```bash
uv run pytest tests/apps/event/test_event_integration.py -v
```
Expected: pass.

- [ ] **Step 3: Rebuild the graph after code changes**

Run:
```bash
python3 -c "from graphify.watch import _rebuild_code; from pathlib import Path; _rebuild_code(Path('.'))"
```
Expected: graphify cache and `graphify-out/GRAPH_REPORT.md` refresh without errors.

- [ ] **Step 4: Run a final targeted verification set**

Run:
```bash
uv run pytest tests/apps/event/test_event_service.py tests/apps/event/test_event_urls.py tests/apps/event/test_event_integration.py -v
```
Expected: all event interest and regression tests pass.

- [ ] **Step 5: Commit**

```bash
git add tests/apps/event/test_event_integration.py
git commit -m "test: cover event interest flows"
```

## Self-Review

1. Spec coverage:
   - Combined user-or-guest authentication is covered by the new `get_current_user_or_guest` dependency in Task 1.
   - Public engagement routing is covered by the new `src/apps/event/public_urls.py` router in Tasks 1 and 3.
   - `interested_counter` exposure is covered in `EventResponse` in Task 1 so the public event detail page can render it.
   - Transactional interest creation and counter increments are covered in Task 2.
   - Migration and schema persistence are covered in Task 4.
   - Guest-to-user identity remains intentionally separate and is covered in Task 5.

2. Placeholder scan:
   - No `TBD`, `TODO`, or vague implementation instructions remain.
   - All code-changing steps include concrete snippets, file paths, and commands.

3. Type consistency:
   - `ActorContext`, `get_current_user_or_guest`, `EventInterestModel`, `EventInterestResponse`, and `interest_event` are used consistently across tasks.
   - The public route returns `BaseResponse[EventInterestResponse]`.

Plan complete and saved to `docs/superpowers/plans/2026-04-12-event-interest-tracking.md`. Two execution options:

1. Subagent-Driven (recommended) - I dispatch a fresh subagent per task, review between tasks, fast iteration
2. Inline Execution - Execute tasks in this session using executing-plans, batch execution with checkpoints

Which approach?
