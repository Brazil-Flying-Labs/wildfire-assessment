import requests
import time
import os
from shapely.geometry import Polygon

# --- CONFIGURAÇÕES ---
USERNAME = "camargo.advanced@gmail.com"
PASSWORD = "nastyz-Qepxat-fekro2"
BBOX_POLYGON = [
    [-47.919273, -21.483102],
    [-47.919273, -21.467767],
    [-47.610283, -21.467767],
    [-47.610283, -21.483102],
    [-47.919273, -21.483102]
]
START_DATE = "2024-07-01"  # Changed to past date
END_DATE = "2024-07-25"
MAX_CLOUD = 5
OUT_DIR = "sentinel_downloads"
os.makedirs(OUT_DIR, exist_ok=True)

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

def download_product(token, product_id, title, out_dir):
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
    except requests.exceptions.HTTPError as e:
        print(f"Erro no download: {e}")
    except Exception as e:
        print(f"Erro inesperado: {e}")

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

    download_product(token, product_id, title, OUT_DIR)

if __name__ == "__main__":
    main()
