"""Seed São Paulo conservation units (Fundação Florestal) as areas of interest.

Downloads the official DataGEO WFS layers (Proteção Integral and Uso
Sustentável), merges the parts of each UC into a single MultiPolygon,
uploads the GeoJSON to GCS and creates AreaOfInterest rows with the
government names. Idempotent: existing names are skipped.

Run as part of a fresh deployment (after migrate):

    python manage.py register_ucs
"""

import json
import logging
from collections import defaultdict

import requests
from django.core.management.base import BaseCommand, CommandError
from shapely.geometry import shape
from shapely.ops import unary_union

from wildfire_assessment.models import AreaOfInterest, Country
from wildfire_assessment.serializers import (
    MAX_AREA_HA,
    compute_area_ha,
    compute_centroid,
    generate_polygon_filename,
)
from wildfire_assessment.svc.object_storage import upload_polygon

LOG = logging.getLogger(__name__)

WFS_LAYERS = [
    "Areas_Protegidas_PI_DG_UCs_Protecao_Integral",
    "Areas_Protegidas_US_DG_UCs_Uso_Sustentavel",
]


def download_layer(layer: str, session: requests.Session) -> list:
    """Fetch one DataGEO WFS layer as GeoJSON and return its features."""
    url = (
        "https://datageo.ambiente.sp.gov.br/geoserver/datageo/ows"
        "?service=WFS&version=1.0.0&request=GetFeature"
        f"&typeName=datageo:{layer}&outputFormat=application/json"
    )
    response = session.get(url, timeout=120)
    response.raise_for_status()
    return response.json().get("features", [])


def to_geojson(name: str, geometries) -> dict:
    """Merge geometries into one MultiPolygon FeatureCollection for the app."""
    merged = unary_union(geometries)
    polygons = [merged] if merged.geom_type == "Polygon" else list(merged.geoms)
    geometry = {
        "type": "MultiPolygon",
        "coordinates": [
            [list(p.exterior.coords)]
            + [list(interior.coords) for interior in p.interiors]
            for p in polygons
        ],
    }
    return {
        "type": "FeatureCollection",
        "features": [
            {"type": "Feature", "properties": {"name": name}, "geometry": geometry}
        ],
    }


class Command(BaseCommand):
    help = (
        "Seed the official São Paulo conservation units (Fundação Florestal) "
        "as areas of interest."
    )

    def handle(self, *args, **options):
        session = requests.Session()
        features = []
        for layer in WFS_LAYERS:
            try:
                features.extend(download_layer(layer, session))
                self.stdout.write(self.style.SUCCESS(f"Downloaded {layer}"))
            except requests.RequestException as exc:
                raise CommandError(f"Failed to download {layer}: {exc}") from exc

        by_name = defaultdict(list)
        for feature in features:
            name = feature["properties"].get("Unidade")
            if name and feature.get("geometry"):
                by_name[name].append(shape(feature["geometry"]))

        brazil, _ = Country.objects.get_or_create(name="Brazil", code="BR")
        created = 0
        skipped_existing = 0
        skipped_oversized = []
        for name in sorted(by_name):
            if AreaOfInterest.objects.filter(name=name, country=brazil).exists():
                skipped_existing += 1
                continue

            geojson_data = to_geojson(name, by_name[name])
            area_ha = compute_area_ha(geojson_data)
            if area_ha is None or area_ha > MAX_AREA_HA:
                skipped_oversized.append(name)
                continue

            filename = generate_polygon_filename(name)
            upload_polygon(filename, geojson_data)
            centroid = compute_centroid(geojson_data)
            AreaOfInterest.objects.create(
                name=name,
                country=brazil,
                polygon_path=filename,
                area_ha=area_ha,
                centroid_lat=centroid[0] if centroid else None,
                centroid_lng=centroid[1] if centroid else None,
            )
            created += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Registered {created} conservation units; "
                f"skipped {skipped_existing} existing names."
            )
        )
        if skipped_oversized:
            self.stdout.write(
                self.style.WARNING(
                    f"Skipped {len(skipped_oversized)} units over the "
                    f"{MAX_AREA_HA:,} ha platform limit: {skipped_oversized}"
                )
            )
