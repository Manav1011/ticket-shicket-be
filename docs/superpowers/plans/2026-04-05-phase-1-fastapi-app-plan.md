# Phase 1 FastAPI Apps Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the Phase 1 backend for organizer-owned draft events, event days, optional ticketing, and day-level scan control using the existing FastAPI app architecture.

**Architecture:** Add three new apps that match the current `models / repository / service / request / response / exceptions / urls` pattern: `organizer`, `event`, and `ticketing`. Keep `event_days` and scan lifecycle inside the `event` app because they are tightly coupled to draft creation and scheduling, and keep ticket generation inside `ticketing` because it is the inventory module that depends on event access mode and day allocation state.

**Tech Stack:** FastAPI, Pydantic, SQLAlchemy 2.0 async, Alembic, PostgreSQL, pytest, unittest.mock/AsyncMock

---

## Scope Check

This plan intentionally covers one connected subsystem: the Phase 1 event-operations backend. It does **not** include media uploads, FAQs, public event page rendering, payments, coupons, attendee registration for open events, or low-level live scan ingestion APIs.

## Recommended App Boundaries

Create exactly these three apps:

- `src/apps/organizer`: organizer page ownership, listing, creation, and update.
- `src/apps/event`: draft event shell, event-day scheduling, setup progress, event access mode, and day-level scan lifecycle.
- `src/apps/ticketing`: ticket types, day allocations, and ticket row generation.

Do **not** create these apps in Phase 1:

- `event_day`: keep it inside `event`.
- `media`: phase 2 concern.
- `orders`: later commerce concern.
- `scanning`: scan state belongs to `event_days`; full scan ingestion can come later.
- `registration`: open-event RSVP is a different subsystem from ticketing.

## File Structure

- `src/db/model_registry.py`: imports every SQLAlchemy model so Alembic sees all metadata.
- `src/migrations/env.py`: imports `db.model_registry` before reading `Base.metadata`.
- `src/server.py`: includes the three new routers.
- `src/apps/organizer/__init__.py`: exports organizer router.
- `src/apps/organizer/models.py`: `OrganizerPageModel`.
- `src/apps/organizer/repository.py`: owner-scoped organizer queries and mutations.
- `src/apps/organizer/service.py`: organizer business rules and visibility ownership checks.
- `src/apps/organizer/request.py`: create/update organizer payloads.
- `src/apps/organizer/response.py`: organizer response DTOs.
- `src/apps/organizer/exceptions.py`: owner/slug/domain exceptions.
- `src/apps/organizer/urls.py`: organizer CRUD routes.
- `src/apps/event/__init__.py`: exports event router.
- `src/apps/event/models.py`: `EventModel` and `EventDayModel`.
- `src/apps/event/repository.py`: draft creation, owner-scoped fetch/update, event-day CRUD, and scan-state updates.
- `src/apps/event/service.py`: organizer ownership validation, draft creation, setup progress updates, event-day operations, and scan lifecycle rules.
- `src/apps/event/request.py`: create-draft, update-basic-info, create-event-day, update-event-day payloads.
- `src/apps/event/response.py`: event summary/detail DTOs and event-day DTOs.
- `src/apps/event/exceptions.py`: event ownership, publish-readiness, invalid scan transition, and event-day ownership exceptions.
- `src/apps/event/urls.py`: draft event routes, event-day CRUD routes, and scan control routes.
- `src/apps/ticketing/__init__.py`: exports ticketing router.
- `src/apps/ticketing/models.py`: `TicketTypeModel`, `DayTicketAllocationModel`, `TicketModel`.
- `src/apps/ticketing/repository.py`: ticketing persistence and bulk ticket insertion helpers.
- `src/apps/ticketing/service.py`: event access checks, day allocation, ticket generation, and reserved-seat-compatible metadata handling.
- `src/apps/ticketing/request.py`: create ticket type and allocate-to-day payloads.
- `src/apps/ticketing/response.py`: ticket type and allocation DTOs.
- `src/apps/ticketing/exceptions.py`: open-event ticketing rejection and allocation validation exceptions.
- `src/apps/ticketing/urls.py`: ticketing routes.
- `tests/unit/db/test_model_registry.py`: Alembic model-registration regression test.
- `tests/apps/organizer/test_organizer_service.py`: organizer service rules.
- `tests/apps/organizer/test_organizer_urls.py`: organizer route contract tests.
- `tests/apps/event/test_event_service.py`: draft creation, setup-progress, event-day, and scan lifecycle tests.
- `tests/apps/event/test_event_urls.py`: event and event-day route contract tests.
- `tests/apps/event/test_app_bootstrap.py`: server route wiring test.
- `tests/apps/ticketing/test_ticketing_service.py`: ticket generation and open-vs-ticketed guards.
- `tests/apps/ticketing/test_ticketing_urls.py`: ticketing route tests.

