"""
Integration tests for Organizer Media Asset workflow.

Tests the complete lifecycle of organizer logo and cover images:
- Upload logo
- Upload cover
- Both can coexist
- Validation errors

Run with: pytest tests/apps/organizer/test_organizer_media_integration.py -v
"""
import pytest
from uuid import uuid4
from unittest.mock import AsyncMock, MagicMock, patch
from types import SimpleNamespace

from apps.organizer.service import OrganizerService
from apps.organizer.models import OrganizerPageModel
from src.utils.file_validation import FileValidationError


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def mock_s3_client():
    """Mock S3 client that tracks upload/delete calls."""
    mock = MagicMock()
    mock.upload_file.return_value = "organizers/test-org-id/logo_abc12345_logo.png"
    mock.delete_file.return_value = True
    mock.generate_public_url.return_value = "http://localhost:4566/test-bucket/organizers/test-org-id/logo_abc12345_logo.png"
    return mock


@pytest.fixture
def organizer_repo():
    """Mock OrganizerRepository."""
    repo = AsyncMock()
    repo.add = MagicMock()
    repo.session = AsyncMock()
    repo.session.flush = AsyncMock()
    repo.session.refresh = AsyncMock()
    return repo


# =============================================================================
# Workflow Tests - Logo Upload
# =============================================================================

@pytest.mark.asyncio
async def test_upload_logo_persists_logo_url_to_organizer(organizer_repo, mock_s3_client):
    """Test that uploading a logo updates the organizer's logo_url."""
    from PIL import Image
    from io import BytesIO

    owner_id = uuid4()
    organizer_id = uuid4()

    organizer = SimpleNamespace(
        id=organizer_id,
        owner_user_id=owner_id,
        name="Test Organizer",
        slug="test-organizer",
        logo_url=None,
        cover_image_url=None,
    )

    organizer_repo.get_by_id_for_owner = AsyncMock(return_value=organizer)

    service = OrganizerService(organizer_repo)

    # Create a valid 200x200 PNG image
    img = Image.new("RGB", (200, 200), color="green")
    buf = BytesIO()
    img.save(buf, format="PNG")
    valid_image_bytes = buf.getvalue()

    with patch("apps.organizer.service.get_s3_client", return_value=mock_s3_client):
        updated_organizer = await service.upload_logo(
            owner_user_id=owner_id,
            organizer_page_id=organizer_id,
            file_name="logo.png",
            file_content=valid_image_bytes,
        )

    # Verify S3 upload was called
    mock_s3_client.upload_file.assert_called_once()
    call_args = mock_s3_client.upload_file.call_args
    assert call_args.kwargs["resource_id"] == organizer_id
    assert call_args.kwargs["asset_type"] == "logo"

    # Verify organizer's logo_url was updated
    assert updated_organizer.logo_url is not None
    assert "logo_" in updated_organizer.logo_url or "logo" in mock_s3_client.generate_public_url.call_args[0][0]
    organizer_repo.session.flush.assert_called()


@pytest.mark.asyncio
async def test_upload_logo_replaces_existing_logo(organizer_repo, mock_s3_client):
    """Test that uploading a new logo replaces the existing one."""
    from PIL import Image
    from io import BytesIO

    owner_id = uuid4()
    organizer_id = uuid4()

    organizer = SimpleNamespace(
        id=organizer_id,
        owner_user_id=owner_id,
        name="Test Organizer",
        slug="test-organizer",
        logo_url="http://localhost:4566/old-logo.png",
        cover_image_url=None,
    )

    organizer_repo.get_by_id_for_owner = AsyncMock(return_value=organizer)

    service = OrganizerService(organizer_repo)

    # Create a valid 200x200 PNG image
    img = Image.new("RGB", (200, 200), color="orange")
    buf = BytesIO()
    img.save(buf, format="PNG")
    logo_bytes = buf.getvalue()

    # New logo upload returns different URL
    mock_s3_client.generate_public_url.return_value = "http://localhost:4566/new-logo.png"

    with patch("apps.organizer.service.get_s3_client", return_value=mock_s3_client):
        updated_organizer = await service.upload_logo(
            owner_user_id=owner_id,
            organizer_page_id=organizer_id,
            file_name="new_logo.png",
            file_content=logo_bytes,
        )

    # Verify new logo URL was set
    assert updated_organizer.logo_url == "http://localhost:4566/new-logo.png"


