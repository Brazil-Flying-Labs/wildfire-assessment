import json
from datetime import timedelta

import ee


def load_polygon(file_name):
    """Loads all polygons from GeoJSON files in a directory.

    Args:
        directory_path: str, Path to the directory containing GeoJSON files.

    Returns:
        list, List of tuples (file name, ee.Geometry) corresponding to the loaded polygons.
    """

    file_path = "../../polygons/" + file_name

    with open(file_path, "r", encoding="utf-8") as f:
        geojson = json.load(f)

    # If the GeoJSON has multiple features, use FeatureCollection and get the aggregated geometry
    try:
        features = geojson.get("features")
        if features and len(features) > 1:
            fc = ee.FeatureCollection(features)
            geometry = fc.geometry()
        else:
            geometry = ee.Geometry(features[0]["geometry"]) if features else ee.Geometry(geojson)
    except Exception:
        geometry = ee.Geometry(geojson)

    return geometry


def calculate_date_range(pre_fire_date, post_fire_date, days_before=60, days_after=60):
    """
    Calculates a date range around a given date.

    Args:
        date (datetime.date or datetime.datetime): The reference date.
        days_before (int): Number of days before the reference date.
        days_after (int): Number of days after the reference date.

    Returns:
        tuple: (date_before, date_after) as datetime objects, or (None, None) if input is invalid.
    """
    if not pre_fire_date and not post_fire_date:
        return None, None
    try:
        date_before = pre_fire_date - timedelta(days=days_before)
        date_after = post_fire_date + timedelta(days=days_after)
        return date_before, date_after
    except (ValueError, TypeError):
        return None, None
