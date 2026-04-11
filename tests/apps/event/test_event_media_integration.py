"""
Integration tests for Event Media Asset workflow.

Tests the complete lifecycle of media assets:
- Upload (banner, gallery_image, gallery_video)
- List with filtering
- Update metadata
- Delete

Also tests validation errors and publish validation.

Run with: pytest tests/apps/event/test_event_media_integration.py -v
"""
import pytest
from datetime import datetime, date
from uuid import uuid4
from unittest.mock import AsyncMock, MagicMock, patch
from types import SimpleNamespace

from apps.event.service import EventService
from apps.event.models import EventMediaAssetModel, EventModel, EventDayModel
from apps.event.enums import AssetType, EventAccessType, LocationMode, ScanStatus
from src.utils.file_validation import FileValidationError


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def mock_s3_client():
    """Mock S3 client that tracks upload/delete calls."""
    mock = MagicMock()
    mock.upload_file.return_value = "events/test-event-id/banner_abc12345_test.png"
    mock.delete_file.return_value = True
    mock.generate_public_url.return_value = "http://localhost:4566/test-bucket/events/test-event-id/banner_abc12345_test.png"
    return mock


@pytest.fixture
def event_repo():
    """Mock EventRepository."""
    repo = AsyncMock()
    repo.add = MagicMock()
    repo.session = AsyncMock()
    repo.session.flush = AsyncMock()
    repo.session.refresh = AsyncMock()
    return repo


@pytest.fixture
def organizer_repo():
    """Mock OrganizerRepository."""
    return AsyncMock()


# =============================================================================
# Workflow Tests - Upload Media Assets
# =============================================================================

@pytest.mark.asyncio
async def test_upload_banner_asset_persists_to_database(event_repo, organizer_repo, mock_s3_client):
    """Test that uploading a banner creates a DB record with correct storage_key format."""
    from PIL import Image
    from io import BytesIO

    event_id = uuid4()
    owner_id = uuid4()

    event = SimpleNamespace(
        id=event_id,
        title="Test Event",
        organizer_page_id=uuid4(),
        event_access_type=EventAccessType.ticketed,
        setup_status={},
    )

    event_repo.get_by_id_for_owner = AsyncMock(return_value=event)
    event_repo.list_media_assets = AsyncMock(return_value=[])
    event_repo.count_event_days = AsyncMock(return_value=0)
    event_repo.count_ticket_types = AsyncMock(return_value=0)
    event_repo.count_ticket_allocations = AsyncMock(return_value=0)

    # Create a valid 200x200 PNG image for testing
    img = Image.new("RGB", (200, 200), color="green")
    buf = BytesIO()
    img.save(buf, format="PNG")
    valid_image_bytes = buf.getvalue()

    service = EventService(event_repo, organizer_repo)

    with patch("apps.event.service.get_s3_client", return_value=mock_s3_client):
        asset = await service.upload_media_asset(
            owner_user_id=owner_id,
            event_id=event_id,
            asset_type="banner",
            file_name="banner.png",
            file_content=valid_image_bytes,
            title="Main Banner",
        )

    # Verify asset was added to session
    event_repo.add.assert_called_once()
    added_asset = event_repo.add.call_args[0][0]
    assert added_asset.event_id == event_id
    assert added_asset.asset_type == "banner"
    assert "banner_" in added_asset.storage_key
    assert added_asset.title == "Main Banner"
    assert added_asset.public_url.startswith("http://localhost:4566")


