import pytest
from unittest.mock import MagicMock, patch
from uuid import uuid4
from botocore.exceptions import ClientError

from src.utils.s3_client import S3Client


@pytest.fixture
def s3_client():
    """Fixture providing mocked S3Client."""
    with patch("src.utils.s3_client.boto3.client") as mock_boto:
        mock_s3 = MagicMock()
        mock_boto.return_value = mock_s3
        client = S3Client()
        client.client = mock_s3
        yield client


@pytest.mark.asyncio
async def test_upload_file_returns_storage_key(s3_client):
    """Test that upload_file returns correct storage key format."""
    event_id = uuid4()
    file_name = "logo.png"
    file_content = b"fake image data"

    storage_key = s3_client.upload_file(
        event_id=event_id,
        asset_type="banner",
        file_name=file_name,
        file_content=file_content,
    )

    assert storage_key.startswith(f"events/{event_id}/banner_")
    assert storage_key.endswith("_logo.png")
    s3_client.client.put_object.assert_called_once()


@pytest.mark.asyncio
async def test_delete_file_calls_s3_delete(s3_client):
    """Test that delete_file calls S3 delete."""
    storage_key = "events/123/banner_abc_logo.png"

    result = s3_client.delete_file(storage_key)

    assert result is True
    s3_client.client.delete_object.assert_called_once_with(
        Bucket=s3_client.bucket, Key=storage_key
    )


@pytest.mark.asyncio
async def test_generate_public_url_with_localstack_endpoint(s3_client):
    """Test URL generation with LocalStack endpoint."""
    s3_client.bucket = "test-bucket"
    storage_key = "events/123/banner_abc_logo.png"

    with patch("src.utils.s3_client.settings") as mock_settings:
        mock_settings.AWS_S3_ENDPOINT_URL = "http://localhost:4566"
        url = s3_client.generate_public_url(storage_key)

    assert url == "http://localhost:4566/test-bucket/events/123/banner_abc_logo.png"


@pytest.mark.asyncio
async def test_get_content_type_returns_correct_mime(s3_client):
    """Test that content type detection works."""
    test_cases = [
        ("image.jpg", "image/jpeg"),
        ("image.png", "image/png"),
        ("video.mp4", "video/mp4"),
        ("file.unknown", "application/octet-stream"),
    ]

    for file_name, expected_mime in test_cases:
        mime = s3_client._get_content_type(file_name)
        assert mime == expected_mime
