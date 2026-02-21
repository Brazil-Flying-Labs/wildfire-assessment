from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("wildfire_assessment", "0012_add_scientific_deliverable_task_ids"),
    ]

    operations = [
        migrations.AddField(
            model_name="userprofile",
            name="dashboard_widgets",
            field=models.JSONField(
                blank=True,
                default=None,
                help_text="Ordered list of visible dashboard widget IDs",
                null=True,
            ),
        ),
    ]
