# Generated manually for dashboard query optimization

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("wildfire_assessment", "0026_add_expo_push_token"),
    ]

    operations = [
        migrations.AddIndex(
            model_name="analysisrun",
            index=models.Index(
                fields=["user", "severity_data"],
                name="analysisrun_user_severity",
            ),
        ),
        migrations.AddIndex(
            model_name="analysisrun",
            index=models.Index(
                fields=["user", "created_at"],
                name="analysisrun_user_created",
            ),
        ),
        migrations.AddIndex(
            model_name="analysisrun",
            index=models.Index(
                fields=["user", "severity_data", "created_at"],
                name="analysisrun_user_sev_created",
            ),
        ),
    ]