## Task 1: Add Model Registry and Organizer App

**Files:**
- Create: `src/db/model_registry.py`
- Modify: `src/migrations/env.py`
- Create: `src/apps/organizer/__init__.py`
- Create: `src/apps/organizer/models.py`
- Create: `src/apps/organizer/repository.py`
- Create: `src/apps/organizer/service.py`
- Create: `src/apps/organizer/request.py`
- Create: `src/apps/organizer/response.py`
- Create: `src/apps/organizer/exceptions.py`
- Create: `src/apps/organizer/urls.py`
- Create: `tests/unit/db/test_model_registry.py`
- Create: `tests/apps/organizer/test_organizer_service.py`
- Create: `tests/apps/organizer/test_organizer_urls.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/unit/db/test_model_registry.py
from db.base import Base
import db.model_registry  # noqa: F401


def test_model_registry_loads_organizer_table():
    assert "organizer_pages" in Base.metadata.tables
```

```python
# tests/apps/organizer/test_organizer_service.py
from types import SimpleNamespace
from uuid import uuid4
from unittest.mock import AsyncMock

import pytest

from apps.organizer.service import OrganizerService


@pytest.mark.asyncio
async def test_create_organizer_normalizes_slug_and_uses_owner_scope():
    repo = AsyncMock()
    repo.get_by_slug.return_value = None
    service = OrganizerService(repo)

    organizer = await service.create_organizer(
        owner_user_id=uuid4(),
        name="Ahmedabad Talks",
        slug=" Ahmedabad Talks ",
        bio="Meetups",
        visibility="public",
    )

    assert organizer.slug == "ahmedabad-talks"
    repo.add.assert_called_once()


@pytest.mark.asyncio
async def test_list_organizers_only_returns_owner_rows():
    owner_id = uuid4()
    repo = AsyncMock()
    repo.list_by_owner.return_value = [SimpleNamespace(owner_user_id=owner_id)]
    service = OrganizerService(repo)

    organizers = await service.list_organizers(owner_id)

    assert len(organizers) == 1
    repo.list_by_owner.assert_awaited_once_with(owner_id)
```

```python
# tests/apps/organizer/test_organizer_urls.py
from types import SimpleNamespace
from uuid import uuid4
from unittest.mock import AsyncMock

import pytest

from apps.organizer.request import CreateOrganizerPageRequest
from apps.organizer.urls import create_organizer


@pytest.mark.asyncio
async def test_create_organizer_uses_current_user():
    owner_id = uuid4()
    request = SimpleNamespace(state=SimpleNamespace(user=SimpleNamespace(id=owner_id)))
    service = AsyncMock()
    service.create_organizer.return_value = SimpleNamespace(
        id=uuid4(),
        owner_user_id=owner_id,
        name="Ahmedabad Talks",
        slug="ahmedabad-talks",
        bio="Meetups",
        visibility="public",
        status="active",
    )
    body = CreateOrganizerPageRequest(
        name="Ahmedabad Talks",
        slug="Ahmedabad Talks",
        bio="Meetups",
        visibility="public",
    )

    response = await create_organizer(request=request, body=body, service=service)

    assert response.data.owner_user_id == owner_id
    service.create_organizer.assert_awaited_once()
```

- [ ] **Step 2: Run the tests to verify they fail**

Run:

```bash
python3 -m pytest tests/unit/db/test_model_registry.py tests/apps/organizer/test_organizer_service.py tests/apps/organizer/test_organizer_urls.py -v
```

Expected:

```text
FAIL: ModuleNotFoundError for apps.organizer
FAIL: organizer_pages table missing from Base.metadata
```

- [ ] **Step 3: Write the minimal implementation**

```python
# src/db/model_registry.py
from apps.user.models import RefreshTokenModel, UserModel
from apps.guest.models import GuestModel, GuestRefreshTokenModel
from apps.organizer.models import OrganizerPageModel

__all__ = [
    "UserModel",
    "RefreshTokenModel",
    "GuestModel",
    "GuestRefreshTokenModel",
    "OrganizerPageModel",
]
```

```python
# src/migrations/env.py
import db.model_registry  # noqa: F401
from db.base import Base
```

```python
# src/apps/organizer/models.py
import uuid

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from db.base import Base, TimeStampMixin, UUIDPrimaryKeyMixin


class OrganizerPageModel(Base, UUIDPrimaryKeyMixin, TimeStampMixin):
    __tablename__ = "organizer_pages"

    owner_user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), index=True)
    name: Mapped[str] = mapped_column(String(255), index=True)
    slug: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    bio: Mapped[str | None] = mapped_column(nullable=True)
    visibility: Mapped[str] = mapped_column(default="private", nullable=False)
    status: Mapped[str] = mapped_column(default="active", nullable=False)
```

