from decimal import Decimal

from django.utils import timezone
from wildfire_assessment.models import AnalysisRun


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


def get_dashboard_stats(user):
    """Compute dashboard statistics for the authenticated user."""
    user_analyses = AnalysisRun.objects.filter(user=user)

    now = timezone.now()
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    total_analyses = user_analyses.count()
    total_areas = user_analyses.values("area_of_interest").count()

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
    }