@pytest.mark.asyncio
async def test_upload_logo_with_valid_image_passes_validation(organizer_repo, mock_s3_client):
    """Test that a valid 200x200+ image passes validation."""
    owner_id = uuid4()
    organizer_id = uuid4()

    organizer = SimpleNamespace(
        id=organizer_id,
        owner_user_id=owner_id,
        name="Test Organizer",
        slug="test-organizer",
        logo_url=None,
        cover_image_url=None,
    )

    organizer_repo.get_by_id_for_owner = AsyncMock(return_value=organizer)

    service = OrganizerService(organizer_repo)

    # Create a proper 200x200 PNG image
    from PIL import Image
    from io import BytesIO

    img = Image.new("RGB", (200, 200), color="green")
    buf = BytesIO()
    img.save(buf, format="PNG")
    valid_image_bytes = buf.getvalue()

    with patch("apps.organizer.service.get_s3_client", return_value=mock_s3_client):
        # Should not raise
        result = await service.upload_logo(
            owner_user_id=owner_id,
            organizer_page_id=organizer_id,
            file_name="valid_logo.png",
            file_content=valid_image_bytes,
        )

    assert result.logo_url is not None


# =============================================================================
# Workflow Tests - Cover Image Upload
# =============================================================================

@pytest.mark.asyncio
async def test_upload_cover_persists_cover_url_to_organizer(organizer_repo, mock_s3_client):
    """Test that uploading a cover image updates the organizer's cover_image_url."""
    from PIL import Image
    from io import BytesIO

    owner_id = uuid4()
    organizer_id = uuid4()

    organizer = SimpleNamespace(
        id=organizer_id,
        owner_user_id=owner_id,
        name="Test Organizer",
        slug="test-organizer",
        logo_url=None,
        cover_image_url=None,
    )

    organizer_repo.get_by_id_for_owner = AsyncMock(return_value=organizer)

    service = OrganizerService(organizer_repo)

    # Create a valid 200x200 PNG image
    img = Image.new("RGB", (200, 200), color="blue")
    buf = BytesIO()
    img.save(buf, format="PNG")
    valid_image_bytes = buf.getvalue()

    with patch("apps.organizer.service.get_s3_client", return_value=mock_s3_client):
        updated_organizer = await service.upload_cover_image(
            owner_user_id=owner_id,
            organizer_page_id=organizer_id,
            file_name="cover.png",
            file_content=valid_image_bytes,
        )

    # Verify S3 upload was called with cover type
    mock_s3_client.upload_file.assert_called_once()
    call_args = mock_s3_client.upload_file.call_args
    assert call_args.kwargs["asset_type"] == "cover"

    # Verify organizer's cover_image_url was updated
    assert updated_organizer.cover_image_url is not None
    organizer_repo.session.flush.assert_called()


@pytest.mark.asyncio
async def test_upload_cover_replaces_existing_cover(organizer_repo, mock_s3_client):
    """Test that uploading a new cover replaces the existing one."""
    from PIL import Image
    from io import BytesIO

    owner_id = uuid4()
    organizer_id = uuid4()

    organizer = SimpleNamespace(
        id=organizer_id,
        owner_user_id=owner_id,
        name="Test Organizer",
        slug="test-organizer",
        logo_url=None,
        cover_image_url="http://localhost:4566/old-cover.png",
    )

    organizer_repo.get_by_id_for_owner = AsyncMock(return_value=organizer)

    service = OrganizerService(organizer_repo)

    # Create a valid 200x200 PNG image
    img = Image.new("RGB", (200, 200), color="red")
    buf = BytesIO()
    img.save(buf, format="PNG")
    valid_image_bytes = buf.getvalue()

    mock_s3_client.generate_public_url.return_value = "http://localhost:4566/new-cover.png"

    with patch("apps.organizer.service.get_s3_client", return_value=mock_s3_client):
        updated_organizer = await service.upload_cover_image(
            owner_user_id=owner_id,
            organizer_page_id=organizer_id,
            file_name="new_cover.png",
            file_content=valid_image_bytes,
        )

    assert updated_organizer.cover_image_url == "http://localhost:4566/new-cover.png"


# =============================================================================
# Workflow Tests - Both Images
# =============================================================================