@pytest.mark.asyncio
async def test_upload_gallery_image_persists_to_database(event_repo, organizer_repo, mock_s3_client):
    """Test that uploading a gallery image creates DB record."""
    event_id = uuid4()
    owner_id = uuid4()

    event = SimpleNamespace(
        id=event_id,
        title="Test Event",
        organizer_page_id=uuid4(),
        event_access_type=EventAccessType.ticketed,
        setup_status={},
    )

    event_repo.get_by_id_for_owner = AsyncMock(return_value=event)
    event_repo.list_media_assets = AsyncMock(return_value=[])
    event_repo.count_event_days = AsyncMock(return_value=0)
    event_repo.count_ticket_types = AsyncMock(return_value=0)
    event_repo.count_ticket_allocations = AsyncMock(return_value=0)

    service = EventService(event_repo, organizer_repo)

    mock_s3_client.upload_file.return_value = "events/test-id/gallery_image_abc12345_gallery.png"
    mock_s3_client.generate_public_url.return_value = "http://localhost:4566/bucket/events/test-id/gallery_image_abc12345_gallery.png"

    with patch("apps.event.service.get_s3_client", return_value=mock_s3_client):
        asset = await service.upload_media_asset(
            owner_user_id=owner_id,
            event_id=event_id,
            asset_type="gallery_image",
            file_name="gallery.png",
            file_content=b"fake_gallery_data",
            caption="Event gallery photo",
        )

    event_repo.add.assert_called_once()
    added_asset = event_repo.add.call_args[0][0]
    assert added_asset.asset_type == "gallery_image"
    assert added_asset.caption == "Event gallery photo"


@pytest.mark.asyncio
async def test_upload_gallery_video_persists_to_database(event_repo, organizer_repo, mock_s3_client):
    """Test that uploading a gallery video creates DB record."""
    event_id = uuid4()
    owner_id = uuid4()

    event = SimpleNamespace(
        id=event_id,
        title="Test Event",
        organizer_page_id=uuid4(),
        event_access_type=EventAccessType.ticketed,
        setup_status={},
    )

    event_repo.get_by_id_for_owner = AsyncMock(return_value=event)
    event_repo.list_media_assets = AsyncMock(return_value=[])
    event_repo.count_event_days = AsyncMock(return_value=0)
    event_repo.count_ticket_types = AsyncMock(return_value=0)
    event_repo.count_ticket_allocations = AsyncMock(return_value=0)

    service = EventService(event_repo, organizer_repo)

    mock_s3_client.upload_file.return_value = "events/test-id/gallery_video_abc12345_promo.mp4"
    mock_s3_client.generate_public_url.return_value = "http://localhost:4566/bucket/events/test-id/gallery_video_abc12345_promo.mp4"

    with patch("apps.event.service.get_s3_client", return_value=mock_s3_client):
        asset = await service.upload_media_asset(
            owner_user_id=owner_id,
            event_id=event_id,
            asset_type="gallery_video",
            file_name="promo.mp4",
            file_content=b"fake_video_data" * 1000,  # >5MB to pass minimum video size
        )

    event_repo.add.assert_called_once()
    added_asset = event_repo.add.call_args[0][0]
    assert added_asset.asset_type == "gallery_video"


# =============================================================================
# Workflow Tests - List Media Assets
# =============================================================================

@pytest.mark.asyncio
async def test_list_media_assets_returns_all_assets(event_repo, organizer_repo):
    """Test that listing media assets returns all assets for an event."""
    event_id = uuid4()
    owner_id = uuid4()

    event = SimpleNamespace(id=event_id, title="Test Event")

    mock_assets = [
        SimpleNamespace(id=uuid4(), asset_type="banner", title="Banner 1"),
        SimpleNamespace(id=uuid4(), asset_type="gallery_image", title="Gallery 1"),
    ]

    event_repo.get_by_id_for_owner = AsyncMock(return_value=event)
    event_repo.list_media_assets = AsyncMock(return_value=mock_assets)

    service = EventService(event_repo, organizer_repo)

    assets = await service.list_media_assets(owner_id, event_id)

    assert len(assets) == 2
    event_repo.list_media_assets.assert_called_with(event_id, None)


@pytest.mark.asyncio
async def test_list_media_assets_filters_by_type(event_repo, organizer_repo):
    """Test that listing media assets with asset_type filter works."""
    event_id = uuid4()
    owner_id = uuid4()

    event = SimpleNamespace(id=event_id, title="Test Event")

    mock_banners = [
        SimpleNamespace(id=uuid4(), asset_type="banner", title="Banner 1"),
        SimpleNamespace(id=uuid4(), asset_type="banner", title="Banner 2"),
    ]

    event_repo.get_by_id_for_owner = AsyncMock(return_value=event)
    event_repo.list_media_assets = AsyncMock(return_value=mock_banners)

    service = EventService(event_repo, organizer_repo)

    assets = await service.list_media_assets(owner_id, event_id, asset_type="banner")

    assert len(assets) == 2
    event_repo.list_media_assets.assert_called_with(event_id, "banner")


