import io
import os

import ee
import geopandas as gpd
import numpy as np
import rasterio
import requests
from rasterio.io import MemoryFile
from wildfire_assessment.svc.config.settings import (
    EXPORT_CRS,
    EXPORT_MAX_PIXELS,
    EXPORT_SCALE,
)


def export_local(data, description, region, extension, output_dir='exports', min_scale=30):
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

        # Suporte para overlay do polígono
        overlay_polygon = None
        if hasattr(data, 'overlay_polygon'):
            overlay_polygon = data.overlay_polygon

        if isinstance(data, ee.Image):
            scale = EXPORT_SCALE
            if region is None:
                try:
                    poly_geom = data.geometry().bounds(1)
                    region = poly_geom
                    bounds = poly_geom.getInfo()['coordinates'][0]
                    lon_min, lat_min = bounds[0]
                    lon_max, lat_max = bounds[2]
                    width_m = abs(lon_max - lon_min) * 111320
                    height_m = abs(lat_max - lat_min) * 111320
                    max_dim = max(width_m, height_m)
                    scale = max_dim / 32768
                    scale = max(scale, min_scale)
                    if scale < min_scale or max_dim / scale > 32768:
                        scale = max(min_scale, 1000)
                except Exception:
                    scale = max(min_scale, 1000)
            # Overlay do polígono (borda vermelha)
            if overlay_polygon is not None:
                data = data.visualize(**{
                    'bands': ['R', 'G', 'B'] if 'R' in data.bandNames().getInfo() else data.bandNames().getInfo(),
                    'min': 0,
                    'max': 255,
                }).blend(
                    ee.Image().paint(overlay_polygon, 1, 3).visualize(**{
                        'palette': ['red'],
                        'opacity': 0.7
                    })
                )
            # Exportação JPEG não georreferenciado
            if extension in ['jpeg', 'jpg']:
                download_params = {
                    'name': description,
                    'scale': scale,
                    'crs': EXPORT_CRS,
                    'maxPixels': EXPORT_MAX_PIXELS,
                    'format': 'jpg'
                }
            else:
                download_params = {
                    'name': description,
                    'scale': scale,
                    'crs': EXPORT_CRS,
                    'maxPixels': EXPORT_MAX_PIXELS,
                    'format': 'GEO_TIFF'
                }
            if region is not None:
                download_params['region'] = region
            download_info = data.getDownloadURL(download_params)
            print(f"Download URL para {description}: {download_info}")
            # Baixar arquivo em stream para evitar OOM
            with requests.get(download_info, stream=True) as response:
                if response.status_code != 200:
                    raise Exception(f"Erro ao baixar {description}: {response.text}")
                print(f"Tipo de conteúdo para {description}: {response.headers.get('content-type')}")
                output_path = os.path.join(output_dir, f"{description}.{extension}")
                if extension in ['jpeg', 'jpg']:
                    # Salva JPEG diretamente
                    with open(output_path, 'wb') as f:
                        for chunk in response.iter_content(chunk_size=8192):
                            f.write(chunk)
            if 'image/tiff' in response.headers.get('content-type', ''):
                # Salva conteúdo em arquivo temporário para abrir com rasterio
                import tempfile
                with tempfile.NamedTemporaryFile(delete=False) as tmp_file:
                    for chunk in response.iter_content(chunk_size=8192):
                        tmp_file.write(chunk)
                    tmp_file_path = tmp_file.name
                with MemoryFile(open(tmp_file_path, 'rb').read()) as memfile:
                    with memfile.open() as src:
                        profile = src.profile
                        array = src.read()
                        print(f"Forma do array para {description}: {array.shape}")
                        print(f"Perfil do GeoTIFF para {description}: {profile}")
                    if description.endswith(('RGB_PreFire', 'RGB_PostFire', 'RBR')):
                        if array.shape[0] != 3:
                            raise ValueError(f"Esperado 3 bandas para {description}, mas encontrado {array.shape[0]}")
                        profile.update(
                            count=3,
                            dtype=rasterio.uint8,
                            photometric='rgb'
                        )
                    # Garante que o parâmetro 'driver' está presente
                    if 'driver' not in profile:
                        profile['driver'] = 'GTiff'
                    with rasterio.open(output_path, 'w', **profile) as dst:
                        dst.write(array)
                os.remove(tmp_file_path)
            # Removido o else inválido
            print(f"Exportação local {description}.{extension} concluída em {output_path}")

        elif isinstance(data, ee.FeatureCollection):
            geojson = data.getInfo()
            gdf = gpd.GeoDataFrame.from_features(geojson['features'], crs='EPSG:4326')
            output_path = os.path.join(output_dir, f"{description}.geojson")
            gdf.to_file(output_path, driver='GeoJSON')
            print(f"Exportação local {description}.geojson concluída em {output_path}")

        else:
            raise ValueError(f"Tipo de dado não suportado para exportação: {type(data)}")

        return output_path

    except Exception as e:
        print(f"Erro ao exportar localmente {description}: {e}")
        raise