@pytest.mark.asyncio
async def test_both_logo_and_cover_can_coexist(organizer_repo, mock_s3_client):
    """Test that uploading logo doesn't affect cover and vice versa."""
    from PIL import Image
    from io import BytesIO

    owner_id = uuid4()
    organizer_id = uuid4()

    organizer = SimpleNamespace(
        id=organizer_id,
        owner_user_id=owner_id,
        name="Test Organizer",
        slug="test-organizer",
        logo_url=None,
        cover_image_url=None,
    )

    organizer_repo.get_by_id_for_owner = AsyncMock(return_value=organizer)

    service = OrganizerService(organizer_repo)

    # Create valid images
    logo_img = Image.new("RGB", (200, 200), color="green")
    logo_buf = BytesIO()
    logo_img.save(logo_buf, format="PNG")
    logo_bytes = logo_buf.getvalue()

    cover_img = Image.new("RGB", (200, 200), color="blue")
    cover_buf = BytesIO()
    cover_img.save(cover_buf, format="PNG")
    cover_bytes = cover_buf.getvalue()

    # First upload logo
    mock_s3_client.generate_public_url.return_value = "http://localhost:4566/logo.png"
    with patch("apps.organizer.service.get_s3_client", return_value=mock_s3_client):
        result1 = await service.upload_logo(
            owner_user_id=owner_id,
            organizer_page_id=organizer_id,
            file_name="logo.png",
            file_content=logo_bytes,
        )

    # Then upload cover
    mock_s3_client.generate_public_url.return_value = "http://localhost:4566/cover.png"
    with patch("apps.organizer.service.get_s3_client", return_value=mock_s3_client):
        result2 = await service.upload_cover_image(
            owner_user_id=owner_id,
            organizer_page_id=organizer_id,
            file_name="cover.png",
            file_content=cover_bytes,
        )

    # Both should be set independently
    assert result1.logo_url == "http://localhost:4566/logo.png"
    assert result2.cover_image_url == "http://localhost:4566/cover.png"


@pytest.mark.asyncio
async def test_logo_does_not_affect_cover_url(organizer_repo, mock_s3_client):
    """Test that uploading logo doesn't modify cover_image_url."""
    from PIL import Image
    from io import BytesIO

    owner_id = uuid4()
    organizer_id = uuid4()

    # Organizer already has a cover image
    organizer = SimpleNamespace(
        id=organizer_id,
        owner_user_id=owner_id,
        name="Test Organizer",
        slug="test-organizer",
        logo_url=None,
        cover_image_url="http://localhost:4566/existing-cover.png",
    )

    organizer_repo.get_by_id_for_owner = AsyncMock(return_value=organizer)

    service = OrganizerService(organizer_repo)

    # Create a valid 200x200 PNG image
    img = Image.new("RGB", (200, 200), color="purple")
    buf = BytesIO()
    img.save(buf, format="PNG")
    logo_bytes = buf.getvalue()

    mock_s3_client.generate_public_url.return_value = "http://localhost:4566/new-logo.png"

    with patch("apps.organizer.service.get_s3_client", return_value=mock_s3_client):
        result = await service.upload_logo(
            owner_user_id=owner_id,
            organizer_page_id=organizer_id,
            file_name="logo.png",
            file_content=logo_bytes,
        )

    # Cover should remain unchanged
    assert result.cover_image_url == "http://localhost:4566/existing-cover.png"
    # Logo should be updated
    assert result.logo_url == "http://localhost:4566/new-logo.png"


# =============================================================================
# Validation Error Tests - Logo
# =============================================================================

@pytest.mark.asyncio
async def test_upload_logo_with_invalid_file_type_raises_error(organizer_repo, mock_s3_client):
    """Test that uploading a non-image file raises FileValidationError."""
    owner_id = uuid4()
    organizer_id = uuid4()

    organizer = SimpleNamespace(
        id=organizer_id,
        owner_user_id=owner_id,
        name="Test Organizer",
        slug="test-organizer",
    )

    organizer_repo.get_by_id_for_owner = AsyncMock(return_value=organizer)

    service = OrganizerService(organizer_repo)

    with patch("apps.organizer.service.get_s3_client", return_value=mock_s3_client):
        with pytest.raises(FileValidationError, match="Invalid file type"):
            await service.upload_logo(
                owner_user_id=owner_id,
                organizer_page_id=organizer_id,
                file_name="document.txt",
                file_content=b"not an image" * 1000,
            )


