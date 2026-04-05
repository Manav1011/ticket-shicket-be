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
