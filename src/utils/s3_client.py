import boto3
from botocore.exceptions import ClientError
from typing import Optional
from uuid import UUID

from src.config import settings


class S3Client:
    """Wrapper around boto3 S3 client for event media uploads."""

    def __init__(self):
        self.bucket = settings.AWS_S3_BUCKET
        self.region = settings.AWS_S3_REGION
        self.client = boto3.client(
            "s3",
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            region_name=settings.AWS_S3_REGION,
            endpoint_url=settings.AWS_S3_ENDPOINT_URL,
        )

    def upload_file(
        self,
        event_id: UUID,
        asset_type: str,
        file_name: str,
        file_content: bytes,
    ) -> str:
        """
        Upload file to S3 and return storage key.

        Args:
            event_id: UUID of the event
            asset_type: Type of asset (banner, gallery_image, gallery_video, promo_video)
            file_name: Original filename
            file_content: File bytes

        Returns:
            Storage key (path in S3)

        Raises:
            ClientError: If S3 upload fails
        """
        # Create storage key: events/{event_id}/{asset_type}_{uuid}_{filename}
        from uuid import uuid4

        unique_id = str(uuid4())[:8]
        storage_key = f"events/{event_id}/{asset_type}_{unique_id}_{file_name}"

        try:
            self.client.put_object(
                Bucket=self.bucket,
                Key=storage_key,
                Body=file_content,
                ContentType=self._get_content_type(file_name),
            )
            return storage_key
        except ClientError as e:
            raise ClientError(
                {"Error": {"Code": "UploadFailed", "Message": str(e)}},
                "PutObject",
            )

    def delete_file(self, storage_key: str) -> bool:
        """
        Delete file from S3.

        Args:
            storage_key: S3 storage key (path)

        Returns:
            True if successful

        Raises:
            ClientError: If deletion fails
        """
        try:
            self.client.delete_object(Bucket=self.bucket, Key=storage_key)
            return True
        except ClientError as e:
            raise ClientError(
                {"Error": {"Code": "DeleteFailed", "Message": str(e)}},
                "DeleteObject",
            )

    def generate_public_url(self, storage_key: str) -> str:
        """
        Generate public URL for file (works for LocalStack and real AWS).

        Args:
            storage_key: S3 storage key (path)

        Returns:
            Public/presigned URL
        """
        if settings.AWS_S3_ENDPOINT_URL:
            # LocalStack: return direct HTTP URL
            return f"{settings.AWS_S3_ENDPOINT_URL}/{self.bucket}/{storage_key}"
        else:
            # AWS: generate presigned URL valid for 7 days
            try:
                url = self.client.generate_presigned_url(
                    "get_object",
                    Params={"Bucket": self.bucket, "Key": storage_key},
                    ExpiresIn=604800,  # 7 days
                )
                return url
            except ClientError as e:
                raise ClientError(
                    {"Error": {"Code": "PresignFailed", "Message": str(e)}},
                    "GeneratePresignedUrl",
                )

    def _get_content_type(self, file_name: str) -> str:
        """Determine MIME type based on file extension."""
        ext = file_name.lower().split(".")[-1]
        mime_types = {
            "jpg": "image/jpeg",
            "jpeg": "image/jpeg",
            "png": "image/png",
            "webp": "image/webp",
            "mp4": "video/mp4",
            "webm": "video/webm",
            "gif": "image/gif",
        }
        return mime_types.get(ext, "application/octet-stream")


# Singleton instance
_s3_client = None


def get_s3_client() -> S3Client:
    """Get S3 client singleton."""
    global _s3_client
    if _s3_client is None:
        _s3_client = S3Client()
    return _s3_client
