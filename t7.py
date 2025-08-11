import requests
import os
import zipfile
import rasterio
from rasterio.warp import calculate_default_transform, reproject, Resampling
import glob
from rasterio.mask import mask
from shapely.geometry import mapping, Polygon, MultiPolygon, shape
from pyproj import Transformer
from rasterio.merge import merge
import numpy as np
import shutil
import time
import geojson

# --- CONFIGURAÇÕES ---
USERNAME = "camargo.advanced@gmail.com"
PASSWORD = "nastyz-Qepxat-fekro2"
BBOX_POLYGON = [
    [-47.848, -21.677999999999997],
    [-47.848, -21.514],
    [-47.6762, -21.514],
    [-47.6762, -21.677999999999997],
    [-47.848, -21.677999999999997]
]
START_DATE = "2024-07-01"
END_DATE = "2024-07-25"
MAX_CLOUD = 5
SAFE_DIR = "sentinel_downloads"
GEOJSON_PATH = "jatai.geojson"
os.makedirs(SAFE_DIR, exist_ok=True)
TEMP_DIR = os.path.join(SAFE_DIR, "temp")
os.makedirs(TEMP_DIR, exist_ok=True)
PROCESSED_DIR = os.path.join(SAFE_DIR, "processed")
os.makedirs(PROCESSED_DIR, exist_ok=True)

CATALOGUE_URL = "https://catalogue.dataspace.copernicus.eu/odata/v1/Products"

# --- FUNÇÕES ---

def convert_bbox(bbox4326, from_epsg="4326", to_epsg="32723"):
    transformer = Transformer.from_crs(from_epsg, to_epsg, always_xy=True)
    converted = [transformer.transform(lon, lat) for lon, lat in bbox4326]
    return converted

def bbox_to_wkt(bbox):
    if bbox[-1] != bbox[0]:
        bbox = bbox + [bbox[0]]
    polygon = Polygon(bbox)
    return polygon.wkt

def get_token():
    r = requests.post(
        "https://identity.dataspace.copernicus.eu/auth/realms/CDSE/protocol/openid-connect/token",
        data={"client_id": "cdse-public", "username": USERNAME, "password": PASSWORD, "grant_type": "password"},
    )
    r.raise_for_status()
    return r.json()["access_token"]

def search_products(token, wkt):
    query = (
        f"$filter=Collection/Name eq 'SENTINEL-2' and "
        f"Attributes/OData.CSC.StringAttribute/any(a:a/Name eq 'productType' and a/Value eq 'S2MSI2A') and "
        f"ContentDate/Start ge {START_DATE}T00:00:00.000Z and ContentDate/Start le {END_DATE}T23:59:59.999Z and "
        f"OData.CSC.Intersects(area=geography'SRID=4326;{wkt}') and "
        f"Attributes/OData.CSC.DoubleAttribute/any(a:a/Name eq 'cloudCover' and a/Value le {MAX_CLOUD})"
    )
    url = f"{CATALOGUE_URL}?$orderby=ContentDate/Start desc&$top=1&{query}"
    headers = {"Authorization": f"Bearer {token}"}
    r = requests.get(url, headers=headers)
    r.raise_for_status()
    return r.json().get("value", [])

def unzip_file(zip_path, extract_to):
    try:
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(extract_to)
        print(f"Arquivo extraído para: {extract_to}")
    except zipfile.BadZipFile:
        print(f"Erro: {zip_path} não é um arquivo ZIP válido.")

def download_product(token, product_id, title, out_dir):
    unzip_dir = os.path.join(out_dir, title)
    zip_path = os.path.join(out_dir, title + ".zip")

    if os.path.exists(unzip_dir):
        print(f"[INFO] Produto {title} já existe extraído em {unzip_dir}, pulando download e unzip.")
        return unzip_dir

    try:
        if os.path.exists(zip_path):
            try:
                with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                    bad = zip_ref.testzip()
                    if bad is None:
                        print(f"[INFO] ZIP válido encontrado: {zip_path}. Extraindo...")
                        unzip_file(zip_path, out_dir)
                        return unzip_dir
                    else:
                        print(f"[WARN] ZIP corrompido encontrado: {zip_path}. Removendo.")
                        os.remove(zip_path)
            except zipfile.BadZipFile:
                print(f"[WARN] ZIP corrompido encontrado: {zip_path}. Removendo.")
                os.remove(zip_path)

        url = f"https://zipper.dataspace.copernicus.eu/odata/v1/Products({product_id})/$value"
        headers = {"Authorization": f"Bearer {token}"}

        print(f"Iniciando download: {url}")
        with requests.get(url, headers=headers, stream=True) as r:
            r.raise_for_status()
            with open(zip_path, "wb") as f:
                for chunk in r.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
        print(f"Download concluído: {zip_path}")

        unzip_file(zip_path, out_dir)
        return unzip_dir
    except requests.exceptions.HTTPError as e:
        print(f"Erro no download: {e}")
    except Exception as e:
        print(f"Erro inesperado: {e}")
    return None

