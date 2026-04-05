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
        title=None,
        slug=None,
        description=None,
        event_type=None,
        status="draft",
        event_access_type="ticketed",
        setup_status={},
        location_mode=None,
        timezone=None,
        start_date=None,
        end_date=None,
        venue_name=None,
        venue_address=None,
        venue_city=None,
        venue_state=None,
        venue_country=None,
        venue_latitude=None,
        venue_longitude=None,
        venue_google_place_id=None,
        online_event_url=None,
        recorded_event_url=None,
        published_at=None,
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
        start_time=None,
        end_time=None,
        scan_status="active",
        scan_started_at="2026-04-15T10:00:00",
        scan_paused_at=None,
        scan_ended_at=None,
        next_ticket_index=1,
    )

    response = await start_scan(event_day_id=event_day_id, request=request, service=service)

    assert response.data.scan_status == "active"
