# Generated manually

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('wildfire_assessment', '0024_alter_areaofinterest_options_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='userprofile',
            name='cookie_consent',
            field=models.BooleanField(blank=True, default=None, null=True),
        ),
        migrations.AddField(
            model_name='userprofile',
            name='cookie_consent_updated_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
