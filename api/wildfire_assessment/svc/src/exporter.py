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
                'maxPixels': EXPORT_MAX_PIXELS,
                'format': 'GEO_TIFF'
            })
            print(f"Download URL para {description}: {download_info}")
            # Baixar dados
            response = requests.get(download_info)
            if response.status_code != 200:
                raise Exception(f"Erro ao baixar {description}: {response.text}")
            print(f"Tipo de conteúdo para {description}: {response.headers.get('content-type')}")
            
            # Verificar se o conteúdo é um GeoTIFF direto
            output_path = os.path.join(output_dir, f"{description}.tif")
            if 'image/tiff' in response.headers.get('content-type', ''):
                # Abrir o GeoTIFF diretamente do conteúdo da resposta
                with MemoryFile(response.content) as memfile:
                    with memfile.open() as src:
                        profile = src.profile
                        array = src.read()
                        print(f"Forma do array para {description}: {array.shape}")
                        print(f"Perfil do GeoTIFF para {description}: {profile}")
                    # Atualizar perfil para imagens RGB
                    if description.endswith(('RGB_PreFire', 'RGB_PostFire', 'RBR')):
                        if array.shape[0] != 3:
                            raise ValueError(f"Esperado 3 bandas para {description}, mas encontrado {array.shape[0]}")
                        profile.update(
                            count=3,  # Três bandas para RGB
                            dtype=rasterio.uint8,  # Garantir tipo uint8
                            photometric='rgb'  # Especificar interpretação RGB
                        )
                    with rasterio.open(output_path, 'w', **profile) as dst:
                        dst.write(array)
            else:
                # Tratar como ZIP (caso o comportamento do GEE mude no futuro)
                import tempfile
                import zipfile
                with zipfile.ZipFile(io.BytesIO(response.content)) as z:
                    with tempfile.TemporaryDirectory() as tmp_dir:
                        z.extractall(tmp_dir)
                        tiff_file = [f for f in os.listdir(tmp_dir) if f.endswith('.tif')][0]
                        tiff_path = os.path.join(tmp_dir, tiff_file)
                        with rasterio.open(tiff_path) as src:
                            profile = src.profile
                            array = src.read()
                            print(f"Forma do array para {description}: {array.shape}")
                            print(f"Perfil do GeoTIFF para {description}: {profile}")
                        # Atualizar perfil para imagens RGB
                        if description.endswith(('RGB_PreFire', 'RGB_PostFire', 'RBR')):
                            if array.shape[0] != 3:
                                raise ValueError(f"Esperado 3 bandas para {description}, mas encontrado {array.shape[0]}")
                            profile.update(
                                count=3,  # Três bandas para RGB
                                dtype=rasterio.uint8,  # Garantir tipo uint8
                                photometric='rgb'  # Especificar interpretação RGB
                            )
                        with rasterio.open(output_path, 'w', **profile) as dst:
                            dst.write(array)
            print(f"Exportação local {description}.tif concluída em {output_path}")

        elif isinstance(data, ee.FeatureCollection):
            # Obter dados como GeoJSON
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