from collections import defaultdict
from decimal import Decimal

from django.db.models import Count
from django.utils import timezone
from wildfire_assessment.models import AnalysisRun

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


def _sum_severity_totals(analyses_qs, severity_key):
    """Sum a severity_data value across all runs in the queryset."""
    total = Decimal(0)
    found = False
    for run in analyses_qs.filter(severity_data__isnull=False):
        data = run.severity_data
        if isinstance(data, dict):
            val = data.get(severity_key, {}).get("area_ha")
            if val is not None:
                total += Decimal(str(val))
                found = True
    return total if found else None


def _aggregate_severity_breakdown(analyses_qs):
    """Sum area_ha per severity class across all runs."""
    totals = {k: Decimal(0) for k in SEVERITY_KEYS}
    found = False
    for run in analyses_qs.filter(severity_data__isnull=False):
        data = run.severity_data
        if not isinstance(data, dict):
            continue
        for key in SEVERITY_KEYS:
            val = data.get(key, {}).get("area_ha")
            if val is not None:
                totals[key] += Decimal(str(val))
                found = True
    if not found:
        return []
    return [{"label": k, "area_ha": totals[k]} for k in SEVERITY_KEYS]


def _area_comparison(analyses_qs):
    """Total burned ha per area of interest, sorted descending."""
    area_burned = defaultdict(
        lambda: {"area_name": "", "total_burned_ha": Decimal(0)}
    )
    for run in analyses_qs.filter(
        severity_data__isnull=False
    ).select_related("area_of_interest"):
        data = run.severity_data
        if not isinstance(data, dict):
            continue
        burned = data.get("Total Burned Area", {}).get("area_ha")
        if burned is not None:
            aoi_id = run.area_of_interest_id
            area_burned[aoi_id]["area_name"] = run.area_of_interest.name
            area_burned[aoi_id]["total_burned_ha"] += Decimal(str(burned))
    return sorted(
        area_burned.values(),
        key=lambda x: x["total_burned_ha"],
        reverse=True,
    )


def _average_burn_severity(analyses_qs):
    """Weighted average severity across all runs."""
    weighted_sum = Decimal(0)
    total_area = Decimal(0)
    for run in analyses_qs.filter(severity_data__isnull=False):
        data = run.severity_data
        if not isinstance(data, dict):
            continue
        for key, weight in SEVERITY_WEIGHTS.items():
            val = data.get(key, {}).get("area_ha")
            if val is not None:
                area = Decimal(str(val))
                weighted_sum += Decimal(str(weight)) * area
                total_area += area
    if total_area == 0:
        return None
    return (weighted_sum / total_area).quantize(Decimal("0.01"))


def _most_analyzed_area(analyses_qs):
    """Area of interest with the most runs."""
    result = (
        analyses_qs.values("area_of_interest__name")
        .annotate(run_count=Count("id"))
        .order_by("-run_count")
        .first()
    )
    if not result:
        return None
    return {
        "area_name": result["area_of_interest__name"],
        "run_count": result["run_count"],
    }


def _largest_fire(analyses_qs):
    """Single run with the highest Total Burned Area."""
    max_burned = None
    max_area_name = None
    for run in analyses_qs.filter(
        severity_data__isnull=False
    ).select_related("area_of_interest"):
        data = run.severity_data
        if not isinstance(data, dict):
            continue
        burned = data.get("Total Burned Area", {}).get("area_ha")
        if burned is not None:
            burned_dec = Decimal(str(burned))
            if max_burned is None or burned_dec > max_burned:
                max_burned = burned_dec
                max_area_name = run.area_of_interest.name
    if max_burned is None:
        return None
    return {"area_name": max_area_name, "burned_ha": max_burned}


def _severity_trend(analyses_qs):
    """Weighted average severity per month, sorted chronologically."""
    monthly = defaultdict(lambda: {"weighted_sum": Decimal(0), "total_area": Decimal(0)})
    for run in analyses_qs.filter(severity_data__isnull=False):
        data = run.severity_data
        if not isinstance(data, dict):
            continue
        month_key = run.created_at.strftime("%Y-%m") if run.created_at else None
        if not month_key:
            continue
        for key, weight in SEVERITY_WEIGHTS.items():
            val = data.get(key, {}).get("area_ha")
            if val is not None:
                area = Decimal(str(val))
                monthly[month_key]["weighted_sum"] += Decimal(str(weight)) * area
                monthly[month_key]["total_area"] += area
    result = []
    for month_key in sorted(monthly.keys()):
        entry = monthly[month_key]
        if entry["total_area"] > 0:
            avg = float(
                (entry["weighted_sum"] / entry["total_area"]).quantize(Decimal("0.01"))
            )
            result.append({"month": month_key, "avg_severity": avg})
    return result


def _areas_geo(analyses_qs):
    """Aggregate geo data for all areas with analyses."""
    area_data = {}
    for run in analyses_qs.filter(
        severity_data__isnull=False
    ).select_related("area_of_interest"):
        aoi = run.area_of_interest
        if aoi.centroid_lat is None or aoi.centroid_lng is None:
            continue
        if aoi.id not in area_data:
            area_data[aoi.id] = {
                "id": aoi.id,
                "name": aoi.name,
                "lat": float(aoi.centroid_lat),
                "lng": float(aoi.centroid_lng),
                "total_burned_ha": Decimal(0),
                "last_analysis_date": None,
                "run_count": 0,
            }
        entry = area_data[aoi.id]
        burned = run.severity_data.get("Total Burned Area", {}).get("area_ha")
        if burned is not None:
            entry["total_burned_ha"] += Decimal(str(burned))
        entry["run_count"] += 1
        run_date = str(run.created_at.date()) if run.created_at else None
        if run_date and (
            entry["last_analysis_date"] is None
            or run_date > entry["last_analysis_date"]
        ):
            entry["last_analysis_date"] = run_date
    for entry in area_data.values():
        entry["total_burned_ha"] = float(entry["total_burned_ha"])
    return list(area_data.values())


def get_dashboard_stats(user):
    """Compute dashboard statistics for the authenticated user."""
    user_analyses = AnalysisRun.objects.filter(user=user)

    now = timezone.now()
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    total_analyses = user_analyses.count()
    total_areas = user_analyses.values("area_of_interest").distinct().count()

    total_analyzed_ha = _sum_severity_totals(user_analyses, "Total Area")
    total_burned_ha = _sum_severity_totals(
        user_analyses, "Total Burned Area"
    )
    analyses_this_month = user_analyses.filter(
        created_at__gte=month_start
    ).count()

    recent_analyses = user_analyses.select_related(
        "area_of_interest", "area_of_interest__country", "user"
    )[:10]

    return {
        "total_analyses": total_analyses,
        "total_areas": total_areas,
        "total_analyzed_ha": total_analyzed_ha,
        "total_burned_ha": total_burned_ha,
        "analyses_this_month": analyses_this_month,
        "recent_analyses": recent_analyses,
        "severity_breakdown": _aggregate_severity_breakdown(user_analyses),
        "area_comparison": _area_comparison(user_analyses),
        "average_burn_severity": _average_burn_severity(user_analyses),
        "most_analyzed_area": _most_analyzed_area(user_analyses),
        "largest_fire": _largest_fire(user_analyses),
        "areas_geo": _areas_geo(user_analyses),
        "severity_trend": _severity_trend(user_analyses),
    }
