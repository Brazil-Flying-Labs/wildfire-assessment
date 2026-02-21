# Generated manually

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("wildfire_assessment", "0019_set_dark_theme_default"),
    ]

    operations = [
        migrations.AlterField(
            model_name="userprofile",
            name="theme",
            field=models.CharField(
                choices=[("light", "Light"), ("dark", "Dark")],
                default="dark",
                max_length=10,
            ),
        ),
    ]
