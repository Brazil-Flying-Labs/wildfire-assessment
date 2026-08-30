"""Object storage layer backed by Google Cloud Storage.

Polygons and analysis images live in the application bucket
(`GCS_APP_BUCKET_NAME`) under an environment prefix (`GCS_APP_PREFIX`,
e.g. `dev/` or `prod/`), keeping the same logical `polygons/` and `images/`
structure used before with the previous storage.
"""

import json
import logging
import os

from django.conf import settings
from google.cloud import storage

logger = logging.getLogger(__name__)


def _bucket():
    """Return the configured application GCS bucket."""
    return storage.Client().bucket(settings.GCS_APP_BUCKET_NAME)


def _polygon_key(filename):
    """Build the object key for a polygon file (basename only)."""
    return f"{settings.GCS_APP_PREFIX}/polygons/{os.path.basename(filename)}"


def _image_key(key):
    """Build the object key for an image."""
    return f"{settings.GCS_APP_PREFIX}/images/{key}"


def upload_polygon(filename, geojson_data) -> None:
    """Upload GeoJSON data to GCS under the polygons/ prefix."""
    body = (
        json.dumps(geojson_data) if not isinstance(geojson_data, str) else geojson_data
    )
    _bucket().blob(_polygon_key(filename)).upload_from_string(
        body, content_type="application/json"
    )


def download_polygon(filename) -> str:
    """Download a polygon GeoJSON file from GCS and return its content as a string."""
    return _bucket().blob(_polygon_key(filename)).download_as_text()


def delete_polygon(filename) -> bool:
    """Delete a polygon GeoJSON file from GCS. Returns True on success, False on failure."""
    try:
        _bucket().blob(_polygon_key(filename)).delete()
        return True
    except Exception as e:
        logger.warning("Failed to delete polygon from GCS: %s", e)
        return False


def upload_image(key, image_data, content_type="image/jpeg") -> None:
    """Upload image binary data to GCS under the images/ prefix."""
    _bucket().blob(_image_key(key)).upload_from_string(
        image_data, content_type=content_type
    )


def delete_image(key) -> bool:
    """Delete an image from GCS under the images/ prefix. Returns True on success."""
    try:
        _bucket().blob(_image_key(key)).delete()
        return True
    except Exception as e:
        logger.warning("Failed to delete image from GCS: %s", e)
        return False


def get_signed_image_url(key, expiration=3600) -> str:
    """Generate a signed URL for an image stored in GCS."""
    return (
        _bucket()
        .blob(_image_key(key))
        .generate_signed_url(version="v4", expiration=expiration)
    )
