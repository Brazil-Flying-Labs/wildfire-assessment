"""
Reshape AIProvider into a singleton configuration model.

1. Delete all existing rows
2. Remove old columns (name, is_active, created_at)
3. Add new column (provider)
4. Seed one default row
"""

from django.db import migrations, models


def clear_data(apps, schema_editor):
    """Delete all rows using the OLD schema (before field changes)."""
    AIProvider = apps.get_model("wildfire_assessment", "AIProvider")
    AIProvider.objects.all().delete()


def seed_default(apps, schema_editor):
    """Seed the singleton row using the NEW schema (after field changes)."""
    AIProvider = apps.get_model("wildfire_assessment", "AIProvider")
    AIProvider.objects.create(
        pk=1, provider="gemini", model_name="gemini-2.0-flash-lite"
    )


class Migration(migrations.Migration):

    dependencies = [
        ("wildfire_assessment", "0022_aiprovider"),
    ]

    operations = [
        # 1. Wipe existing data (uses OLD schema)
        migrations.RunPython(clear_data, migrations.RunPython.noop),
        # 2. Remove old fields
        migrations.RemoveField(model_name="aiprovider", name="name"),
        migrations.RemoveField(model_name="aiprovider", name="is_active"),
        migrations.RemoveField(model_name="aiprovider", name="created_at"),
        # 3. Add new provider field
        migrations.AddField(
            model_name="aiprovider",
            name="provider",
            field=models.CharField(
                choices=[("gemini", "Google Gemini"), ("openai", "OpenAI")],
                default="gemini",
                max_length=20,
            ),
        ),
        # 4. Update meta
        migrations.AlterModelOptions(
            name="aiprovider",
            options={
                "verbose_name": "AI Provider Configuration",
                "verbose_name_plural": "AI Provider Configuration",
            },
        ),
        # 5. Update model_name field default
        migrations.AlterField(
            model_name="aiprovider",
            name="model_name",
            field=models.CharField(
                default="gemini-2.0-flash-lite",
                help_text="Model identifier, e.g. gemini-2.0-flash-lite or gpt-4o-mini",
                max_length=100,
            ),
        ),
        # 6. Seed default row (uses NEW schema with 'provider' field)
        migrations.RunPython(seed_default, migrations.RunPython.noop),
    ]
