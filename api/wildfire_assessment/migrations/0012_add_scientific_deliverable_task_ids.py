from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("wildfire_assessment", "0011_add_scientific_deliverable_urls"),
    ]

    operations = [
        migrations.AddField(
            model_name="analysisrun",
            name="scientific_rgb_pre_fire_task_id",
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AddField(
            model_name="analysisrun",
            name="scientific_rgb_post_fire_task_id",
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AddField(
            model_name="analysisrun",
            name="scientific_dndvi_task_id",
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AddField(
            model_name="analysisrun",
            name="scientific_dnbr_task_id",
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AddField(
            model_name="analysisrun",
            name="scientific_rbr_task_id",
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
    ]
