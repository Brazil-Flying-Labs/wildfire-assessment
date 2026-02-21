# Generated manually

from django.db import migrations


def set_dark_theme(apps, schema_editor):
    """Update all existing user profiles to use dark theme."""
    UserProfile = apps.get_model("wildfire_assessment", "UserProfile")
    UserProfile.objects.filter(theme="light").update(theme="dark")


def revert_to_light_theme(apps, schema_editor):
    """Revert all dark theme profiles back to light."""
    UserProfile = apps.get_model("wildfire_assessment", "UserProfile")
    UserProfile.objects.filter(theme="dark").update(theme="light")


class Migration(migrations.Migration):

    dependencies = [
        ("wildfire_assessment", "0018_remove_optional_widgets_from_all_profiles"),
    ]

    operations = [
        migrations.RunPython(set_dark_theme, revert_to_light_theme),
    ]
