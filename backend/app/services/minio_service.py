"""MinIO object-storage service for 3D models and simulation output."""

from io import BytesIO
import logging

from minio import Minio
from minio.error import S3Error

from app.config import settings

logger = logging.getLogger(__name__)


def _get_client() -> Minio:
    return Minio(
        settings.MINIO_ENDPOINT,
        access_key=settings.MINIO_ROOT_USER,
        secret_key=settings.MINIO_ROOT_PASSWORD,
        secure=False,  # use TLS in production
    )


def ensure_bucket() -> None:
    """Create the bucket if it does not already exist."""
    client = _get_client()
    if not client.bucket_exists(settings.MINIO_BUCKET):
        client.make_bucket(settings.MINIO_BUCKET)
        logger.info("Created MinIO bucket: %s", settings.MINIO_BUCKET)


def upload_bytes(object_key: str, data: bytes, content_type: str = "application/octet-stream") -> str:
    """Upload raw bytes and return the object key."""
    client = _get_client()
    ensure_bucket()
    client.put_object(
        settings.MINIO_BUCKET,
        object_key,
        BytesIO(data),
        length=len(data),
        content_type=content_type,
    )
    logger.info("Uploaded %s (%d bytes)", object_key, len(data))
    return object_key


def download_bytes(object_key: str) -> bytes:
    """Download an object as bytes."""
    client = _get_client()
    response = client.get_object(settings.MINIO_BUCKET, object_key)
    try:
        return response.read()
    finally:
        response.close()
        response.release_conn()


def get_presigned_url(object_key: str, expires_hours: int = 1) -> str:
    """Generate a pre-signed GET URL (valid for `expires_hours`)."""
    from datetime import timedelta
    client = _get_client()
    return client.presigned_get_object(
        settings.MINIO_BUCKET,
        object_key,
        expires=timedelta(hours=expires_hours),
    )


def delete_object(object_key: str) -> None:
    """Remove an object from the bucket."""
    client = _get_client()
    try:
        client.remove_object(settings.MINIO_BUCKET, object_key)
        logger.info("Deleted %s", object_key)
    except S3Error as exc:
        logger.warning("Failed to delete %s: %s", object_key, exc)
