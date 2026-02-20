from django.db.models import Sum
from django.utils import timezone
from wildfire_assessment.models import AnalysisRun, AreaOfInterest
from wildfire_assessment.svc.area_of_interest import get_user_country_ids


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

    analyzed_area_ids = accessible_analyses.values_list(
        "area_of_interest_id", flat=True
    ).distinct()
    total_analyzed_ha = accessible_areas.filter(id__in=analyzed_area_ids).aggregate(
        total=Sum("area_ha")
    )["total"]

    total_burned_ha = accessible_analyses.aggregate(total=Sum("total_burned_ha"))[
        "total"
    ]
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