```python
# src/apps/organizer/service.py
import re

from .exceptions import OrganizerSlugAlreadyExists
from .models import OrganizerPageModel


class OrganizerService:
    def __init__(self, repository) -> None:
        self.repository = repository

    async def list_organizers(self, owner_user_id):
        return await self.repository.list_by_owner(owner_user_id)

    async def create_organizer(self, owner_user_id, name, slug, bio, visibility):
        normalized_slug = re.sub(r"[^a-z0-9]+", "-", slug.strip().lower()).strip("-")
        if await self.repository.get_by_slug(normalized_slug):
            raise OrganizerSlugAlreadyExists

        organizer = OrganizerPageModel(
            owner_user_id=owner_user_id,
            name=name.strip(),
            slug=normalized_slug,
            bio=bio,
            visibility=visibility,
            status="active",
        )
        self.repository.add(organizer)
        await self.repository.session.flush()
        await self.repository.session.refresh(organizer)
        return organizer
```

```python
# src/apps/organizer/urls.py
from typing import Annotated

from fastapi import APIRouter, Body, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from auth.dependencies import get_current_user
from db.session import db_session
from utils.schema import BaseResponse
from .repository import OrganizerRepository
from .request import CreateOrganizerPageRequest
from .response import OrganizerPageResponse
from .service import OrganizerService

router = APIRouter(prefix="/api/organizers", tags=["Organizer"], dependencies=[Depends(get_current_user)])


def get_organizer_service(session: Annotated[AsyncSession, Depends(db_session)]) -> OrganizerService:
    return OrganizerService(OrganizerRepository(session))


@router.post("")
async def create_organizer(
    request: Request,
    body: Annotated[CreateOrganizerPageRequest, Body()],
    service: Annotated[OrganizerService, Depends(get_organizer_service)],
) -> BaseResponse[OrganizerPageResponse]:
    organizer = await service.create_organizer(
        owner_user_id=request.state.user.id,
        **body.model_dump(),
    )
    return BaseResponse(data=OrganizerPageResponse.model_validate(organizer))
```

- [ ] **Step 4: Re-run the tests**

Run:

```bash
python3 -m pytest tests/unit/db/test_model_registry.py tests/apps/organizer/test_organizer_service.py tests/apps/organizer/test_organizer_urls.py -v
```

Expected:

```text
PASS
```

- [ ] **Step 5: Commit**

```bash
git add src/db/model_registry.py src/migrations/env.py src/apps/organizer tests/unit/db/test_model_registry.py tests/apps/organizer
git commit -m "feat: add organizer app and model registry"
```

## Task 2: Add Event App for Draft Events, Event Days, and Scan Control

**Files:**
- Modify: `src/db/model_registry.py`
- Create: `src/apps/event/__init__.py`
- Create: `src/apps/event/models.py`
- Create: `src/apps/event/repository.py`
- Create: `src/apps/event/service.py`
- Create: `src/apps/event/request.py`
- Create: `src/apps/event/response.py`
- Create: `src/apps/event/exceptions.py`
- Create: `src/apps/event/urls.py`
- Create: `tests/apps/event/test_event_service.py`
- Create: `tests/apps/event/test_event_urls.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/apps/event/test_event_service.py
from types import SimpleNamespace
from uuid import uuid4
from unittest.mock import AsyncMock

import pytest

from apps.event.exceptions import InvalidScanTransition
from apps.event.service import EventService


@pytest.mark.asyncio
async def test_create_draft_event_uses_organizer_ownership_and_defaults():
    owner_id = uuid4()
    organizer_id = uuid4()
    organizer = SimpleNamespace(id=organizer_id, owner_user_id=owner_id)
    organizer_repo = AsyncMock()
    organizer_repo.get_by_id_for_owner.return_value = organizer
    event_repo = AsyncMock()
    event_repo.session = AsyncMock()
    event_repo.session.flush = AsyncMock()
    event_repo.session.refresh = AsyncMock()
    service = EventService(event_repo, organizer_repo)

    event = await service.create_draft_event(owner_id, organizer_id)

    assert event.organizer_page_id == organizer_id
    assert event.status == "draft"
    assert event.event_access_type == "ticketed"
    assert event.setup_status == {}


@pytest.mark.asyncio
async def test_create_event_day_and_start_scan_from_same_service():
    owner_id = uuid4()
    event_id = uuid4()
    event = SimpleNamespace(id=event_id, organizer_page_id=uuid4())
    day = SimpleNamespace(
        id=uuid4(),
        event_id=event_id,
        day_index=1,
        date="2026-04-15",
        scan_status="not_started",
        scan_started_at=None,
        scan_paused_at=None,
        scan_ended_at=None,
    )
    organizer_repo = AsyncMock()
    event_repo = AsyncMock()
    event_repo.get_by_id_for_owner.return_value = event
    event_repo.create_event_day.return_value = day
    event_repo.get_event_day_for_owner.return_value = day
    event_repo.session = AsyncMock()
    service = EventService(event_repo, organizer_repo)

    created_day = await service.create_event_day(owner_id, event_id, 1, "2026-04-15")
    updated_day = await service.start_scan(owner_id, created_day.id)

    assert created_day.event_id == event_id
    assert updated_day.scan_status == "active"
    assert updated_day.scan_started_at is not None


@pytest.mark.asyncio
async def test_ended_scan_cannot_restart():
    organizer_repo = AsyncMock()
    event_repo = AsyncMock()
    event_repo.get_event_day_for_owner.return_value = SimpleNamespace(
        id=uuid4(),
        scan_status="ended",
        scan_started_at=None,
        scan_paused_at=None,
        scan_ended_at="2026-04-15T12:00:00",
    )
    event_repo.session = AsyncMock()
    service = EventService(event_repo, organizer_repo)

    with pytest.raises(InvalidScanTransition):
        await service.start_scan(uuid4(), uuid4())
```

