# Squashed from 0001..0035: single initial migration for fresh installs.
# RunPython helpers were ported manually from the original migrations.

import json
import logging

import django.contrib.postgres.operations
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models

logger = logging.getLogger(__name__)

PREVIOUS_DEFAULT = [
    "total_areas",
    "total_analyses",
    "total_analyzed_ha",
    "total_burned_ha",
    "analyses_this_month",
    "avg_severity",
    "most_analyzed",
    "largest_fire",
    "recent_analyses",
]

WIDGETS_TO_REMOVE = {"avg_severity", "most_analyzed", "largest_fire"}


def create_brazil_and_assign(apps, schema_editor):
    Country = apps.get_model("wildfire_assessment", "Country")
    EcologicalReserve = apps.get_model("wildfire_assessment", "EcologicalReserve")

    brazil, _ = Country.objects.get_or_create(name="Brazil", code="BR")
    EcologicalReserve.objects.filter(country__isnull=True).update(country=brazil)


def backfill_centroids(apps, schema_editor):
    from shapely.geometry import shape
    from wildfire_assessment.svc.object_storage import download_polygon

    AreaOfInterest = apps.get_model("wildfire_assessment", "AreaOfInterest")
    areas = AreaOfInterest.objects.filter(centroid_lat__isnull=True)
    updated = []
    for area in areas:
        try:
            raw = download_polygon(area.polygon_path)
            geojson = json.loads(raw)
            if geojson.get("type") == "Feature":
                geom = shape(geojson["geometry"])
            elif geojson.get("type") == "FeatureCollection":
                geom = shape(geojson["features"][0]["geometry"])
            else:
                geom = shape(geojson)
            centroid = geom.centroid
            area.centroid_lat = round(centroid.y, 7)
            area.centroid_lng = round(centroid.x, 7)
            updated.append(area)
        except Exception as e:
            logger.warning(
                "Failed to compute centroid for area %s (%s): %s",
                area.id,
                area.name,
                e,
            )
    if updated:
        AreaOfInterest.objects.bulk_update(
            updated, ["centroid_lat", "centroid_lng"], batch_size=100
        )
        logger.info("Backfilled centroids for %d areas", len(updated))


def backfill_widgets(apps, schema_editor):
    UserProfile = apps.get_model("wildfire_assessment", "UserProfile")
    updated = UserProfile.objects.filter(dashboard_widgets__isnull=True).update(
        dashboard_widgets=PREVIOUS_DEFAULT,
    )
    if updated:
        print(f"  Backfilled dashboard_widgets for {updated} profile(s)")


def reverse_backfill(apps, schema_editor):
    UserProfile = apps.get_model("wildfire_assessment", "UserProfile")
    UserProfile.objects.filter(dashboard_widgets=PREVIOUS_DEFAULT).update(
        dashboard_widgets=None,
    )


def remove_widgets(apps, schema_editor):
    UserProfile = apps.get_model("wildfire_assessment", "UserProfile")
    profiles = UserProfile.objects.filter(dashboard_widgets__isnull=False)
    updated = 0
    for profile in profiles:
        original = profile.dashboard_widgets
        if not isinstance(original, list):
            continue
        filtered = [w for w in original if w not in WIDGETS_TO_REMOVE]
        if len(filtered) != len(original):
            profile.dashboard_widgets = filtered if filtered else None
            profile.save(update_fields=["dashboard_widgets"])
            updated += 1
    if updated:
        print(f"  Removed optional widgets from {updated} profile(s)")


def restore_widgets(apps, schema_editor):
    """Re-add the 3 insight widgets before recent_analyses for profiles that lack them."""
    UserProfile = apps.get_model("wildfire_assessment", "UserProfile")
    profiles = UserProfile.objects.filter(dashboard_widgets__isnull=False)
    updated = 0
    for profile in profiles:
        widgets = profile.dashboard_widgets
        if not isinstance(widgets, list):
            continue
        missing = [
            w
            for w in ("avg_severity", "most_analyzed", "largest_fire")
            if w not in widgets
        ]
        if missing:
            # Insert before recent_analyses if present, otherwise append
            try:
                idx = widgets.index("recent_analyses")
            except ValueError:
                idx = len(widgets)
            for w in reversed(missing):
                widgets.insert(idx, w)
            profile.dashboard_widgets = widgets
            profile.save(update_fields=["dashboard_widgets"])
            updated += 1
    if updated:
        print(f"  Restored optional widgets for {updated} profile(s)")


