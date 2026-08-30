"""Tests for the register_ucs management command (UC seeding)."""

import json
import shutil
import tempfile
from pathlib import Path
from unittest.mock import patch

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase
from wildfire_assessment.models import AreaOfInterest, Country

SMALL_SQUARE = [
    [-47.0, -22.0],
    [-46.9, -22.0],
    [-46.9, -21.9],
    [-47.0, -21.9],
    [-47.0, -22.0],
]

SMALL_SQUARE_2 = [
    [-48.0, -23.0],
    [-47.9, -23.0],
    [-47.9, -22.9],
    [-48.0, -22.9],
    [-48.0, -23.0],
]

# A huge box (2 degrees square) — far above the 110,000 ha platform limit.
HUGE_BOX = [
    [-60.0, -30.0],
    [-58.0, -30.0],
    [-58.0, -28.0],
    [-60.0, -28.0],
    [-60.0, -30.0],
]


def uc_file(name, coordinates, geometry_type="Polygon"):
    if geometry_type == "Polygon":
        geometry = {"type": "Polygon", "coordinates": coordinates}
    else:
        geometry = {"type": "MultiPolygon", "coordinates": coordinates}
    return {
        "type": "FeatureCollection",
        "features": [
            {"type": "Feature", "properties": {"name": name}, "geometry": geometry}
        ],
    }


class RegisterUcsCommandTests(TestCase):
    def setUp(self):
        self.data_dir = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.data_dir)

    def _write(self, filename, payload):
        path = self.data_dir / filename
        path.write_text(json.dumps(payload), encoding="utf-8")
        return path

    def _run(self):
        with patch(
            "wildfire_assessment.management.commands.register_ucs.upload_polygon"
        ) as mock_upload:
            call_command("register_ucs", data_dir=str(self.data_dir))
        return mock_upload

    def test_command_registers_units_and_skips_oversized(self):
        self._write(
            "parque_test.geojson", uc_file("Parque Estadual Test", [SMALL_SQUARE])
        )
        self._write(
            "estacao_test.geojson",
            uc_file(
                "Estação Ecológica Test",
                [[SMALL_SQUARE], [SMALL_SQUARE_2]],
                geometry_type="MultiPolygon",
            ),
        )
        self._write("apa_gigante.geojson", uc_file("APA Gigante Test", [HUGE_BOX]))

        mock_upload = self._run()

        brazil = Country.objects.get(code="BR")
        names = set(
            AreaOfInterest.objects.filter(country=brazil).values_list("name", flat=True)
        )
        self.assertEqual(names, {"Parque Estadual Test", "Estação Ecológica Test"})
        self.assertEqual(mock_upload.call_count, 2)
        area = AreaOfInterest.objects.get(name="Parque Estadual Test")
        self.assertIsNotNone(area.polygon_path)
        self.assertIsNotNone(area.area_ha)
        self.assertIsNotNone(area.centroid_lat)
        self.assertIsNotNone(area.centroid_lng)

    def test_command_skips_existing_names(self):
        brazil, _ = Country.objects.get_or_create(name="Brazil", code="BR")
        AreaOfInterest.objects.create(
            name="Parque Estadual Test",
            country=brazil,
            polygon_path="existing.geojson",
        )
        self._write(
            "parque_test.geojson", uc_file("Parque Estadual Test", [SMALL_SQUARE])
        )
        self._write(
            "estacao_test.geojson", uc_file("Estação Ecológica Test", [SMALL_SQUARE_2])
        )

        mock_upload = self._run()

        self.assertEqual(mock_upload.call_count, 1)
        existing = AreaOfInterest.objects.get(name="Parque Estadual Test")
        self.assertEqual(existing.polygon_path, "existing.geojson")

    def test_command_skips_invalid_and_nameless_files(self):
        self._write("broken.geojson", "{not json")
        self._write(
            "nameless.geojson",
            uc_file("", [SMALL_SQUARE]),
        )
        self._write("ok.geojson", uc_file("Parque Estadual Test", [SMALL_SQUARE]))

        mock_upload = self._run()

        self.assertEqual(mock_upload.call_count, 1)
        self.assertTrue(
            AreaOfInterest.objects.filter(name="Parque Estadual Test").exists()
        )

    def test_command_missing_data_dir_raises(self):
        with self.assertRaises(CommandError):
            call_command("register_ucs", data_dir=str(self.data_dir / "nope"))