```python
# tests/apps/event/test_event_urls.py
from types import SimpleNamespace
from uuid import uuid4
from unittest.mock import AsyncMock

import pytest

from apps.event.request import CreateDraftEventRequest
from apps.event.urls import create_draft_event, start_scan


@pytest.mark.asyncio
async def test_create_draft_event_returns_draft_summary():
    owner_id = uuid4()
    organizer_id = uuid4()
    request = SimpleNamespace(state=SimpleNamespace(user=SimpleNamespace(id=owner_id)))
    body = CreateDraftEventRequest(organizer_page_id=organizer_id)
    service = AsyncMock()
    service.create_draft_event.return_value = SimpleNamespace(
        id=uuid4(),
        organizer_page_id=organizer_id,
        created_by_user_id=owner_id,
        title="Untitled Event",
        slug=None,
        description=None,
        event_type=None,
        status="draft",
        event_access_type="ticketed",
        setup_status={},
        location_mode="venue",
        timezone="Asia/Kolkata",
    )

    response = await create_draft_event(request=request, body=body, service=service)

    assert response.data.status == "draft"
    assert response.data.organizer_page_id == organizer_id


@pytest.mark.asyncio
async def test_start_scan_returns_active_state():
    owner_id = uuid4()
    event_day_id = uuid4()
    request = SimpleNamespace(state=SimpleNamespace(user=SimpleNamespace(id=owner_id)))
    service = AsyncMock()
    service.start_scan.return_value = SimpleNamespace(
        id=event_day_id,
        event_id=uuid4(),
        day_index=1,
        date="2026-04-15",
        scan_status="active",
        scan_started_at="2026-04-15T10:00:00",
        scan_paused_at=None,
        scan_ended_at=None,
    )

    response = await start_scan(event_day_id=event_day_id, request=request, service=service)

    assert response.data.scan_status == "active"
```

- [ ] **Step 2: Run the tests to verify they fail**

Run:

```bash
python3 -m pytest tests/apps/event/test_event_service.py tests/apps/event/test_event_urls.py -v
```

Expected:

```text
FAIL: ModuleNotFoundError for apps.event
```

- [ ] **Step 3: Write the minimal implementation**

```python
# src/apps/event/models.py
import uuid

from sqlalchemy import ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from db.base import Base, TimeStampMixin, UUIDPrimaryKeyMixin


class EventModel(Base, UUIDPrimaryKeyMixin, TimeStampMixin):
    __tablename__ = "events"

    organizer_page_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organizer_pages.id"), index=True)
    created_by_user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), index=True)
    title: Mapped[str] = mapped_column(String(255), default="Untitled Event")
    slug: Mapped[str | None] = mapped_column(String(255), unique=True, nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    event_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="draft", nullable=False)
    event_access_type: Mapped[str] = mapped_column(String(32), default="ticketed", nullable=False)
    setup_status: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    location_mode: Mapped[str] = mapped_column(String(32), default="venue", nullable=False)
    timezone: Mapped[str] = mapped_column(String(64), default="Asia/Kolkata", nullable=False)


class EventDayModel(Base, UUIDPrimaryKeyMixin, TimeStampMixin):
    __tablename__ = "event_days"

    event_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("events.id"), index=True)
    day_index: Mapped[int] = mapped_column(Integer, nullable=False)
    date: Mapped[str] = mapped_column(String(32), nullable=False)
    scan_status: Mapped[str] = mapped_column(String(32), default="not_started", nullable=False)
    scan_started_at: Mapped[str | None] = mapped_column(nullable=True)
    scan_paused_at: Mapped[str | None] = mapped_column(nullable=True)
    scan_ended_at: Mapped[str | None] = mapped_column(nullable=True)
    next_ticket_index: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
```