def set_dark_theme(apps, schema_editor):
    """Update all existing user profiles to use dark theme."""
    UserProfile = apps.get_model("wildfire_assessment", "UserProfile")
    UserProfile.objects.filter(theme="light").update(theme="dark")


def revert_to_light_theme(apps, schema_editor):
    """Revert all dark theme profiles back to light."""
    UserProfile = apps.get_model("wildfire_assessment", "UserProfile")
    UserProfile.objects.filter(theme="dark").update(theme="light")


def seed_providers(apps, schema_editor):
    AIProvider = apps.get_model("wildfire_assessment", "AIProvider")
    AIProvider.objects.get_or_create(
        name="gemini",
        defaults={"is_active": True, "model_name": "gemini-2.0-flash-lite"},
    )
    AIProvider.objects.get_or_create(
        name="openai",
        defaults={"is_active": False, "model_name": "gpt-4o-mini"},
    )


def clear_data(apps, schema_editor):
    """Delete all rows using the OLD schema (before field changes)."""
    AIProvider = apps.get_model("wildfire_assessment", "AIProvider")
    AIProvider.objects.all().delete()


def seed_default(apps, schema_editor):
    """Seed the singleton row using the NEW schema (after field changes)."""
    AIProvider = apps.get_model("wildfire_assessment", "AIProvider")
    AIProvider.objects.create(
        pk=1, provider="gemini", model_name="gemini-2.0-flash-lite"
    )


