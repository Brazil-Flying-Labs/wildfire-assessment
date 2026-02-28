import json
import logging
from collections import defaultdict
from datetime import timedelta
from decimal import Decimal

from django.core.cache import cache
from django.db.models import Count, Q
from django.utils import timezone
from wildfire_assessment.models import AnalysisRun

logger = logging.getLogger(__name__)

SEVERITY_KEYS = [
    "Unburned",
    "Low Severity",
    "Moderate Severity",
    "High Severity",
    "Very High Severity",
]

SEVERITY_WEIGHTS = {
    "Unburned": 0,
    "Low Severity": 1,
    "Moderate Severity": 2,
    "High Severity": 3,
    "Very High Severity": 4,
}


def _extract_geometry(geojson_data):
    """Extract geometry from a GeoJSON object (Feature, FeatureCollection, or bare geometry)."""
    geojson_type = geojson_data.get("type", "")
    if geojson_type == "FeatureCollection":
        features = geojson_data.get("features", [])
        if features:
            return features[0].get("geometry")
    elif geojson_type == "Feature":
        return geojson_data.get("geometry")
    elif geojson_type in ("Polygon", "MultiPolygon"):
        return geojson_data
    return None


def get_dashboard_stats(user):
    """Compute dashboard statistics for the authenticated user.

    Optimized to use a single pass over analysis runs for all severity-based
    metrics, reducing database queries from 8+ to 1.
    """
    now = timezone.now()
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    trend_cutoff = now - timedelta(days=180)

    # Base queryset for all user analyses
    all_runs_qs = AnalysisRun.objects.filter(user=user)

    # === DB AGGREGATIONS (single query for all counts) ===
    agg = all_runs_qs.aggregate(
        total_analyses=Count("id"),
        total_areas=Count("area_of_interest", distinct=True),
        analyses_this_month=Count("id", filter=Q(created_at__gte=month_start)),
    )
    total_analyses = agg["total_analyses"]
    total_areas = agg["total_areas"]
    analyses_this_month = agg["analyses_this_month"]

    # Most analyzed area (DB aggregation)
    most_analyzed_result = (
        all_runs_qs.values("area_of_interest__name")
        .annotate(run_count=Count("id"))
        .order_by("-run_count")
        .first()
    )
    most_analyzed_area = None
    if most_analyzed_result:
        most_analyzed_area = {
            "area_name": most_analyzed_result["area_of_interest__name"],
            "run_count": most_analyzed_result["run_count"],
        }

    # Recent analyses (for serialization)
    recent_analyses = all_runs_qs.select_related(
        "area_of_interest", "area_of_interest__country", "user"
    )[:10]

    # === SINGLE QUERY for all runs with severity data ===
    runs_with_severity = list(
        all_runs_qs.filter(severity_data__isnull=False)
        .select_related("area_of_interest", "area_of_interest__country")
    )

    # === Initialize accumulators ===
    # For _sum_severity_totals
    total_area_ha = Decimal(0)
    total_burned_ha = Decimal(0)
    found_area = False
    found_burned = False

    # For _aggregate_severity_breakdown
    severity_totals = {key: Decimal(0) for key in SEVERITY_KEYS}
    found_severity = False

    # For _average_burn_severity
    weighted_sum = Decimal(0)
    total_weighted_area = Decimal(0)

    # For _area_comparison
    area_burned = defaultdict(lambda: {"area_name": "", "total_burned_ha": Decimal(0)})

    # For _largest_fire
    max_burned = None
    max_burned_area_name = None

    # For _severity_trend
    trend_data = []

    # For _areas_geo
    areas_geo = {}

    # === SINGLE PASS over all runs ===
    for run in runs_with_severity:
        data = run.severity_data
        if not isinstance(data, dict):
            continue

        aoi = run.area_of_interest
        aoi_id = run.area_of_interest_id

        # --- _sum_severity_totals: Total Area ---
        total_area_val = data.get("Total Area", {}).get("area_ha")
        if total_area_val is not None:
            total_area_ha += Decimal(str(total_area_val))
            found_area = True

        # --- _sum_severity_totals: Total Burned Area ---
        burned_val = data.get("Total Burned Area", {}).get("area_ha")
        if burned_val is not None:
            burned_dec = Decimal(str(burned_val))
            total_burned_ha += burned_dec
            found_burned = True

            # --- _largest_fire ---
            if max_burned is None or burned_dec > max_burned:
                max_burned = burned_dec
                max_burned_area_name = aoi.name

            # --- _area_comparison ---
            area_burned[aoi_id]["area_name"] = aoi.name
            area_burned[aoi_id]["total_burned_ha"] += burned_dec

        # --- _aggregate_severity_breakdown + _average_burn_severity ---
        for key in SEVERITY_KEYS:
            val = data.get(key, {}).get("area_ha")
            if val is not None:
                area = Decimal(str(val))
                severity_totals[key] += area
                found_severity = True
                # For weighted average
                weight = SEVERITY_WEIGHTS[key]
                weighted_sum += Decimal(str(weight)) * area
                total_weighted_area += area

        # --- _severity_trend (last 180 days only) ---
        if run.created_at and run.created_at >= trend_cutoff:
            run_weighted_sum = Decimal(0)
            run_total_area = Decimal(0)
            for key, weight in SEVERITY_WEIGHTS.items():
                val = data.get(key, {}).get("area_ha")
                if val is not None:
                    area = Decimal(str(val))
                    run_weighted_sum += Decimal(str(weight)) * area
                    run_total_area += area
            if run_total_area > 0:
                avg = float(
                    (run_weighted_sum / run_total_area).quantize(Decimal("0.01"))
                )
                trend_data.append({
                    "created_at": run.created_at.isoformat(),
                    "avg_severity": avg,
                })

        # --- _areas_geo ---
        if aoi.centroid_lat is not None and aoi.centroid_lng is not None:
            if aoi_id not in areas_geo:
                areas_geo[aoi_id] = {
                    "id": aoi_id,
                    "name": aoi.name,
                    "lat": float(aoi.centroid_lat),
                    "lng": float(aoi.centroid_lng),
                    "total_burned_ha": Decimal(0),
                    "last_analysis_date": None,
                    "run_count": 0,
                    "geometry": None,
                }

            entry = areas_geo[aoi_id]
            if burned_val is not None:
                entry["total_burned_ha"] += Decimal(str(burned_val))
            entry["run_count"] += 1
            run_date = str(run.created_at.date()) if run.created_at else None
            if run_date and (
                entry["last_analysis_date"] is None
                or run_date > entry["last_analysis_date"]
            ):
                entry["last_analysis_date"] = run_date

    # === POST-PROCESSING ===

    # Sort trend data by date
    trend_data.sort(key=lambda x: x["created_at"])

    # Severity breakdown
    severity_breakdown = []
    if found_severity:
        severity_breakdown = [
            {"label": k, "area_ha": severity_totals[k]} for k in SEVERITY_KEYS
        ]

    # Area comparison (sorted descending)
    area_comparison = sorted(
        area_burned.values(),
        key=lambda x: x["total_burned_ha"],
        reverse=True,
    )

    # Average burn severity
    average_burn_severity = None
    if total_weighted_area > 0:
        average_burn_severity = (weighted_sum / total_weighted_area).quantize(
            Decimal("0.01")
        )

    # Largest fire
    largest_fire = None
    if max_burned is not None:
        largest_fire = {"area_name": max_burned_area_name, "burned_ha": max_burned}

    # NOTE: Geometry download removed - frontend lazy-loads via /area_of_interest/{id}/geojson/
    # This significantly speeds up the dashboard endpoint.

    # Convert Decimal to float for JSON serialization
    for entry in areas_geo.values():
        entry["total_burned_ha"] = float(entry["total_burned_ha"])

    return {
        "total_analyses": total_analyses,
        "total_areas": total_areas,
        "total_analyzed_ha": total_area_ha if found_area else None,
        "total_burned_ha": total_burned_ha if found_burned else None,
        "analyses_this_month": analyses_this_month,
        "recent_analyses": recent_analyses,
        "severity_breakdown": severity_breakdown,
        "area_comparison": area_comparison,
        "average_burn_severity": average_burn_severity,
        "most_analyzed_area": most_analyzed_area,
        "largest_fire": largest_fire,
        "areas_geo": list(areas_geo.values()),
        "severity_trend": trend_data,
    }


def invalidate_dashboard_cache(user_id):
    """Clear the cached dashboard response for a user."""
    cache.delete(f"dashboard_{user_id}")
