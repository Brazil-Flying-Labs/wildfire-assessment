import requests
import os
import zipfile
import rasterio
from rasterio.warp import calculate_default_transform, reproject, Resampling
import glob
from rasterio.mask import mask
from shapely.geometry import mapping, Polygon, shape, MultiPolygon
from pyproj import Transformer
import json
import numpy as np

# --- CONFIGURAÇÕES ---
USERNAME = "camargo.advanced@gmail.com"
PASSWORD = "nastyz-Qepxat-fekro2"
START_DATE = "2024-07-01"  # Exemplo
END_DATE = "2024-07-25"
MAX_CLOUD = 5
SAFE_DIR = "sentinel_downloads"
os.makedirs(SAFE_DIR, exist_ok=True)
TEMP_DIR = os.path.join(SAFE_DIR, "temp")
os.makedirs(TEMP_DIR, exist_ok=True)
PROCESSED_DIR = os.path.join(SAFE_DIR, "processed")
os.makedirs(PROCESSED_DIR, exist_ok=True)

CATALOGUE_URL = "https://catalogue.dataspace.copernicus.eu/odata/v1/Products"

# --- FUNÇÕES ---

def load_geojson(path):
    with open(path, 'r') as f:
        data = json.load(f)
    geom = shape(data["features"][0]["geometry"])
    geom_simple = geom.simplify(0.001)  # ajustar tolerância conforme necessidade
    wkt = geom_simple.wkt
    return wkt, geom_simple

def reproject_geometry(geometry, from_epsg, to_epsg):
    transformer = Transformer.from_crs(from_epsg, to_epsg, always_xy=True)
    if geometry.geom_type == 'Polygon':
        coords = [transformer.transform(x, y) for x, y in geometry.exterior.coords]
        return Polygon(coords)
    elif geometry.geom_type == 'MultiPolygon':
        new_polygons = []
        for poly in geometry.geoms:
            coords = [transformer.transform(x, y) for x, y in poly.exterior.coords]
            new_polygons.append(Polygon(coords))
        return MultiPolygon(new_polygons)
    else:
        raise ValueError(f"Geometria não suportada: {geometry.geom_type}")

def get_token():
    r = requests.post(
        "https://identity.dataspace.copernicus.eu/auth/realms/CDSE/protocol/openid-connect/token",
        data={
            "client_id": "cdse-public",
            "username": USERNAME,
            "password": PASSWORD,
            "grant_type": "password"
        },
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
    unzip_dir = os.path.join(out_dir, title)  # sem .SAFE
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
    with rasterio.open(ref_path) as ref:
        dst_transform, dst_width, dst_height = calculate_default_transform(
            ref.crs, ref.crs, ref.width, ref.height, *ref.bounds
        )
        dst_profile = ref.profile.copy()
        dst_profile.update({
            "transform": dst_transform,
            "width": dst_width,
            "height": dst_height
        })
        
        with rasterio.open(src_path) as src:
            data = src.read(
                out_shape=(src.count, dst_height, dst_width),
                resampling=Resampling.bilinear
            )
        
        with rasterio.open(out_path, 'w', **dst_profile) as dst:
            dst.write(data)
    print(f"[OK] Banda reamostrada salva em: {out_path}")

def find_band_path(safe_dir, band_code, resolution):
    pattern = os.path.join(
        safe_dir,
        "GRANULE/*/IMG_DATA/R{}/*_{}_{}.jp2".format(resolution, band_code, resolution)
    )
    matches = glob.glob(pattern)
    if not matches:
        raise FileNotFoundError(f"Banda {band_code} ({resolution}) não encontrada em {safe_dir}")
    return matches[0]

def crop_raster_by_geometry(src_path, geometry, out_path):
    with rasterio.open(src_path) as src:
        geojson = [mapping(geometry)]
        nodata_val = src.nodata if src.nodata is not None else 0
        out_image, out_transform = mask(src, geojson, crop=True, nodata=nodata_val)
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

# --- MAIN ---
def main():
    print("Gerando token...")
    token = get_token()

    print("Carregando GeoJSON jatai.geojson...")
    wkt, geom = load_geojson("jatai.geojson")

    print("Buscando produtos Sentinel-2 L2A...")
    products = search_products(token, wkt)
    if not products:
        print("Nenhum produto encontrado.")
        return

    product = products[0]
    title = product["Name"]
    size = product["ContentLength"] / (1024 ** 3)
    product_id = product.get("Id")
    online = product.get("Online", False)

    print(f"Produto selecionado: {title} ({size:.2f} GB)")
    if not online:
        print("⚠️ Produto ainda não está disponível online.")
        return

    if not product_id:
        print("Erro: ID do produto não encontrado.")
        return

    safe_path = download_product(token, product_id, title, SAFE_DIR)
    if not safe_path:
        print("Erro ao obter o produto.")
        return

    b04_path = find_band_path(safe_path, "B04", "10m")
    b08_path = find_band_path(safe_path, "B08", "10m")
    b12_path = find_band_path(safe_path, "B12", "20m")

    b12_resampled_path = os.path.join(TEMP_DIR, "B12_10m.tif")
    resample_to_match(b12_path, b04_path, b12_resampled_path)

    b04_cropped = os.path.join(TEMP_DIR, "B04_cropped.tif")
    b08_cropped = os.path.join(TEMP_DIR, "B08_cropped.tif")
    b12_cropped = os.path.join(TEMP_DIR, "B12_cropped.tif")

    # Reprojeta geometria para CRS do raster antes do recorte
    with rasterio.open(b04_path) as ref:
        geom_proj = reproject_geometry(geom, "EPSG:4326", ref.crs)

    crop_raster_by_geometry(b04_path, geom_proj, b04_cropped)
    crop_raster_by_geometry(b08_path, geom_proj, b08_cropped)
    crop_raster_by_geometry(b12_resampled_path, geom_proj, b12_cropped)

    ndvi_path = os.path.join(TEMP_DIR, "NDVI.tif")
    calculate_index(b08_cropped, b04_cropped, ndvi_path, "NDVI")

    nbr_path = os.path.join(TEMP_DIR, "NBR.tif")
    calculate_index(b08_cropped, b12_cropped, nbr_path, "NBR")

if __name__ == "__main__":
    main()
