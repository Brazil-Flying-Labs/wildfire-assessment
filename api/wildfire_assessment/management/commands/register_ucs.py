"""Seed São Paulo conservation units (Fundação Florestal) as areas of interest.

Reads the official conservation-unit GeoJSONs bundled in
``wildfire_assessment/data/ucs/`` (parts of each UC already merged into
one MultiPolygon), uploads them to GCS and creates AreaOfInterest rows
with the government names. Idempotent: existing names are skipped.

Run as part of a fresh deployment (after migrate):

    python manage.py register_ucs
"""

import json
import logging
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from wildfire_assessment.models import AreaOfInterest, Country
from wildfire_assessment.serializers import (
    MAX_AREA_HA,
    compute_area_ha,
    compute_centroid,
    generate_polygon_filename,
)
from wildfire_assessment.svc.object_storage import upload_polygon

LOG = logging.getLogger(__name__)

DEFAULT_DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "ucs"


class Command(BaseCommand):
    help = (
        "Seed the official São Paulo conservation units (Fundação Florestal) "
        "as areas of interest from the bundled GeoJSONs."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--data-dir",
            type=str,
            default=str(DEFAULT_DATA_DIR),
            help="Directory containing the bundled UC GeoJSON files.",
        )

    def handle(self, *args, **options):
        data_dir = Path(options["data_dir"])
        if not data_dir.is_dir():
            raise CommandError(f"UC data directory not found: {data_dir}")

        brazil, _ = Country.objects.get_or_create(name="Brazil", code="BR")
        created = 0
        skipped_existing = 0
        skipped_oversized = []
        skipped_invalid = 0
        for path in sorted(data_dir.glob("*.geojson")):
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                name = data["features"][0]["properties"].get("name", "")
            except (json.JSONDecodeError, KeyError, IndexError, TypeError) as exc:
                LOG.warning("Skipping invalid UC file %s: %s", path.name, exc)
                skipped_invalid += 1
                continue
            if not name:
                LOG.warning("Skipping UC file %s: no name", path.name)
                skipped_invalid += 1
                continue

            if AreaOfInterest.objects.filter(name=name, country=brazil).exists():
                skipped_existing += 1
                continue

            area_ha = compute_area_ha(data)
            if area_ha is None or area_ha > MAX_AREA_HA:
                skipped_oversized.append(name)
                continue

            filename = generate_polygon_filename(name)
            upload_polygon(filename, data)
            centroid = compute_centroid(data)
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
        if skipped_invalid:
            self.stdout.write(
                self.style.WARNING(f"Skipped {skipped_invalid} invalid files.")
            )
        if skipped_oversized:
            self.stdout.write(
                self.style.WARNING(
                    f"Skipped {len(skipped_oversized)} units over the "
                    f"{MAX_AREA_HA:,} ha platform limit: {skipped_oversized}"
                )
            )
