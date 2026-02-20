# Generated manually
from django.contrib.postgres.operations import UnaccentExtension
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('wildfire_assessment', '0006_userprofile_theme'),
    ]

    operations = [
        UnaccentExtension(),
    ]