# =============================================================================
# Workflow Tests - Update Media Asset Metadata
# =============================================================================

@pytest.mark.asyncio
async def test_update_media_asset_metadata_updates_fields(event_repo, organizer_repo):
    """Test that updating metadata modifies the correct fields."""
    event_id = uuid4()
    owner_id = uuid4()
    asset_id = uuid4()

    event = SimpleNamespace(id=event_id, title="Test Event")
    asset = SimpleNamespace(
        id=asset_id,
        event_id=event_id,
        asset_type="banner",
        title="Old Title",
        caption=None,
        alt_text=None,
        sort_order=0,
        is_primary=False,
    )

    event_repo.get_by_id_for_owner = AsyncMock(return_value=event)
    event_repo.get_media_asset_by_id = AsyncMock(return_value=asset)

    service = EventService(event_repo, organizer_repo)

    updated_asset = await service.update_media_asset_metadata(
        owner_user_id=owner_id,
        event_id=event_id,
        asset_id=asset_id,
        title="New Title",
        caption="New Caption",
        sort_order=1,
        is_primary=True,
    )

    assert asset.title == "New Title"
    assert asset.caption == "New Caption"
    assert asset.sort_order == 1
    assert asset.is_primary is True
    event_repo.session.flush.assert_called()


@pytest.mark.asyncio
async def test_update_media_asset_preserves_unspecified_fields(event_repo, organizer_repo):
    """Test that updating one field preserves others."""
    event_id = uuid4()
    owner_id = uuid4()
    asset_id = uuid4()

    event = SimpleNamespace(id=event_id, title="Test Event")
    asset = SimpleNamespace(
        id=asset_id,
        event_id=event_id,
        asset_type="banner",
        title="Original Title",
        caption="Original Caption",
        alt_text="Original Alt",
        sort_order=5,
        is_primary=True,
    )

    event_repo.get_by_id_for_owner = AsyncMock(return_value=event)
    event_repo.get_media_asset_by_id = AsyncMock(return_value=asset)

    service = EventService(event_repo, organizer_repo)

    # Only update title, nothing else
    await service.update_media_asset_metadata(
        owner_user_id=owner_id,
        event_id=event_id,
        asset_id=asset_id,
        title="Updated Title",
    )

    assert asset.title == "Updated Title"
    assert asset.caption == "Original Caption"  # Preserved
    assert asset.sort_order == 5  # Preserved
    assert asset.is_primary is True  # Preserved


# =============================================================================
# Workflow Tests - Delete Media Asset
# =============================================================================

@pytest.mark.asyncio
async def test_delete_media_asset_removes_from_database_and_s3(event_repo, organizer_repo, mock_s3_client):
    """Test that deleting an asset removes it from DB and S3."""
    event_id = uuid4()
    owner_id = uuid4()
    asset_id = uuid4()

    event = SimpleNamespace(id=event_id, title="Test Event", setup_status={})
    asset = SimpleNamespace(
        id=asset_id,
        event_id=event_id,
        asset_type="banner",
        storage_key="events/test-id/banner_abc12345_test.png",
    )

    event_repo.get_by_id_for_owner = AsyncMock(return_value=event)
    event_repo.get_media_asset_by_id = AsyncMock(return_value=asset)
    event_repo.count_event_days = AsyncMock(return_value=0)
    event_repo.count_ticket_types = AsyncMock(return_value=0)
    event_repo.count_ticket_allocations = AsyncMock(return_value=0)

    service = EventService(event_repo, organizer_repo)

    with patch("apps.event.service.get_s3_client", return_value=mock_s3_client):
        await service.delete_media_asset(owner_id, event_id, asset_id)

    # Verify S3 delete was called
    mock_s3_client.delete_file.assert_called_with(asset.storage_key)
    event_repo.delete_media_asset.assert_called_once()


