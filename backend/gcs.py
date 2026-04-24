"""Google Cloud Storage integration for TikTok Manager.

Provides helpers for uploading video and image files to GCS buckets:
  - Videos: claude-agent-storage
  - Images: claude-agent-images

Service account credentials are loaded from /data/gcp-sa.json (if present)
or from the GOOGLE_APPLICATION_CREDENTIALS environment variable.
"""
import logging
import os
from pathlib import Path

logger = logging.getLogger(__name__)

GCS_PROJECT = os.getenv("GCS_PROJECT", "autogpt-406113")
GCS_VIDEO_BUCKET = os.getenv("GCS_VIDEO_BUCKET", "claude-agent-storage")
GCS_IMAGE_BUCKET = os.getenv("GCS_IMAGE_BUCKET", "claude-agent-images")

# Default SA key path; override with GOOGLE_APPLICATION_CREDENTIALS
_DEFAULT_SA_KEY = "/data/gcp-sa.json"


def _get_storage_client():
    """Return an authenticated google.cloud.storage.Client.

    Raises ImportError if google-cloud-storage is not installed.
    Raises FileNotFoundError/EnvironmentError if credentials are missing.
    """
    from google.cloud import storage  # type: ignore[import-untyped]
    from google.oauth2 import service_account  # type: ignore[import-untyped]

    # Prefer explicit env var, then the default /data path
    sa_key_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS") or _DEFAULT_SA_KEY
    if Path(sa_key_path).exists():
        credentials = service_account.Credentials.from_service_account_file(sa_key_path)
        return storage.Client(project=GCS_PROJECT, credentials=credentials)

    # Fall back to ADC (Application Default Credentials) — works in Cloud Run
    return storage.Client(project=GCS_PROJECT)


def upload_video(content: bytes, destination_blob_name: str, content_type: str = "video/mp4") -> str:
    """Upload video bytes to GCS and return the public GCS URI (gs://).

    Args:
        content: Raw video bytes.
        destination_blob_name: Object name inside the bucket (e.g. "videos/uuid.mp4").
        content_type: MIME type of the video.

    Returns:
        GCS URI: "gs://<bucket>/<blob_name>"

    Raises:
        Exception: Re-raised Google Cloud exceptions on failure.
    """
    client = _get_storage_client()
    bucket = client.bucket(GCS_VIDEO_BUCKET)
    blob = bucket.blob(destination_blob_name)
    blob.upload_from_string(content, content_type=content_type)
    logger.info("Uploaded video to gs://%s/%s (%d bytes)", GCS_VIDEO_BUCKET, destination_blob_name, len(content))
    return f"gs://{GCS_VIDEO_BUCKET}/{destination_blob_name}"


def upload_image(content: bytes, destination_blob_name: str, content_type: str = "image/jpeg") -> str:
    """Upload image bytes to GCS and return the public GCS URI (gs://).

    Args:
        content: Raw image bytes.
        destination_blob_name: Object name inside the bucket (e.g. "thumbnails/uuid.jpg").
        content_type: MIME type of the image.

    Returns:
        GCS URI: "gs://<bucket>/<blob_name>"

    Raises:
        Exception: Re-raised Google Cloud exceptions on failure.
    """
    client = _get_storage_client()
    bucket = client.bucket(GCS_IMAGE_BUCKET)
    blob = bucket.blob(destination_blob_name)
    blob.upload_from_string(content, content_type=content_type)
    logger.info("Uploaded image to gs://%s/%s (%d bytes)", GCS_IMAGE_BUCKET, destination_blob_name, len(content))
    return f"gs://{GCS_IMAGE_BUCKET}/{destination_blob_name}"


def generate_signed_url(bucket_name: str, blob_name: str, expiration_seconds: int = 3600) -> str:
    """Generate a time-limited signed URL for a GCS object.

    Args:
        bucket_name: GCS bucket name.
        blob_name: Object name inside the bucket.
        expiration_seconds: URL validity duration (default: 1 hour).

    Returns:
        HTTPS signed URL string.
    """
    import datetime
    from google.cloud.storage import Client  # type: ignore[import-untyped]

    client = _get_storage_client()
    bucket = client.bucket(bucket_name)
    blob = bucket.blob(blob_name)
    url = blob.generate_signed_url(
        version="v4",
        expiration=datetime.timedelta(seconds=expiration_seconds),
        method="GET",
    )
    return url
