import pytest
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

from src.apps.organizer.service import OrganizerService


@pytest.fixture
def service_mock():
    """Mock OrganizerService."""
    return AsyncMock(spec=OrganizerService)


@pytest.mark.asyncio
async def test_upload_logo_endpoint_calls_service(service_mock):
    """Test that upload logo endpoint calls service method."""
    organizer_id = uuid4()
    user_id = uuid4()

    updated_organizer = MagicMock(
        id=organizer_id,
        logo_url="http://localhost:4566/bucket/organizers/123/logo.png",
    )
    service_mock.upload_logo.return_value = updated_organizer

    result = await service_mock.upload_logo(
        owner_user_id=user_id,
        organizer_page_id=organizer_id,
        file_name="logo.png",
        file_content=b"fake image",
    )

    assert result.logo_url is not None
    service_mock.upload_logo.assert_awaited_once_with(
        owner_user_id=user_id,
        organizer_page_id=organizer_id,
        file_name="logo.png",
        file_content=b"fake image",
    )


@pytest.mark.asyncio
async def test_upload_cover_endpoint_calls_service(service_mock):
    """Test that upload cover endpoint calls service method."""
    organizer_id = uuid4()
    user_id = uuid4()

    updated_organizer = MagicMock(
        id=organizer_id,
        cover_image_url="http://localhost:4566/bucket/organizers/123/cover.png",
    )
    service_mock.upload_cover_image.return_value = updated_organizer

    result = await service_mock.upload_cover_image(
        owner_user_id=user_id,
        organizer_page_id=organizer_id,
        file_name="cover.png",
        file_content=b"fake image",
    )

    assert result.cover_image_url is not None
    service_mock.upload_cover_image.assert_awaited_once()
