# tests/apps/organizer/test_organizer_events_list.py
from uuid import uuid4
from unittest.mock import AsyncMock
import unittest.mock
import pytest
from apps.organizer.service import OrganizerService
from types import SimpleNamespace


@pytest.mark.asyncio
async def test_list_my_events_returns_pagination_meta():
    owner_id = uuid4()
    organizer_repo = AsyncMock()
    organizer_repo.session = AsyncMock()

    service = OrganizerService(organizer_repo)

    # Mock event_repo.list_events_for_user
    with unittest.mock.patch("apps.event.repository.EventRepository") as MockEventRepo:
        mock_instance = MockEventRepo.return_value
        mock_instance.list_events_for_user = AsyncMock(return_value=([], 0))

        events, meta = await service.list_my_events(owner_id, limit=20, offset=0)

        assert meta["total"] == 0
        assert meta["has_more"] is False
        mock_instance.list_events_for_user.assert_called_once()


@pytest.mark.asyncio
async def test_list_my_events_endpoint_returns_paginated_response():
    from apps.organizer.urls import list_my_events
    from datetime import datetime

    owner_id = uuid4()
    request = unittest.mock.MagicMock()
    request.state.user.id = owner_id
    
    service = AsyncMock()
    
    mock_event = SimpleNamespace(
        id=uuid4(),
        organizer_page_id=uuid4(),
        created_by_user_id=owner_id,
        title="Event 1",
        slug="event-1",
        description=None,
        event_type=None,
        status="draft",
        event_access_type="open",
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
        is_published=False,
        show_tickets=False,
        interested_counter=0,
        media_assets=[],
        created_at=datetime.utcnow()
    )

    service.list_my_events.return_value = ([mock_event], {"total": 1, "limit": 20, "offset": 0, "has_more": False})

    response = await list_my_events(
        request=request,
        service=service,
        limit=20,
        offset=0
    )

    assert len(response.data["events"]) == 1
    assert response.data["pagination"]["total"] == 1
    service.list_my_events.assert_awaited_once()
