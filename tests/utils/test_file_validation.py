import pytest
from PIL import Image
from io import BytesIO

from src.utils.file_validation import FileValidator, FileValidationError


@pytest.fixture
def valid_image_bytes():
    """Create valid test image bytes (200x200 PNG)."""
    img = Image.new("RGB", (200, 200), color="red")
    img_bytes = BytesIO()
    img.save(img_bytes, format="PNG")
    return img_bytes.getvalue()


@pytest.fixture
def small_image_bytes():
    """Create small test image bytes (100x100 PNG)."""
    img = Image.new("RGB", (100, 100), color="red")
    img_bytes = BytesIO()
    img.save(img_bytes, format="PNG")
    return img_bytes.getvalue()


def test_validate_banner_image_success(valid_image_bytes):
    """Test successful banner image validation."""
    # Should not raise
    FileValidator.validate_banner_image("logo.png", valid_image_bytes)


def test_validate_banner_image_invalid_type():
    """Test banner image rejects invalid file type."""
    with pytest.raises(FileValidationError, match="Invalid file type"):
        FileValidator.validate_banner_image("logo.txt", b"fake data")


def test_validate_banner_image_too_large():
    """Test banner image rejects oversized file."""
    large_file = b"x" * (6 * 1024 * 1024)  # 6MB
    with pytest.raises(FileValidationError, match="exceeds maximum"):
        FileValidator.validate_banner_image("image.png", large_file)


def test_validate_banner_image_too_small_dimensions(small_image_bytes):
    """Test banner image rejects undersized dimensions."""
    with pytest.raises(FileValidationError, match="below minimum"):
        FileValidator.validate_banner_image("image.png", small_image_bytes)


def test_validate_gallery_image_success(valid_image_bytes):
    """Test successful gallery image validation."""
    FileValidator.validate_gallery_image("photo.jpg", valid_image_bytes)


def test_validate_gallery_video_success():
    """Test successful gallery video validation (file type only)."""
    # Gallery video validation doesn't check dimensions
    FileValidator.validate_gallery_video("video.mp4", b"x" * 1000)


def test_validate_gallery_video_invalid_type():
    """Test gallery video rejects invalid file type."""
    with pytest.raises(FileValidationError, match="Invalid file type"):
        FileValidator.validate_gallery_video("video.avi", b"fake data")


def test_validate_promo_video_url_success():
    """Test successful promo video URL validation."""
    FileValidator.validate_promo_video_url("https://youtube.com/watch?v=123")


def test_validate_promo_video_url_empty():
    """Test promo video URL rejects empty string."""
    with pytest.raises(FileValidationError, match="cannot be empty"):
        FileValidator.validate_promo_video_url("")


def test_validate_promo_video_url_no_protocol():
    """Test promo video URL requires http/https."""
    with pytest.raises(FileValidationError, match="must start with http"):
        FileValidator.validate_promo_video_url("youtube.com/watch?v=123")


def test_validate_promo_video_url_too_long():
    """Test promo video URL has length limit."""
    long_url = "https://example.com/" + ("x" * 2100)
    with pytest.raises(FileValidationError, match="too long"):
        FileValidator.validate_promo_video_url(long_url)
