import io
import logging
import os
import tempfile
import time
from typing import Any, Dict, Optional

import ee
import geopandas as gpd
import numpy as np
import rasterio
import requests
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


class ImageExporter:
    """Exportador de imagens do Google Earth Engine para arquivos locais."""
    
    # Configurações
    MIN_SCALE = 60
    MAX_RETRIES = 5
    DOWNLOAD_TIMEOUT = 300
    CONNECT_TIMEOUT = 10
    CHUNK_SIZE = 8192
    
    @classmethod
    def export_local(
        cls, 
        data: ee.Image | ee.FeatureCollection, 
        description: str, 
        region: ee.Geometry, 
        extension: str, 
        output_dir: str = "exports"
    ) -> Optional[str]:
        """
        Exporta dados do Google Earth Engine para arquivos locais.
        
        Args:
            data: Imagem ou FeatureCollection do EE
            description: Nome do arquivo (sem extensão)
            region: Região de exportação
            extension: Extensão do arquivo (tif, jpg, geojson)
            output_dir: Diretório de saída
            
        Returns:
            Caminho do arquivo salvo ou None em caso de erro
        """
        try:
            logger.debug("Iniciando exportação: %s.%s", description, extension)
            os.makedirs(output_dir, exist_ok=True)

            if isinstance(data, ee.Image):
                return cls._export_image(data, description, region, extension, output_dir)
            elif isinstance(data, ee.FeatureCollection):
                return cls._export_feature_collection(data, description, output_dir)
            else:
                raise ValueError(f"Tipo não suportado: {type(data)}")

        except Exception as e:
            logger.exception("Erro ao exportar %s: %s", description, e)
            return None

    @classmethod
    def _export_image(
        cls, 
        image: ee.Image, 
        description: str, 
        region: ee.Geometry, 
        extension: str, 
        output_dir: str
    ) -> Optional[str]:
        """Exporta uma imagem EE para arquivo local."""
        # Prepara imagem com overlay se necessário
        processed_image = cls._prepare_image_with_overlay(image)
        
        # Calcula escala otimizada
        scale = cls._calculate_optimal_scale(processed_image, region)
        
        # Obtém URL de download
        download_url = cls._get_download_url(processed_image, description, region, scale, extension)
        if not download_url:
            return None

        # Faz download e processa arquivo
        output_path = os.path.join(output_dir, f"{description}.{extension}")
        
        if extension in ["jpg", "jpeg"]:
            return cls._download_jpeg(download_url, output_path)
        else:
            return cls._download_geotiff(download_url, output_path, description)

    @classmethod
    def _prepare_image_with_overlay(cls, image: ee.Image) -> ee.Image:
        """Prepara imagem com overlay do polígono se necessário."""
        overlay_polygon = getattr(image, "overlay_polygon", None)
        
        if not overlay_polygon:
            return image

        # Aplica overlay
        bands = ["R", "G", "B"] if "R" in image.bandNames().getInfo() else image.bandNames().getInfo()
        
        visualized = image.visualize(
            bands=bands,
            min=0,
            max=255
        )
        
        overlay = ee.Image().paint(overlay_polygon, 1, 3).visualize(
            palette=["red"], 
            opacity=0.7
        )
        
        return visualized.blend(overlay)

    @classmethod
    def _calculate_optimal_scale(cls, image: ee.Image, region: ee.Geometry) -> float:
        """Calcula escala otimizada para exportação."""
        if region:
            return EXPORT_SCALE

        try:
            poly_geom = image.geometry().bounds(1)
            bounds = poly_geom.getInfo()["coordinates"][0]
            lon_min, lat_min = bounds[0]
            lon_max, lat_max = bounds[2]
            
            width_m = abs(lon_max - lon_min) * 111320
            height_m = abs(lat_max - lat_min) * 111320
            max_dim = max(width_m, height_m)
            
            scale = max_dim / 32768
            scale = max(scale, cls.MIN_SCALE)
            
            if scale < cls.MIN_SCALE or max_dim / scale > 32768:
                scale = max(cls.MIN_SCALE, 1000)
                
            return scale
            
        except Exception as e:
            logger.warning("Erro ao calcular escala: %s", e)
            return max(cls.MIN_SCALE, 1000)

    @classmethod
    def _get_download_url(
        cls, 
        image: ee.Image, 
        description: str, 
        region: ee.Geometry, 
        scale: float, 
        extension: str
    ) -> Optional[str]:
        """Obtém URL de download do EE com retry automático."""
        download_params = cls._build_download_params(description, scale, region, extension)
        
        for attempt in range(cls.MAX_RETRIES):
            try:
                logger.debug("Solicitando URL para %s (tentativa %s)", description, attempt + 1)
                download_url = image.getDownloadURL(download_params)
                logger.debug("URL obtida para %s", description)
                return download_url
                
            except Exception as e:
                error_msg = str(e)
                if cls._is_size_error(error_msg):
                    # Aumenta escala para reduzir tamanho
                    old_scale = download_params['scale']
                    download_params['scale'] = max(old_scale * 2, old_scale + 1)
                    logger.warning("Aumentando escala de %s para %s", old_scale, download_params['scale'])
                    continue
                else:
                    logger.error("Erro ao obter URL para %s: %s", description, e)
                    return None

        logger.error("Falha ao obter URL para %s após %s tentativas", description, cls.MAX_RETRIES)
        return None

    @classmethod
    def _build_download_params(
        cls, 
        description: str, 
        scale: float, 
        region: ee.Geometry, 
        extension: str
    ) -> Dict[str, Any]:
        """Constrói parâmetros para download."""
        params = {
            "name": description,
            "scale": scale,
            "crs": EXPORT_CRS,
            "maxPixels": EXPORT_MAX_PIXELS,
        }

        if extension in ["jpg", "jpeg"]:
            params["format"] = "jpg"
        else:
            params["format"] = "GEO_TIFF"

        if region is not None:
            params["region"] = region

        return params

    @classmethod
    def _is_size_error(cls, error_msg: str) -> bool:
        """Verifica se o erro é relacionado ao tamanho da requisição."""
        size_errors = [
            'Total request size',
            'must be less than or equal', 
            'request size'
        ]
        return any(error in error_msg for error in size_errors)

    @classmethod
    def _download_jpeg(cls, download_url: str, output_path: str) -> Optional[str]:
        """Faz download de imagem JPEG."""
        try:
            response = cls._make_request(download_url)
            if not response:
                return None

            with open(output_path, "wb") as f:
                for chunk in response.iter_content(chunk_size=cls.CHUNK_SIZE):
                    if chunk:
                        f.write(chunk)

            cls._validate_file(output_path)
            logger.info("JPEG exportado: %s", output_path)
            return output_path

        except Exception as e:
            logger.error("Erro ao baixar JPEG: %s", e)
            return None

    @classmethod
    def _download_geotiff(cls, download_url: str, output_path: str, description: str) -> Optional[str]:
        """Faz download e processa arquivo GeoTIFF."""
        try:
            response = cls._make_request(download_url)
            if not response:
                return None

            # Processa TIFF em arquivo temporário
            with tempfile.NamedTemporaryFile(delete=False) as tmp_file:
                for chunk in response.iter_content(chunk_size=cls.CHUNK_SIZE):
                    if chunk:
                        tmp_file.write(chunk)
                tmp_path = tmp_file.name

            try:
                # Valida e processa o TIFF
                cls._process_tiff_file(tmp_path, output_path, description)
                cls._validate_file(output_path)
                logger.info("GeoTIFF exportado: %s", output_path)
                return output_path

            finally:
                # Limpa arquivo temporário
                try:
                    os.remove(tmp_path)
                except Exception:
                    pass

        except Exception as e:
            logger.error("Erro ao baixar GeoTIFF: %s", e)
            return None

    @classmethod
    def _make_request(cls, url: str) -> Optional[requests.Response]:
        """Faz requisição HTTP com retry mechanism."""
        session = requests.Session()
        
        retry_strategy = Retry(
            total=cls.MAX_RETRIES,
            backoff_factor=2,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET"],
        )
        
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("https://", adapter)
        session.mount("http://", adapter)

        for attempt in range(cls.MAX_RETRIES):
            try:
                logger.debug("Tentativa %s para baixar URL", attempt + 1)
                response = session.get(
                    url, 
                    stream=True, 
                    timeout=(cls.CONNECT_TIMEOUT, cls.DOWNLOAD_TIMEOUT)
                )
                
                if response.status_code == 200:
                    return response
                else:
                    raise Exception(f"HTTP {response.status_code}: {response.text}")

            except (RequestException, ReqConnectionError, ReqTimeout) as e:
                logger.warning("Erro de rede (tentativa %s): %s", attempt + 1, e)
                if attempt < cls.MAX_RETRIES - 1:
                    sleep_time = min(60, 2 ** attempt)
                    time.sleep(sleep_time)
                    continue
                else:
                    raise

        return None

    @classmethod
    def _process_tiff_file(cls, tmp_path: str, output_path: str, description: str):
        """Processa e valida arquivo TIFF."""
        # Verifica se o arquivo é um TIFF válido
        cls._validate_tiff_header(tmp_path)
        
        # Abre e processa o TIFF
        with rasterio.open(tmp_path) as src:
            profile = src.profile.copy()
            array = src.read()

        # Ajusta profile baseado no tipo de imagem
        cls._adjust_profile(profile, array, description)
        
        # Escreve arquivo final
        with rasterio.open(output_path, "w", **profile) as dst:
            dst.write(array)

    @classmethod
    def _validate_tiff_header(cls, file_path: str):
        """Valida se o arquivo tem header TIFF válido."""
        with open(file_path, "rb") as f:
            header = f.read(4)
            
        if header not in [b"II*\x00", b"MM\x00*"]:
            raise ValueError("Arquivo não é um TIFF válido")

    @classmethod
    def _adjust_profile(cls, profile: Dict, array: np.ndarray, description: str):
        """Ajusta profile do rasterio baseado no array e descrição."""
        # Define dimensões básicas
        profile.update({
            "width": array.shape[-1],
            "height": array.shape[-2],
            "count": array.shape[0],
            "dtype": str(array.dtype)
        })

        # Configurações específicas para imagens RGB
        if any(name in description for name in ["RGB_PreFire", "RGB_PostFire", "RBR"]):
            if array.shape[0] != 3:
                raise ValueError(f"Esperadas 3 bandas para {description}, encontradas {array.shape[0]}")
            
            profile.update({
                "count": 3,
                "dtype": "uint8",
                "photometric": "rgb"
            })

    @classmethod
    def _validate_file(cls, file_path: str):
        """Valida se arquivo existe e tem conteúdo."""
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Arquivo não encontrado: {file_path}")
            
        if os.path.getsize(file_path) == 0:
            raise ValueError(f"Arquivo vazio: {file_path}")

    @classmethod
    def _export_feature_collection(
        cls, 
        features: ee.FeatureCollection, 
        description: str, 
        output_dir: str
    ) -> str:
        """Exporta FeatureCollection para GeoJSON."""
        geojson_data = features.getInfo()
        gdf = gpd.GeoDataFrame.from_features(geojson_data["features"], crs="EPSG:4326")
        
        output_path = os.path.join(output_dir, f"{description}.geojson")
        gdf.to_file(output_path, driver="GeoJSON")
        
        logger.info("GeoJSON exportado: %s", output_path)
        return output_path


# Função de compatibilidade (mantém interface original)
def export_local(data, description, region, extension, output_dir="exports", min_scale=60):
    """
    Exporta dados do Google Earth Engine para arquivos locais.
    
    Args:
        data: ee.Image ou ee.FeatureCollection
        description: Nome do arquivo (sem extensão)
        region: Região de exportação
        extension: Extensão do arquivo
        output_dir: Diretório de saída
        min_scale: Escala mínima (para compatibilidade)
        
    Returns:
        Caminho do arquivo salvo ou None
    """
    ImageExporter.MIN_SCALE = min_scale
    return ImageExporter.export_local(data, description, region, extension, output_dir)