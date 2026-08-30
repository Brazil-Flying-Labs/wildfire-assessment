import json
import logging
import os
import tempfile
import time
from datetime import timedelta

import ee
from celery import shared_task
from celery.result import AsyncResult
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from django.db.models import Q
from django.utils.timezone import now
from dotenv import load_dotenv
from wildfire_analyser.fire_assessment.deliverables import Deliverable
from wildfire_analyser.fire_assessment.post_fire_assessment import PostFireAssessment
from wildfire_assessment.models import AnalysisRun, Notification, UserProfile
from wildfire_assessment.svc.object_storage import download_polygon
from wildfire_assessment.svc.dashboard import invalidate_dashboard_cache
from wildfire_assessment.translations import get_email_translation

logger = logging.getLogger(__name__)
load_dotenv()

VALID_MOSAIC_STRATEGIES = {
    "best_date_mosaic",
    "best_date_masked_mosaic",
    "best_available_per_tile_mosaic",
    "cloud_masked_light_mosaic",
}


def process_fire_assessment(
    pre_fire_date: str,
    post_fire_date: str,
    polygon_path: str,
    roi_only: bool = True,
    cloud_threshold: int = 100,
    days_before_after: int = 30,
    pre_fire_mosaic_strategy: str = "best_available_per_tile_mosaic",
    post_fire_mosaic_strategy: str = "best_available_per_tile_mosaic",
    roi_only_bg_color: str = "black",
) -> dict:
    """
    Process a full fire assessment with all deliverables.

    Args:
        pre_fire_date (str): Pre-fire date in YYYY-MM-DD format.
        post_fire_date (str): Post-fire date in YYYY-MM-DD format.
        polygon_path (str): Path to the polygon file.
        roi_only (bool): Whether to crop output to the ROI extent.
        cloud_threshold (int): Maximum cloud cover percentage (0-100).
        days_before_after (int): Days before/after the fire dates to search.
        pre_fire_mosaic_strategy (str): Strategy for pre-fire image mosaic.
        post_fire_mosaic_strategy (str): Strategy for post-fire image mosaic.
        roi_only_bg_color (str): Background color when roi_only is True.

    Returns:
        dict: A dictionary with URLs to the generated deliverables and area statistics.
    """
    # Download polygon from GCS to a temp file for PostFireAssessment
    geojson_content = download_polygon(polygon_path)
    tmp = tempfile.NamedTemporaryFile(suffix=".geojson", delete=False)
    try:
        tmp.write(geojson_content.encode("utf-8"))
        tmp.close()

        runner = PostFireAssessment(
            get_gee_private_key_json(),
            tmp.name,
            pre_fire_date,
            post_fire_date,
            deliverables=[
                Deliverable.RGB_PRE_FIRE_VISUAL,
                Deliverable.RGB_POST_FIRE_VISUAL,
                Deliverable.DNDVI_VISUAL,
                Deliverable.DNBR_VISUAL,
                Deliverable.RBR_VISUAL,
                Deliverable.DNBR_AREA_STATISTICS,
            ],
            roi_only=roi_only,
            cloud_threshold=cloud_threshold,
            days_before_after=days_before_after,
            pre_fire_mosaic_strategy=pre_fire_mosaic_strategy,
            post_fire_mosaic_strategy=post_fire_mosaic_strategy,
            roi_only_bg_color=roi_only_bg_color,
        )

        result = runner.run()

        return {
            "severity_map": json.dumps(result["statistics"]["DNBR_AREA_STATISTICS"]),
            "rgb_pre_fire_visual_jpg": result["visual"]["RGB_PRE_FIRE_VISUAL"]["url"],
            "rgb_post_fire_visual_jpg": result["visual"]["RGB_POST_FIRE_VISUAL"]["url"],
            "dndvi_visual_jpg": result["visual"]["DNDVI_VISUAL"]["url"],
            "dnbr_visual_jpg": result["visual"]["DNBR_VISUAL"]["url"],
            "rbr_visual_jpg": result["visual"]["RBR_VISUAL"]["url"],
            "provenance": result.get("provenance", {}),
        }
    finally:
        os.unlink(tmp.name)


# Map deliverable names to AnalysisRun field names
DELIVERABLE_FIELD_MAP = {
    "RGB_PRE_FIRE": "scientific_rgb_pre_fire_url",
    "RGB_POST_FIRE": "scientific_rgb_post_fire_url",
    "DNDVI": "scientific_dndvi_url",
    "DNBR": "scientific_dnbr_url",
    "RBR": "scientific_rbr_url",
}