@pytest.mark.asyncio
async def test_upload_logo_with_oversized_file_raises_error(organizer_repo, mock_s3_client):
    """Test that uploading a file >5MB raises FileValidationError."""
    owner_id = uuid4()
    organizer_id = uuid4()

    organizer = SimpleNamespace(
        id=organizer_id,
        owner_user_id=owner_id,
        name="Test Organizer",
        slug="test-organizer",
    )

    organizer_repo.get_by_id_for_owner = AsyncMock(return_value=organizer)

    service = OrganizerService(organizer_repo)

    # 6MB of data exceeds 5MB limit
    large_content = b"x" * (6 * 1024 * 1024)

    with patch("apps.organizer.service.get_s3_client", return_value=mock_s3_client):
        with pytest.raises(FileValidationError, match="exceeds maximum"):
            await service.upload_logo(
                owner_user_id=owner_id,
                organizer_page_id=organizer_id,
                file_name="large.png",
                file_content=large_content,
            )


@pytest.mark.asyncio
async def test_upload_logo_with_undersized_image_raises_error(organizer_repo, mock_s3_client):
    """Test that uploading an image <200x200 raises FileValidationError."""
    owner_id = uuid4()
    organizer_id = uuid4()

    organizer = SimpleNamespace(
        id=organizer_id,
        owner_user_id=owner_id,
        name="Test Organizer",
        slug="test-organizer",
    )

    organizer_repo.get_by_id_for_owner = AsyncMock(return_value=organizer)

    service = OrganizerService(organizer_repo)

    # Create a small image (100x100)
    from PIL import Image
    from io import BytesIO

    small_img = Image.new("RGB", (100, 100), color="red")
    buf = BytesIO()
    small_img.save(buf, format="PNG")
    small_content = buf.getvalue()

    with patch("apps.organizer.service.get_s3_client", return_value=mock_s3_client):
        with pytest.raises(FileValidationError, match="below minimum"):
            await service.upload_logo(
                owner_user_id=owner_id,
                organizer_page_id=organizer_id,
                file_name="small.png",
                file_content=small_content,
            )


@pytest.mark.asyncio
async def test_upload_logo_unauthorized_raises_not_found(organizer_repo, mock_s3_client):
    """Test that uploading logo for non-owned organizer raises OrganizerNotFound."""
    owner_id = uuid4()
    wrong_owner_id = uuid4()
    organizer_id = uuid4()

    # No organizer found for this owner
    organizer_repo.get_by_id_for_owner = AsyncMock(return_value=None)

    service = OrganizerService(organizer_repo)

    with pytest.raises(Exception):  # OrganizerNotFound
        await service.upload_logo(
            owner_user_id=wrong_owner_id,
            organizer_page_id=organizer_id,
            file_name="logo.png",
            file_content=b"logo_data",
        )


# =============================================================================
# Validation Error Tests - Cover
# =============================================================================

@pytest.mark.asyncio
async def test_upload_cover_with_invalid_file_type_raises_error(organizer_repo, mock_s3_client):
    """Test that uploading a non-image file raises FileValidationError."""
    owner_id = uuid4()
    organizer_id = uuid4()

    organizer = SimpleNamespace(
        id=organizer_id,
        owner_user_id=owner_id,
        name="Test Organizer",
        slug="test-organizer",
    )

    organizer_repo.get_by_id_for_owner = AsyncMock(return_value=organizer)

    service = OrganizerService(organizer_repo)

    with patch("apps.organizer.service.get_s3_client", return_value=mock_s3_client):
        with pytest.raises(FileValidationError, match="Invalid file type"):
            await service.upload_cover_image(
                owner_user_id=owner_id,
                organizer_page_id=organizer_id,
                file_name="document.txt",
                file_content=b"not an image" * 1000,
            )


@pytest.mark.asyncio
async def test_upload_cover_with_oversized_file_raises_error(organizer_repo, mock_s3_client):
    """Test that uploading a file >5MB raises FileValidationError."""
    owner_id = uuid4()
    organizer_id = uuid4()

    organizer = SimpleNamespace(
        id=organizer_id,
        owner_user_id=owner_id,
        name="Test Organizer",
        slug="test-organizer",
    )

    organizer_repo.get_by_id_for_owner = AsyncMock(return_value=organizer)

    service = OrganizerService(organizer_repo)

    large_content = b"x" * (6 * 1024 * 1024)

    with patch("apps.organizer.service.get_s3_client", return_value=mock_s3_client):
        with pytest.raises(FileValidationError, match="exceeds maximum"):
            await service.upload_cover_image(
                owner_user_id=owner_id,
                organizer_page_id=organizer_id,
                file_name="large.png",
                file_content=large_content,
            )


