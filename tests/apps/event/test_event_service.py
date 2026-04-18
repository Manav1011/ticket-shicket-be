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

    event = await service.create_draft_event(owner_id, organizer_id, "Test Event", "ticketed")

    assert event.organizer_page_id == organizer_id
    assert event.status == "draft"
    assert event.event_access_type == "ticketed"
    assert event.setup_status == {}
    assert event.title == "Test Event"
    assert event.slug is None
    assert event.start_date is None
    assert event.end_date is None


@pytest.mark.asyncio
async def test_create_event_day_and_start_scan_from_same_service():
    owner_id = uuid4()
    event_id = uuid4()
    event = SimpleNamespace(id=event_id, organizer_page_id=uuid4(), days_count=0)
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
    event_repo.count_event_days.return_value = 1
    event_repo.count_ticket_types.return_value = 0
    event_repo.count_ticket_allocations.return_value = 0
    event_repo.session = AsyncMock()
    service = EventService(event_repo, organizer_repo)

    created_day = await service.create_event_day(
        owner_id, event_id, datetime(2026, 4, 15).date()
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


@pytest.mark.asyncio
async def test_update_basic_info_marks_basic_info_complete():
    owner_id = uuid4()
    event_id = uuid4()
    organizer_repo = AsyncMock()
    event_repo = AsyncMock()
    event_repo.session = AsyncMock()
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
    event_repo.get_by_id_for_owner.return_value = event
    event_repo.count_event_days.return_value = 0
    event_repo.count_ticket_types.return_value = 0
    event_repo.count_ticket_allocations.return_value = 0
    service = EventService(event_repo, organizer_repo)

    updated = await service.update_basic_info(
        owner_id,
        event_id,
        title="Ahmedabad Startup Meetup",
        description="Founders and builders meetup",
        event_type="meetup",
        event_access_type="open",
        location_mode="venue",
        timezone="Asia/Kolkata",
    )

    assert updated.setup_status["basic_info"] is True
    assert updated.setup_status["tickets"] is True


@pytest.mark.asyncio
async def test_update_basic_info_preserves_omitted_fields():
    owner_id = uuid4()
    event_id = uuid4()
    organizer_repo = AsyncMock()
    event_repo = AsyncMock()
    event_repo.session = AsyncMock()
    event = SimpleNamespace(
        id=event_id,
        title="Existing title",
        description="Existing description",
        event_type="meetup",
        event_access_type="ticketed",
        location_mode="venue",
        timezone="Asia/Kolkata",
        setup_status={},
    )
    event_repo.get_by_id_for_owner.return_value = event
    event_repo.count_event_days.return_value = 0
    event_repo.count_ticket_types.return_value = 0
    event_repo.count_ticket_allocations.return_value = 0
    service = EventService(event_repo, organizer_repo)

    updated = await service.update_basic_info(owner_id, event_id, title="Updated title")

    assert updated.title == "Updated title"
    assert updated.description == "Existing description"
    assert updated.event_access_type == "ticketed"
    assert updated.location_mode == "venue"


@pytest.mark.asyncio
async def test_get_readiness_reports_missing_sections_from_setup_status():
    owner_id = uuid4()
    event_id = uuid4()
    organizer_repo = AsyncMock()
    event_repo = AsyncMock()
    event_repo.session = AsyncMock()
    event_repo.get_by_id_for_owner.return_value = SimpleNamespace(
        id=event_id,
        setup_status={"basic_info": True, "schedule": False, "tickets": False, "assets": False},
    )
    service = EventService(event_repo, organizer_repo)

    readiness = await service.get_readiness(owner_id, event_id)

    assert readiness["completed_sections"] == ["basic_info"]
    assert "schedule" in readiness["missing_sections"]
    assert "Add at least one event day" in readiness["blocking_issues"]


@pytest.mark.asyncio
async def test_create_event_day_marks_schedule_complete():
    owner_id = uuid4()
    event_id = uuid4()
    event = SimpleNamespace(
        id=event_id,
        title="Ahmedabad Startup Meetup",
        event_access_type="open",
        location_mode="venue",
        timezone="Asia/Kolkata",
        setup_status={},
        days_count=0,
    )
    day = SimpleNamespace(
        id=uuid4(),
        event_id=event_id,
        day_index=1,
        date=datetime(2026, 4, 15).date(),
        start_time=None,
        end_time=None,
        scan_status="not_started",
        scan_started_at=None,
        scan_paused_at=None,
        scan_ended_at=None,
        next_ticket_index=1,
    )
    organizer_repo = AsyncMock()
    event_repo = AsyncMock()
    event_repo.get_by_id_for_owner.return_value = event
    event_repo.create_event_day.return_value = day
    event_repo.count_event_days.return_value = 1
    event_repo.count_ticket_types.return_value = 0
    event_repo.count_ticket_allocations.return_value = 0
    event_repo.session = AsyncMock()
    service = EventService(event_repo, organizer_repo)

    await service.create_event_day(owner_id, event_id, datetime(2026, 4, 15).date())

    assert event.setup_status["schedule"] is True


@pytest.mark.asyncio
async def test_pause_resume_end_scan_enforces_valid_transitions():
    owner_id = uuid4()
    organizer_repo = AsyncMock()
    event_repo = AsyncMock()
    event_repo.session = AsyncMock()
    day = SimpleNamespace(
        id=uuid4(),
        event_id=uuid4(),
        scan_status="active",
        scan_started_at=None,
        scan_paused_at=None,
        scan_ended_at=None,
        next_ticket_index=1,
    )
    event_repo.get_event_day_for_owner.return_value = day
    service = EventService(event_repo, organizer_repo)

    paused = await service.pause_scan(owner_id, day.id)
    assert paused.scan_status == "paused"

    resumed = await service.resume_scan(owner_id, day.id)
    assert resumed.scan_status == "active"

    ended = await service.end_scan(owner_id, day.id)
    assert ended.scan_status == "ended"


@pytest.mark.asyncio
async def test_update_event_day_preserves_omitted_fields():
    owner_id = uuid4()
    day_id = uuid4()
    organizer_repo = AsyncMock()
    event_repo = AsyncMock()
    event_repo.session = AsyncMock()
    day = SimpleNamespace(
        id=day_id,
        event_id=uuid4(),
        day_index=1,
        date=datetime(2026, 4, 15).date(),
        start_time=datetime(2026, 4, 15, 10, 0, 0),
        end_time=datetime(2026, 4, 15, 12, 0, 0),
        scan_status="not_started",
        scan_started_at=None,
        scan_paused_at=None,
        scan_ended_at=None,
        next_ticket_index=1,
    )
    event_repo.get_event_day_for_owner.return_value = day
    service = EventService(event_repo, organizer_repo)

    updated = await service.update_event_day(
        owner_id,
        day_id,
        start_time=datetime(2026, 4, 15, 11, 0, 0),
    )

    assert updated.start_time == datetime(2026, 4, 15, 11, 0, 0)
    assert updated.end_time == datetime(2026, 4, 15, 12, 0, 0)
    assert updated.day_index == 1


@pytest.mark.asyncio
async def test_validate_for_publish_open_venue_complete():
    """Open event with venue and all basic info complete should be ready."""
    owner_id = uuid4()
    event_id = uuid4()
    event = SimpleNamespace(
        id=event_id,
        title="Open Workshop",
        event_access_type="open",
        location_mode="venue",
        timezone="Asia/Kolkata",
        venue_name="Community Hall",
        venue_address="123 Main St",
        venue_city="Pune",
        venue_country="India",
        online_event_url=None,
        recorded_event_url=None,
    )
    day = SimpleNamespace(
        id=uuid4(),
        event_id=event_id,
        day_index=1,
        date=datetime(2026, 4, 15).date(),
        start_time=None,
        end_time=None,
    )
    organizer_repo = AsyncMock()
    event_repo = AsyncMock()
    event_repo.get_by_id_for_owner.return_value = event
    event_repo.list_event_days.return_value = [day]
    event_repo.list_ticket_types.return_value = []
    event_repo.list_allocations.return_value = []
    event_repo.list_media_assets = AsyncMock(return_value=[SimpleNamespace(id=uuid4(), asset_type="banner", storage_key="test.jpg", public_url="https://test.com/test.jpg")])
    service = EventService(event_repo, organizer_repo)

    validation = await service.validate_for_publish(owner_id, event_id)

    assert validation["can_publish"] is True
    assert validation["sections"]["basic_info"]["complete"] is True
    assert validation["sections"]["schedule"]["complete"] is True
    assert validation["sections"]["tickets"]["complete"] is True


@pytest.mark.asyncio
async def test_validate_for_publish_ticketed_missing_tickets():
    """Ticketed event without tickets can publish but section marked incomplete."""
    owner_id = uuid4()
    event_id = uuid4()
    event = SimpleNamespace(
        id=event_id,
        title="Ticketed Workshop",
        event_access_type="ticketed",
        location_mode="venue",
        timezone="Asia/Kolkata",
        venue_name="Community Hall",
        venue_address="123 Main St",
        venue_city="Pune",
        venue_country="India",
        online_event_url=None,
        recorded_event_url=None,
    )
    day = SimpleNamespace(
        id=uuid4(),
        event_id=event_id,
        day_index=1,
        date=datetime(2026, 4, 15).date(),
        start_time=datetime(2026, 4, 15, 10, 0, 0),
        end_time=None,
    )
    organizer_repo = AsyncMock()
    event_repo = AsyncMock()
    event_repo.get_by_id_for_owner.return_value = event
    event_repo.list_event_days.return_value = [day]
    event_repo.list_ticket_types.return_value = []
    event_repo.list_allocations.return_value = []
    event_repo.list_media_assets = AsyncMock(return_value=[SimpleNamespace(id=uuid4(), asset_type="banner", storage_key="test.jpg", public_url="https://test.com/test.jpg")])
    service = EventService(event_repo, organizer_repo)

    validation = await service.validate_for_publish(owner_id, event_id)

    # Ticketed events without tickets can publish
    # but the tickets section is still marked incomplete for the organizer dashboard
    assert validation["can_publish"] is True
    assert validation["sections"]["tickets"]["complete"] is False
    assert len(validation["sections"]["tickets"]["errors"]) == 0


@pytest.mark.asyncio
async def test_validate_for_publish_ticketed_without_tickets_allows_publish():
    """Ticketed event without tickets should NOT fail validation."""
    owner_id = uuid4()
    event_id = uuid4()
    event = SimpleNamespace(
        id=event_id,
        title="Ticketed Workshop",
        event_access_type="ticketed",
        location_mode="venue",
        timezone="Asia/Kolkata",
        venue_name="Community Hall",
        venue_address="123 Main St",
        venue_city="Pune",
        venue_country="India",
        online_event_url=None,
        recorded_event_url=None,
    )
    day = SimpleNamespace(
        id=uuid4(),
        event_id=event_id,
        day_index=1,
        date=datetime(2026, 4, 15).date(),
        start_time=datetime(2026, 4, 15, 10, 0, 0),
        end_time=None,
    )
    organizer_repo = AsyncMock()
    event_repo = AsyncMock()
    event_repo.get_by_id_for_owner.return_value = event
    event_repo.list_event_days.return_value = [day]
    event_repo.list_ticket_types.return_value = []
    event_repo.list_allocations.return_value = []
    event_repo.list_media_assets.return_value = [SimpleNamespace(id=uuid4(), asset_type="banner")]
    service = EventService(event_repo, organizer_repo)

    validation = await service.validate_for_publish(owner_id, event_id)

    # tickets section: can_publish=True (tickets don't block publish), but section marked incomplete
    assert validation["sections"]["tickets"]["complete"] is False
    assert validation["can_publish"] is True
    assert len(validation["sections"]["tickets"]["errors"]) == 0  # no errors returned


@pytest.mark.asyncio
async def test_validate_for_publish_ticketed_no_start_time():
    """Ticketed event day without start_time should fail schedule validation."""
    owner_id = uuid4()
    event_id = uuid4()
    event = SimpleNamespace(
        id=event_id,
        title="Ticketed Workshop",
        event_access_type="ticketed",
        location_mode="venue",
        timezone="Asia/Kolkata",
        venue_name="Community Hall",
        venue_address="123 Main St",
        venue_city="Pune",
        venue_country="India",
        online_event_url=None,
        recorded_event_url=None,
    )
    day = SimpleNamespace(
        id=uuid4(),
        event_id=event_id,
        day_index=1,
        date=datetime(2026, 4, 15).date(),
        start_time=None,
        end_time=None,
    )
    organizer_repo = AsyncMock()
    event_repo = AsyncMock()
    event_repo.get_by_id_for_owner.return_value = event
    event_repo.list_event_days.return_value = [day]
    event_repo.list_ticket_types.return_value = [SimpleNamespace(id=uuid4(), name="General")]
    event_repo.list_allocations.return_value = [SimpleNamespace(id=uuid4(), quantity=50)]
    service = EventService(event_repo, organizer_repo)

    validation = await service.validate_for_publish(owner_id, event_id)

    assert validation["can_publish"] is False
    assert validation["sections"]["schedule"]["complete"] is False
    assert any("start_time" in e.field for e in validation["sections"]["schedule"]["errors"])


@pytest.mark.asyncio
async def test_publish_event_sets_published_fields():
    """Publishing event should set status, is_published, and published_at."""
    owner_id = uuid4()
    event_id = uuid4()
    event = SimpleNamespace(
        id=event_id,
        title="Complete Event",
        event_access_type="open",
        location_mode="venue",
        timezone="Asia/Kolkata",
        venue_name="Community Hall",
        venue_address="123 Main St",
        venue_city="Pune",
        venue_country="India",
        online_event_url=None,
        recorded_event_url=None,
        status="draft",
        is_published=False,
        published_at=None,
    )
    day = SimpleNamespace(
        id=uuid4(),
        event_id=event_id,
        day_index=1,
        date=datetime(2026, 4, 15).date(),
        start_time=None,
        end_time=None,
    )
    organizer_repo = AsyncMock()
    event_repo = AsyncMock()
    event_repo.get_by_id_for_owner.return_value = event
    event_repo.list_event_days.return_value = [day]
    event_repo.list_ticket_types.return_value = []
    event_repo.list_allocations.return_value = []
    event_repo.list_media_assets = AsyncMock(return_value=[SimpleNamespace(id=uuid4(), asset_type="banner", storage_key="test.jpg", public_url="https://test.com/test.jpg")])
    event_repo.session = AsyncMock()
    event_repo.session.flush = AsyncMock()
    event_repo.session.refresh = AsyncMock()
    service = EventService(event_repo, organizer_repo)

    published_event = await service.publish_event(owner_id, event_id)

    assert event.status == "published"
    assert event.is_published is True
    assert event.published_at is not None


@pytest.mark.asyncio
async def test_setup_status_tickets_false_when_show_tickets_disabled():
    """Even with ticket types and allocations, tickets section is incomplete if show_tickets=False."""
    owner_id = uuid4()
    event_id = uuid4()
    event = SimpleNamespace(id=event_id, title="Ticketed Workshop", event_access_type="ticketed", location_mode="venue", timezone="Asia/Kolkata", setup_status={}, show_tickets=False)
    day = SimpleNamespace(id=uuid4(), event_id=event_id, day_index=1, date=datetime(2026, 4, 15).date(), start_time=datetime(2026, 4, 15, 10, 0, 0), end_time=None)
    organizer_repo = AsyncMock()
    event_repo = AsyncMock()
    event_repo.get_by_id_for_owner.return_value = event
    event_repo.list_event_days.return_value = [day]
    event_repo.list_ticket_types.return_value = [SimpleNamespace(id=uuid4(), name="General")]
    event_repo.list_allocations.return_value = [SimpleNamespace(id=uuid4(), quantity=50)]
    event_repo.count_event_days.return_value = 1
    event_repo.count_ticket_types.return_value = 1
    event_repo.count_ticket_allocations.return_value = 1
    event_repo.session = AsyncMock()
    event_repo.list_media_assets = AsyncMock(return_value=[SimpleNamespace(id=uuid4(), asset_type="banner")])
    service = EventService(event_repo, organizer_repo)
    # show_tickets=False, so tickets should be incomplete even with real tickets
    setup_status = await service._build_setup_status(event, 1, 1, 1)
    assert setup_status["tickets"] is False


@pytest.mark.asyncio
async def test_ticketed_event_can_be_published_without_tickets_and_then_tickets_added():
    """Ticketed event can publish without tickets; tickets section incomplete until show_tickets enabled."""
    owner_id = uuid4()
    event_id = uuid4()
    event = SimpleNamespace(id=event_id, title="Ticketed Workshop", event_access_type="ticketed", location_mode="venue", timezone="Asia/Kolkata", venue_name="Community Hall", venue_address="123 Main St", venue_city="Pune", venue_country="India", online_event_url=None, recorded_event_url=None, status="draft", is_published=False, published_at=None, show_tickets=False)
    day = SimpleNamespace(id=uuid4(), event_id=event_id, day_index=1, date=datetime(2026, 4, 15).date(), start_time=datetime(2026, 4, 15, 10, 0, 0), end_time=None)
    organizer_repo = AsyncMock()
    event_repo = AsyncMock()
    event_repo.get_by_id_for_owner.return_value = event
    event_repo.list_event_days.return_value = [day]
    event_repo.list_ticket_types.return_value = []
    event_repo.list_allocations.return_value = []
    event_repo.session = AsyncMock()
    event_repo.session.flush = AsyncMock()
    event_repo.session.refresh = AsyncMock()
    event_repo.list_media_assets = AsyncMock(return_value=[SimpleNamespace(id=uuid4(), asset_type="banner", storage_key="test.jpg", public_url="https://test.com/test.jpg")])
    service = EventService(event_repo, organizer_repo)
    validation = await service.validate_for_publish(owner_id, event_id)
    assert validation["can_publish"] is True
    assert validation["sections"]["tickets"]["complete"] is False
    # Now add tickets
    event.show_tickets = True
    event_repo.list_ticket_types.return_value = [SimpleNamespace(id=uuid4(), name="General")]
    event_repo.list_allocations.return_value = [SimpleNamespace(id=uuid4(), quantity=50)]
    validation2 = await service.validate_for_publish(owner_id, event_id)
    assert validation2["can_publish"] is True
    assert validation2["sections"]["tickets"]["complete"] is True


class _AsyncNullContext:
    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False


@pytest.mark.asyncio
async def test_interest_event_creates_row_and_increments_counter_for_user():
    event_id = uuid4()
    event = SimpleNamespace(id=event_id, interested_counter=3)
    event_repo = AsyncMock()
    event_repo.get_by_id_for_update.return_value = event
    event_repo.get_interest_for_actor.return_value = None
    event_repo.get_by_id.return_value = event
    event_repo.create_event_interest.return_value = SimpleNamespace(id=uuid4())
    event_repo.increment_event_interest_counter = AsyncMock()
    event_repo.session = SimpleNamespace(begin_nested=lambda: _AsyncNullContext())
    service = EventService(event_repo, AsyncMock())

    result = await service.interest_event(
        actor_kind="user",
        actor_id=uuid4(),
        event_id=event_id,
        ip_address="203.0.113.10",
        user_agent="Mozilla/5.0",
    )

    assert result["created"] is True
    assert result["interested_counter"] == 3
    event_repo.create_event_interest.assert_awaited_once()
    event_repo.increment_event_interest_counter.assert_awaited_once_with(event_id)


@pytest.mark.asyncio
async def test_interest_event_is_idempotent_for_same_guest_event_pair():
    event_id = uuid4()
    event = SimpleNamespace(id=event_id, interested_counter=3)
    event_repo = AsyncMock()
    event_repo.get_by_id_for_update.return_value = event
    event_repo.get_interest_for_actor.return_value = SimpleNamespace(id=uuid4())
    event_repo.get_by_id.return_value = event
    event_repo.session = SimpleNamespace(begin_nested=lambda: _AsyncNullContext())
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


@pytest.mark.asyncio
async def test_list_published_events_returns_only_published():
    from apps.event.repository import EventRepository
    
    session = AsyncMock()
    repo = EventRepository(session)

    events_data = [
        SimpleNamespace(id=uuid4(), title="Published Event 1", is_published=True),
        SimpleNamespace(id=uuid4(), title="Published Event 2", is_published=True),
    ]
    mock_result = MagicMock()
    mock_result.all = MagicMock(return_value=events_data)
    session.scalars = AsyncMock(return_value=mock_result)

    events = await repo.list_published_events()

    assert len(events) == 2
    session.scalars.assert_called_once()


@pytest.mark.asyncio
async def test_list_public_events_returns_only_published():
    from apps.event.public_service import PublicEventService
    
    event_repo = AsyncMock()
    event_repo.list_published_events.return_value = [
        SimpleNamespace(id=uuid4(), title="Event 1", is_published=True),
        SimpleNamespace(id=uuid4(), title="Event 2", is_published=True),
    ]
    ticketing_repo = AsyncMock()
    service = PublicEventService(event_repo, ticketing_repo)

    result = await service.list_public_events()

    assert len(result) == 2
    event_repo.list_published_events.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_public_event_returns_event_with_embedded_data():
    from apps.event.public_service import PublicEventService
    from datetime import date
    
    event_id = uuid4()
    event_repo = AsyncMock()
    event_repo.get_by_id.return_value = SimpleNamespace(
        id=event_id,
        title="Test Event",
        slug="test-event",
        is_published=True,
        interested_counter=5,
        organizer_page_id=uuid4(),
        status="published",
        event_access_type="ticketed",
    )
    event_repo.list_event_days.return_value = [SimpleNamespace(
        id=uuid4(),
        day_index=0,
        date=date(2026, 4, 15),
        start_time=None,
        end_time=None,
        scan_status="not_started",
    )]
    event_repo.list_media_assets.return_value = []
    ticketing_repo = AsyncMock()
    ticketing_repo.list_ticket_types_for_event.return_value = []
    ticketing_repo.list_allocations_for_event.return_value = []
    service = PublicEventService(event_repo, ticketing_repo)

    result = await service.get_public_event(event_id)

    assert result["id"] == event_id
    assert result["interested_counter"] == 5
    assert "days" in result
    assert "ticket_types" in result
    assert "media_assets" in result
    assert "ticket_allocations" in result
