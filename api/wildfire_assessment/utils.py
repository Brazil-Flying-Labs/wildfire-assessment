import json
from datetime import datetime, timedelta

import ee


def load_polygon(file_name):
    """Carrega todos os polígonos de arquivos GeoJSON em um diretório.

    Args:
        directory_path: str, Caminho para o diretório contendo arquivos GeoJSON.

    Returns:
        list, Lista de tuplas (nome do arquivo, ee.Geometry) correspondentes aos polígonos carregados.
    """

    file_path = "../../polygons/" + file_name

    with open(file_path, "r", encoding="utf-8") as f:
        geojson = json.load(f)
    # Carregar a primeira feature do GeoJSON
    geometry = ee.Geometry(geojson["features"][0]["geometry"])

    return geometry


def calculate_date_range(date, days_before=60, days_after=60):
    """
    Calculates a date range around a given date.

    Args:
        date (datetime.date or datetime.datetime): The reference date.
        days_before (int): Number of days before the reference date.
        days_after (int): Number of days after the reference date.

    Returns:
        tuple: (date_before, date_after) as datetime objects, or (None, None) if input is invalid.
    """
    if not date:
        return None, None
    try:
        date_before = date - timedelta(days=days_before)
        date_after = date + timedelta(days=days_after)
        return date_before, date_after
    except (ValueError, TypeError):
        return None, None