@pytest.mark.asyncio
async def test_upload_cover_with_undersized_image_raises_error(organizer_repo, mock_s3_client):
    """Test that uploading an image <200x200 raises FileValidationError."""
    owner_id = uuid4()
    organizer_id = uuid4()

    organizer = SimpleNamespace(
        id=organizer_id,
        owner_user_id=owner_id,
        name="Test Organizer",
        slug="test-organizer",
    )

    organizer_repo.get_by_id_for_owner = AsyncMock(return_value=organizer)

    service = OrganizerService(organizer_repo)

    from PIL import Image
    from io import BytesIO

    small_img = Image.new("RGB", (100, 100), color="red")
    buf = BytesIO()
    small_img.save(buf, format="PNG")
    small_content = buf.getvalue()

    with patch("apps.organizer.service.get_s3_client", return_value=mock_s3_client):
        with pytest.raises(FileValidationError, match="below minimum"):
            await service.upload_cover_image(
                owner_user_id=owner_id,
                organizer_page_id=organizer_id,
                file_name="small.png",
                file_content=small_content,
            )


@pytest.mark.asyncio
async def test_upload_cover_unauthorized_raises_not_found(organizer_repo, mock_s3_client):
    """Test that uploading cover for non-owned organizer raises OrganizerNotFound."""
    owner_id = uuid4()
    wrong_owner_id = uuid4()
    organizer_id = uuid4()

    organizer_repo.get_by_id_for_owner = AsyncMock(return_value=None)

    service = OrganizerService(organizer_repo)

    with pytest.raises(Exception):  # OrganizerNotFound
        await service.upload_cover_image(
            owner_user_id=wrong_owner_id,
            organizer_page_id=organizer_id,
            file_name="cover.png",
            file_content=b"cover_data",
        )


# =============================================================================
# Validation Error Tests - JPG Image
# =============================================================================

@pytest.mark.asyncio
async def test_upload_logo_with_valid_jpg_passes(organizer_repo, mock_s3_client):
    """Test that a valid JPG image passes validation."""
    owner_id = uuid4()
    organizer_id = uuid4()

    organizer = SimpleNamespace(
        id=organizer_id,
        owner_user_id=owner_id,
        name="Test Organizer",
        slug="test-organizer",
        logo_url=None,
        cover_image_url=None,
    )

    organizer_repo.get_by_id_for_owner = AsyncMock(return_value=organizer)

    service = OrganizerService(organizer_repo)

    # Create a proper 200x200 JPEG image
    from PIL import Image
    from io import BytesIO

    img = Image.new("RGB", (200, 200), color="blue")
    buf = BytesIO()
    img.save(buf, format="JPEG")
    valid_jpg_bytes = buf.getvalue()

    with patch("apps.organizer.service.get_s3_client", return_value=mock_s3_client):
        result = await service.upload_logo(
            owner_user_id=owner_id,
            organizer_page_id=organizer_id,
            file_name="logo.jpg",
            file_content=valid_jpg_bytes,
        )

    assert result.logo_url is not None


@pytest.mark.asyncio
async def test_upload_logo_with_valid_webp_passes(organizer_repo, mock_s3_client):
    """Test that a valid WebP image passes validation."""
    owner_id = uuid4()
    organizer_id = uuid4()

    organizer = SimpleNamespace(
        id=organizer_id,
        owner_user_id=owner_id,
        name="Test Organizer",
        slug="test-organizer",
        logo_url=None,
        cover_image_url=None,
    )

    organizer_repo.get_by_id_for_owner = AsyncMock(return_value=organizer)

    service = OrganizerService(organizer_repo)

    # Create a proper 200x200 WebP image
    from PIL import Image
    from io import BytesIO

    img = Image.new("RGB", (200, 200), color="red")
    buf = BytesIO()
    img.save(buf, format="WEBP")
    valid_webp_bytes = buf.getvalue()

    with patch("apps.organizer.service.get_s3_client", return_value=mock_s3_client):
        result = await service.upload_logo(
            owner_user_id=owner_id,
            organizer_page_id=organizer_id,
            file_name="logo.webp",
            file_content=valid_webp_bytes,
        )

    assert result.logo_url is not None