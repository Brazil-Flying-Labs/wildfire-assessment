from decimal import Decimal

from django.db.models import Sum
from django.utils import timezone
from wildfire_assessment.models import AnalysisRun, AreaOfInterest
from wildfire_assessment.svc.area_of_interest import get_user_country_ids


def _sum_distinct_severity_totals(analyses_qs, severity_key):
    """Sum a severity_data value across distinct (area, pre_fire_date, post_fire_date) combos.

    For each unique combination, uses the most recent run's severity_data.
    """
    seen = {}
    for run in analyses_qs.filter(severity_data__isnull=False).order_by("-created_at"):
        combo = (run.area_of_interest_id, run.pre_fire_date, run.post_fire_date)
        if combo in seen:
            continue
        data = run.severity_data
        if isinstance(data, dict):
            val = data.get(severity_key, {}).get("area_ha")
            if val is not None:
                seen[combo] = Decimal(str(val))
            else:
                seen[combo] = None
        else:
            seen[combo] = None
    values = [v for v in seen.values() if v is not None]
    return sum(values) if values else None


def get_dashboard_stats(user):
    """Compute dashboard statistics for the authenticated user."""
    country_ids = get_user_country_ids(user)

    accessible_areas = AreaOfInterest.objects.filter(country_id__in=country_ids)
    accessible_analyses = AnalysisRun.objects.filter(
        area_of_interest__country_id__in=country_ids
    )

    now = timezone.now()
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    total_analyses = accessible_analyses.count()
    total_areas = accessible_areas.count()

    total_analyzed_ha = _sum_distinct_severity_totals(
        accessible_analyses, "Total Area"
    )
    total_burned_ha = _sum_distinct_severity_totals(
        accessible_analyses, "Total Burned Area"
    )
    analyses_this_month = accessible_analyses.filter(
        created_at__gte=month_start
    ).count()

    recent_analyses = accessible_analyses.select_related(
        "area_of_interest", "area_of_interest__country", "user"
    )[:10]

    return {
        "total_analyses": total_analyses,
        "total_areas": total_areas,
        "total_analyzed_ha": total_analyzed_ha,
        "total_burned_ha": total_burned_ha,
        "analyses_this_month": analyses_this_month,
        "recent_analyses": recent_analyses,
    }
