#!/usr/bin/env python3

import argparse, sys, numpy as np
from pathlib import Path
from shapely.geometry import box, mapping
from pystac_client import Client
import rasterio
from rasterio.enums import Resampling
from rasterio.session import AWSSession
import rasterio.shutil
from tqdm import tqdm
import boto3.session
import matplotlib.pyplot as plt
from PIL import Image
import io, os
from botocore.exceptions import ClientError

p = argparse.ArgumentParser()
p.add_argument("--bbox",   nargs=4, type=float, metavar=("W","S","E","N"), required=True)
p.add_argument("--date",   required=True, help="YYYY-MM-DD")
p.add_argument("--layers", nargs="+", default=["ndvi","rgb"], choices=["ndvi","nbr","rgb"])
p.add_argument("--out",    default="sentinel2_download")
p.add_argument("--days-pad", type=int, default=1,
               help="Search this many days before and after the target date if nothing is found (default: 1)")
p.add_argument("--location", required=True,
               help="Logical AOI name, used as first part of the S3 key")
p.add_argument("--bucket", default=os.getenv("OUTPUT_BUCKET"),
               help="Destination S3 bucket (default: env OUTPUT_BUCKET)")
args = p.parse_args()

aoi   = box(*args.bbox)
EPSILON = 0.02  
stac = Client.open("https://earth-search.aws.element84.com/v1")

def attempt_search(date_from, date_to, bbox, max_cloud=30):
    collections = ["sentinel-2-l2a", "sentinel-2-c1-l2a"]
    return list(stac.search(
        collections=collections,
        intersects=mapping(bbox),
        datetime=f"{date_from}/{date_to}",
        query=(None if max_cloud is None else {"eo:cloud_cover": {"lte": max_cloud}}),
        limit=20
    ).items())

items = attempt_search(f"{args.date}T00:00:00Z", f"{args.date}T23:59:59Z", aoi)
if not items:
    items = attempt_search(f"{args.date}T00:00:00Z", f"{args.date}T23:59:59Z", aoi, max_cloud=None)
if not items:
    grown = box(args.bbox[0]-EPSILON, args.bbox[1]-EPSILON,
                args.bbox[2]+EPSILON, args.bbox[3]+EPSILON)
    items = attempt_search(f"{args.date}T00:00:00Z", f"{args.date}T23:59:59Z", grown, max_cloud=None)
if not items and args.days_pad > 0:
    from datetime import datetime, timedelta
    target = datetime.fromisoformat(args.date)
    df = (target - timedelta(days=args.days_pad)).strftime("%Y-%m-%dT00:00:00Z")
    dt = (target + timedelta(days=args.days_pad)).strftime("%Y-%m-%dT23:59:59Z")
    items = attempt_search(df, dt, grown, max_cloud=None)

if not items:
    sys.exit("No Sentinel-2 scene found after relaxing filters. "
             "Try a broader bbox or larger --days-pad.")

ALIAS = {
    "B02": ["blue", "visual"],
    "B03": ["green"],
    "B04": ["red"],
    "B08": ["nir", "nir08"],
    "B12": ["swir22"],
}

def has_band(item, code):
    a = item.assets
    for k in (f"{code}_10m", f"{code}_20m", f"{code}_60m", code):
        if k in a:
            return True
    for alias in ALIAS.get(code, []):
        if alias in a or f"{alias}-jp2" in a:
            return True
    return False

required = {"B08", "B04"}
if "nbr" in args.layers: required.add("B12")
if "rgb" in args.layers: required |= {"B02", "B03"}

chosen = None
for it in sorted(items, key=lambda i: i.properties.get("eo:cloud_cover", 100)):
    if all(has_band(it, b) for b in required):
        chosen = it
        break

if chosen is None:
    sys.exit("None of the scenes contains all required bands. "
             "Increase --days-pad or enlarge the bbox.")

item = chosen
print("Chosen scene:", item.id, "cloud cover:", item.properties.get("eo:cloud_cover", "N/A"))
assets = item.assets

def href_for(code: str) -> str | None:
    a = assets
    for key in (f"{code}_10m", f"{code}_20m", f"{code}_60m", code):
        if key in a:
            return a[key].href
    for alias in ALIAS.get(code, []):
        if alias in a:
            return a[alias].href
        jp2 = f"{alias}-jp2"
        if jp2 in a:
            return a[jp2].href
    return None

