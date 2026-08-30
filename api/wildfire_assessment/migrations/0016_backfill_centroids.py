import json
import logging

from django.db import migrations

logger = logging.getLogger(__name__)


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


class Migration(migrations.Migration):

    dependencies = [
        ("wildfire_assessment", "0015_areaofinterest_centroid_fields"),
    ]

    operations = [
        migrations.RunPython(backfill_centroids, migrations.RunPython.noop),
    ]
