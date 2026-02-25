from django.db.models import Count, Max, Min, Sum
from django.db.models.functions import TruncDate, TruncMonth
from django.utils import timezone
from wildfire_assessment.models import AnalysisRun


def get_analytics_summary():
    """Return high-level summary statistics for all analyses."""
    now = timezone.now()
    qs = AnalysisRun.objects.all()
    return {
        "total_analyses": qs.count(),
        "total_users": qs.values("user").distinct().count(),
        "total_burned_ha": qs.aggregate(total=Sum("total_burned_ha"))["total"],
        "total_areas_analyzed": qs.values("area_of_interest").distinct().count(),
        "analyses_this_month": qs.filter(
            created_at__year=now.year, created_at__month=now.month
        ).count(),
    }


def get_user_stats():
    """Return per-user analysis statistics."""
    return list(
        AnalysisRun.objects.values("user__email", "user__first_name", "user__last_name")
        .annotate(
            analysis_count=Count("id"),
            total_burned_ha=Sum("total_burned_ha"),
            areas_analyzed=Count("area_of_interest", distinct=True),
            last_analysis_date=Max("created_at"),
            first_analysis_date=Min("created_at"),
        )
        .order_by("-analysis_count")
    )


def get_monthly_stats():
    """Return analysis counts and burned area grouped by month and user (last 12 months)."""
    twelve_months_ago = timezone.now() - timezone.timedelta(days=365)
    return list(
        AnalysisRun.objects.filter(created_at__gte=twelve_months_ago)
        .annotate(month=TruncMonth("created_at"))
        .values("month", "user__email")
        .annotate(
            analysis_count=Count("id"),
            total_burned_ha=Sum("total_burned_ha"),
        )
        .order_by("-month", "user__email")
    )


def get_top_areas(limit=10):
    """Return areas of interest grouped by user, ordered by user then analysis count."""
    return list(
        AnalysisRun.objects.values(
            "user__email", "area_of_interest__name", "area_of_interest__country__name"
        )
        .annotate(
            analysis_count=Count("id"),
            total_burned_ha=Sum("total_burned_ha"),
            last_analyzed=Max("created_at"),
        )
        .order_by("user__email", "-analysis_count")[:limit]
    )


def get_daily_run_counts(days=90):
    """Return analysis counts per day for the last N days."""
    cutoff = timezone.now() - timezone.timedelta(days=days)
    return list(
        AnalysisRun.objects.filter(created_at__gte=cutoff)
        .annotate(day=TruncDate("created_at"))
        .values("day")
        .annotate(count=Count("id"))
        .order_by("day")
    )


def get_user_analysis_counts(start_date=None, end_date=None):
    """Return per-user analysis counts within an optional date range."""
    qs = AnalysisRun.objects.all()
    if start_date:
        qs = qs.filter(created_at__date__gte=start_date)
    if end_date:
        qs = qs.filter(created_at__date__lte=end_date)
    return list(
        qs.values("user__first_name", "user__last_name", "user__email")
        .annotate(analysis_count=Count("id"))
        .order_by("-analysis_count")
    )


def get_recent_analyses(limit=20):
    """Return the most recent analysis runs."""
    return list(
        AnalysisRun.objects.select_related(
            "user", "area_of_interest", "area_of_interest__country"
        )
        .order_by("-created_at")
        .values(
            "user__email",
            "area_of_interest__name",
            "area_of_interest__country__name",
            "pre_fire_date",
            "post_fire_date",
            "total_burned_ha",
            "status",
            "created_at",
        )[:limit]
    )
