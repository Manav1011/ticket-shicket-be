from types import SimpleNamespace
from datetime import datetime
from uuid import uuid4
from unittest.mock import AsyncMock

import pytest

from apps.event.request import CreateDraftEventRequest, CreateEventDayRequest, UpdateEventBasicInfoRequest, UpdateEventDayRequest
from apps.event.response import EventInterestResponse
from apps.event.public_urls import mark_event_interest
from apps.event.urls import (
    create_draft_event,
    create_event_day,
    delete_event_day,
    end_scan,
    get_event_detail,
    get_event_readiness,
    list_event_days,
    pause_scan,
    resume_scan,
    start_scan,
    update_basic_info,
    update_event_day,
    create_reseller_invite,
)


@pytest.mark.asyncio
async def test_create_draft_event_returns_draft_summary():
    owner_id = uuid4()
    organizer_id = uuid4()
    request = SimpleNamespace(state=SimpleNamespace(user=SimpleNamespace(id=owner_id)))
    body = CreateDraftEventRequest(
        organizer_page_id=organizer_id,
        title="Test Event",
        event_access_type="ticketed",
    )
    service = AsyncMock()
    service.create_draft_event.return_value = SimpleNamespace(
        id=uuid4(),
        organizer_page_id=organizer_id,
        created_by_user_id=owner_id,
        title="Test Event",
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
        is_published=False,
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


@pytest.mark.asyncio
async def test_get_event_detail_returns_owner_scoped_event():
    owner_id = uuid4()
    event_id = uuid4()
    request = SimpleNamespace(state=SimpleNamespace(user=SimpleNamespace(id=owner_id)))
    service = AsyncMock()
    service.get_event_detail.return_value = SimpleNamespace(
        id=event_id,
        organizer_page_id=uuid4(),
        created_by_user_id=owner_id,
        title=None,
        slug=None,
        description=None,
        event_type=None,
        status="draft",
        event_access_type="ticketed",
        setup_status={"basic_info": False, "schedule": False, "tickets": False},
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
    )

    response = await get_event_detail(event_id=event_id, request=request, service=service)

    assert response.data.id == event_id


@pytest.mark.asyncio
async def test_update_basic_info_returns_recomputed_setup_status():
    owner_id = uuid4()
    event_id = uuid4()
    request = SimpleNamespace(state=SimpleNamespace(user=SimpleNamespace(id=owner_id)))
    body = UpdateEventBasicInfoRequest(
        title="Ahmedabad Startup Meetup",
        description="Founders and builders meetup",
        event_type="meetup",
        event_access_type="open",
        location_mode="venue",
        timezone="Asia/Kolkata",
    )
    service = AsyncMock()
    service.update_basic_info.return_value = SimpleNamespace(
        id=event_id,
        organizer_page_id=uuid4(),
        created_by_user_id=owner_id,
        title="Ahmedabad Startup Meetup",
        slug=None,
        description="Founders and builders meetup",
        event_type="meetup",
        status="draft",
        event_access_type="open",
        setup_status={"basic_info": True, "schedule": False, "tickets": True},
        location_mode="venue",
        timezone="Asia/Kolkata",
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
    )

    response = await update_basic_info(
        event_id=event_id, request=request, body=body, service=service
    )

    assert response.data.setup_status["basic_info"] is True


@pytest.mark.asyncio
async def test_update_basic_info_forwards_only_set_fields():
    owner_id = uuid4()
    event_id = uuid4()
    request = SimpleNamespace(state=SimpleNamespace(user=SimpleNamespace(id=owner_id)))
    body = UpdateEventBasicInfoRequest(title="Updated title")
    service = AsyncMock()
    service.update_basic_info.return_value = SimpleNamespace(
        id=event_id,
        organizer_page_id=uuid4(),
        created_by_user_id=owner_id,
        title="Updated title",
        slug=None,
        description="Existing description",
        event_type="meetup",
        status="draft",
        event_access_type="ticketed",
        setup_status={"basic_info": True, "schedule": False, "tickets": False},
        location_mode="venue",
        timezone="Asia/Kolkata",
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
    )

    response = await update_basic_info(
        event_id=event_id,
        request=request,
        body=body,
        service=service,
    )

    assert response.data.title == "Updated title"
    service.update_basic_info.assert_awaited_once_with(
        owner_id,
        event_id,
        title="Updated title",
    )


@pytest.mark.asyncio
async def test_get_event_readiness_returns_missing_sections():
    owner_id = uuid4()
    event_id = uuid4()
    request = SimpleNamespace(state=SimpleNamespace(user=SimpleNamespace(id=owner_id)))
    service = AsyncMock()
    service.get_readiness.return_value = {
        "completed_sections": ["basic_info"],
        "missing_sections": ["schedule", "tickets"],
        "blocking_issues": ["Add at least one event day"],
    }

    response = await get_event_readiness(
        event_id=event_id,
        request=request,
        service=service,
    )

    assert "schedule" in response.data.missing_sections


@pytest.mark.asyncio
async def test_create_event_day_returns_day_payload():
    owner_id = uuid4()
    event_id = uuid4()
    request = SimpleNamespace(state=SimpleNamespace(user=SimpleNamespace(id=owner_id)))
    body = CreateEventDayRequest(date="2026-04-15")
    service = AsyncMock()
    service.create_event_day.return_value = SimpleNamespace(
        id=uuid4(),
        event_id=event_id,
        day_index=1,
        date="2026-04-15",
        start_time=None,
        end_time=None,
        scan_status="not_started",
        scan_started_at=None,
        scan_paused_at=None,
        scan_ended_at=None,
        next_ticket_index=1,
    )

    response = await create_event_day(
        event_id=event_id, request=request, body=body, service=service
    )

    assert response.data.day_index == 1


@pytest.mark.asyncio
async def test_list_event_days_returns_event_day_list():
    owner_id = uuid4()
    event_id = uuid4()
    request = SimpleNamespace(state=SimpleNamespace(user=SimpleNamespace(id=owner_id)))
    service = AsyncMock()
    service.list_event_days.return_value = [
        SimpleNamespace(
            id=uuid4(),
            event_id=event_id,
            day_index=1,
            date="2026-04-15",
            start_time=None,
            end_time=None,
            scan_status="not_started",
            scan_started_at=None,
            scan_paused_at=None,
            scan_ended_at=None,
            next_ticket_index=1,
        )
    ]

    response = await list_event_days(event_id=event_id, request=request, service=service)

    assert len(response.data) == 1


@pytest.mark.asyncio
async def test_update_event_day_returns_latest_day_payload():
    owner_id = uuid4()
    event_day_id = uuid4()
    request = SimpleNamespace(state=SimpleNamespace(user=SimpleNamespace(id=owner_id)))
    service = AsyncMock()
    body = UpdateEventDayRequest(day_index=2, date="2026-04-16")
    service.update_event_day.return_value = SimpleNamespace(
        id=event_day_id,
        event_id=uuid4(),
        day_index=2,
        date="2026-04-16",
        start_time=None,
        end_time=None,
        scan_status="not_started",
        scan_started_at=None,
        scan_paused_at=None,
        scan_ended_at=None,
        next_ticket_index=1,
    )

    response = await update_event_day(
        event_day_id=event_day_id,
        request=request,
        body=body,
        service=service,
    )

    assert response.data.day_index == 2


@pytest.mark.asyncio
async def test_update_event_day_forwards_only_set_fields():
    owner_id = uuid4()
    event_day_id = uuid4()
    request = SimpleNamespace(state=SimpleNamespace(user=SimpleNamespace(id=owner_id)))
    body = UpdateEventDayRequest(start_time="2026-04-16T18:00:00")
    service = AsyncMock()
    service.update_event_day.return_value = SimpleNamespace(
        id=event_day_id,
        event_id=uuid4(),
        day_index=1,
        date="2026-04-16",
        start_time="2026-04-16T18:00:00",
        end_time="2026-04-16T20:00:00",
        scan_status="not_started",
        scan_started_at=None,
        scan_paused_at=None,
        scan_ended_at=None,
        next_ticket_index=1,
    )

    response = await update_event_day(
        event_day_id=event_day_id,
        request=request,
        body=body,
        service=service,
    )

    assert response.data.start_time == datetime(2026, 4, 16, 18, 0, 0)
    service.update_event_day.assert_awaited_once_with(
        owner_id,
        event_day_id,
        start_time=datetime(2026, 4, 16, 18, 0, 0),
    )


@pytest.mark.asyncio
async def test_delete_event_day_returns_deleted_true():
    owner_id = uuid4()
    event_day_id = uuid4()
    request = SimpleNamespace(state=SimpleNamespace(user=SimpleNamespace(id=owner_id)))
    service = AsyncMock()

    response = await delete_event_day(
        event_day_id=event_day_id,
        request=request,
        service=service,
    )

    assert response.data["deleted"] is True


@pytest.mark.asyncio
async def test_pause_resume_end_scan_routes_return_latest_day_state():
    owner_id = uuid4()
    event_day_id = uuid4()
    request = SimpleNamespace(state=SimpleNamespace(user=SimpleNamespace(id=owner_id)))
    service = AsyncMock()
    service.pause_scan.return_value = SimpleNamespace(
        id=event_day_id,
        event_id=uuid4(),
        day_index=1,
        date="2026-04-15",
        start_time=None,
        end_time=None,
        scan_status="paused",
        scan_started_at="2026-04-15T09:00:00",
        scan_paused_at="2026-04-15T09:30:00",
        scan_ended_at=None,
        next_ticket_index=1,
    )
    service.resume_scan.return_value = SimpleNamespace(
        id=event_day_id,
        event_id=uuid4(),
        day_index=1,
        date="2026-04-15",
        start_time=None,
        end_time=None,
        scan_status="active",
        scan_started_at="2026-04-15T09:00:00",
        scan_paused_at="2026-04-15T09:30:00",
        scan_ended_at=None,
        next_ticket_index=1,
    )
    service.end_scan.return_value = SimpleNamespace(
        id=event_day_id,
        event_id=uuid4(),
        day_index=1,
        date="2026-04-15",
        start_time=None,
        end_time=None,
        scan_status="ended",
        scan_started_at="2026-04-15T09:00:00",
        scan_paused_at="2026-04-15T09:30:00",
        scan_ended_at="2026-04-15T11:00:00",
        next_ticket_index=1,
    )

    paused = await pause_scan(event_day_id=event_day_id, request=request, service=service)
    resumed = await resume_scan(event_day_id=event_day_id, request=request, service=service)
    ended = await end_scan(event_day_id=event_day_id, request=request, service=service)

    assert paused.data.scan_status == "paused"
    assert resumed.data.scan_status == "active"
    assert ended.data.scan_status == "ended"


def test_event_interest_response_includes_created_and_counter():
    response = EventInterestResponse.model_validate({"created": True, "interested_counter": 7})
    assert response.created is True
    assert response.interested_counter == 7


def test_public_interest_router_uses_combined_actor_dependency():
    from apps.event.public_urls import router

    route = next(route for route in router.routes if getattr(route, "path", "") == "/api/open/events/{event_id}/interest")
    dependency_names = [getattr(dep.call, "__name__", "") for dep in route.dependant.dependencies]
    assert "get_current_user_or_guest" in dependency_names


@pytest.mark.asyncio
async def test_interest_event_endpoint_passes_actor_and_metadata_to_service():
    event_id = uuid4()
    actor = SimpleNamespace(kind="guest", id=uuid4())
    request = SimpleNamespace(
        state=SimpleNamespace(actor=actor),
        client=SimpleNamespace(host="203.0.113.10"),
        headers={"user-agent": "Mozilla/5.0"},
    )
    service = AsyncMock()
    service.interest_event.return_value = {"created": True, "interested_counter": 1}

    response = await mark_event_interest(event_id=event_id, request=request, service=service)

    service.interest_event.assert_awaited_once_with(
        actor_kind="guest",
        actor_id=actor.id,
        event_id=event_id,
        ip_address="203.0.113.10",
        user_agent="Mozilla/5.0",
    )
    assert response.data.created is True
    assert response.data.interested_counter == 1


@pytest.mark.asyncio
async def test_create_reseller_invite_accepts_user_ids():
    from apps.event.request import CreateResellerInviteRequest
    from apps.event.response import ResellerInviteResponse

    owner_id = uuid4()
    event_id = uuid4()
    target_user_id = uuid4()
    request = SimpleNamespace(state=SimpleNamespace(user=SimpleNamespace(id=owner_id)))
    body = CreateResellerInviteRequest(user_ids=[target_user_id])
    event_service = AsyncMock()
    invite_service = AsyncMock()
    mock_event = SimpleNamespace(id=event_id, organizer_page_id=uuid4())
    event_service.repository.get_by_id_for_owner = AsyncMock(return_value=mock_event)
    invite_service.user_repository.find_by_id = AsyncMock(return_value=SimpleNamespace(id=target_user_id))
    invite_service.repository.get_pending_invite_for_user_event = AsyncMock(return_value=None)
    invite_service.create_invite_batch = AsyncMock(return_value=[
        SimpleNamespace(
            id=uuid4(),
            target_user_id=target_user_id,
            created_by_id=owner_id,
            status="pending",
            invite_type="reseller",
            meta={"event_id": str(event_id), "permissions": []},
            created_at=datetime.utcnow(),
        )
    ])

    response = await create_reseller_invite(
        event_id=event_id,
        request=request,
        body=body,
        event_service=event_service,
        invite_service=invite_service,
    )

    assert response.data is not None
    assert len(response.data) == 1
    assert response.data[0].status == "pending"
    invite_service.create_invite_batch.assert_awaited_once()
