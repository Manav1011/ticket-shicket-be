from datetime import datetime
from types import SimpleNamespace
from uuid import uuid4
from unittest.mock import AsyncMock

import pytest

from apps.event.service import EventService


@pytest.mark.asyncio
async def test_readiness_marks_open_event_complete_without_ticket_setup():
    owner_id = uuid4()
    event_id = uuid4()
    repo = AsyncMock()
    organizer_repo = AsyncMock()
    event = SimpleNamespace(
        id=event_id,
        title="Open Community Meetup",
        event_access_type="open",
        location_mode="venue",
        timezone="Asia/Kolkata",
        setup_status={},
    )
    repo.get_by_id_for_owner.return_value = event
    repo.count_event_days.return_value = 1
    repo.count_ticket_types.return_value = 0
    repo.count_ticket_allocations.return_value = 0
    repo.session = AsyncMock()
    service = EventService(repo, organizer_repo)

    await service._refresh_setup_status(event)
    readiness = await service.get_readiness(owner_id, event_id)

    assert readiness["completed_sections"] == ["basic_info", "schedule", "tickets"]
    assert readiness["missing_sections"] == []
    assert readiness["blocking_issues"] == []


@pytest.mark.asyncio
async def test_progressive_basic_info_patch_can_update_only_title_then_only_timezone():
    owner_id = uuid4()
    event_id = uuid4()
    repo = AsyncMock()
    organizer_repo = AsyncMock()
    repo.session = AsyncMock()
    event = SimpleNamespace(
        id=event_id,
        title=None,
        description=None,
        event_type=None,
        event_access_type="ticketed",
        location_mode=None,
        timezone=None,
        setup_status={},
    )
    repo.get_by_id_for_owner.return_value = event
    repo.count_event_days.return_value = 0
    repo.count_ticket_types.return_value = 0
    repo.count_ticket_allocations.return_value = 0
    service = EventService(repo, organizer_repo)

    await service.update_basic_info(owner_id, event_id, title="Partial title")
    await service.update_basic_info(owner_id, event_id, timezone="Asia/Kolkata")

    assert event.title == "Partial title"
    assert event.timezone == "Asia/Kolkata"


@pytest.mark.asyncio
async def test_progressive_event_day_patch_can_update_only_start_time():
    owner_id = uuid4()
    day_id = uuid4()
    repo = AsyncMock()
    organizer_repo = AsyncMock()
    repo.session = AsyncMock()
    day = SimpleNamespace(
        id=day_id,
        event_id=uuid4(),
        day_index=1,
        date=datetime(2026, 4, 16).date(),
        start_time=None,
        end_time=datetime(2026, 4, 16, 20, 0, 0),
        scan_status="not_started",
        scan_started_at=None,
        scan_paused_at=None,
        scan_ended_at=None,
        next_ticket_index=1,
    )
    repo.get_event_day_for_owner.return_value = day
    service = EventService(repo, organizer_repo)

    await service.update_event_day(
        owner_id,
        day_id,
        start_time=datetime(2026, 4, 16, 18, 0, 0),
    )

    assert day.start_time == datetime(2026, 4, 16, 18, 0, 0)
    assert day.end_time == datetime(2026, 4, 16, 20, 0, 0)
