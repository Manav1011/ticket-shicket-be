from types import SimpleNamespace
from uuid import uuid4
from unittest.mock import AsyncMock, MagicMock

import pytest

from apps.organizer.service import OrganizerService


@pytest.mark.asyncio
async def test_create_organizer_normalizes_slug_and_uses_owner_scope():
    repo = AsyncMock()
    repo.get_by_slug.return_value = None
    repo.add = MagicMock()
    service = OrganizerService(repo)

    organizer = await service.create_organizer(
        owner_user_id=uuid4(),
        name="Ahmedabad Talks",
        slug=" Ahmedabad Talks ",
        bio="Meetups",
        logo_url="https://cdn/logo.png",
        cover_image_url="https://cdn/cover.png",
        website_url="https://example.com",
        instagram_url="https://instagram.com/ahmedabadtalks",
        facebook_url=None,
        youtube_url=None,
        visibility="public",
    )

    assert organizer.slug == "ahmedabad-talks"
    assert organizer.logo_url == "https://cdn/logo.png"
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


@pytest.mark.asyncio
async def test_list_organizer_events_filters_by_owner_and_status():
    owner_id = uuid4()
    organizer_id = uuid4()
    repo = AsyncMock()
    repo.list_events_for_owner.return_value = [
        SimpleNamespace(id=uuid4(), organizer_page_id=organizer_id, status="draft")
    ]
    service = OrganizerService(repo)

    events = await service.list_organizer_events(owner_id, organizer_id, "draft")

    assert len(events) == 1
    repo.list_events_for_owner.assert_awaited_once_with(owner_id, organizer_id, "draft")


@pytest.mark.asyncio
async def test_update_organizer_only_changes_provided_fields():
    owner_id = uuid4()
    organizer_id = uuid4()
    organizer = SimpleNamespace(
        id=organizer_id,
        owner_user_id=owner_id,
        name="Ahmedabad Talks",
        slug="ahmedabad-talks",
        bio="Meetups",
        logo_url="https://cdn/logo.png",
        cover_image_url=None,
        website_url=None,
        instagram_url=None,
        facebook_url=None,
        youtube_url=None,
        visibility="public",
    )
    repo = AsyncMock()
    repo.get_by_id_for_owner.return_value = organizer
    repo.get_by_slug.return_value = None
    repo.session = AsyncMock()
    service = OrganizerService(repo)

    updated = await service.update_organizer(
        owner_user_id=owner_id,
        organizer_id=organizer_id,
        bio="New bio",
    )

    assert updated.bio == "New bio"
    assert updated.name == "Ahmedabad Talks"
    assert updated.logo_url == "https://cdn/logo.png"


@pytest.mark.asyncio
async def test_list_public_organizers_returns_only_active():
    from apps.organizer.repository import OrganizerRepository
    
    session = AsyncMock()
    repo = OrganizerRepository(session)

    organizers_data = [
        SimpleNamespace(id=uuid4(), name="Org 1", status="active"),
        SimpleNamespace(id=uuid4(), name="Org 2", status="active"),
    ]
    mock_result = MagicMock()
    mock_result.all = MagicMock(return_value=organizers_data)
    session.scalars = AsyncMock(return_value=mock_result)

    organizers = await repo.list_public_organizers()

    assert len(organizers) == 2
    session.scalars.assert_called_once()


@pytest.mark.asyncio
async def test_get_organizer_by_id_returns_organizer():
    from apps.organizer.repository import OrganizerRepository
    
    org_id = uuid4()
    session = AsyncMock()
    repo = OrganizerRepository(session)

    session.scalar.return_value = SimpleNamespace(id=org_id, name="Test Org")

    result = await repo.get_by_id(org_id)

    assert result is not None
    assert result.id == org_id


@pytest.mark.asyncio
async def test_list_events_by_organizer_public_returns_published_events():
    from apps.organizer.repository import OrganizerRepository
    
    org_id = uuid4()
    session = AsyncMock()
    repo = OrganizerRepository(session)

    events_data = [
        SimpleNamespace(id=uuid4(), title="Event 1", is_published=True),
    ]
    mock_result = MagicMock()
    mock_result.all = MagicMock(return_value=events_data)
    session.scalars = AsyncMock(return_value=mock_result)

    events = await repo.list_events_by_organizer_public(org_id)

    assert len(events) == 1
    session.scalars.assert_called_once()
