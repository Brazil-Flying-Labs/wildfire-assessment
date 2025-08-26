import ee


def mask_clouds(image):
    """Mascara nuvens em uma imagem Sentinel-2 usando a banda QA60.

    Args:
        image: ee.Image, Imagem Sentinel-2.

    Returns:
        ee.Image, Imagem com nuvens mascaradas.
    """
    qa = image.select('QA60')
    cloud_bit_mask = 1 << 10
    cirrus_bit_mask = 1 << 11
    mask = qa.bitwiseAnd(cloud_bit_mask).eq(0).And(qa.bitwiseAnd(cirrus_bit_mask).eq(0))
    return image.updateMask(mask)


def get_sentinel_collection(polygon, cloud_percentage=20):
    """Recupera e filtra a coleção de imagens Sentinel-2.

    Args:
        polygon: ee.Geometry, Região de interesse.
        cloud_percentage: float, Percentual máximo de cobertura de nuvens.

    Returns:
        ee.ImageCollection, Coleção Sentinel-2 filtrada.
    """
    return (ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED')
            .filterBounds(polygon)
            .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', cloud_percentage))
            .map(mask_clouds))


def get_best_image(collection, start_date, end_date):
    """Seleciona a melhor imagem (menor cobertura de nuvens) de uma coleção.

    Args:
        collection: ee.ImageCollection, Coleção de imagens.
        start_date: str, Data inicial (YYYY-MM-DD).
        end_date: str, Data final (YYYY-MM-DD).

    Returns:
        ee.Image, Melhor imagem escalada por 0.0001.

    Raises:
        Exception: Se nenhuma imagem for encontrada no intervalo de datas.
    """
    img = (collection
           .filterDate(start_date, end_date)
           .sort('CLOUDY_PIXEL_PERCENTAGE')
           .first())
    if img is None:
        raise Exception(f"Nenhuma imagem encontrada entre {start_date} e {end_date}")
    return img.select('B.*').multiply(0.0001)


def calculate_ndvi(image):
    """Calcula o NDVI de uma imagem Sentinel-2.

    Args:
        image: ee.Image, Imagem com bandas B8 (NIR) e B4 (Red).

    Returns:
        ee.Image, Imagem NDVI.
    """
    return image.normalizedDifference(['B8', 'B4']).rename('NDVI')


def calculate_nbr(image):
    """Calcula o NBR de uma imagem Sentinel-2.

    Args:
        image: ee.Image, Imagem com bandas B8 (NIR) e B12 (SWIR).

    Returns:
        ee.Image, Imagem NBR.
    """
    return image.expression(
        '(NIR - SWIR) / (NIR + SWIR)',
        {'NIR': image.select('B8'), 'SWIR': image.select('B12')}
    ).rename('NBR')


def calculate_differences(pre_image, post_image):
    """Calcula ΔNDVI, ΔNBR e RBR entre imagens pré e pós-fogo.

    Args:
        pre_image: ee.Image, Imagem pré-fogo.
        post_image: ee.Image, Imagem pós-fogo.

    Returns:
        tuple: (ee.Image, ee.Image, ee.Image, ee.Image, ee.Image, ee.Image),
               NDVI pré-fogo, NDVI pós-fogo, NBR pré-fogo, NBR pós-fogo, ΔNDVI, ΔNBR, RBR.
    """
    pre_ndvi = calculate_ndvi(pre_image).rename('NDVI_preFire')
    post_ndvi = calculate_ndvi(post_image).rename('NDVI_postFire')
    pre_nbr = calculate_nbr(pre_image).rename('NBR_preFire')
    post_nbr = calculate_nbr(post_image).rename('NBR_postFire')
    
    delta_ndvi = pre_ndvi.subtract(post_ndvi).rename('DeltaNDVI')
    delta_nbr = pre_nbr.subtract(post_nbr).rename('DeltaNBR')
    rbr = delta_nbr.divide(pre_nbr.add(1.001)).rename('RBR')
    
    return pre_ndvi, post_ndvi, pre_nbr, post_nbr, delta_ndvi, delta_nbr, rbr