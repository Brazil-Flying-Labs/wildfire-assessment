import json
import logging
import uuid

import requests
from django.db import connection
from django.db.models import Q
from django.utils import timezone
from wildfire_assessment.models import (
    AnalysisRun,
    AnalysisRunProvenance,
    AreaOfInterest,
)
from wildfire_assessment.svc.aws import (
    delete_polygon_from_s3,
    download_polygon_from_s3,
    upload_image_to_s3,
)

LOG = logging.getLogger(__name__)


def get_user_country_ids(user):
    """Return a list of country IDs the user is authorized for."""
    return list(user.country_permissions.values_list("country_id", flat=True))


def get_areas_queryset(user, search=None):
    """Return AreaOfInterest queryset filtered by user permissions and optional search."""
    country_ids = get_user_country_ids(user)
    if not country_ids:
        return AreaOfInterest.objects.none()

    queryset = AreaOfInterest.objects.filter(country_id__in=country_ids).order_by(
        "name"
    )

    if search:
        if connection.vendor == "postgresql":  # pragma: no cover
            queryset = queryset.filter(
                Q(name__unaccent__icontains=search)
                | Q(country__name__unaccent__icontains=search)
            )
        else:  # pragma: no cover
            queryset = queryset.filter(
                Q(name__icontains=search) | Q(country__name__icontains=search)
            )

    return queryset


def user_can_access_area(user, area):
    """Check if a user has country-level permission for an area."""
    country_ids = get_user_country_ids(user)
    return area.country_id in country_ids


def delete_polygon_file(polygon_path):
    """Delete a polygon GeoJSON file from S3."""
    if not polygon_path:
        return False

    return delete_polygon_from_s3(polygon_path)


def _download_and_store_image(url, run_id, name):
    """Download an image from a URL and upload it to S3. Returns the S3 key or None."""
    if not url:
        return None
    try:
        resp = requests.get(url, timeout=30)
        resp.raise_for_status()
        key = f"{run_id}/{name}.jpg"
        upload_image_to_s3(key, resp.content)
        return key
    except Exception:
        LOG.warning("Failed to download/store image %s for run %s", name, run_id)
        return None


def save_analysis_run(
    user,
    area,
    pre_fire_date,
    post_fire_date,
    assessment_result,
    roi_only=True,
    cloud_threshold=100,
    days_before_after=30,
    pre_fire_mosaic_strategy="best_available_per_tile_mosaic",
    post_fire_mosaic_strategy="best_available_per_tile_mosaic",
    roi_only_bg_color="black",
):
    """Extract severity data from an assessment result and persist an AnalysisRun."""
    severity_data = None
    total_burned_ha = None

    try:
        severity_map = assessment_result.get("severity_map")
        if severity_map:
            if isinstance(severity_map, str):
                severity_data = json.loads(severity_map)
            else:
                severity_data = severity_map
            if severity_data and "Total Burned Area" in severity_data:
                total_burned_ha = severity_data["Total Burned Area"].get("area_ha")
    except (json.JSONDecodeError, TypeError, KeyError):
        pass

    run_id = uuid.uuid4().hex[:12]

    image_fields = {
        "rgb_pre_fire_image": ("rgb_pre_fire_visual_jpg", "pre_fire_rgb"),
        "rgb_post_fire_image": ("rgb_post_fire_visual_jpg", "post_fire_rgb"),
        "dndvi_image": ("dndvi_visual_jpg", "dndvi"),
        "dnbr_image": ("dnbr_visual_jpg", "dnbr"),
        "rbr_image": ("rbr_visual_jpg", "rbr"),
    }
    image_keys = {}
    for field, (result_key, s3_name) in image_fields.items():
        url = assessment_result.get(result_key)
        image_keys[field] = _download_and_store_image(url, run_id, s3_name)

    run = AnalysisRun.objects.create(
        user=user,
        area_of_interest=area,
        pre_fire_date=pre_fire_date,
        post_fire_date=post_fire_date,
        status="completed",
        severity_data=severity_data,
        total_burned_ha=total_burned_ha,
        roi_only=roi_only,
        cloud_threshold=cloud_threshold,
        days_before_after=days_before_after,
        pre_fire_mosaic_strategy=pre_fire_mosaic_strategy,
        post_fire_mosaic_strategy=post_fire_mosaic_strategy,
        roi_only_bg_color=roi_only_bg_color,
        completed_at=timezone.now(),
        **image_keys,
    )

    # Persist provenance records for both phases
    provenance_data = assessment_result.get("provenance", {})
    records = []
    for phase in ("pre_fire", "post_fire"):
        phase_data = provenance_data.get(phase, {})
        items = phase_data.get("images", []) if isinstance(phase_data, dict) else phase_data
        for item in items:
            try:
                records.append(
                    AnalysisRunProvenance(
                        analysis_run=run,
                        phase=phase,
                        scene_id=item["id"],
                        date=item["date"],
                        spacecraft_name=item.get("spacecraft_name"),
                        cloud_percent=item.get("cloud_percent"),
                    )
                )
            except (KeyError, TypeError, ValueError):
                LOG.warning(
                    "Skipping malformed provenance record for run %s: %r",
                    run.id,
                    item,
                )
    if records:
        AnalysisRunProvenance.objects.bulk_create(records)

    return run


def save_deliverable_task_id(analysis_run_id, task_field, task_id):
    """Persist a Celery task ID on an AnalysisRun for a scientific deliverable."""
    AnalysisRun.objects.filter(id=analysis_run_id).update(**{task_field: task_id})


def get_analysis_runs_queryset(user):
    """Return AnalysisRun queryset filtered by user country permissions."""
    country_ids = get_user_country_ids(user)
    if not country_ids:
        return AnalysisRun.objects.none()

    return (
        AnalysisRun.objects.filter(
            area_of_interest__country_id__in=country_ids
        )
        .prefetch_related("provenance_records")
        .order_by("-created_at")
    )


def validate_deliverable_urls(analysis_run_id):
    """Check GCS deliverable URLs and clear any that are no longer accessible."""
    from wildfire_assessment.svc.processor import DELIVERABLE_FIELD_MAP

    run = AnalysisRun.objects.get(id=analysis_run_id)

    urls_to_check = {}
    for field_name in DELIVERABLE_FIELD_MAP.values():
        url = getattr(run, field_name)
        if url:
            urls_to_check[field_name] = url

    if not urls_to_check:
        return run

    fields_to_clear = {}
    for field_name, url in urls_to_check.items():
        try:
            resp = requests.head(url, timeout=10, allow_redirects=True)
            if resp.status_code >= 400:
                fields_to_clear[field_name] = None
        except requests.RequestException:
            fields_to_clear[field_name] = None

    if fields_to_clear:
        AnalysisRun.objects.filter(id=analysis_run_id).update(**fields_to_clear)
        run.refresh_from_db()

    return run


def get_area_geojson(polygon_path):
    """Download and return GeoJSON data for an area's polygon.

    Returns the parsed GeoJSON object, or None if download fails.
    """
    if not polygon_path:
        return None

    try:
        raw = download_polygon_from_s3(polygon_path)
        return json.loads(raw)
    except Exception:
        LOG.warning("Failed to download polygon: %s", polygon_path)
        return None