def resample_to_match(src_path, ref_path, out_path):
    if os.path.exists(out_path):
        try:
            os.remove(out_path)
            print(f"[INFO] Arquivo existente {out_path} removido para sobrescrever.")
        except PermissionError:
            print(f"[ERRO] Não foi possível remover {out_path}: Permissão negada.")
            return

    with rasterio.open(ref_path) as ref:
        dst_transform, dst_width, dst_height = calculate_default_transform(
            ref.crs, ref.crs, ref.width, ref.height, *ref.bounds
        )
        dst_profile = ref.profile.copy()
        dst_profile.update({"transform": dst_transform, "width": dst_width, "height": dst_height})
        
        with rasterio.open(src_path) as src:
            data = src.read(out_shape=(src.count, dst_height, dst_width), resampling=Resampling.bilinear)
        
        with rasterio.open(out_path, 'w', **dst_profile) as dst:
            dst.write(data)
    print(f"[OK] Banda reamostrada salva em: {out_path}")

def find_band_path(safe_dir, band_code, resolution):
    pattern = os.path.join(safe_dir, "GRANULE/*/IMG_DATA/R{}/*_{}_{}.jp2".format(resolution, band_code, resolution))
    matches = glob.glob(pattern)
    if not matches:
        raise FileNotFoundError(f"Banda {band_code} ({resolution}) não encontrada em {safe_dir}")
    return matches[0]

def crop_raster_by_geometry(src_path, geometry, out_path):
    with rasterio.open(src_path) as src:
        print(f"CRS do raster: {src.crs}")
        print(f"Limites do raster (em CRS): {src.bounds}")
        # Converter geometria para o CRS do raster
        transformer = Transformer.from_crs("EPSG:4326", src.crs, always_xy=True)
        if geometry.geom_type == 'MultiPolygon':
            transformed_geoms = []
            for geom in geometry.geoms:
                coords = list(geom.exterior.coords[:-1])  # Remover o último ponto duplicado
                transformed_coords = [transformer.transform(lon, lat) for lon, lat in coords]
                transformed_geoms.append(Polygon(transformed_coords))
            transformed_geometry = MultiPolygon(transformed_geoms)
        else:
            coords = list(geometry.exterior.coords[:-1])
            transformed_coords = [transformer.transform(lon, lat) for lon, lat in coords]
            transformed_geometry = Polygon(transformed_coords)

        print(f"Geometria transformada: {transformed_geometry.bounds}")
        # Verificar sobreposição com os limites do raster
        raster_bounds = Polygon([
            [src.bounds.left, src.bounds.bottom],
            [src.bounds.left, src.bounds.top],
            [src.bounds.right, src.bounds.top],
            [src.bounds.right, src.bounds.bottom],
            [src.bounds.left, src.bounds.bottom]
        ])
        if not transformed_geometry.intersects(raster_bounds):
            print(f"ERRO: Geometria transformada não se sobrepõe aos limites do raster: {raster_bounds.bounds}")
            return

        geojson = [mapping(transformed_geometry)]

        nodata_val = src.nodata if src.nodata is not None else 0
        try:
            out_image, out_transform = mask(src, geojson, crop=True, nodata=nodata_val, all_touched=True)
            print(f"Shape da imagem recortada: {out_image.shape}")
            print(f"Transformação recortada: {out_transform}")
        except ValueError as e:
            print(f"Erro ao recortar: {e}. Verifique se a geometria está dentro da área do raster.")
            return

        out_meta = src.meta.copy()
        out_meta.update({
            "driver": "GTiff",
            "height": out_image.shape[1],
            "width": out_image.shape[2],
            "transform": out_transform,
            "nodata": nodata_val
        })

        with rasterio.open(out_path, "w", **out_meta) as dest:
            dest.write(out_image)

        print(f"[OK] Raster recortado salvo em: {out_path}")
        if out_image.shape[1] == 0 or out_image.shape[2] == 0:
            print(f"[ERRO] Imagem recortada está vazia. Verifique se a geometria está dentro da área da imagem.")