```python
# src/apps/event/service.py
from datetime import datetime

from .exceptions import EventNotFound, InvalidScanTransition, OrganizerOwnershipError
from .models import EventDayModel, EventModel


class EventService:
    def __init__(self, repository, organizer_repository) -> None:
        self.repository = repository
        self.organizer_repository = organizer_repository

    async def create_draft_event(self, owner_user_id, organizer_page_id):
        organizer = await self.organizer_repository.get_by_id_for_owner(organizer_page_id, owner_user_id)
        if not organizer:
            raise OrganizerOwnershipError

        event = EventModel(
            organizer_page_id=organizer_page_id,
            created_by_user_id=owner_user_id,
            title="Untitled Event",
            status="draft",
            event_access_type="ticketed",
            setup_status={},
            location_mode="venue",
            timezone="Asia/Kolkata",
        )
        self.repository.add(event)
        await self.repository.session.flush()
        await self.repository.session.refresh(event)
        return event

    async def update_basic_info(self, owner_user_id, event_id, title, description, location_mode, timezone, event_access_type):
        event = await self.repository.get_by_id_for_owner(event_id, owner_user_id)
        if not event:
            raise EventNotFound

        event.title = title
        event.description = description
        event.location_mode = location_mode
        event.timezone = timezone
        event.event_access_type = event_access_type
        event.setup_status = {**event.setup_status, "basic_info": True, "access": True}
        await self.repository.session.flush()
        return event

    async def create_event_day(self, owner_user_id, event_id, day_index, date):
        event = await self.repository.get_by_id_for_owner(event_id, owner_user_id)
        if not event:
            raise EventNotFound
        return await self.repository.create_event_day(event_id, day_index, date)

    async def start_scan(self, owner_user_id, event_day_id):
        day = await self.repository.get_event_day_for_owner(event_day_id, owner_user_id)
        if day.scan_status == "ended":
            raise InvalidScanTransition
        day.scan_status = "active"
        if day.scan_started_at is None:
            day.scan_started_at = datetime.utcnow().isoformat()
        await self.repository.session.flush()
        return day
```

```python
# src/apps/event/urls.py
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Body, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from auth.dependencies import get_current_user
from db.session import db_session
from utils.schema import BaseResponse
from apps.organizer.repository import OrganizerRepository
from .repository import EventRepository
from .request import CreateDraftEventRequest
from .response import EventDayResponse, EventResponse
from .service import EventService

router = APIRouter(prefix="/api/events", tags=["Event"], dependencies=[Depends(get_current_user)])


def get_event_service(session: Annotated[AsyncSession, Depends(db_session)]) -> EventService:
    return EventService(EventRepository(session), OrganizerRepository(session))


@router.post("/drafts")
async def create_draft_event(
    request: Request,
    body: Annotated[CreateDraftEventRequest, Body()],
    service: Annotated[EventService, Depends(get_event_service)],
) -> BaseResponse[EventResponse]:
    event = await service.create_draft_event(request.state.user.id, body.organizer_page_id)
    return BaseResponse(data=EventResponse.model_validate(event))


@router.post("/days/{event_day_id}/start-scan")
async def start_scan(
    event_day_id: UUID,
    request: Request,
    service: Annotated[EventService, Depends(get_event_service)],
) -> BaseResponse[EventDayResponse]:
    day = await service.start_scan(request.state.user.id, event_day_id)
    return BaseResponse(data=EventDayResponse.model_validate(day))
```

- [ ] **Step 4: Re-run the tests**

Run:

```bash
python3 -m pytest tests/apps/event/test_event_service.py tests/apps/event/test_event_urls.py -v
```

Expected:

```text
PASS
```

- [ ] **Step 5: Commit**

```bash
git add src/apps/event src/db/model_registry.py tests/apps/event
git commit -m "feat: add event app with days and scan lifecycle"
```

## Task 3: Add Ticketing App with Open-vs-Ticketed Guards

