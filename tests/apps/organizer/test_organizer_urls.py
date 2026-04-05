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
