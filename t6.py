import requests
import os
import zipfile
import rasterio
from rasterio.warp import calculate_default_transform, reproject, Resampling
import glob
from rasterio.mask import mask
from shapely.geometry import mapping, Polygon
from pyproj import Transformer

# --- CONFIGURAÇÕES ---
USERNAME = "camargo.advanced@gmail.com"
PASSWORD = "nastyz-Qepxat-fekro2"
BBOX_POLYGON = [
    [-47.6, -21.3],
    [-47.6, -21.0],
    [-47.2, -21.0],
    [-47.2, -21.3],
    [-47.6, -21.3]
]
START_DATE = "2024-07-01"  # Changed to past date
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

def convert_bbox(bbox4326, from_epsg="4326", to_epsg="32723"):
    """
    Converte uma lista de coordenadas BBOX de um CRS para outro.
    bbox4326 = lista de [lon, lat] (EPSG:4326)
    Retorna lista de coordenadas no CRS de destino.
    """
    transformer = Transformer.from_crs(from_epsg, to_epsg, always_xy=True)
    converted = [transformer.transform(lon, lat) for lon, lat in bbox4326]
    return converted

def bbox_to_wkt(bbox):
    polygon = Polygon(bbox)
    return polygon.wkt

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
    """Extrai um arquivo .zip para a pasta especificada."""
    try:
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(extract_to)
        print(f"Arquivo extraído para: {extract_to}")
    except zipfile.BadZipFile:
        print(f"Erro: {zip_path} não é um arquivo ZIP válido.")

def download_product(token, product_id, title, out_dir):
    unzip_dir = os.path.join(out_dir, title)  # <-- NÃO adiciona .SAFE
    zip_path = os.path.join(out_dir, title + ".zip")

    # Se a pasta SAFE já existe, usa direto e não mexe no ZIP
    if os.path.exists(unzip_dir):
        print(f"[INFO] Produto {title} já existe extraído em {unzip_dir}, pulando download e unzip.")
        return unzip_dir

    # Caso contrário, baixa (ou reusa um ZIP válido)
    try:
        # Se o ZIP existe, checar se é válido
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

        # Se não tinha ZIP válido, baixa
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
    """Reamostra src_path para ter a mesma resolução/grade de ref_path."""
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

def crop_raster_by_bbox(src_path, bbox, out_path):
    """Recorta um raster para o BBOX informado e salva como GeoTIFF."""
    geom = Polygon(bbox)
    geojson = [mapping(geom)]

    with rasterio.open(src_path) as src:
        out_image, out_transform = mask(src, geojson, crop=True)
        out_meta = src.meta.copy()

    out_meta.update({
        "driver": "GTiff",
        "height": out_image.shape[1],
        "width": out_image.shape[2],
        "transform": out_transform
    })

    with rasterio.open(out_path, "w", **out_meta) as dest:
        dest.write(out_image)

    print(f"[OK] Raster recortado salvo em: {out_path}")

# --- MAIN ---
def main():
    print("Gerando token...")
    token = get_token()
    wkt = bbox_to_wkt(BBOX_POLYGON)

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
    print(f"Metadata: {product}")  # Debug: print full metadata
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

    # Encontrar bandas
    b04_path = find_band_path(safe_path, "B04", "10m")
    b08_path = find_band_path(safe_path, "B08", "10m")
    b12_path = find_band_path(safe_path, "B12", "20m")

    # Reamostrar B12 para 10m
    b12_resampled_path = os.path.join(TEMP_DIR, "B12_10m.tif")
    resample_to_match(b12_path, b04_path, b12_resampled_path)

    # Cortar todas as bandas para o BBOX
    b04_cropped = os.path.join(TEMP_DIR, "B04_cropped.tif")
    b08_cropped = os.path.join(TEMP_DIR, "B08_cropped.tif")
    b12_cropped = os.path.join(TEMP_DIR, "B12_cropped.tif")

    # Converta para EPSG:32723 para recorte
    BBOX_32723 = convert_bbox(BBOX_POLYGON)

    crop_raster_by_bbox(b04_path, BBOX_32723, b04_cropped)
    crop_raster_by_bbox(b08_path, BBOX_32723, b08_cropped)
    crop_raster_by_bbox(b12_resampled_path, BBOX_32723, b12_cropped)

if __name__ == "__main__":
    main()
