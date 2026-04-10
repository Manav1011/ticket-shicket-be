from typing import Tuple
from PIL import Image
from io import BytesIO


class FileValidationError(Exception):
    """Raised when file validation fails."""

    pass


class FileValidator:
    """Validate media files before upload."""

    # Image constraints
    ALLOWED_IMAGE_TYPES = {"jpg", "jpeg", "png", "webp"}
    MAX_IMAGE_SIZE = 5 * 1024 * 1024  # 5MB
    MIN_IMAGE_WIDTH = 200
    MIN_IMAGE_HEIGHT = 200

    # Video constraints
    ALLOWED_VIDEO_TYPES = {"mp4", "webm"}
    MAX_VIDEO_SIZE = 100 * 1024 * 1024  # 100MB

    @classmethod
    def validate_banner_image(cls, file_name: str, file_content: bytes) -> None:
        """
        Validate banner image.

        Args:
            file_name: Original filename
            file_content: File bytes

        Raises:
            FileValidationError: If validation fails
        """
        cls._validate_file_type(file_name, cls.ALLOWED_IMAGE_TYPES)
        cls._validate_file_size(file_content, cls.MAX_IMAGE_SIZE)
        cls._validate_image_dimensions(file_content, cls.MIN_IMAGE_WIDTH, cls.MIN_IMAGE_HEIGHT)

    @classmethod
    def validate_gallery_image(cls, file_name: str, file_content: bytes) -> None:
        """Validate gallery image."""
        cls._validate_file_type(file_name, cls.ALLOWED_IMAGE_TYPES)
        cls._validate_file_size(file_content, cls.MAX_IMAGE_SIZE)

    @classmethod
    def validate_gallery_video(cls, file_name: str, file_content: bytes) -> None:
        """Validate gallery video."""
        cls._validate_file_type(file_name, cls.ALLOWED_VIDEO_TYPES)
        cls._validate_file_size(file_content, cls.MAX_VIDEO_SIZE)

    @classmethod
    def validate_promo_video_url(cls, url: str) -> None:
        """
        Validate promo video URL.

        Args:
            url: Video URL (YouTube, Vimeo, etc.)

        Raises:
            FileValidationError: If URL is invalid
        """
        if not url or not isinstance(url, str) or len(url.strip()) == 0:
            raise FileValidationError("Promo video URL cannot be empty")

        # Basic URL validation
        if not (url.startswith("http://") or url.startswith("https://")):
            raise FileValidationError("Promo video URL must start with http:// or https://")

        if len(url) > 2048:
            raise FileValidationError("Promo video URL is too long (max 2048 chars)")

    @classmethod
    def _validate_file_type(cls, file_name: str, allowed_types: set) -> None:
        """Validate file extension against allowed types."""
        ext = file_name.lower().split(".")[-1]

        if ext not in allowed_types:
            raise FileValidationError(
                f"Invalid file type: {ext}. Allowed types: {', '.join(allowed_types)}"
            )

    @classmethod
    def _validate_file_size(cls, file_content: bytes, max_size: int) -> None:
        """Validate file size."""
        if len(file_content) > max_size:
            max_mb = max_size / (1024 * 1024)
            raise FileValidationError(f"File size exceeds maximum ({max_mb}MB)")

    @classmethod
    def _validate_image_dimensions(
        cls, file_content: bytes, min_width: int, min_height: int
    ) -> None:
        """Validate image dimensions."""
        try:
            image = Image.open(BytesIO(file_content))
            width, height = image.size

            if width < min_width or height < min_height:
                raise FileValidationError(
                    f"Image dimensions {width}x{height} are below minimum {min_width}x{min_height}"
                )
        except Exception as e:
            if isinstance(e, FileValidationError):
                raise
            raise FileValidationError(f"Invalid image file: {str(e)}")