**Files:**
- Modify: `src/db/model_registry.py`
- Create: `src/apps/ticketing/__init__.py`
- Create: `src/apps/ticketing/models.py`
- Create: `src/apps/ticketing/repository.py`
- Create: `src/apps/ticketing/service.py`
- Create: `src/apps/ticketing/request.py`
- Create: `src/apps/ticketing/response.py`
- Create: `src/apps/ticketing/exceptions.py`
- Create: `src/apps/ticketing/urls.py`
- Create: `tests/apps/ticketing/test_ticketing_service.py`
- Create: `tests/apps/ticketing/test_ticketing_urls.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/apps/ticketing/test_ticketing_service.py
from types import SimpleNamespace
from uuid import uuid4
from unittest.mock import AsyncMock

import pytest

from apps.ticketing.exceptions import OpenEventDoesNotSupportTickets
from apps.ticketing.service import TicketingService


@pytest.mark.asyncio
async def test_allocate_day_inventory_generates_ticket_rows():
    event = SimpleNamespace(id=uuid4(), event_access_type="ticketed")
    ticket_type = SimpleNamespace(id=uuid4(), event_id=event.id, name="General")
    event_repo = AsyncMock()
    event_repo.get_by_id_for_owner.return_value = event
    day_repo = AsyncMock()
    day_repo.get_event_day_for_owner.return_value = SimpleNamespace(id=uuid4(), event_id=event.id, next_ticket_index=1)
    repo = AsyncMock()
    repo.create_ticket_type.return_value = ticket_type
    repo.session = AsyncMock()
    service = TicketingService(repo, event_repo, day_repo)

    await service.allocate_ticket_type_to_day(
        owner_user_id=uuid4(),
        event_id=event.id,
        event_day_id=day_repo.get_event_day_for_owner.return_value.id,
        ticket_type_id=ticket_type.id,
        quantity=3,
    )

    repo.bulk_create_tickets.assert_awaited_once()


@pytest.mark.asyncio
async def test_open_event_rejects_ticket_type_creation():
    event = SimpleNamespace(id=uuid4(), event_access_type="open")
    repo = AsyncMock()
    repo.session = AsyncMock()
    event_repo = AsyncMock()
    event_repo.get_by_id_for_owner.return_value = event
    day_repo = AsyncMock()
    service = TicketingService(repo, event_repo, day_repo)

    with pytest.raises(OpenEventDoesNotSupportTickets):
        await service.create_ticket_type(
            owner_user_id=uuid4(),
            event_id=event.id,
            name="General",
            category="PUBLIC",
            price=0,
            currency="INR",
        )
```

```python
# tests/apps/ticketing/test_ticketing_urls.py
from types import SimpleNamespace
from uuid import uuid4
from unittest.mock import AsyncMock

import pytest

from apps.ticketing.request import CreateTicketTypeRequest
from apps.ticketing.urls import create_ticket_type


@pytest.mark.asyncio
async def test_create_ticket_type_returns_ticket_type_dto():
    owner_id = uuid4()
    event_id = uuid4()
    request = SimpleNamespace(state=SimpleNamespace(user=SimpleNamespace(id=owner_id)))
    body = CreateTicketTypeRequest(name="General", category="PUBLIC", price=0, currency="INR")
    service = AsyncMock()
    service.create_ticket_type.return_value = SimpleNamespace(
        id=uuid4(),
        event_id=event_id,
        name="General",
        category="PUBLIC",
        price=0,
        currency="INR",
    )

    response = await create_ticket_type(event_id=event_id, request=request, body=body, service=service)

    assert response.data.name == "General"
```

- [ ] **Step 2: Run the tests to verify they fail**

Run:

```bash
python3 -m pytest tests/apps/ticketing/test_ticketing_service.py tests/apps/ticketing/test_ticketing_urls.py -v
```

Expected:

```text
FAIL: ModuleNotFoundError for apps.ticketing
```

- [ ] **Step 3: Write the minimal implementation**

```python
# src/apps/ticketing/models.py
import uuid

from sqlalchemy import ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from db.base import Base, TimeStampMixin, UUIDPrimaryKeyMixin


class TicketTypeModel(Base, UUIDPrimaryKeyMixin, TimeStampMixin):
    __tablename__ = "ticket_types"

    event_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("events.id"), index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    category: Mapped[str] = mapped_column(String(32), nullable=False)
    price: Mapped[float] = mapped_column(Numeric, nullable=False)
    currency: Mapped[str] = mapped_column(String(8), default="INR", nullable=False)


class DayTicketAllocationModel(Base, UUIDPrimaryKeyMixin, TimeStampMixin):
    __tablename__ = "day_ticket_allocations"

    event_day_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("event_days.id"), index=True)
    ticket_type_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("ticket_types.id"), index=True)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)


class TicketModel(Base, UUIDPrimaryKeyMixin, TimeStampMixin):
    __tablename__ = "tickets"

    event_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("events.id"), index=True)
    event_day_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("event_days.id"), index=True)
    ticket_type_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("ticket_types.id"), index=True)
    ticket_index: Mapped[int] = mapped_column(Integer, nullable=False)
    seat_label: Mapped[str | None] = mapped_column(nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="active", nullable=False)
```