def get_geometry_from_geojson(geojson_path):
    with open(geojson_path, 'r', encoding='utf-8') as f:
        data = geojson.load(f)
    # Extrair o primeiro feature e sua geometria (MultiPolygon)
    geometry = shape(data['features'][0]['geometry'])
    return geometry

def calculate_index(band_nir_path, band_red_path, out_path, index_type="NDVI"):
    with rasterio.open(band_nir_path) as nir_src, rasterio.open(band_red_path) as red_src:
        nir = nir_src.read(1).astype("float32")
        red = red_src.read(1).astype("float32")
        profile = nir_src.profile

    if index_type == "NDVI":
        index = (nir - red) / (nir + red + 1e-10)
    elif index_type == "NBR":
        index = (nir - red) / (nir + red + 1e-10)
    else:
        raise ValueError("Índice desconhecido.")

    profile.update(dtype=rasterio.float32, count=1)

    with rasterio.open(out_path, "w", **profile) as dst:
        dst.write(index, 1)

    print(f"[OK] {index_type} salvo em: {out_path}")

def reproject_raster(src_path, dst_crs, out_path):
    with rasterio.open(src_path) as src:
        transform, width, height = calculate_default_transform(
            src.crs, dst_crs, src.width, src.height, *src.bounds)
        kwargs = src.meta.copy()
        kwargs.update({
            'crs': dst_crs,
            'transform': transform,
            'width': width,
            'height': height
        })

        with rasterio.open(out_path, 'w', **kwargs) as dst:
            for i in range(1, src.count + 1):
                reproject(
                    source=rasterio.band(src, i),
                    destination=rasterio.band(dst, i),
                    src_transform=src.transform,
                    src_crs=src.crs,
                    dst_transform=transform,
                    dst_crs=dst_crs,
                    resampling=Resampling.nearest)
    print(f"[OK] Raster reprojetado salvo em: {out_path}")

def merge_rasters(raster_paths, out_path, reference_crs="EPSG:32722"):
    reprojected_paths = []
    for path in raster_paths:
        with rasterio.open(path) as src:
            if src.crs != rasterio.crs.CRS.from_string(reference_crs):
                reprojected_path = os.path.join(os.path.dirname(path), f"reprojected_{os.path.basename(path)}")
                reproject_raster(path, rasterio.crs.CRS.from_string(reference_crs), reprojected_path)
                reprojected_paths.append(reprojected_path)
            else:
                reprojected_paths.append(path)

    src_files = [rasterio.open(path) for path in reprojected_paths]
    mosaic, out_trans = merge(src_files)
    out_meta = src_files[0].meta.copy()
    out_meta.update({"height": mosaic.shape[1], "width": mosaic.shape[2], "transform": out_trans})
    with rasterio.open(out_path, "w", **out_meta) as dest:
        dest.write(mosaic)
    print(f"[OK] Rasters mesclados salvos em: {out_path}")

    for f in src_files:
        f.close()

    for path in reprojected_paths:
        if "reprojected_" in path and os.path.exists(path):
            for _ in range(5):
                try:
                    os.remove(path)
                    print(f"[INFO] Arquivo temporário {path} removido.")
                    break
                except PermissionError:
                    print(f"[WARN] Tentativa de remover {path} falhou. Aguardando 1 segundo...")
                    time.sleep(1)
            else:
                print(f"[ERRO] Não foi possível remover {path} após 5 tentativas.")

