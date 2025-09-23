import logging
from datetime import datetime, timezone

import ee

logger = logging.getLogger(__name__)


def get_sentinel_collection(polygon):
    """Obtém coleção de imagens Sentinel-2 para a região de interesse.

    Args:
        polygon: ee.Geometry, Polígono da região de interesse.

    Returns:
        ee.ImageCollection, Coleção de imagens Sentinel-2 filtrada.
    """
    collection = (
        ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED")
        .filterBounds(polygon)
        .filter(ee.Filter.lt("CLOUDY_PIXEL_PERCENTAGE", 20))
    )
    # print(f"Bandas disponíveis na coleção Sentinel-2: {collection.first().bandNames().getInfo()}")
    return collection


def get_best_image(collection, start_date, end_date, polygon=None):
    logger.debug("%s", "########################################################")
    logger.debug("Start date: %s", start_date)
    logger.debug("End date: %s", end_date)
    filtered = collection.filterDate(start_date, end_date).filterMetadata(
        "CLOUDY_PIXEL_PERCENTAGE", "less_than", 20
    )

    logger.debug(
        "Número de imagens após filtragem por data e nuvens: %s", filtered.size().getInfo()
    )
    logger.debug("%s", "########################################################")

    # Mosaic the filtered collection to cover the entire area, sorting by lowest cloud cover first
    if filtered.size().getInfo() > 0:
        best = filtered.sort("CLOUDY_PIXEL_PERCENTAGE").mosaic()
    else:
        raise ValueError("Nenhuma imagem válida encontrada para as datas e região fornecidas.")

    # Get timestamp from the first image in the filtered collection
    first_image = filtered.sort("CLOUDY_PIXEL_PERCENTAGE").first()
    timestamp = None
    if first_image:
        timestamp = first_image.get("system:time_start").getInfo()
        logger.debug("Timestamp bruto: %s", timestamp)

    if timestamp is None:
        raise ValueError("Não foi possível obter o timestamp da imagem. Verifique a coleção ou as datas.")

    # Convert timestamp to date
    date = datetime.fromtimestamp(timestamp / 1000, tz=timezone.utc).strftime("%Y-%m-%d")
    return best, date


def calculate_differences(pre_fire, post_fire):
    """Calcula índices NDVI, NBR e suas diferenças, além do RBR.

    Args:
        pre_fire: ee.Image, Imagem pré-fogo.
        post_fire: ee.Image, Imagem pós-fogo.

    Returns:
        tuple, Contendo NDVI pré/pós, NBR pré/pós, ΔNDVI, ΔNBR e RBR.
    """
    # Cálculo do NDVI
    pre_ndvi = pre_fire.normalizedDifference(["B8", "B4"]).rename("NDVI")
    post_ndvi = post_fire.normalizedDifference(["B8", "B4"]).rename("NDVI")

    # Cálculo do NBR
    pre_nbr = pre_fire.normalizedDifference(["B8", "B12"]).rename("NBR")
    post_nbr = post_fire.normalizedDifference(["B8", "B12"]).rename("NBR")

    # Diferenças
    delta_ndvi = pre_ndvi.subtract(post_ndvi).rename("DeltaNDVI")
    delta_nbr = pre_nbr.subtract(post_nbr).rename("DeltaNBR")

    # Cálculo do RBR
    rbr = pre_nbr.subtract(post_nbr).divide(pre_nbr.add(1.001)).rename("RBR")

    return pre_ndvi, post_ndvi, pre_nbr, post_nbr, delta_ndvi, delta_nbr, rbr