```python
# src/apps/ticketing/service.py
from .exceptions import OpenEventDoesNotSupportTickets
from .models import TicketTypeModel


class TicketingService:
    def __init__(self, repository, event_repository, event_day_repository) -> None:
        self.repository = repository
        self.event_repository = event_repository
        self.event_day_repository = event_day_repository

    async def create_ticket_type(self, owner_user_id, event_id, name, category, price, currency):
        event = await self.event_repository.get_by_id_for_owner(event_id, owner_user_id)
        if event.event_access_type != "ticketed":
            raise OpenEventDoesNotSupportTickets

        ticket_type = TicketTypeModel(
            event_id=event_id,
            name=name,
            category=category,
            price=price,
            currency=currency,
        )
        self.repository.add(ticket_type)
        await self.repository.session.flush()
        await self.repository.session.refresh(ticket_type)
        return ticket_type

    async def allocate_ticket_type_to_day(self, owner_user_id, event_id, event_day_id, ticket_type_id, quantity):
        event = await self.event_repository.get_by_id_for_owner(event_id, owner_user_id)
        if event.event_access_type != "ticketed":
            raise OpenEventDoesNotSupportTickets

        day = await self.event_day_repository.get_event_day_for_owner(event_day_id, owner_user_id)
        await self.repository.create_day_allocation(event_day_id, ticket_type_id, quantity)
        await self.repository.bulk_create_tickets(
            event_id,
            event_day_id,
            ticket_type_id,
            start_index=day.next_ticket_index,
            quantity=quantity,
        )
        day.next_ticket_index += quantity
        await self.repository.session.flush()
```

```python
# src/apps/ticketing/urls.py
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Body, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from auth.dependencies import get_current_user
from db.session import db_session
from utils.schema import BaseResponse
from apps.event.repository import EventRepository
from .repository import TicketingRepository
from .request import CreateTicketTypeRequest
from .response import TicketTypeResponse
from .service import TicketingService

router = APIRouter(prefix="/api/events", tags=["Ticketing"], dependencies=[Depends(get_current_user)])


def get_ticketing_service(session: Annotated[AsyncSession, Depends(db_session)]) -> TicketingService:
    return TicketingService(TicketingRepository(session), EventRepository(session), EventRepository(session))


@router.post("/{event_id}/ticket-types")
async def create_ticket_type(
    event_id: UUID,
    request: Request,
    body: Annotated[CreateTicketTypeRequest, Body()],
    service: Annotated[TicketingService, Depends(get_ticketing_service)],
) -> BaseResponse[TicketTypeResponse]:
    ticket_type = await service.create_ticket_type(request.state.user.id, event_id, **body.model_dump())
    return BaseResponse(data=TicketTypeResponse.model_validate(ticket_type))
```

- [ ] **Step 4: Re-run the tests**

Run:

```bash
python3 -m pytest tests/apps/ticketing/test_ticketing_service.py tests/apps/ticketing/test_ticketing_urls.py -v
```

Expected:

```text
PASS
```

- [ ] **Step 5: Commit**

```bash
git add src/apps/ticketing src/db/model_registry.py tests/apps/ticketing
git commit -m "feat: add phase one ticketing app"
```

## Task 4: Wire Routers, Export App Modules, and Generate Migration

**Files:**
- Modify: `src/apps/organizer/__init__.py`
- Modify: `src/apps/event/__init__.py`
- Modify: `src/apps/ticketing/__init__.py`
- Modify: `src/server.py`
- Create: `src/migrations/versions/<revision>_add_phase_one_event_tables.py`

- [ ] **Step 1: Write the failing smoke test**

```python
# tests/apps/event/test_app_bootstrap.py
from server import create_app


def test_phase_one_routes_are_registered():
    app = create_app()
    paths = {route.path for route in app.routes}

    assert "/api/organizers" in paths
    assert "/api/events/drafts" in paths
    assert "/api/events/days/{event_day_id}/start-scan" in paths
    assert "/api/events/{event_id}/ticket-types" in paths
```

- [ ] **Step 2: Run the smoke test to verify it fails**

Run:

```bash
python3 -m pytest tests/apps/event/test_app_bootstrap.py -v
```

Expected:

```text
FAIL: one or more Phase 1 routes are missing from create_app()
```

