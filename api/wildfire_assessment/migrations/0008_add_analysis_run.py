# Generated manually
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('wildfire_assessment', '0007_add_unaccent_extension'),
    ]

    operations = [
        migrations.CreateModel(
            name='AnalysisRun',
            fields=[
                ('id', models.AutoField(primary_key=True, serialize=False)),
                ('pre_fire_date', models.DateField()),
                ('post_fire_date', models.DateField()),
                ('status', models.CharField(
                    choices=[
                        ('pending', 'Pending'),
                        ('running', 'Running'),
                        ('completed', 'Completed'),
                        ('failed', 'Failed'),
                    ],
                    default='completed',
                    max_length=20,
                )),
                ('severity_data', models.JSONField(blank=True, null=True)),
                ('total_burned_ha', models.DecimalField(
                    blank=True, decimal_places=3, max_digits=15, null=True
                )),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('completed_at', models.DateTimeField(blank=True, null=True)),
                ('area_of_interest', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='analysis_runs',
                    to='wildfire_assessment.ecologicalreserve',
                )),
                ('user', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='analysis_runs',
                    to=settings.AUTH_USER_MODEL,
                )),
            ],
            options={
                'verbose_name': 'Analysis Run',
                'verbose_name_plural': 'Analysis Runs',
                'ordering': ['-created_at'],
            },
        ),
    ]
