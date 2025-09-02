import json

import ee


def load_polygon(file_name):
    """Carrega todos os polígonos de arquivos GeoJSON em um diretório.

    Args:
        directory_path: str, Caminho para o diretório contendo arquivos GeoJSON.

    Returns:
        list, Lista de tuplas (nome do arquivo, ee.Geometry) correspondentes aos polígonos carregados.
    """

    file_path = "../../polygons/" + file_name
    
    with open(file_path, 'r', encoding='utf-8') as f:
        geojson = json.load(f)
    # Carregar a primeira feature do GeoJSON
    geometry = ee.Geometry(geojson['features'][0]['geometry'])

    return geometry

    