- [ ] **Step 3: Wire routers and generate migration**

```python
# src/apps/organizer/__init__.py
from .urls import router as organizer_router

__all__ = ["organizer_router"]
```

```python
# src/apps/event/__init__.py
from .urls import router as event_router

__all__ = ["event_router"]
```

```python
# src/apps/ticketing/__init__.py
from .urls import router as ticketing_router

__all__ = ["ticketing_router"]
```

```python
# src/server.py
from apps.organizer import organizer_router
from apps.event import event_router
from apps.ticketing import ticketing_router

base_router.include_router(organizer_router)
base_router.include_router(event_router)
base_router.include_router(ticketing_router)
```

Run:

```bash
python3 main.py makemigrations -m "add phase one event tables"
```

Expected:

```text
Changes detected! Generating migrations.
Generating src/migrations/versions/<revision>_add_phase_one_event_tables.py
```

- [ ] **Step 4: Re-run the smoke test and migration check**

Run:

```bash
python3 -m pytest tests/apps/event/test_app_bootstrap.py -v
python3 main.py showmigrations
```

Expected:

```text
PASS
Migration script for organizer_pages, events, event_days, ticket_types, day_ticket_allocations, tickets exists
```

- [ ] **Step 5: Commit**

```bash
git add src/server.py src/apps/organizer/__init__.py src/apps/event/__init__.py src/apps/ticketing/__init__.py src/migrations/versions tests/apps/event/test_app_bootstrap.py
git commit -m "feat: wire phase one routers and migrations"
```

## Task 5: Final Verification

**Files:**
- Modify: `docs/schemas/base.md` if implementation diverged from schema decisions
- Modify: `docs/schemas/ER_Diagram.mmd` if implementation diverged from schema decisions

- [ ] **Step 1: Run the focused Phase 1 backend test suite**

Run:

```bash
python3 -m pytest \
  tests/unit/db/test_model_registry.py \
  tests/apps/organizer/test_organizer_service.py \
  tests/apps/organizer/test_organizer_urls.py \
  tests/apps/event/test_event_service.py \
  tests/apps/event/test_event_urls.py \
  tests/apps/event/test_app_bootstrap.py \
  tests/apps/ticketing/test_ticketing_service.py \
  tests/apps/ticketing/test_ticketing_urls.py -v
```

Expected:

```text
PASS
```

- [ ] **Step 2: Apply migrations on the local database**

Run:

```bash
python3 main.py migrate
```

Expected:

```text
Database migrated successfully
```

- [ ] **Step 3: Manual API sanity check**

Run:

```bash
python3 main.py runserver
```

Then verify in Swagger:

- `POST /api/organizers`
- `POST /api/events/drafts`
- `POST /api/events/days/{event_day_id}/start-scan`
- `POST /api/events/{event_id}/ticket-types`

- [ ] **Step 4: Commit**

```bash
git add .
git commit -m "test: verify phase one event backend flow"
```

## Implementation Notes

- Organizer selection UX edge cases belong in frontend flow, but backend must support them cleanly:
  - zero organizer pages -> frontend should call organizer create first.
  - one organizer page -> frontend can skip chooser and call event draft create directly.
  - many organizer pages -> frontend should show chooser and pass `organizer_page_id`.
- Keep `event_access_type` on `events`, not `event_days`.
- Keep scan lifecycle on `event_days`, but keep the code for it inside the `event` app.
- Do not create ticket rows for `open` events.
- Do not create a scan-session table in Phase 1; `scan_status` plus timestamps are enough for now.
- Keep `seat_label` optional in `tickets`; do not let it drive business logic.

## Self-Review

**Spec coverage:** This plan covers organizer ownership, draft-first event creation, setup progress, event access mode, event-day scan control, and ticket generation. It intentionally excludes media, FAQs, publish workflow hardening, orders, coupons, and open-event registration.

**Placeholder scan:** No `TODO`, `TBD`, or “implement later” placeholders were left in the tasks. Every task names exact files, test commands, and concrete class/function names.

**Type consistency:** The plan consistently uses `OrganizerPageModel`, `EventModel`, `EventDayModel`, `TicketTypeModel`, `DayTicketAllocationModel`, `TicketModel`, and service names `OrganizerService`, `EventService`, and `TicketingService`. Route prefixes are consistently `/api/organizers` and `/api/events`.

Plan complete and saved to `docs/superpowers/plans/2026-04-05-phase-1-fastapi-app-plan.md`. Two execution options:

**1. Subagent-Driven (recommended)** - I dispatch a fresh subagent per task, review between tasks, fast iteration

**2. Inline Execution** - Execute tasks in this session using executing-plans, batch execution with checkpoints

Which approach?
