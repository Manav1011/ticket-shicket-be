# tests/apps/organizer/test_organizer_events_list.py
from uuid import uuid4
from unittest.mock import AsyncMock
import unittest.mock
import pytest
from apps.organizer.service import OrganizerService


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
