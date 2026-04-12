from types import SimpleNamespace
from uuid import uuid4
from unittest.mock import AsyncMock

import pytest

from apps.organizer.request import CreateOrganizerPageRequest, UpdateOrganizerPageRequest
from apps.organizer.urls import create_organizer, list_organizer_events, list_organizers, update_organizer


@pytest.mark.asyncio
async def test_create_organizer_uses_current_user():
    from datetime import datetime
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
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    body = CreateOrganizerPageRequest(
        name="Ahmedabad Talks",
        slug="Ahmedabad Talks",
        bio="Meetups",
        logo_url="https://cdn.example.com/logo.png",
        cover_image_url="https://cdn.example.com/cover.png",
        website_url="https://example.com",
        instagram_url="https://instagram.com/ahmedabadtalks",
        facebook_url=None,
        youtube_url=None,
        visibility="public",
    )

    response = await create_organizer(request=request, body=body, service=service)

    assert response.data.owner_user_id == owner_id
    service.create_organizer.assert_awaited_once()


@pytest.mark.asyncio
async def test_list_organizers_returns_owner_scoped_rows():
    owner_id = uuid4()
    request = SimpleNamespace(state=SimpleNamespace(user=SimpleNamespace(id=owner_id)))
    service = AsyncMock()
    from datetime import datetime
    service.list_organizers.return_value = [
        SimpleNamespace(
            id=uuid4(),
            owner_user_id=owner_id,
            name="Ahmedabad Talks",
            slug="ahmedabad-talks",
            bio="Meetups",
            logo_url=None,
            cover_image_url=None,
            website_url=None,
            instagram_url=None,
            facebook_url=None,
            youtube_url=None,
            visibility="public",
            status="active",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
    ]

    response = await list_organizers(request=request, service=service)

    assert len(response.data) == 1


@pytest.mark.asyncio
async def test_list_organizer_events_returns_draft_summaries():
    owner_id = uuid4()
    organizer_id = uuid4()
    request = SimpleNamespace(state=SimpleNamespace(user=SimpleNamespace(id=owner_id)))
    service = AsyncMock()
    service.list_organizer_events.return_value = [
        SimpleNamespace(
            id=uuid4(),
            organizer_page_id=organizer_id,
            title=None,
            status="draft",
            event_access_type="ticketed",
            setup_status={"basic_info": False, "schedule": False, "tickets": False},
            created_at="2026-04-05T10:00:00",
        )
    ]

    response = await list_organizer_events(
        organizer_id=organizer_id,
        status="draft",
        request=request,
        service=service,
    )

    assert response.data[0].status == "draft"


@pytest.mark.asyncio
async def test_update_organizer_forwards_only_set_fields():
    from datetime import datetime
    owner_id = uuid4()
    organizer_id = uuid4()
    request = SimpleNamespace(state=SimpleNamespace(user=SimpleNamespace(id=owner_id)))
    body = UpdateOrganizerPageRequest(bio="New bio")
    service = AsyncMock()
    service.update_organizer.return_value = SimpleNamespace(
        id=organizer_id,
        owner_user_id=owner_id,
        name="Ahmedabad Talks",
        slug="ahmedabad-talks",
        bio="New bio",
        logo_url=None,
        cover_image_url=None,
        website_url=None,
        instagram_url=None,
        facebook_url=None,
        youtube_url=None,
        visibility="public",
        status="active",
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )

    response = await update_organizer(
        organizer_id=organizer_id,
        request=request,
        body=body,
        service=service,
    )

    assert response.data.bio == "New bio"
    service.update_organizer.assert_awaited_once_with(
        owner_id,
        organizer_id,
        bio="New bio",
    )
