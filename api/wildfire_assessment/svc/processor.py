import json
import logging
import os
import tempfile
import time

import ee
from celery import shared_task
from django.contrib.auth import get_user_model
from dotenv import load_dotenv
from wildfire_analyser.fire_assessment.deliverables import Deliverable
from wildfire_analyser.fire_assessment.post_fire_assessment import PostFireAssessment
from wildfire_assessment.models import AnalysisRun, Notification, UserProfile
from wildfire_assessment.svc.aws import (
    download_polygon_from_s3,
    get_aws_secret_manager_secret,
)
from wildfire_assessment.translations import get_email_translation
from wildfire_assessment.utils import send_gmail_email

logger = logging.getLogger(__name__)
load_dotenv()

ENV = os.environ.get("ENV", "local")


def process_fire_assessment(
    pre_fire_date: str,
    post_fire_date: str,
    polygon_path: str,
) -> dict:
    """
    Process a full fire assessment with all deliverables.

    Args:
        pre_fire_date (str): Pre-fire date in YYYY-MM-DD format.
        post_fire_date (str): Post-fire date in YYYY-MM-DD format.
        polygon_path (str): Path to the polygon file.

    Returns:
        dict: A dictionary with URLs to the generated deliverables and area statistics.
    """
    # Download polygon from S3 to a temp file for PostFireAssessment
    geojson_content = download_polygon_from_s3(polygon_path)
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
        )

        result = runner.run()

        return {
            "severity_map": json.dumps(result["statistics"]["DNBR_AREA_STATISTICS"]),
            "rgb_pre_fire_visual_jpg": result["visual"]["RGB_PRE_FIRE_VISUAL"]["url"],
            "rgb_post_fire_visual_jpg": result["visual"]["RGB_POST_FIRE_VISUAL"]["url"],
            "dndvi_visual_jpg": result["visual"]["DNDVI_VISUAL"]["url"],
            "dnbr_visual_jpg": result["visual"]["DNBR_VISUAL"]["url"],
            "rbr_visual_jpg": result["visual"]["RBR_VISUAL"]["url"],
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

            print(f"[GEE] task={gee_task_id} state={state}")

            if state == "COMPLETED":
                return state

            if state in ("FAILED", "CANCELLED"):
                error = status.get("error_message", "Unknown error")
                raise RuntimeError(f"Task failed: {error}")

            time.sleep(POLL_INTERVAL_SECONDS)

    # Download polygon from S3 to a temp file for PostFireAssessment
    geojson_content = download_polygon_from_s3(polygon_path)
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
            gcs_bucket="wildfire-analyser-outputs",
            verbose=False,
        )

        result = runner.run()

        deliverable_key = deliverable.name

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
                        Notification.objects.create(
                            user=user,
                            analysis_run_id=analysis_run_id,
                            notification_type="deliverable_ready",
                            deliverable_name=deliverable_key,
                            message=(
                                f"Scientific {deliverable_key} deliverable "
                                f"for {area_name} is ready to download."
                            ),
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

            send_gmail_email(
                username="Brazil@flyinglabs.org",
                password=json.loads(get_aws_secret_manager_secret(ENV))["GMAIL_PWD"],
                to_address=email,
                subject=subject,
                body=body,
            )

        return result_wait
    finally:
        os.unlink(tmp.name)


def get_gee_private_key_json() -> str:
    """
    Recovers the GEE private key JSON from AWS Secrets Manager and formats it properly.

    Returns:
        str: Chave privada do GEE em formato JSON
    """
    secret = json.loads(get_aws_secret_manager_secret(ENV))

    GEE_PRIVATE_KEY_JSON = secret["GEE_PRIVATE_KEY_JSON"]

    if isinstance(GEE_PRIVATE_KEY_JSON, str):
        if GEE_PRIVATE_KEY_JSON.startswith("'") and GEE_PRIVATE_KEY_JSON.endswith("'"):
            GEE_PRIVATE_KEY_JSON = GEE_PRIVATE_KEY_JSON[1:-1]
        GEE_PRIVATE_KEY_JSON = GEE_PRIVATE_KEY_JSON.replace('\\"', '"').replace(
            "\\\\", "\\"
        )

        # When stored as a nested JSON string in Secrets Manager, literal
        # control characters (e.g. newlines in the RSA private key) survive
        # the outer json.loads() but break the downstream json.loads() that
        # parses the GEE service-account JSON.  Re-parse leniently and
        # re-serialize so every control character is properly escaped.
        try:
            json.loads(GEE_PRIVATE_KEY_JSON)
        except json.JSONDecodeError:
            GEE_PRIVATE_KEY_JSON = json.dumps(
                json.loads(GEE_PRIVATE_KEY_JSON, strict=False)
            )

    return GEE_PRIVATE_KEY_JSON
