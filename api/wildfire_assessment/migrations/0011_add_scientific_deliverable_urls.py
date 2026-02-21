from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("wildfire_assessment", "0010_remove_analysisrun_dnbr_url_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="analysisrun",
            name="scientific_rgb_pre_fire_url",
            field=models.URLField(blank=True, max_length=500, null=True),
        ),
        migrations.AddField(
            model_name="analysisrun",
            name="scientific_rgb_post_fire_url",
            field=models.URLField(blank=True, max_length=500, null=True),
        ),
        migrations.AddField(
            model_name="analysisrun",
            name="scientific_dndvi_url",
            field=models.URLField(blank=True, max_length=500, null=True),
        ),
        migrations.AddField(
            model_name="analysisrun",
            name="scientific_dnbr_url",
            field=models.URLField(blank=True, max_length=500, null=True),
        ),
        migrations.AddField(
            model_name="analysisrun",
            name="scientific_rbr_url",
            field=models.URLField(blank=True, max_length=500, null=True),
        ),
    ]
