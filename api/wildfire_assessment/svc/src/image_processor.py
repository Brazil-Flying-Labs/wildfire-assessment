import ee


def get_sentinel_collection(polygon):
    """Obtém coleção de imagens Sentinel-2 para a região de interesse.

    Args:
        polygon: ee.Geometry, Polígono da região de interesse.

    Returns:
        ee.ImageCollection, Coleção de imagens Sentinel-2 filtrada.
    """
    collection = (ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED')
                  .filterBounds(polygon)
                  .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', 20)))
    # print(f"Bandas disponíveis na coleção Sentinel-2: {collection.first().bandNames().getInfo()}")
    return collection


def get_best_image(collection, start_date, end_date, polygon=None):  # Adicione polygon como param opcional
    filtered = collection.filterDate(start_date, end_date) \
                         .filterMetadata('CLOUDY_PIXEL_PERCENTAGE', 'less_than', 10)  # Filtre nuvens <10%
    composite = filtered.median()  # Ou .mean() para média; .qualityMosaic('NDVI') para priorizar vegetação
    if polygon:
        composite = composite.clip(polygon)
    return composite


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