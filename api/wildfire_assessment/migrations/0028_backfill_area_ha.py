import json
import logging

from django.db import migrations

logger = logging.getLogger(__name__)


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
        ("wildfire_assessment", "0027_add_dashboard_indexes"),
    ]

    operations = [
        migrations.RunPython(backfill_area_ha, migrations.RunPython.noop),
    ]