B = {
    "blue":  href_for("B02"),
    "green": href_for("B03"),
    "red":   href_for("B04"),
    "nir":   href_for("B08"),
    "swir2": href_for("B12"),
}

if (B["nir"] is None or B["red"] is None) and {"ndvi","nbr"} & set(args.layers):
    sys.exit("Chosen scene lacks NIR or RED – cannot compute NDVI/NBR.")
if B["swir2"] is None and "nbr" in args.layers:
    sys.exit("Scene lacks SWIR-2 – cannot compute NBR.")
if "rgb" in args.layers and (B["blue"] is None or B["green"] is None or B["red"] is None):
    print("⚠️ Scene missing RGB bands – skipping RGB.")
    args.layers = [l for l in args.layers if l!="rgb"]

aws_session = boto3.session.Session(region_name="us-west-2")
aws = AWSSession(aws_session, region_name="us-west-2")
s3 = boto3.session.Session().client("s3")
arr, meta = {}, None
for name, url in tqdm({k: v for k, v in B.items() if v}.items(), desc="reading"):
    if url.startswith("http"):
        url = f"/vsicurl/{url}"
    with rasterio.Env(aws):
        with rasterio.open(url) as src:
            if meta is None:
                meta = src.profile
                meta.update(driver="GTiff", compress="deflate")
            if src.height != meta["height"] or src.width != meta["width"]:
                data = src.read(
                    1,
                    out_shape=(meta["height"], meta["width"]),
                    resampling=Resampling.bilinear
                )
            else:
                data = src.read(1)
            arr[name] = data.astype(np.float32)

def _s3_key(layer: str, ext: str) -> str:
    """
    <location>/<date>/<layer>.<ext>
    """
    return f"{args.location}/{args.date}/{layer}.{ext}"

def _upload(buf: bytes, key: str, ctype: str):
    s3.put_object(
        Bucket=args.bucket,
        Key=key,
        Body=buf,
        ContentType=ctype,
        ACL="public-read"  
    )
    print(f"s3://{args.bucket}/{key}")

def save(layer, data, dtype, scale=None):
    """
    Writes GeoTIFF + PNG directly to S3 in the desired key structure.
    """
    if scale is not None:
        data = (np.clip(data / scale, 0, 1) * 255).astype("uint8")
        dtype = "uint8"
    prof = meta.copy(); prof.update(dtype=dtype,
                                    count=(data.shape[0] if data.ndim == 3 else 1))
    with rasterio.MemoryFile() as mem:
        with mem.open(**prof) as dst:
            if data.ndim == 2:
                dst.write(data, 1)
            else:
                dst.write(data)
        _upload(mem.read(), _s3_key(layer, "tif"), "image/tiff")
        with rasterio.MemoryFile() as cog_mem:
            rasterio.shutil.copy(
                mem, cog_mem,
                driver='COG',
                compress='deflate',
                BLOCKSIZE=512,
                overview_resampling=Resampling.nearest
            )
            _upload(cog_mem.read(), _s3_key(layer + "_COG", "tif"), "image/tiff")

    if layer in ("NDVI", "NBR"):
        fig = plt.figure(frameon=False); plt.axis("off")
        plt.imshow(data, vmin=-1, vmax=1, cmap='RdYlGn')
        buf = io.BytesIO()
        fig.savefig(buf, format="png", bbox_inches='tight', pad_inches=0, dpi=96)
        plt.close(fig); buf.seek(0)
        _upload(buf.getvalue(), _s3_key(layer, "png"), "image/png")
    else:  
        rgb_arr = data.transpose(1, 2, 0)
        img_buf = io.BytesIO()
        Image.fromarray(rgb_arr).save(img_buf, format="PNG")
        _upload(img_buf.getvalue(), _s3_key(layer, "png"), "image/png")

if "ndvi" in args.layers:
    ndvi = (arr["nir"]-arr["red"])/(arr["nir"]+arr["red"])
    save("NDVI", np.clip(ndvi,-1,1), "float32")
if "nbr" in args.layers:
    nbr = (arr["nir"]-arr["swir2"])/(arr["nir"]+arr["swir2"])
    save("NBR", np.clip(nbr,-1,1), "float32")
if "rgb" in args.layers:
    rgb = np.stack([arr["red"],arr["green"],arr["blue"]])
    save("RGB", rgb, "uint8", scale=3500.0)

print("Finished.")