# Map deliverable names to AnalysisRun task ID field names
DELIVERABLE_TASK_FIELD_MAP = {
    "RGB_PRE_FIRE": "scientific_rgb_pre_fire_task_id",
    "RGB_POST_FIRE": "scientific_rgb_post_fire_task_id",
    "DNDVI": "scientific_dndvi_task_id",
    "DNBR": "scientific_dnbr_task_id",
    "RBR": "scientific_rbr_task_id",
}

# Map deliverable names to AnalysisRun error field names
DELIVERABLE_ERROR_FIELD_MAP = {
    "RGB_PRE_FIRE": "scientific_rgb_pre_fire_error",
    "RGB_POST_FIRE": "scientific_rgb_post_fire_error",
    "DNDVI": "scientific_dndvi_error",
    "DNBR": "scientific_dnbr_error",
    "RBR": "scientific_rbr_error",
}

GEE_PENDING_STATES = {"READY", "RUNNING"}


@shared_task
def process_scientific_deliverable(
    *,
    pre_fire_date: str,
    post_fire_date: str,
    polygon_path: str,
    deliverable_name: str,
    email: str,
    reserve_name: str,
    analysis_run_id: int | None = None,
    user_id: int | None = None,
) -> str:
    """
    Kick off a single scientific deliverable export in the background.

    Args:
        pre_fire_date (str): Pre-fire date in YYYY-MM-DD format.
        post_fire_date (str): Post-fire date in YYYY-MM-DD format.
        polygon_path (str): Path to the polygon file.
        deliverable_name (str): Name of the deliverable to process.
        email (str): Email address to notify when done.
        reserve_name (str): Name of the ecological reserve.
        analysis_run_id (int | None): ID of the AnalysisRun to update with the URL.
        user_id (int | None): ID of the requesting user (for notifications).
    Returns:
        str: Final status of the task ("COMPLETED", "FAILED", etc.)
    """
    try:
        deliverable = Deliverable[deliverable_name]
    except KeyError as exc:
        raise ValueError(f"Invalid deliverable '{deliverable_name}'") from exc

    POLL_INTERVAL_SECONDS = 15

    def wait_for_task(gee_task_id: str):
        while True:
            statuses = ee.data.getTaskStatus(gee_task_id)

            if not statuses:
                raise RuntimeError(f"Task {gee_task_id} not found")

            status = statuses[0]
            state = status["state"]

            logger.info("[GEE] task=%s state=%s", gee_task_id, state)

            if state == "COMPLETED":
                return state

            if state not in GEE_PENDING_STATES:
                error_msg = status.get("error_message", "Unknown error")
                logger.exception(
                    "GEE task %s ended with state '%s': %s",
                    gee_task_id,
                    state,
                    error_msg,
                )
                raise RuntimeError(f"GEE task {state}: {error_msg}")

            time.sleep(POLL_INTERVAL_SECONDS)

    deliverable_key = deliverable.name

    # Read advanced settings from the AnalysisRun if available
    advanced_kwargs = {}
    if analysis_run_id:
        try:
            run = AnalysisRun.objects.get(id=analysis_run_id)
            advanced_kwargs = {
                "roi_only": run.roi_only,
                "cloud_threshold": run.cloud_threshold,
                "days_before_after": run.days_before_after,
                "pre_fire_mosaic_strategy": run.pre_fire_mosaic_strategy,
                "post_fire_mosaic_strategy": run.post_fire_mosaic_strategy,
                "roi_only_bg_color": run.roi_only_bg_color,
            }
        except AnalysisRun.DoesNotExist:
            pass

    # Download polygon from GCS to a temp file for PostFireAssessment
    geojson_content = download_polygon(polygon_path)
    tmp = tempfile.NamedTemporaryFile(suffix=".geojson", delete=False)
    try:
        tmp.write(geojson_content.encode("utf-8"))
        tmp.close()

        runner = PostFireAssessment(
            get_gee_private_key_json(),
            tmp.name,
            pre_fire_date,
            post_fire_date,
            deliverables=[deliverable],
            gcs_bucket=settings.GCS_BUCKET_NAME,
            verbose=False,
            **advanced_kwargs,
        )

        result = runner.run()

        result_wait = wait_for_task(
            result["scientific"][deliverable_key]["gee_task_id"]
        )

        if result_wait == "COMPLETED":
            deliverable_url = result["scientific"][deliverable_key]["url"]

            # Save the deliverable URL and clear the task ID on the AnalysisRun
            if analysis_run_id:
                field_name = DELIVERABLE_FIELD_MAP.get(deliverable_key)
                task_field = DELIVERABLE_TASK_FIELD_MAP.get(deliverable_key)
                updates = {}
                if field_name:
                    updates[field_name] = deliverable_url
                if task_field:
                    updates[task_field] = None
                if updates:
                    try:
                        AnalysisRun.objects.filter(id=analysis_run_id).update(**updates)
                    except Exception:
                        logger.warning(
                            "Failed to update AnalysisRun %s with %s URL",
                            analysis_run_id,
                            deliverable_key,
                        )

            # Create in-app notification
            if analysis_run_id and user_id:
                try:
                    User = get_user_model()
                    user = User.objects.filter(id=user_id).first()
                    if user:
                        run = (
                            AnalysisRun.objects.filter(id=analysis_run_id)
                            .select_related("area_of_interest")
                            .first()
                        )
                        area_name = run.area_of_interest.name if run else "Unknown"
                        notification_message = (
                            f"Scientific {deliverable_key} deliverable "
                            f"for {area_name} is ready to download."
                        )
                        Notification.objects.create(
                            user=user,
                            analysis_run_id=analysis_run_id,
                            notification_type="deliverable_ready",
                            deliverable_name=deliverable_key,
                            message=notification_message,
                        )
                except Exception:
                    logger.warning(
                        "Failed to create notification for user %s, " "analysis %s",
                        email,
                        analysis_run_id,
                    )

            # Get user's language preference, default to English
            language = "en"
            try:
                lookup = {"user_id": user_id} if user_id else {"user__email": email}
                profile = UserProfile.objects.filter(**lookup).first()
                if profile and profile.default_language:
                    language = profile.default_language
            except Exception:
                pass  # Fall back to English on any error

            subject = get_email_translation(language, "email.subject")
            body = get_email_translation(language, "email.body").format(
                reserve_name=reserve_name,
                url=deliverable_url,
            )

            send_mail(
                subject=subject,
                message=body,
                from_email=None,
                recipient_list=[email],
            )

            if user_id:
                invalidate_dashboard_cache(user_id)

        return result_wait
    except Exception as exc:
        # Persist the error on the AnalysisRun so the UI can show it
        if analysis_run_id:
            error_field = DELIVERABLE_ERROR_FIELD_MAP.get(deliverable_key)
            task_field = DELIVERABLE_TASK_FIELD_MAP.get(deliverable_key)
            updates = {}
            if error_field:
                updates[error_field] = str(exc)[:500]
            if task_field:
                updates[task_field] = None
            if updates:
                try:
                    AnalysisRun.objects.filter(id=analysis_run_id).update(**updates)
                except Exception:
                    logger.warning(
                        "Failed to persist error for AnalysisRun %s, " "deliverable %s",
                        analysis_run_id,
                        deliverable_key,
                    )
        raise
    finally:
        os.unlink(tmp.name)