def backfill_area_ha(apps, schema_editor):
    from pyproj import Geod
    from shapely.geometry import shape
    from wildfire_assessment.svc.object_storage import download_polygon

    geod = Geod(ellps="WGS84")
    AreaOfInterest = apps.get_model("wildfire_assessment", "AreaOfInterest")
    areas = AreaOfInterest.objects.filter(area_ha__isnull=True)
    updated = []
    for area in areas:
        try:
            raw = download_polygon(area.polygon_path)
            geojson = json.loads(raw)
            geojson_type = geojson.get("type")
            total_area_m2 = 0

            if geojson_type == "Feature":
                geom = shape(geojson["geometry"])
                area_m2, _ = geod.geometry_area_perimeter(geom)
                total_area_m2 = abs(area_m2)
            elif geojson_type == "FeatureCollection":
                for feature in geojson.get("features", []):
                    geom = shape(feature["geometry"])
                    area_m2, _ = geod.geometry_area_perimeter(geom)
                    total_area_m2 += abs(area_m2)
            else:
                geom = shape(geojson)
                area_m2, _ = geod.geometry_area_perimeter(geom)
                total_area_m2 = abs(area_m2)

            area.area_ha = round(total_area_m2 / 10_000, 3)
            updated.append(area)
        except Exception as e:
            logger.warning(
                "Failed to compute area_ha for area %s (%s): %s",
                area.id,
                area.name,
                e,
            )
    if updated:
        AreaOfInterest.objects.bulk_update(updated, ["area_ha"], batch_size=100)
        logger.info("Backfilled area_ha for %d areas", len(updated))


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="Country",
            fields=[
                ("id", models.AutoField(primary_key=True, serialize=False)),
                ("name", models.CharField(max_length=255, unique=True)),
                ("code", models.CharField(max_length=2, unique=True)),
            ],
        ),
        migrations.CreateModel(
            name="EcologicalReserve",
            fields=[
                ("id", models.AutoField(primary_key=True, serialize=False)),
                ("name", models.CharField(max_length=255)),
                ("polygon_path", models.CharField(max_length=255)),
                (
                    "area_ha",
                    models.DecimalField(
                        blank=True, decimal_places=3, max_digits=15, null=True
                    ),
                ),
                ("codigo_ibge", models.CharField(blank=True, max_length=7, null=True)),
                ("municipio", models.CharField(blank=True, max_length=255, null=True)),
                ("site", models.URLField(blank=True, max_length=500, null=True)),
                (
                    "country",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="ecological_reserves",
                        to="wildfire_assessment.country",
                    ),
                ),
            ],
        ),
        migrations.RunPython(
            code=create_brazil_and_assign,
            reverse_code=migrations.RunPython.noop,
        ),
        migrations.CreateModel(
            name="UserCountry",
            fields=[
                ("id", models.AutoField(primary_key=True, serialize=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "country",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="authorized_users",
                        to="wildfire_assessment.country",
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="country_permissions",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "ordering": ["user", "country"],
                "unique_together": {("user", "country")},
                "verbose_name": "User country access",
                "verbose_name_plural": "User country access",
            },
        ),
        migrations.CreateModel(
            name="UserProfile",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "default_language",
                    models.CharField(
                        choices=[
                            ("en", "English"),
                            ("pt-BR", "Português (Brasil)"),
                            ("fr", "Français"),
                        ],
                        default="en",
                        max_length=5,
                    ),
                ),
                (
                    "user",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="profile",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "theme",
                    models.CharField(
                        choices=[("light", "Light"), ("dark", "Dark")],
                        default="light",
                        max_length=10,
                    ),
                ),
            ],
        ),
        django.contrib.postgres.operations.UnaccentExtension(),
        migrations.CreateModel(
            name="AnalysisRun",
            fields=[
                ("id", models.AutoField(primary_key=True, serialize=False)),
                ("pre_fire_date", models.DateField()),
                ("post_fire_date", models.DateField()),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("pending", "Pending"),
                            ("running", "Running"),
                            ("completed", "Completed"),
                            ("failed", "Failed"),
                        ],
                        default="completed",
                        max_length=20,
                    ),
                ),
                ("severity_data", models.JSONField(blank=True, null=True)),
                (
                    "total_burned_ha",
                    models.DecimalField(
                        blank=True, decimal_places=3, max_digits=15, null=True
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("completed_at", models.DateTimeField(blank=True, null=True)),
                (
                    "area_of_interest",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="analysis_runs",
                        to="wildfire_assessment.ecologicalreserve",
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="analysis_runs",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                ("dnbr_image", models.CharField(blank=True, max_length=255, null=True)),
                (
                    "dndvi_image",
                    models.CharField(blank=True, max_length=255, null=True),
                ),
                ("rbr_image", models.CharField(blank=True, max_length=255, null=True)),
                (
                    "rgb_post_fire_image",
                    models.CharField(blank=True, max_length=255, null=True),
                ),
                (
                    "rgb_pre_fire_image",
                    models.CharField(blank=True, max_length=255, null=True),
                ),
                (
                    "scientific_rgb_pre_fire_url",
                    models.URLField(blank=True, max_length=500, null=True),
                ),
                (
                    "scientific_rgb_post_fire_url",
                    models.URLField(blank=True, max_length=500, null=True),
                ),
                (
                    "scientific_dndvi_url",
                    models.URLField(blank=True, max_length=500, null=True),
                ),
                (
                    "scientific_dnbr_url",
                    models.URLField(blank=True, max_length=500, null=True),
                ),
                (
                    "scientific_rbr_url",
                    models.URLField(blank=True, max_length=500, null=True),
                ),
                (
                    "scientific_rgb_pre_fire_task_id",
                    models.CharField(blank=True, max_length=255, null=True),
                ),
                (
                    "scientific_rgb_post_fire_task_id",
                    models.CharField(blank=True, max_length=255, null=True),
                ),
                (
                    "scientific_dndvi_task_id",
                    models.CharField(blank=True, max_length=255, null=True),
                ),
                (
                    "scientific_dnbr_task_id",
                    models.CharField(blank=True, max_length=255, null=True),
                ),
                (
                    "scientific_rbr_task_id",
                    models.CharField(blank=True, max_length=255, null=True),
                ),
            ],
            options={
                "verbose_name": "Analysis Run",
                "verbose_name_plural": "Analysis Runs",
                "ordering": ["-created_at"],
            },
        ),
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
        migrations.RenameModel(
            old_name="EcologicalReserve",
            new_name="AreaOfInterest",
        ),
        migrations.AlterModelTable(
            name="areaofinterest",
            table=None,
        ),
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
        migrations.RunPython(
            code=backfill_centroids,
            reverse_code=migrations.RunPython.noop,
        ),
        migrations.RunPython(
            code=backfill_widgets,
            reverse_code=reverse_backfill,
        ),
        migrations.RunPython(
            code=remove_widgets,
            reverse_code=restore_widgets,
        ),
        migrations.RunPython(
            code=set_dark_theme,
            reverse_code=revert_to_light_theme,
        ),
        migrations.AlterField(
            model_name="userprofile",
            name="theme",
            field=models.CharField(
                choices=[("light", "Light"), ("dark", "Dark")],
                default="dark",
                max_length=10,
            ),
        ),
        migrations.CreateModel(
            name="Notification",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "notification_type",
                    models.CharField(
                        choices=[("deliverable_ready", "Deliverable Ready")],
                        default="deliverable_ready",
                        max_length=30,
                    ),
                ),
                ("deliverable_name", models.CharField(blank=True, max_length=30)),
                ("message", models.CharField(max_length=500)),
                ("is_read", models.BooleanField(db_index=True, default=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="notifications",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "analysis_run",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="notifications",
                        to="wildfire_assessment.analysisrun",
                    ),
                ),
            ],
            options={
                "ordering": ["-created_at"],
                "indexes": [
                    models.Index(
                        fields=["user", "is_read", "-created_at"],
                        name="wildfire_as_user_id_88ff66_idx",
                    )
                ],
            },
        ),
        migrations.CreateModel(
            name="AIProvider",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "name",
                    models.CharField(
                        choices=[("gemini", "Google Gemini"), ("openai", "OpenAI")],
                        max_length=20,
                        unique=True,
                    ),
                ),
                ("is_active", models.BooleanField(default=False)),
                (
                    "model_name",
                    models.CharField(
                        help_text="Model identifier, e.g. gemini-2.0-flash-lite or gpt-4o-mini",
                        max_length=100,
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "verbose_name": "AI Provider",
                "verbose_name_plural": "AI Providers",
            },
        ),
        migrations.RunPython(
            code=seed_providers,
            reverse_code=migrations.RunPython.noop,
        ),
        migrations.RunPython(
            code=clear_data,
            reverse_code=migrations.RunPython.noop,
        ),
        migrations.RemoveField(
            model_name="aiprovider",
            name="name",
        ),
        migrations.RemoveField(
            model_name="aiprovider",
            name="is_active",
        ),
        migrations.RemoveField(
            model_name="aiprovider",
            name="created_at",
        ),
        migrations.AddField(
            model_name="aiprovider",
            name="provider",
            field=models.CharField(
                choices=[("gemini", "Google Gemini"), ("openai", "OpenAI")],
                default="gemini",
                max_length=20,
            ),
        ),
        migrations.AlterModelOptions(
            name="aiprovider",
            options={
                "verbose_name": "AI Provider Configuration",
                "verbose_name_plural": "AI Provider Configuration",
            },
        ),
        migrations.AlterField(
            model_name="aiprovider",
            name="model_name",
            field=models.CharField(
                default="gemini-2.0-flash-lite",
                help_text="Model identifier, e.g. gemini-2.0-flash-lite or gpt-4o-mini",
                max_length=100,
            ),
        ),
        migrations.RunPython(
            code=seed_default,
            reverse_code=migrations.RunPython.noop,
        ),
        migrations.AlterModelOptions(
            name="areaofinterest",
            options={
                "verbose_name": "Area of Interest",
                "verbose_name_plural": "Areas of Interest",
            },
        ),
        migrations.AddField(
            model_name="userprofile",
            name="terms_accepted_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name="aiprovider",
            name="id",
            field=models.BigAutoField(
                auto_created=True, primary_key=True, serialize=False, verbose_name="ID"
            ),
        ),
        migrations.AlterField(
            model_name="areaofinterest",
            name="country",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="areas_of_interest",
                to="wildfire_assessment.country",
            ),
        ),
        migrations.AlterField(
            model_name="notification",
            name="id",
            field=models.BigAutoField(
                auto_created=True, primary_key=True, serialize=False, verbose_name="ID"
            ),
        ),
        migrations.AddField(
            model_name="analysisrun",
            name="scientific_dnbr_error",
            field=models.CharField(blank=True, max_length=500, null=True),
        ),
        migrations.AddField(
            model_name="analysisrun",
            name="scientific_dndvi_error",
            field=models.CharField(blank=True, max_length=500, null=True),
        ),
        migrations.AddField(
            model_name="analysisrun",
            name="scientific_rbr_error",
            field=models.CharField(blank=True, max_length=500, null=True),
        ),
        migrations.AddField(
            model_name="analysisrun",
            name="scientific_rgb_post_fire_error",
            field=models.CharField(blank=True, max_length=500, null=True),
        ),
        migrations.AddField(
            model_name="analysisrun",
            name="scientific_rgb_pre_fire_error",
            field=models.CharField(blank=True, max_length=500, null=True),
        ),
        migrations.AddField(
            model_name="userprofile",
            name="expo_push_token",
            field=models.CharField(blank=True, max_length=100, null=True),
        ),
        migrations.AddIndex(
            model_name="analysisrun",
            index=models.Index(
                fields=["user", "severity_data"], name="analysisrun_user_severity"
            ),
        ),
        migrations.AddIndex(
            model_name="analysisrun",
            index=models.Index(
                fields=["user", "created_at"], name="analysisrun_user_created"
            ),
        ),
        migrations.AddIndex(
            model_name="analysisrun",
            index=models.Index(
                fields=["user", "severity_data", "created_at"],
                name="analysisrun_user_sev_created",
            ),
        ),
        migrations.RunPython(
            code=backfill_area_ha,
            reverse_code=migrations.RunPython.noop,
        ),
        migrations.AlterField(
            model_name="userprofile",
            name="default_language",
            field=models.CharField(
                choices=[
                    ("en", "English"),
                    ("pt-BR", "Português (Brasil)"),
                    ("fr", "Français"),
                    ("es-ES", "Español (España)"),
                ],
                default="en",
                max_length=5,
            ),
        ),
        migrations.AddField(
            model_name="analysisrun",
            name="roi_only",
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name="analysisrun",
            name="cloud_threshold",
            field=models.IntegerField(default=100),
        ),
        migrations.AddField(
            model_name="analysisrun",
            name="days_before_after",
            field=models.IntegerField(default=30),
        ),
        migrations.AddField(
            model_name="analysisrun",
            name="post_fire_mosaic_strategy",
            field=models.CharField(
                default="best_available_per_tile_mosaic", max_length=50
            ),
        ),
        migrations.AddField(
            model_name="analysisrun",
            name="pre_fire_mosaic_strategy",
            field=models.CharField(
                default="best_available_per_tile_mosaic", max_length=50
            ),
        ),
        migrations.AddField(
            model_name="analysisrun",
            name="roi_only_bg_color",
            field=models.CharField(default="black", max_length=10),
        ),
        migrations.AddField(
            model_name="analysisrun",
            name="report_summary",
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="analysisrun",
            name="report_summary_language",
            field=models.CharField(blank=True, max_length=10, null=True),
        ),
        migrations.CreateModel(
            name="AnalysisRunProvenance",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "phase",
                    models.CharField(
                        choices=[("pre_fire", "Pre-fire"), ("post_fire", "Post-fire")],
                        max_length=10,
                    ),
                ),
                ("scene_id", models.CharField(max_length=255)),
                ("date", models.DateField()),
                (
                    "spacecraft_name",
                    models.CharField(blank=True, max_length=100, null=True),
                ),
                ("cloud_percent", models.FloatField(blank=True, null=True)),
                (
                    "analysis_run",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="provenance_records",
                        to="wildfire_assessment.analysisrun",
                    ),
                ),
            ],
            options={
                "verbose_name": "Analysis Run Provenance",
                "verbose_name_plural": "Analysis Run Provenance Records",
                "ordering": ["phase", "date", "scene_id"],
            },
        ),
        migrations.AlterField(
            model_name="analysisrun",
            name="created_at",
            field=models.DateTimeField(auto_now_add=True, db_index=True),
        ),
        migrations.AddIndex(
            model_name="analysisrun",
            index=models.Index(
                fields=["status", "completed_at"], name="analysisrun_status_completed"
            ),
        ),
        migrations.AddIndex(
            model_name="areaofinterest",
            index=models.Index(fields=["name", "country"], name="aoi_name_country"),
        ),
        migrations.RemoveField(
            model_name="userprofile",
            name="expo_push_token",
        ),
    ]
