"""Set DeepSeek as the active AI provider for fresh installations."""

from django.db import migrations


def enable_deepseek(apps, schema_editor):
    AIProvider = apps.get_model("wildfire_assessment", "AIProvider")
    AIProvider.objects.filter(provider="gemini").update(
        provider="deepseek", model_name="deepseek-chat"
    )


class Migration(migrations.Migration):

    dependencies = [
        ("wildfire_assessment", "0002_alter_aiprovider_model_name_and_more"),
    ]

    operations = [
        migrations.RunPython(enable_deepseek, migrations.RunPython.noop),
    ]
