import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4
from PIL import Image
from io import BytesIO

from apps.organizer.service import OrganizerService
from apps.organizer.exceptions import OrganizerNotFound
from src.utils.file_validation import FileValidationError


@pytest.fixture
def valid_image_bytes():
    """Create valid test image bytes (200x200 PNG)."""
    img = Image.new("RGB", (200, 200), color="blue")
    img_bytes = BytesIO()
    img.save(img_bytes, format="PNG")
    return img_bytes.getvalue()


@pytest.fixture
def organizer_service_mock():
    """Mock OrganizerService with mocked dependencies."""
    repo_mock = AsyncMock()
    service = OrganizerService(repo_mock)
    return service, repo_mock


@pytest.mark.asyncio
async def test_upload_logo_success(organizer_service_mock, valid_image_bytes):
    """Test successful logo upload."""
    service, repo_mock = organizer_service_mock

    owner_id = uuid4()
    organizer_id = uuid4()

    organizer = MagicMock(id=organizer_id, logo_url=None)
    repo_mock.get_by_id_for_owner.return_value = organizer
    repo_mock.session = AsyncMock()

    with patch("apps.organizer.service.get_s3_client") as mock_s3:
        mock_client = MagicMock()
        mock_s3.return_value = mock_client
        mock_client.upload_file.return_value = "organizers/123/logo_abc_test.png"
        mock_client.generate_public_url.return_value = "http://localhost:4566/bucket/organizers/123/logo_abc_test.png"

        result = await service.upload_logo(
            owner_user_id=owner_id,
            organizer_page_id=organizer_id,
            file_name="logo.png",
            file_content=valid_image_bytes,
        )

    assert result.logo_url == "http://localhost:4566/bucket/organizers/123/logo_abc_test.png"
    repo_mock.get_by_id_for_owner.assert_awaited_once_with(organizer_id, owner_id)
    repo_mock.session.flush.assert_awaited_once()


@pytest.mark.asyncio
async def test_upload_logo_organizer_not_found(organizer_service_mock, valid_image_bytes):
    """Test upload logo rejects if organizer doesn't exist."""
    service, repo_mock = organizer_service_mock

    owner_id = uuid4()
    organizer_id = uuid4()

    repo_mock.get_by_id_for_owner.return_value = None

    with pytest.raises(OrganizerNotFound):
        await service.upload_logo(
            owner_user_id=owner_id,
            organizer_page_id=organizer_id,
            file_name="logo.png",
            file_content=valid_image_bytes,
        )


@pytest.mark.asyncio
async def test_upload_logo_invalid_file_type(organizer_service_mock):
    """Test upload logo rejects invalid file type."""
    service, repo_mock = organizer_service_mock

    owner_id = uuid4()
    organizer_id = uuid4()

    repo_mock.get_by_id_for_owner.return_value = MagicMock(id=organizer_id)

    with pytest.raises(FileValidationError, match="Invalid file type"):
        await service.upload_logo(
            owner_user_id=owner_id,
            organizer_page_id=organizer_id,
            file_name="logo.txt",
            file_content=b"fake data",
        )


@pytest.mark.asyncio
async def test_upload_cover_image_success(organizer_service_mock, valid_image_bytes):
    """Test successful cover image upload."""
    service, repo_mock = organizer_service_mock

    owner_id = uuid4()
    organizer_id = uuid4()

    organizer = MagicMock(id=organizer_id, cover_image_url=None)
    repo_mock.get_by_id_for_owner.return_value = organizer
    repo_mock.session = AsyncMock()

    with patch("apps.organizer.service.get_s3_client") as mock_s3:
        mock_client = MagicMock()
        mock_s3.return_value = mock_client
        mock_client.upload_file.return_value = "organizers/123/cover_xyz_banner.png"
        mock_client.generate_public_url.return_value = "http://localhost:4566/bucket/organizers/123/cover_xyz_banner.png"

        result = await service.upload_cover_image(
            owner_user_id=owner_id,
            organizer_page_id=organizer_id,
            file_name="banner.png",
            file_content=valid_image_bytes,
        )

    assert result.cover_image_url == "http://localhost:4566/bucket/organizers/123/cover_xyz_banner.png"
    repo_mock.get_by_id_for_owner.assert_awaited_once_with(organizer_id, owner_id)


@pytest.mark.asyncio
async def test_upload_cover_image_organizer_not_found(organizer_service_mock, valid_image_bytes):
    """Test upload cover rejects if organizer doesn't exist."""
    service, repo_mock = organizer_service_mock

    owner_id = uuid4()
    organizer_id = uuid4()

    repo_mock.get_by_id_for_owner.return_value = None

    with pytest.raises(OrganizerNotFound):
        await service.upload_cover_image(
            owner_user_id=owner_id,
            organizer_page_id=organizer_id,
            file_name="cover.png",
            file_content=valid_image_bytes,
        )
