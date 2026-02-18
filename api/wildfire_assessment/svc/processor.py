import json
import logging
import os
import time

import ee
from celery import shared_task
from django.contrib.auth import get_user_model
from dotenv import load_dotenv
from wildfire_analyser.fire_assessment.deliverables import Deliverable
from wildfire_analyser.fire_assessment.post_fire_assessment import PostFireAssessment
from wildfire_assessment.svc.aws import get_aws_secret_manager_secret
from wildfire_assessment.translations import get_email_translation
from wildfire_assessment.utils import send_gmail_email

User = get_user_model()

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
    runner = PostFireAssessment(
        get_gee_private_key_json(),
        polygon_path,
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


@shared_task
def process_scientific_deliverable(
    *,
    pre_fire_date: str,
    post_fire_date: str,
    polygon_path: str,
    deliverable_name: str,
    email: str,
    reserve_name: str,
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

    polygon_path = f"../../polygons/{polygon_path}"

    # Executa a análise para o deliverable específico
    runner = PostFireAssessment(
        get_gee_private_key_json(),
        polygon_path,
        pre_fire_date,
        post_fire_date,
        deliverables=[deliverable],
        gcs_bucket="wildfire-analyser-outputs",
        verbose=False,
    )

    result = runner.run()

    if deliverable == Deliverable.RGB_PRE_FIRE:
        deliverable_key = "RGB_PRE_FIRE"
    elif deliverable == Deliverable.RGB_POST_FIRE:
        deliverable_key = "RGB_POST_FIRE"
    elif deliverable == Deliverable.DNBR:
        deliverable_key = "DNBR"
    elif deliverable == Deliverable.RBR:
        deliverable_key = "RBR"
    elif deliverable == Deliverable.DNDVI:
        deliverable_key = "DNDVI"
    else:
        raise ValueError("Invalid deliverable type")

    result_wait = wait_for_task(result["scientific"][deliverable_key]["gee_task_id"])

    if result_wait == "COMPLETED":
        # Get user's language preference, default to English
        language = "en"
        try:
            user = User.objects.filter(email=email).first()
            if user and hasattr(user, "profile"):
                language = user.profile.default_language or "en"
        except Exception:
            pass  # Fall back to English on any error

        subject = get_email_translation(language, "email.subject")
        body = get_email_translation(language, "email.body").format(
            reserve_name=reserve_name,
            url=result["scientific"][deliverable_key]["url"],
        )

        send_gmail_email(
            username="Brazil@flyinglabs.org",
            password=json.loads(get_aws_secret_manager_secret(ENV))["GMAIL_PWD"],
            to_address=email,
            subject=subject,
            body=body,
        )

    return result_wait


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

    return GEE_PRIVATE_KEY_JSON
