from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("wildfire_assessment", "0014_rename_ecologicalreserve_to_areaofinterest"),
    ]

    operations = [
        migrations.AddField(
            model_name="areaofinterest",
            name="centroid_lat",
            field=models.DecimalField(
                blank=True, decimal_places=7, max_digits=10, null=True
            ),
        ),
        migrations.AddField(
            model_name="areaofinterest",
            name="centroid_lng",
            field=models.DecimalField(
                blank=True, decimal_places=7, max_digits=10, null=True
            ),
        ),
    ]
