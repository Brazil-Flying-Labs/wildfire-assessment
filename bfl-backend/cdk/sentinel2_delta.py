#!/usr/bin/env python3

import argparse, sys, numpy as np, datetime as dt
from pathlib import Path
from shapely.geometry import box, mapping
from pystac_client import Client
import rasterio, boto3.session
from rasterio.enums import Resampling
from rasterio.session import AWSSession
import matplotlib.pyplot as plt
from PIL import Image
from tqdm import tqdm
import io, os
from botocore.exceptions import ClientError

p = argparse.ArgumentParser()
p.add_argument("--bbox",   nargs=4, type=float, metavar=("W","S","E","N"), required=True)
p.add_argument("--date-a", required=True, help="First date  (YYYY-MM-DD)")
p.add_argument("--date-b", required=True, help="Second date (YYYY-MM-DD)")
p.add_argument("--index",  choices=["ndvi", "nbr"], default="ndvi",
               help="Change metric to compute (default: ndvi)")
p.add_argument("--out",    default="s2_delta_out")
p.add_argument("--max-cloud", type=int, default=30,
               help="Max %% cloud cover per scene (default 30)")
p.add_argument("--location", required=True,
               help="Logical name for the AOI (used in the S3 key prefix)")
p.add_argument("--bucket", default=os.getenv("OUTPUT_BUCKET"),
               help="Destination S3 bucket (default: env OUTPUT_BUCKET)")
args = p.parse_args()

aoi   = box(*args.bbox)
stac = Client.open("https://earth-search.aws.element84.com/v1")
ALIAS = {"B02": ["blue"], "B03": ["green"], "B04": ["red"],
         "B08": ["nir"],  "B12": ["swir2"]}

def pick_scene(date_iso: str):
    """Return the STAC item with the lowest cloud cover that contains needed bands."""
    def attempt(one_date):
        q = stac.search(
            collections=["sentinel-2-l2a","sentinel-2-c1-l2a"],
            intersects=mapping(aoi),
            datetime=f"{one_date}T00:00:00Z/{one_date}T23:59:59Z",
            query={"eo:cloud_cover": {"lte": args.max_cloud}},
            limit=100,
        )
        return sorted(q.items(), key=lambda i: i.properties.get("eo:cloud_cover", 100))
    items = attempt(date_iso)
    if not items:
        sys.exit(f"No scene on {date_iso} with ≤{args.max_cloud}% clouds")
    return items[0]

def href_for(item, band):
    a = item.assets
    for key in (f"{band}_10m", f"{band}_20m", f"{band}_60m", band):
        if key in a: return a[key].href
    for alias in ALIAS.get(band, []):
        if alias in a: return a[alias].href
        if f"{alias}-jp2" in a: return a[f"{alias}-jp2"].href
    return None

aws = AWSSession(boto3.session.Session(), region_name="us-west-2")
s3 = boto3.client("s3")

def load_bands(item):
    need = {"B08","B04"} if args.index=="ndvi" else {"B08","B12"}
    paths = {b: href_for(item,b) for b in need}
    if None in paths.values():
        sys.exit(f"Scene {item.id} missing required bands.")
    arr, meta = {}, None
    for code, url in tqdm(paths.items(), desc=f"read {item.id}"):
        url = f"/vsicurl/{url}" if url.startswith("http") else url
        with rasterio.Env(aws):
            with rasterio.open(url) as src:
                if meta is None:
                    meta = src.profile; meta.update(driver="GTiff", compress="deflate")
                data = src.read(1)
                if data.shape != (meta["height"], meta["width"]):
                    data = src.read(
                        1,
                        out_shape=(meta["height"], meta["width"]),
                        resampling=Resampling.bilinear
                    )
                arr[code] = data.astype(np.float32)
    return arr, meta

def ndvi(b):
    return (b["B08"] - b["B04"]) / (b["B08"] + b["B04"] + 1e-6)

def nbr(b):
    return (b["B08"] - b["B12"]) / (b["B08"] + b["B12"] + 1e-6)

