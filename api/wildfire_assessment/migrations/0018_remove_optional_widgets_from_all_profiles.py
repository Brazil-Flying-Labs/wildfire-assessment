"""Remove the 3 insight widgets from all user profiles.

These widgets (avg_severity, most_analyzed, largest_fire) are now optional.
This migration strips them from every profile's dashboard_widgets list so all
users start with the new 6-widget default.  Users can re-add them via the "+"
button.
"""

from django.db import migrations

WIDGETS_TO_REMOVE = {"avg_severity", "most_analyzed", "largest_fire"}


def remove_widgets(apps, schema_editor):
    UserProfile = apps.get_model("wildfire_assessment", "UserProfile")
    profiles = UserProfile.objects.filter(dashboard_widgets__isnull=False)
    updated = 0
    for profile in profiles:
        original = profile.dashboard_widgets
        if not isinstance(original, list):
            continue
        filtered = [w for w in original if w not in WIDGETS_TO_REMOVE]
        if len(filtered) != len(original):
            profile.dashboard_widgets = filtered if filtered else None
            profile.save(update_fields=["dashboard_widgets"])
            updated += 1
    if updated:
        print(f"  Removed optional widgets from {updated} profile(s)")


def restore_widgets(apps, schema_editor):
    """Re-add the 3 insight widgets before recent_analyses for profiles that lack them."""
    UserProfile = apps.get_model("wildfire_assessment", "UserProfile")
    profiles = UserProfile.objects.filter(dashboard_widgets__isnull=False)
    updated = 0
    for profile in profiles:
        widgets = profile.dashboard_widgets
        if not isinstance(widgets, list):
            continue
        missing = [
            w
            for w in ("avg_severity", "most_analyzed", "largest_fire")
            if w not in widgets
        ]
        if missing:
            # Insert before recent_analyses if present, otherwise append
            try:
                idx = widgets.index("recent_analyses")
            except ValueError:
                idx = len(widgets)
            for w in reversed(missing):
                widgets.insert(idx, w)
            profile.dashboard_widgets = widgets
            profile.save(update_fields=["dashboard_widgets"])
            updated += 1
    if updated:
        print(f"  Restored optional widgets for {updated} profile(s)")


class Migration(migrations.Migration):

    dependencies = [
        ("wildfire_assessment", "0017_backfill_default_dashboard_widgets"),
    ]

    operations = [
        migrations.RunPython(remove_widgets, restore_widgets),
    ]
