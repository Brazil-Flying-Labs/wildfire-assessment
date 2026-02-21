"""Backfill dashboard_widgets for users who never customised their layout.

Before this migration the frontend default included 9 widgets (the 5 stats +
3 insights + recent_analyses table).  We are now making the 3 insight widgets
optional, so users who relied on the NULL → frontend-default fallback would
suddenly lose them.  This migration explicitly stores the previous 9-widget
default for every profile that still has dashboard_widgets = NULL.
"""

from django.db import migrations

PREVIOUS_DEFAULT = [
    "total_areas",
    "total_analyses",
    "total_analyzed_ha",
    "total_burned_ha",
    "analyses_this_month",
    "avg_severity",
    "most_analyzed",
    "largest_fire",
    "recent_analyses",
]


def backfill_widgets(apps, schema_editor):
    UserProfile = apps.get_model("wildfire_assessment", "UserProfile")
    updated = UserProfile.objects.filter(dashboard_widgets__isnull=True).update(
        dashboard_widgets=PREVIOUS_DEFAULT,
    )
    if updated:
        print(f"  Backfilled dashboard_widgets for {updated} profile(s)")


def reverse_backfill(apps, schema_editor):
    UserProfile = apps.get_model("wildfire_assessment", "UserProfile")
    UserProfile.objects.filter(dashboard_widgets=PREVIOUS_DEFAULT).update(
        dashboard_widgets=None,
    )


class Migration(migrations.Migration):

    dependencies = [
        ("wildfire_assessment", "0016_backfill_centroids"),
    ]

    operations = [
        migrations.RunPython(backfill_widgets, reverse_backfill),
    ]
