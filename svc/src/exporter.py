"""Módulo para exportação de dados do Google Earth Engine."""

import ee
import os
import geopandas as gpd
import rasterio
from rasterio.transform import from_bounds
import numpy as np
from config.settings import EXPORT_SCALE, EXPORT_CRS, EXPORT_MAX_PIXELS


def export_local(data, description, region, output_dir='exports'):
    """Exporta dados do Google Earth Engine para arquivos locais (GeoTIFF ou GeoJSON).

    Args:
        data: ee.Image ou ee.FeatureCollection, Dados a serem exportados.
        description: str, Nome do arquivo exportado (sem extensão).
        region: ee.Geometry, Região de exportação.
        output_dir: str, Diretório local para salvar os arquivos.

    Returns:
        str, Caminho do arquivo salvo.
    """
    try:
        # Criar diretório de saída, se não existir
        os.makedirs(output_dir, exist_ok=True)

        if isinstance(data, ee.Image):
            # Obter informações de download
            download_info = data.getDownloadURL({
                'name': description,
                'scale': EXPORT_SCALE,
                'crs': EXPORT_CRS,
                'region': region,
                'maxPixels': EXPORT_MAX_PIXELS
            })
            # Baixar dados como array numpy
            import requests
            response = requests.get(download_info)
            if response.status_code != 200:
                raise Exception(f"Erro ao baixar {description}: {response.text}")
            import zipfile
            import io
            import tempfile
            with zipfile.ZipFile(io.BytesIO(response.content)) as z:
                with tempfile.TemporaryDirectory() as tmp_dir:
                    z.extractall(tmp_dir)
                    # Assume que o arquivo TIFF está no diretório temporário
                    tiff_file = [f for f in os.listdir(tmp_dir) if f.endswith('.tif')][0]
                    tiff_path = os.path.join(tmp_dir, tiff_file)
                    # Mover para o diretório de saída
                    output_path = os.path.join(output_dir, f"{description}.tif")
                    with rasterio.open(tiff_path) as src:
                        profile = src.profile
                        array = src.read()
                    with rasterio.open(output_path, 'w', **profile) as dst:
                        dst.write(array)
            print(f"Exportação local {description}.tif concluída em {output_path}")

        elif isinstance(data, ee.FeatureCollection):
            # Obter dados como GeoJSON
            geojson = data.getInfo()
            gdf = gpd.GeoDataFrame.from_features(geojson['features'])
            output_path = os.path.join(output_dir, f"{description}.geojson")
            gdf.to_file(output_path, driver='GeoJSON')
            print(f"Exportação local {description}.geojson concluída em {output_path}")

        else:
            raise ValueError(f"Tipo de dado não suportado para exportação: {type(data)}")

        return output_path

    except Exception as e:
        print(f"Erro ao exportar localmente {description}: {e}")
        raise