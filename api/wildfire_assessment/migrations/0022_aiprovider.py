from django.db import migrations, models


def seed_providers(apps, schema_editor):
    AIProvider = apps.get_model("wildfire_assessment", "AIProvider")
    AIProvider.objects.get_or_create(
        name="gemini",
        defaults={"is_active": True, "model_name": "gemini-2.0-flash-lite"},
    )
    AIProvider.objects.get_or_create(
        name="openai",
        defaults={"is_active": False, "model_name": "gpt-4o-mini"},
    )


class Migration(migrations.Migration):

    dependencies = [
        ("wildfire_assessment", "0021_notification"),
    ]

    operations = [
        migrations.CreateModel(
            name="AIProvider",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "name",
                    models.CharField(
                        choices=[
                            ("gemini", "Google Gemini"),
                            ("openai", "OpenAI"),
                        ],
                        max_length=20,
                        unique=True,
                    ),
                ),
                ("is_active", models.BooleanField(default=False)),
                (
                    "model_name",
                    models.CharField(
                        help_text="Model identifier, e.g. gemini-2.0-flash-lite or gpt-4o-mini",
                        max_length=100,
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "verbose_name": "AI Provider",
                "verbose_name_plural": "AI Providers",
            },
        ),
        migrations.RunPython(seed_providers, migrations.RunPython.noop),
    ]
