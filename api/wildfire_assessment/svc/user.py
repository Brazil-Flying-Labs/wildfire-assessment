"""Service layer for user account operations."""

import logging

from wildfire_assessment.models import AnalysisRun
from wildfire_assessment.svc.object_storage import delete_image

LOG = logging.getLogger(__name__)

IMAGE_FIELDS = [
    "rgb_pre_fire_image",
    "rgb_post_fire_image",
    "dndvi_image",
    "dnbr_image",
    "rbr_image",
]


def delete_user_account(user):
    """Delete a user account and clean up all associated stored images.

    Image deletion is best-effort (logged on failure).
    Django CASCADE handles UserProfile, UserCountry, AnalysisRun,
    Notification, and UserSocialAuth records.
    """
    runs = AnalysisRun.objects.filter(user=user)
    for run in runs:
        for field in IMAGE_FIELDS:
            key = getattr(run, field)
            if key:
                delete_image(key)

    user.delete()