@pytest.mark.asyncio
async def test_delete_banner_updates_setup_status(event_repo, organizer_repo, mock_s3_client):
    """Test that deleting a banner marks assets section incomplete."""
    event_id = uuid4()
    owner_id = uuid4()
    asset_id = uuid4()

    event = SimpleNamespace(
        id=event_id,
        title="Test Event",
        setup_status={"basic_info": True, "schedule": True, "tickets": True, "assets": True},
    )
    asset = SimpleNamespace(
        id=asset_id,
        event_id=event_id,
        asset_type="banner",
        storage_key="events/test-id/banner_abc12345_test.png",
    )

    event_repo.get_by_id_for_owner = AsyncMock(return_value=event)
    event_repo.get_media_asset_by_id = AsyncMock(return_value=asset)
    event_repo.count_event_days = AsyncMock(return_value=0)
    event_repo.count_ticket_types = AsyncMock(return_value=0)
    event_repo.count_ticket_allocations = AsyncMock(return_value=0)
    event_repo.delete_media_asset = AsyncMock()

    service = EventService(event_repo, organizer_repo)

    with patch("apps.event.service.get_s3_client", return_value=mock_s3_client):
        await service.delete_media_asset(owner_id, event_id, asset_id)

    # After delete, setup_status["assets"] should be False (no banners left)
    assert event.setup_status["assets"] is False


# =============================================================================
# Validation Error Tests - Upload
# =============================================================================

@pytest.mark.asyncio
async def test_upload_invalid_file_type_raises_error(event_repo, organizer_repo, mock_s3_client):
    """Test that uploading an invalid file type raises FileValidationError."""
    event_id = uuid4()
    owner_id = uuid4()

    event = SimpleNamespace(id=event_id, title="Test Event")
    event_repo.get_by_id_for_owner = AsyncMock(return_value=event)

    service = EventService(event_repo, organizer_repo)

    with patch("apps.event.service.get_s3_client", return_value=mock_s3_client):
        with pytest.raises(FileValidationError, match="Invalid file type"):
            await service.upload_media_asset(
                owner_user_id=owner_id,
                event_id=event_id,
                asset_type="banner",
                file_name="document.txt",
                file_content=b"not an image" * 1000,
            )


@pytest.mark.asyncio
async def test_upload_oversized_file_raises_error(event_repo, organizer_repo, mock_s3_client):
    """Test that uploading a file >5MB raises FileValidationError."""
    event_id = uuid4()
    owner_id = uuid4()

    event = SimpleNamespace(id=event_id, title="Test Event")
    event_repo.get_by_id_for_owner = AsyncMock(return_value=event)

    service = EventService(event_repo, organizer_repo)

    # 6MB of data exceeds 5MB limit
    large_content = b"x" * (6 * 1024 * 1024)

    with patch("apps.event.service.get_s3_client", return_value=mock_s3_client):
        with pytest.raises(FileValidationError, match="exceeds maximum"):
            await service.upload_media_asset(
                owner_user_id=owner_id,
                event_id=event_id,
                asset_type="banner",
                file_name="large.png",
                file_content=large_content,
            )


@pytest.mark.asyncio
async def test_upload_undersized_image_raises_error(event_repo, organizer_repo, mock_s3_client):
    """Test that uploading an image <200x200 raises FileValidationError."""
    event_id = uuid4()
    owner_id = uuid4()

    event = SimpleNamespace(id=event_id, title="Test Event")
    event_repo.get_by_id_for_owner = AsyncMock(return_value=event)

    service = EventService(event_repo, organizer_repo)

    # Create a small image (100x100)
    from PIL import Image
    from io import BytesIO

    small_img = Image.new("RGB", (100, 100), color="red")
    buf = BytesIO()
    small_img.save(buf, format="PNG")
    small_content = buf.getvalue()

    with patch("apps.event.service.get_s3_client", return_value=mock_s3_client):
        with pytest.raises(FileValidationError, match="below minimum"):
            await service.upload_media_asset(
                owner_user_id=owner_id,
                event_id=event_id,
                asset_type="banner",
                file_name="small.png",
                file_content=small_content,
            )


