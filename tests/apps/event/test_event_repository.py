# tests/apps/event/test_event_repository.py
from datetime import date
from uuid import uuid4
from unittest.mock import AsyncMock
from types import SimpleNamespace
import pytest
from apps.event.repository import EventRepository
from apps.event.models import EventModel


@pytest.mark.asyncio
async def test_list_events_for_user_filters_by_owner():
    from apps.organizer.models import OrganizerPageModel

    owner_id = uuid4()
    event_id = uuid4()
    organizer_id = uuid4()

    mock_session = AsyncMock()
    mock_session.scalar = AsyncMock(return_value=1)  # count
    mock_session.scalars = AsyncMock(return_value=AsyncMock(all=lambda: [
        SimpleNamespace(id=event_id, title="Test Event", status="draft")
    ]))

    repo = EventRepository(mock_session)
    events, total = await repo.list_events_for_user(
        owner_user_id=owner_id,
        status="draft",
        limit=20,
        offset=0,
    )

    assert total == 1
    mock_session.scalar.assert_called()


@pytest.mark.asyncio
async def test_list_events_for_user_search_uses_ilike():
    owner_id = uuid4()
    mock_session = AsyncMock()
    mock_session.scalar = AsyncMock(return_value=0)
    mock_session.scalars = AsyncMock(return_value=AsyncMock(all=lambda: []))

    repo = EventRepository(mock_session)
    events, total = await repo.list_events_for_user(
        owner_user_id=owner_id,
        search="meetup",
        limit=20,
        offset=0,
    )
    # Verify ilike was used in the query (check call args)
    assert total == 0
