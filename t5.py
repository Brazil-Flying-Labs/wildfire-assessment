import requests
import time
import os
from shapely.geometry import Polygon
import zipfile
import rasterio
from rasterio.warp import calculate_default_transform, reproject, Resampling


# --- CONFIGURAÇÕES ---
USERNAME = "camargo.advanced@gmail.com"
PASSWORD = "nastyz-Qepxat-fekro2"
BBOX_POLYGON = [
    [-47.919273, -21.483102],
    [-47.919273, -21.467767],
    [-47.610283, -21.467767],
    [-47.610283, -21.483102],
    [-47.919273, -21.483102] #  igual ao primeiro nnumero
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
    unzip_dir = os.path.join(out_dir, title + ".SAFE")
    if os.path.exists(unzip_dir):
        print(f"[INFO] Produto {title} já existe em {unzip_dir}, pulando download.")
        return unzip_dir  # já existe
    
    try:
        url = f"https://zipper.dataspace.copernicus.eu/odata/v1/Products({product_id})/$value"
        headers = {"Authorization": f"Bearer {token}"}
        local_filename = os.path.join(out_dir, title + ".zip")

        print(f"Iniciando download: {url}")
        with requests.get(url, headers=headers, stream=True) as r:
            r.raise_for_status()
            with open(local_filename, "wb") as f:
                for chunk in r.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
        print(f"Download concluído: {local_filename}")

        # Extrair direto para a pasta .SAFE
        unzip_file(local_filename, out_dir)
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

    # resampling de bandas para 10m
    b04_path = "/caminho/para/IMG_DATA/R10m/..._B04_10m.jp2"
    b12_path = "/caminho/para/IMG_DATA/R20m/..._B12_20m.jp2"
    b12_resampled_path = os.path.join(TEMP_DIR, "B12_10m.tif")

    resample_to_match(b12_path, b04_path, b12_resampled_path)


if __name__ == "__main__":
    main()