@shared_task
def cleanup_stale_deliverables():
    """
    Periodic task that detects scientific deliverables whose Celery tasks
    are no longer running and marks them as failed.

    Runs every 30 minutes via Celery Beat.
    """
    cutoff = now() - timedelta(minutes=30)

    stale_runs = AnalysisRun.objects.filter(
        status="completed",
        completed_at__lt=cutoff,
    ).filter(
        Q(scientific_rgb_pre_fire_task_id__isnull=False)
        | Q(scientific_rgb_post_fire_task_id__isnull=False)
        | Q(scientific_dndvi_task_id__isnull=False)
        | Q(scientific_dnbr_task_id__isnull=False)
        | Q(scientific_rbr_task_id__isnull=False)
    )

    for run in stale_runs:
        updates = {}
        for deliverable_key, task_field in DELIVERABLE_TASK_FIELD_MAP.items():
            task_id = getattr(run, task_field)
            if not task_id:
                continue

            result = AsyncResult(task_id)
            state = result.state

            if state == "FAILURE":
                error_field = DELIVERABLE_ERROR_FIELD_MAP[deliverable_key]
                error_msg = str(result.result) if result.result else "Task failed"
                updates[error_field] = error_msg[:500]
                updates[task_field] = None
            elif state == "PENDING":
                # PENDING means the task is not in Celery at all (container
                # killed, Redis flushed, result expired, etc.)
                error_field = DELIVERABLE_ERROR_FIELD_MAP[deliverable_key]
                updates[error_field] = "Task is no longer running"
                updates[task_field] = None
            # STARTED / RETRY → still running, leave alone

        if updates:
            try:
                AnalysisRun.objects.filter(id=run.id).update(**updates)
            except Exception:
                logger.warning(
                    "Failed to clean up stale deliverables for AnalysisRun %s",
                    run.id,
                )


def get_gee_private_key_json() -> str:
    """
    Reads the GEE service-account JSON from the file configured by
    ``GEE_PRIVATE_KEY_FILE`` and returns its raw content.

    Returns:
        str: Chave privada do GEE em formato JSON
    """
    key_file = os.environ.get("GEE_PRIVATE_KEY_FILE")
    if not key_file:
        raise ValueError("GEE_PRIVATE_KEY_FILE environment variable is not set")
    with open(key_file, encoding="utf-8") as file_handle:
        return file_handle.read()