calc_index = ndvi if args.index=="ndvi" else nbr
index_name = args.index.upper()
delta_name = f"D{index_name}"

def _s3_key(date: str, name: str, ext: str) -> str:
    return f"{args.location}/{date}/{name}.{ext}"

def _obj_exists(bucket: str, key: str) -> bool:
    try:
        s3.head_object(Bucket=bucket, Key=key)
        return True
    except ClientError as e:
        if e.response["Error"]["Code"] in ("404", "NoSuchKey"):
            return False
        raise

def _upload_bytes(buf: bytes, key: str, ctype: str):
    s3.put_object(
        Bucket=args.bucket,
        Key=key,
        Body=buf,
        ContentType=ctype,
        ACL="public-read"  
    )
    print(f"s3://{args.bucket}/{key}")

def _delta_prefix():
    return f"d{index_name.lower()}"

def _delta_key(date_a: str, date_b: str, name: str, ext: str) -> str:
    return f"{args.location}/{_delta_prefix()}/{date_a}_{date_b}/{name}.{ext}"

def _delta_exists(date_a: str, date_b: str, name: str, ext: str) -> bool:
    return _obj_exists(args.bucket, _delta_key(date_a, date_b, name, ext))

def write_raster(date: str, name: str, data, meta,
                 cmap="BrBG", vmin=-1, vmax=1):
    tif_key = _s3_key(date, name, "tif")
    png_key = _s3_key(date, name, "png")

    with rasterio.MemoryFile() as mem:
        with mem.open(**meta) as dst:
            dst.write(data.astype("float32"), 1)
        _upload_bytes(mem.getbuffer(), tif_key, "image/tiff")
    fig = plt.figure(frameon=False); plt.axis("off")
    plt.imshow(data, cmap=cmap, vmin=vmin, vmax=vmax)
    buf = io.BytesIO()
    fig.savefig(buf, format="png", bbox_inches='tight', pad_inches=0, dpi=96)
    plt.close(fig); buf.seek(0)
    _upload_bytes(buf.getvalue(), png_key, "image/png")

def write_delta(name: str, data, meta,
                cmap="RdYlGn", vmin=-0.5, vmax=0.5):
    tif_key = _delta_key(args.date_a, args.date_b, name, "tif")
    png_key = _delta_key(args.date_a, args.date_b, name, "png")

    with rasterio.MemoryFile() as mem:
        with mem.open(**meta) as dst:
            dst.write(data.astype("float32"), 1)
        _upload_bytes(mem.getbuffer(), tif_key, "image/tiff")

    fig = plt.figure(frameon=False); plt.axis("off")
    plt.imshow(data, cmap=cmap, vmin=vmin, vmax=vmax)
    buf = io.BytesIO()
    fig.savefig(buf, format="png", bbox_inches='tight', pad_inches=0, dpi=96)
    plt.close(fig); buf.seek(0)
    _upload_bytes(buf.getvalue(), png_key, "image/png")

def load_or_make_index(date_iso: str, scene):
    tif_key = _s3_key(date_iso, index_name, "tif")
    if _obj_exists(args.bucket, tif_key):
        print(f"→ using cached {tif_key}")
        obj = s3.get_object(Bucket=args.bucket, Key=tif_key)
        with rasterio.MemoryFile(obj["Body"].read()) as mem:
            with mem.open() as src:
                return src.read(1), src.profile

    bands, meta = load_bands(scene)
    idx = calc_index(bands)
    write_raster(date_iso, index_name, idx, meta,
                 cmap=("BrBG" if args.index == "ndvi" else "PiYG"))
    return idx, meta

scene_a = pick_scene(args.date_a)
scene_b = pick_scene(args.date_b)

idx_a, meta = load_or_make_index(args.date_a, scene_a)
idx_b, _    = load_or_make_index(args.date_b, scene_b)

if _delta_exists(args.date_a, args.date_b, f"D{index_name}", "tif"):
    print("→ Δ layer already cached – skipping computation")
else:
    didx = np.clip(idx_b - idx_a, -0.5, 0.5)
    write_delta(f"D{index_name}", didx, meta)

print("Finished.")