@pytest.mark.asyncio
async def test_upload_unauthorized_user_raises_event_not_found(event_repo, organizer_repo):
    """Test that uploading to a non-owned event raises EventNotFound."""
    owner_id = uuid4()
    event_id = uuid4()

    # No event found for this owner
    event_repo.get_by_id_for_owner = AsyncMock(return_value=None)

    service = EventService(event_repo, organizer_repo)

    with pytest.raises(Exception):  # EventNotFound
        await service.upload_media_asset(
            owner_user_id=owner_id,
            event_id=event_id,
            asset_type="banner",
            file_name="banner.png",
            file_content=b"fake_image_data",
        )


@pytest.mark.asyncio
async def test_upload_invalid_asset_type_raises_error(event_repo, organizer_repo, mock_s3_client):
    """Test that uploading with invalid asset_type raises InvalidAsset."""
    event_id = uuid4()
    owner_id = uuid4()

    event = SimpleNamespace(id=event_id, title="Test Event")
    event_repo.get_by_id_for_owner = AsyncMock(return_value=event)

    service = EventService(event_repo, organizer_repo)

    with patch("apps.event.service.get_s3_client", return_value=mock_s3_client):
        with pytest.raises(Exception):  # InvalidAsset
            await service.upload_media_asset(
                owner_user_id=owner_id,
                event_id=event_id,
                asset_type="invalid_type",
                file_name="file.png",
                file_content=b"fake_data",
            )


# =============================================================================
# Validation Error Tests - Update/Delete
# =============================================================================

@pytest.mark.asyncio
async def test_update_asset_from_another_event_raises_error(event_repo, organizer_repo):
    """Test that updating an asset from another event raises InvalidAsset."""
    event_id = uuid4()
    owner_id = uuid4()
    asset_id = uuid4()

    event = SimpleNamespace(id=event_id, title="Test Event")
    asset = SimpleNamespace(
        id=asset_id,
        event_id=uuid4(),  # Different event
        asset_type="banner",
    )

    event_repo.get_by_id_for_owner = AsyncMock(return_value=event)
    event_repo.get_media_asset_by_id = AsyncMock(return_value=asset)

    service = EventService(event_repo, organizer_repo)

    with pytest.raises(Exception):  # InvalidAsset
        await service.update_media_asset_metadata(
            owner_user_id=owner_id,
            event_id=event_id,
            asset_id=asset_id,
            title="New Title",
        )


@pytest.mark.asyncio
async def test_delete_asset_from_another_event_raises_error(event_repo, organizer_repo, mock_s3_client):
    """Test that deleting an asset from another event raises InvalidAsset."""
    event_id = uuid4()
    owner_id = uuid4()
    asset_id = uuid4()

    event = SimpleNamespace(id=event_id, title="Test Event")
    asset = SimpleNamespace(
        id=asset_id,
        event_id=uuid4(),  # Different event
        asset_type="banner",
        storage_key="some/key.png",
    )

    event_repo.get_by_id_for_owner = AsyncMock(return_value=event)
    event_repo.get_media_asset_by_id = AsyncMock(return_value=asset)

    service = EventService(event_repo, organizer_repo)

    with pytest.raises(Exception):  # InvalidAsset
        await service.delete_media_asset(owner_id, event_id, asset_id)


# =============================================================================
# Publish Validation Tests
# =============================================================================

