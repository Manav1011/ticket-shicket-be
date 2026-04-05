from datetime import datetime
from types import SimpleNamespace
from uuid import uuid4
from unittest.mock import AsyncMock, MagicMock

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
    event_repo.add = MagicMock()
    event_repo.session = AsyncMock()
    event_repo.session.flush = AsyncMock()
    event_repo.session.refresh = AsyncMock()
    service = EventService(event_repo, organizer_repo)

    event = await service.create_draft_event(owner_id, organizer_id)

    assert event.organizer_page_id == organizer_id
    assert event.status == "draft"
    assert event.event_access_type == "ticketed"
    assert event.setup_status == {}
    assert event.title is None
    assert event.slug is None
    assert event.start_date is None
    assert event.end_date is None


@pytest.mark.asyncio
async def test_create_event_day_and_start_scan_from_same_service():
    owner_id = uuid4()
    event_id = uuid4()
    event = SimpleNamespace(id=event_id, organizer_page_id=uuid4())
    day = SimpleNamespace(
        id=uuid4(),
        event_id=event_id,
        day_index=1,
        date=datetime(2026, 4, 15).date(),
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

    created_day = await service.create_event_day(
        owner_id, event_id, 1, datetime(2026, 4, 15).date()
    )
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
