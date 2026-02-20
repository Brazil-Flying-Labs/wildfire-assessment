# Generated manually

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('wildfire_assessment', '0005_add_user_profile'),
    ]

    operations = [
        migrations.AddField(
            model_name='userprofile',
            name='theme',
            field=models.CharField(
                choices=[('light', 'Light'), ('dark', 'Dark')],
                default='light',
                max_length=10,
            ),
        ),
    ]