# --- MAIN ---
def main():
    temp_dir = TEMP_DIR
    if os.path.exists(temp_dir):
        shutil.rmtree(temp_dir)
    os.makedirs(temp_dir, exist_ok=True)

    geometry = get_geometry_from_geojson(GEOJSON_PATH)
    print("Gerando token...")
    token = get_token()
    wkt = bbox_to_wkt(BBOX_POLYGON)
    print(wkt)

    print("Buscando produtos Sentinel-2 L2A para 22KHA...")
    products_kha = search_products(token, wkt)
    if not products_kha:
        print("Nenhum produto encontrado para 22KHA.")
        return

    product_kha = products_kha[0]
    title_kha = product_kha["Name"]
    product_id_kha = product_kha.get("Id")
    safe_path_kha = download_product(token, product_id_kha, title_kha, SAFE_DIR)
    if not safe_path_kha:
        print("Erro ao obter o produto 22KHA.")
        return

    # Buscar tile adjacente (ex.: 23KKS)
    wkt_kks = "POLYGON((-48.0 -21.3, -48.0 -21.0, -47.0 -21.0, -47.0 -21.3, -48.0 -21.3))"
    print("Buscando produtos Sentinel-2 L2A para 23KKS...")
    products_kks = search_products(token, wkt_kks)
    if not products_kks:
        print("Nenhum produto encontrado para 23KKS. Verifique a data ou área.")
        return

    product_kks = products_kks[0]
    title_kks = product_kks["Name"]
    product_id_kks = product_kks.get("Id")
    safe_path_kks = download_product(token, product_id_kks, title_kks, SAFE_DIR)
    if not safe_path_kks:
        print("Erro ao obter o produto 23KKS.")
        return

    # Encontrar bandas para ambos os tiles
    b04_path_kha = find_band_path(safe_path_kha, "B04", "10m")
    b08_path_kha = find_band_path(safe_path_kha, "B08", "10m")
    b12_path_kha = find_band_path(safe_path_kha, "B12", "20m")
    b04_path_kks = find_band_path(safe_path_kks, "B04", "10m")
    b08_path_kks = find_band_path(safe_path_kks, "B08", "10m")
    b12_path_kks = find_band_path(safe_path_kks, "B12", "20m")

    # Reamostrar B12 para 10m para ambos
    b12_resampled_path_kha = os.path.join(TEMP_DIR, "B12_10m_kha.tif")
    b12_resampled_path_kks = os.path.join(TEMP_DIR, "B12_10m_kks.tif")
    resample_to_match(b12_path_kha, b04_path_kha, b12_resampled_path_kha)
    resample_to_match(b12_path_kks, b04_path_kks, b12_resampled_path_kks)

    # Mesclar as bandas
    merged_b04_path = os.path.join(TEMP_DIR, "merged_B04.tif")
    merged_b08_path = os.path.join(TEMP_DIR, "merged_B08.tif")
    merged_b12_path = os.path.join(TEMP_DIR, "merged_B12.tif")
    merge_rasters([b04_path_kha, b04_path_kks], merged_b04_path)
    merge_rasters([b08_path_kha, b08_path_kks], merged_b08_path)
    merge_rasters([b12_resampled_path_kha, b12_resampled_path_kks], merged_b12_path)

    # Cortar os rasters mesclados usando a geometria
    b04_cropped = os.path.join(TEMP_DIR, "B04_cropped.tif")
    b08_cropped = os.path.join(TEMP_DIR, "B08_cropped.tif")
    b12_cropped = os.path.join(TEMP_DIR, "B12_cropped.tif")
    crop_raster_by_geometry(merged_b04_path, geometry, b04_cropped)
    crop_raster_by_geometry(merged_b08_path, geometry, b08_cropped)
    crop_raster_by_geometry(merged_b12_path, geometry, b12_cropped)

    # Verificar os arquivos recortados
    for cropped_path in [b04_cropped, b08_cropped, b12_cropped]:
        if not os.path.exists(cropped_path):
            print(f"[ERRO] Arquivo recortado não foi criado: {cropped_path}")
            return
        with rasterio.open(cropped_path) as src:
            if src.width == 0 or src.height == 0:
                print(f"[ERRO] Arquivo recortado está vazio: {cropped_path}")
                return

    # Calcular índices
    ndvi_path = os.path.join(TEMP_DIR, "NDVI.tif")
    calculate_index(b08_cropped, b04_cropped, ndvi_path, "NDVI")
    nbr_path = os.path.join(TEMP_DIR, "NBR.tif")
    calculate_index(b08_cropped, b12_cropped, nbr_path, "NBR")

if __name__ == "__main__":
    main()