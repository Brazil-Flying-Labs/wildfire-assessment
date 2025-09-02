import ee


def get_sentinel_collection(polygon):
    """Obtém coleção de imagens Sentinel-2 para a região de interesse.

    Args:
        polygon: ee.Geometry, Polígono da região de interesse.

    Returns:
        ee.ImageCollection, Coleção de imagens Sentinel-2 filtrada.
    """
    collection = (ee.ImageCollection('COPERNICUS/S2_SR')
                  .filterBounds(polygon)
                  .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', 20)))
    print(f"Bandas disponíveis na coleção Sentinel-2: {collection.first().bandNames().getInfo()}")
    return collection


def get_best_image(collection, start_date, end_date):
    """Seleciona a melhor imagem da coleção com base na cobertura de nuvens.

    Args:
        collection: ee.ImageCollection, Coleção de imagens filtrada.
        start_date: str, Data de início (formato YYYY-MM-DD).
        end_date: str, Data de fim (formato YYYY-MM-DD).

    Returns:
        ee.Image, Imagem com menor cobertura de nuvens.
    """
    image = (collection.filterDate(start_date, end_date)
             .sort('CLOUDY_PIXEL_PERCENTAGE')
             .first())
    print(f"Bandas da imagem selecionada ({start_date} a {end_date}): {image.bandNames().getInfo()}")
    return image


def calculate_differences(pre_fire, post_fire):
    """Calcula índices NDVI, NBR e suas diferenças, além do RBR.

    Args:
        pre_fire: ee.Image, Imagem pré-fogo.
        post_fire: ee.Image, Imagem pós-fogo.

    Returns:
        tuple, Contendo NDVI pré/pós, NBR pré/pós, ΔNDVI, ΔNBR e RBR.
    """
    # Cálculo do NDVI
    pre_ndvi = pre_fire.normalizedDifference(['B8', 'B4']).rename('NDVI')
    post_ndvi = post_fire.normalizedDifference(['B8', 'B4']).rename('NDVI')
    
    # Cálculo do NBR
    pre_nbr = pre_fire.normalizedDifference(['B8', 'B12']).rename('NBR')
    post_nbr = post_fire.normalizedDifference(['B8', 'B12']).rename('NBR')
    
    # Diferenças
    delta_ndvi = pre_ndvi.subtract(post_ndvi).rename('DeltaNDVI')
    delta_nbr = pre_nbr.subtract(post_nbr).rename('DeltaNBR')
    
    # Cálculo do RBR
    rbr = pre_nbr.subtract(post_nbr).divide(pre_nbr.add(1.001)).rename('RBR')
    
    return pre_ndvi, post_ndvi, pre_nbr, post_nbr, delta_ndvi, delta_nbr, rbr