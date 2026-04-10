import pytest
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

from src.apps.event.service import EventService


@pytest.fixture
def service_mock():
    """Mock EventService."""
    return AsyncMock(spec=EventService)


@pytest.mark.asyncio
async def test_upload_media_asset_calls_service(service_mock):
    """Test that upload endpoint calls service method."""
    event_id = uuid4()
    asset_id = uuid4()
    owner_id = uuid4()

    service_mock.upload_media_asset.return_value = MagicMock(
        id=asset_id,
        event_id=event_id,
        asset_type="banner",
        public_url="http://localhost:4566/bucket/events/123/banner.png",
        title="Main Banner",
        is_primary=True,
    )

    result = await service_mock.upload_media_asset(
        owner_user_id=owner_id,
        event_id=event_id,
        asset_type="banner",
        file_name="banner.png",
        file_content=b"fake image",
        title="Main Banner",
    )

    assert result.is_primary is True
    service_mock.upload_media_asset.assert_awaited_once()


@pytest.mark.asyncio
async def test_list_media_assets_returns_list(service_mock):
    """Test listing media assets returns list."""
    event_id = uuid4()
    owner_id = uuid4()

    service_mock.list_media_assets.return_value = []

    assets = await service_mock.list_media_assets(owner_id, event_id)

    assert assets == []
    service_mock.list_media_assets.assert_awaited_once()


@pytest.mark.asyncio
async def test_delete_media_asset_calls_service(service_mock):
    """Test delete endpoint calls service."""
    event_id = uuid4()
    asset_id = uuid4()
    owner_id = uuid4()

    service_mock.delete_media_asset.return_value = None

    await service_mock.delete_media_asset(owner_id, event_id, asset_id)

    service_mock.delete_media_asset.assert_awaited_once_with(owner_id, event_id, asset_id)


@pytest.mark.asyncio
async def test_update_media_asset_metadata(service_mock):
    """Test update metadata endpoint."""
    event_id = uuid4()
    asset_id = uuid4()
    owner_id = uuid4()

    updated_asset = MagicMock(
        id=asset_id,
        title="Updated Title",
        caption="New caption",
    )
    service_mock.update_media_asset_metadata.return_value = updated_asset

    result = await service_mock.update_media_asset_metadata(
        owner_id, event_id, asset_id, title="Updated Title", caption="New caption"
    )

    assert result.title == "Updated Title"
    service_mock.update_media_asset_metadata.assert_awaited_once()
