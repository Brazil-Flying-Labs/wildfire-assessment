import io
import logging
import os
import time

import ee
import geopandas as gpd
import numpy as np
import rasterio
import requests
from rasterio.io import MemoryFile
from requests.adapters import HTTPAdapter
from requests.exceptions import ConnectionError as ReqConnectionError
from requests.exceptions import RequestException
from requests.exceptions import Timeout as ReqTimeout
from urllib3.util.retry import Retry
from wildfire_assessment.svc.config.settings import (
    EXPORT_CRS,
    EXPORT_MAX_PIXELS,
    EXPORT_SCALE,
)

logger = logging.getLogger(__name__)


def export_local(
    data, description, region, extension, output_dir="exports", min_scale=60
):
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
        logger.debug("Iniciando exportação: %s.%s", description, extension)
        logger.debug("Parâmetros: output_dir=%s, min_scale=%s, region=%s", output_dir, min_scale, region)
        # Criar diretório de saída, se não existir
        os.makedirs(output_dir, exist_ok=True)

        # Suporte para overlay do polígono
        overlay_polygon = None
        if hasattr(data, "overlay_polygon"):
            overlay_polygon = data.overlay_polygon

        if isinstance(data, ee.Image):
            scale = EXPORT_SCALE
            if region is None:
                try:
                    poly_geom = data.geometry().bounds(1)
                    region = poly_geom
                    bounds = poly_geom.getInfo()["coordinates"][0]
                    lon_min, lat_min = bounds[0]
                    lon_max, lat_max = bounds[2]
                    width_m = abs(lon_max - lon_min) * 111320
                    height_m = abs(lat_max - lat_min) * 111320
                    max_dim = max(width_m, height_m)
                    scale = max_dim / 32768
                    scale = max(scale, min_scale)
                    if scale < min_scale or max_dim / scale > 32768:
                        scale = max(min_scale, 1000)
                except Exception as e:
                    logger.warning("Erro ao calcular escala dinâmica: %s", e)
                    scale = max(min_scale, 1000)
            logger.debug("Usando escala: %s", scale)
            # Overlay do polígono (borda vermelha)
            if overlay_polygon is not None:
                data = data.visualize(
                    **{
                        "bands": (
                            ["R", "G", "B"]
                            if "R" in data.bandNames().getInfo()
                            else data.bandNames().getInfo()
                        ),
                        "min": 0,
                        "max": 255,
                    }
                ).blend(
                    ee.Image()
                    .paint(overlay_polygon, 1, 3)
                    .visualize(**{"palette": ["red"], "opacity": 0.7})
                )
            # Exportação JPEG não georreferenciado
            if extension in ["jpeg", "jpg"]:
                download_params = {
                    "name": description,
                    "scale": scale,
                    "crs": EXPORT_CRS,
                    "maxPixels": EXPORT_MAX_PIXELS,
                    "format": "jpg",
                }
            else:
                download_params = {
                    "name": description,
                    "scale": scale,
                    "crs": EXPORT_CRS,
                    "maxPixels": EXPORT_MAX_PIXELS,
                    "format": "GEO_TIFF",
                }
            if region is not None:
                download_params["region"] = region
            # Tenta obter o download URL. Se o GEE rejeitar por tamanho da requisição,
            # aumenta a escala (reduz resolução) e tenta novamente.
            download_info = None
            max_get_url_retries = 5
            get_url_attempt = 0
            while get_url_attempt < max_get_url_retries:
                try:
                    logger.debug("Solicitando URL de download para %s com parâmetros: %s", description, download_params)
                    download_info = data.getDownloadURL(download_params)
                    logger.debug("Download URL para %s: %s", description, download_info)
                    break
                except Exception as e:
                    msg = str(e)
                    logger.warning("Erro ao obter URL de download para %s: %s", description, e)
                    # Mensagem conhecida do GEE quando payload é muito grande
                    if (
                        'Total request size' in msg
                        or 'must be less than or equal' in msg
                        or 'request size' in msg
                    ):
                        # aumenta a escala para reduzir o tamanho da requisição
                        old_scale = download_params.get('scale', scale)
                        new_scale = int(max(old_scale * 2, old_scale + 1))
                        download_params['scale'] = new_scale
                        logger.warning("Aumentando escala de %s para %s e tentando novamente (%s/%s)...", old_scale, new_scale, get_url_attempt+1, max_get_url_retries)
                        get_url_attempt += 1
                        continue
                    else:
                        download_info = None
                        break
            logger.debug("%s", "#########################################################")
            if not download_info:
                logger.error("Falha ao obter URL de download para %s após %s tentativas", description, get_url_attempt)
                return None

            # Baixar arquivo em stream para evitar OOM
            def download_and_validate(
                download_info,
                description,
                extension,
                output_dir,
                max_retries=5,
                timeout=300,
            ):
                attempt = 0

                # Configure requests Session with Retry
                session = requests.Session()
                retries = Retry(
                    total=max_retries,
                    backoff_factor=2,
                    status_forcelist=[429, 500, 502, 503, 504],
                    allowed_methods=["GET"],
                )
                adapter = HTTPAdapter(max_retries=retries)
                session.mount("https://", adapter)
                session.mount("http://", adapter)

                while attempt < max_retries:
                    try:
                        connect_timeout = 10
                        read_timeout = timeout
                        logger.debug("Tentativa %s para baixar %s com timeout de leitura %ss", attempt+1, description, read_timeout)
                        with session.get(download_info, stream=True, timeout=(connect_timeout, read_timeout)) as response:
                            if response.status_code != 200:
                                raise Exception(f"Erro ao baixar {description}: {response.status_code} {response.text}")
                            logger.debug("Tipo de conteúdo para %s: %s", description, response.headers.get('content-type'))
                            output_path = os.path.join(output_dir, f"{description}.{extension}")
                            output_path = os.path.abspath(output_path)
                            if extension in ["jpeg", "jpg"]:
                                with open(output_path, "wb") as f:
                                    for chunk in response.iter_content(chunk_size=8192):
                                        if chunk:
                                            f.write(chunk)
                                return True, output_path, None, None
                            if "image/tiff" in response.headers.get("content-type", "") or extension in ["tif", "tiff", "geotiff"]:
                                import tempfile

                                with tempfile.NamedTemporaryFile(delete=False) as tmp_file:
                                    for chunk in response.iter_content(chunk_size=8192):
                                        if chunk:
                                            tmp_file.write(chunk)
                                    tmp_file_path = tmp_file.name
                                file_size = os.path.getsize(tmp_file_path)
                                logger.debug("Arquivo TIFF baixado: %s, tamanho: %s bytes, status: %s", tmp_file_path, file_size, response.status_code)
                                if response.status_code != 200:
                                    raise RuntimeError(f"Download falhou para {description}: status {response.status_code}")
                                if file_size == 0:
                                    return False, None, None, None
                                with open(tmp_file_path, "rb") as f:
                                    header = f.read(4)
                                if header not in [b"II*\x00", b"MM\x00*"]:
                                    raise RuntimeError(f"Arquivo baixado não é um TIFF válido. Header: {header}")
                                try:
                                    with rasterio.open(tmp_file_path) as src:
                                        profile = src.profile
                                        array = src.read()
                                except Exception as e:
                                    raise RuntimeError(f"Falha ao abrir TIFF temporário: {e}")
                                # Validação robusta dos campos do profile e escrita para output_path
                                try:
                                    required_fields = ["width", "height", "count", "dtype"]
                                    # width/height
                                    if (
                                        not profile.get("width")
                                        or not isinstance(profile["width"], int)
                                        or profile["width"] <= 0
                                    ):
                                        profile["width"] = array.shape[-1]
                                    if (
                                        not profile.get("height")
                                        or not isinstance(profile["height"], int)
                                        or profile["height"] <= 0
                                    ):
                                        profile["height"] = array.shape[-2]
                                    # count
                                    if (
                                        not profile.get("count")
                                        or not isinstance(profile["count"], int)
                                        or profile["count"] <= 0
                                    ):
                                        profile["count"] = array.shape[0]
                                    # dtype
                                    if not profile.get("dtype") or not isinstance(profile["dtype"], str):
                                        profile["dtype"] = str(array.dtype)
                                    # Ajustes para imagens RGB/RBR esperadas
                                    if description.endswith(("RGB_PreFire", "RGB_PostFire", "RBR")):
                                        if array.shape[0] != 3:
                                            raise ValueError(
                                                f"Esperado 3 bandas para {description}, mas encontrado {array.shape[0]}"
                                            )
                                        profile.update(count=3, dtype=rasterio.uint8, photometric="rgb")
                                    profile["width"] = array.shape[-1]
                                    profile["height"] = array.shape[-2]
                                    # Escrever arquivo GeoTIFF final
                                    with rasterio.open(
                                        output_path,
                                        "w",
                                        driver="GTiff",
                                        **{k: v for k, v in profile.items() if k != "driver"},
                                    ) as dst:
                                        dst.write(array)
                                except Exception as e:
                                    # Limpar tmp e repassar exceção
                                    try:
                                        os.remove(tmp_file_path)
                                    except Exception:
                                        pass
                                    raise
                                # Remover o arquivo temporário após escrita bem-sucedida
                                try:
                                    os.remove(tmp_file_path)
                                except Exception:
                                    pass
                                return True, output_path, profile, array
                            return True, output_path, None, None
                    except (RequestException, ReqConnectionError, ReqTimeout) as e:
                        logger.warning("Erro de rede ao baixar %s: %s. Tentando novamente (%s/%s)...", description, e, attempt+1, max_retries)
                        sleep_time = min(60, 2 ** attempt)
                        time.sleep(sleep_time)
                        attempt += 1
                        continue
                    except Exception as e:
                        logger.exception("Erro inesperado ao baixar %s: %s", description, e)
                        break
                return False, None, None, None

            logger.debug("Iniciando download e validação para %s.%s", description, extension)
            ok, output_path, profile, array = download_and_validate(
                download_info, description, extension, output_dir
            )
            logger.debug("Resultado do download: ok=%s, output_path=%s", ok, output_path)
            # Se o arquivo baixado estiver vazio, tenta novamente com escala maior
            if not ok and extension in ["tif", "tiff", "geotiff"]:
                logger.info("Arquivo vazio para %s, tentando novamente com escala maior...", description)
                download_params["scale"] = max(
                    download_params.get("scale", min_scale) * 2, min_scale * 2
                )
                logger.info("Nova escala para retry: %s", download_params['scale'])
                download_info = data.getDownloadURL(download_params)
                logger.debug("Nova URL de download para retry: %s", download_info)
                ok, output_path, profile, array = download_and_validate(
                    download_info, description, extension, output_dir
                )
                logger.debug("Resultado do retry: ok=%s, output_path=%s", ok, output_path)
                if not ok:
                    raise RuntimeError(
                        f"Arquivo baixado está vazio para {description} mesmo após aumentar a escala. Verifique limites de pixels, autenticação ou parâmetros da requisição."
                    )
                    logger.debug("Forma do array para %s: %s", description, array.shape)
                    logger.debug("Perfil do GeoTIFF para %s: %s", description, profile)
                    # Garante que width e height estejam definidos
                    # Validação robusta dos campos do profile
                    required_fields = ["width", "height", "count", "dtype"]
                    # width/height
                    if (
                        not profile.get("width")
                        or not isinstance(profile["width"], int)
                        or profile["width"] <= 0
                    ):
                        profile["width"] = array.shape[-1]
                    if (
                        not profile.get("height")
                        or not isinstance(profile["height"], int)
                        or profile["height"] <= 0
                    ):
                        profile["height"] = array.shape[-2]
                    # count
                    if (
                        not profile.get("count")
                        or not isinstance(profile["count"], int)
                        or profile["count"] <= 0
                    ):
                        profile["count"] = array.shape[0]
                    # dtype
                    if not profile.get("dtype") or not isinstance(
                        profile["dtype"], str
                    ):
                        profile["dtype"] = str(array.dtype)
                    logger.debug("Forma do array para %s: %s", description, array.shape)
                    logger.debug("Perfil do GeoTIFF para %s: %s", description, profile)
                    if description.endswith(("RGB_PreFire", "RGB_PostFire", "RBR")):
                        if array.shape[0] != 3:
                            raise ValueError(
                                f"Esperado 3 bandas para {description}, mas encontrado {array.shape[0]}"
                            )
                        profile.update(count=3, dtype=rasterio.uint8, photometric="rgb")
                    # Garante que width e height estejam definidos
                    profile["width"] = array.shape[-1]
                    profile["height"] = array.shape[-2]
                    # Sempre passa 'driver' explicitamente, mesmo se profile estiver vazio
                    with rasterio.open(
                        output_path,
                        "w",
                        driver="GTiff",
                        **{k: v for k, v in profile.items() if k != "driver"},
                    ) as dst:
                        dst.write(array)
            # Removido o else inválido
            # Validação final: garantir que o arquivo existe e tem tamanho maior que zero
            try:
                if not os.path.exists(output_path) or os.path.getsize(output_path) == 0:
                    logger.error("Arquivo esperado %s não encontrado ou vazio após exportação", output_path)
                    raise RuntimeError(f"Arquivo esperado {output_path} não encontrado ou vazio após exportação")
            except Exception:
                logger.exception("Erro ao validar arquivo exportado %s", output_path)
                raise

            logger.info("Exportação local %s.%s concluída em %s", description, extension, output_path)

        elif isinstance(data, ee.FeatureCollection):
            geojson = data.getInfo()
            gdf = gpd.GeoDataFrame.from_features(geojson["features"], crs="EPSG:4326")
            output_path = os.path.join(output_dir, f"{description}.geojson")
            gdf.to_file(output_path, driver="GeoJSON")
            logger.info("Exportação local %s.geojson concluída em %s", description, output_path)

        else:
            raise ValueError(
                f"Tipo de dado não suportado para exportação: {type(data)}"
            )

        return output_path

    except Exception as e:
        logger.exception("Erro ao exportar localmente %s: %s", description, e)
        raise