@pytest.mark.asyncio
async def test_event_without_banner_cannot_publish(event_repo, organizer_repo):
    """Test that an event without a banner cannot be published."""
    owner_id = uuid4()
    event_id = uuid4()

    event = SimpleNamespace(
        id=event_id,
        title="Incomplete Event",
        event_access_type=EventAccessType.ticketed,
        location_mode=LocationMode.venue,
        timezone="Asia/Kolkata",
        venue_name="Test Venue",
        venue_address="123 Test St",
        venue_city="Test City",
        venue_country="Test Country",
    )
    day = SimpleNamespace(
        id=uuid4(),
        event_id=event_id,
        day_index=1,
        date=date(2026, 4, 15),
        start_time=datetime(2026, 4, 15, 10, 0, 0),
    )

    event_repo.get_by_id_for_owner = AsyncMock(return_value=event)
    event_repo.list_event_days = AsyncMock(return_value=[day])
    event_repo.list_ticket_types = AsyncMock(return_value=[SimpleNamespace(id=uuid4())])
    event_repo.list_allocations = AsyncMock(return_value=[SimpleNamespace(id=uuid4(), quantity=50)])
    event_repo.list_media_assets = AsyncMock(return_value=[])  # No banner!

    service = EventService(event_repo, organizer_repo)

    validation = await service.validate_for_publish(owner_id, event_id)

    assert validation["can_publish"] is False
    assert validation["sections"]["assets"]["complete"] is False
    assert any("banner" in e.field.lower() or "image" in e.field.lower() for e in validation["sections"]["assets"]["errors"])


@pytest.mark.asyncio
async def test_event_with_banner_can_publish(event_repo, organizer_repo):
    """Test that an event with a banner can be published."""
    owner_id = uuid4()
    event_id = uuid4()

    event = SimpleNamespace(
        id=event_id,
        title="Complete Event",
        event_access_type=EventAccessType.open,  # Open events don't need tickets
        location_mode=LocationMode.venue,
        timezone="Asia/Kolkata",
        venue_name="Test Venue",
        venue_address="123 Test St",
        venue_city="Test City",
        venue_country="Test Country",
    )
    day = SimpleNamespace(
        id=uuid4(),
        event_id=event_id,
        day_index=1,
        date=date(2026, 4, 15),
    )
    banner_asset = SimpleNamespace(
        id=uuid4(),
        asset_type="banner",
        title="Event Banner",
    )

    event_repo.get_by_id_for_owner = AsyncMock(return_value=event)
    event_repo.list_event_days = AsyncMock(return_value=[day])
    event_repo.list_ticket_types = AsyncMock(return_value=[])
    event_repo.list_allocations = AsyncMock(return_value=[])
    event_repo.list_media_assets = AsyncMock(return_value=[banner_asset])  # Has banner

    service = EventService(event_repo, organizer_repo)

    validation = await service.validate_for_publish(owner_id, event_id)

    assert validation["can_publish"] is True
    assert validation["sections"]["assets"]["complete"] is True


@pytest.mark.asyncio
async def test_publish_event_fails_without_banner(event_repo, organizer_repo):
    """Test that publishing fails when banner is missing."""
    owner_id = uuid4()
    event_id = uuid4()

    event = SimpleNamespace(
        id=event_id,
        title="Incomplete Event",
        event_access_type=EventAccessType.open,
        location_mode=LocationMode.venue,
        timezone="Asia/Kolkata",
        venue_name="Test Venue",
        venue_address="123 Test St",
        venue_city="Test City",
        venue_country="Test Country",
        status="draft",
        is_published=False,
        published_at=None,
    )
    day = SimpleNamespace(id=uuid4(), event_id=event_id, day_index=1, date=date(2026, 4, 15))

    event_repo.get_by_id_for_owner = AsyncMock(return_value=event)
    event_repo.list_event_days = AsyncMock(return_value=[day])
    event_repo.list_ticket_types = AsyncMock(return_value=[])
    event_repo.list_allocations = AsyncMock(return_value=[])
    event_repo.list_media_assets = AsyncMock(return_value=[])  # No banner
    event_repo.session = AsyncMock()
    event_repo.session.flush = AsyncMock()
    event_repo.session.refresh = AsyncMock()

    service = EventService(event_repo, organizer_repo)

    from apps.event.exceptions import CannotPublishEvent
    with pytest.raises(CannotPublishEvent):
        await service.publish_event(owner_id, event_id)