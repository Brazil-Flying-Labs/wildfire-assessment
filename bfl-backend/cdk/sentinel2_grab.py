#!/usr/bin/env python3

import argparse, sys, numpy as np
from pathlib import Path
from shapely.geometry import box, mapping
from pystac_client import Client
import rasterio
import logging
import sys
from rasterio.enums import Resampling
from rasterio.session import AWSSession
from tqdm import tqdm
import boto3.session
import matplotlib.pyplot as plt
from PIL import Image
import io, os
from botocore.exceptions import ClientError

logging.basicConfig(stream=sys.stdout, level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

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
    items = attempt_search(f"{args.date}T00:00:00Z", f"{args.date}T23:59:59Z", aoi, max_cloud=30)
if not items:
    grown = box(args.bbox[0]-EPSILON, args.bbox[1]-EPSILON,
                args.bbox[2]+EPSILON, args.bbox[3]+EPSILON)
    items = attempt_search(f"{args.date}T00:00:00Z", f"{args.date}T23:59:59Z", grown, max_cloud=30)
if not items and args.days_pad > 0:
    from datetime import datetime, timedelta
    target = datetime.fromisoformat(args.date)
    df = (target - timedelta(days=args.days_pad)).strftime("%Y-%m-%dT00:00:00Z")
    dt = (target + timedelta(days=args.days_pad)).strftime("%Y-%m-%dT23:59:59Z")
    items = attempt_search(df, dt, grown, max_cloud=30)

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
    logging.info(f"Entering save function for layer: {layer}. Input data shape: {data.shape}, input dtype: {data.dtype}. Target dtype for GeoTIFF: {dtype}, scale: {scale}")
    processing_dtype = data.dtype

    if scale is not None:
        logging.info(f"Layer {layer}: Scaling data. Initial min: {np.min(data):.2f}, max: {np.max(data):.2f}, dtype: {data.dtype}")
        data_scaled_float = data / scale
        logging.info(f"Layer {layer}: After division by scale {scale}. Min: {np.min(data_scaled_float):.2f}, Max: {np.max(data_scaled_float):.2f}")
        data_clipped = np.clip(data_scaled_float, 0, 1)
        logging.info(f"Layer {layer}: After clipping to [0,1]. Min: {np.min(data_clipped):.2f}, Max: {np.max(data_clipped):.2f}")
        data_multiplied = data_clipped * 255
        logging.info(f"Layer {layer}: After multiplying by 255. Min: {np.min(data_multiplied):.2f}, Max: {np.max(data_multiplied):.2f}")
        data = data_multiplied.astype("uint8")
        processing_dtype = data.dtype 
        logging.info(f"Layer {layer}: After converting to uint8. Min: {np.min(data)}, Max: {np.max(data)}, final processing_dtype: {processing_dtype}")
        dtype = "uint8" 
    else:
        logging.info(f"Layer {layer}: No scaling performed. Using original data. Min: {np.min(data)}, Max: {np.max(data)}, dtype: {processing_dtype}")

    logging.info(f"Layer {layer}: Preparing GeoTIFF. Profile dtype: {dtype}, data to write shape: {data.shape}, data to write dtype: {processing_dtype}")
    prof = meta.copy(); prof.update(dtype=dtype, count=(data.shape[0] if data.ndim == 3 else 1))
    if data.dtype != dtype:
        logging.warning(f"Layer {layer}: Data dtype {data.dtype} differs from GeoTIFF profile dtype {dtype}. This might be an issue if not handled by rasterio.")

    try:
        with rasterio.MemoryFile() as mem:
            with mem.open(**prof) as dst:
                if data.ndim == 2:
                    dst.write(data.astype(dtype), 1)
                else:
                    dst.write(data.astype(dtype))
            logging.info(f"Layer {layer}: GeoTIFF written to memory. Uploading...")
            _upload(mem.read(), _s3_key(layer, "tif"), "image/tiff")
            logging.info(f"Layer {layer}: GeoTIFF uploaded.")
    except Exception as e_gtiff:
        logging.error(f"Layer {layer}: Error during GeoTIFF creation/upload: {e_gtiff}", exc_info=True)

    # PNG preview
    if layer in ("NDVI", "NBR"):
        logging.info(f"Layer {layer}: Preparing PNG preview for NDVI/NBR.")
        fig = plt.figure(frameon=False); plt.axis("off")
        plt.imshow(data, vmin=-1, vmax=1, cmap='RdYlGn')
        buf = io.BytesIO()
        fig.savefig(buf, format="png", bbox_inches='tight', pad_inches=0, dpi=96)
        plt.close(fig); buf.seek(0)
        logging.info(f"Layer {layer}: NDVI/NBR PNG preview saved to buffer. Buffer size: {buf.tell()} bytes. Uploading...")
        _upload(buf.getvalue(), _s3_key(layer, "png"), "image/png")
        logging.info(f"Layer {layer}: NDVI/NBR PNG preview uploaded.")
    elif layer == "RGB":  
        logging.info(f"Layer {layer}: Preparing PNG preview for RGB. Data shape before transpose: {data.shape}, dtype: {data.dtype}")
        if data.dtype != np.uint8:
            logging.warning(f"Layer {layer}: RGB data for PNG is not uint8 ({data.dtype}). Attempting conversion.")
            data_for_png = (np.clip(data / np.max(data), 0, 1) * 255).astype(np.uint8) if np.max(data) > 0 else np.zeros_like(data, dtype=np.uint8)
        else:
            data_for_png = data

        rgb_arr = data_for_png.transpose(1, 2, 0)
        logging.info(f"Layer {layer}: RGB data shape after transpose (H,W,C): {rgb_arr.shape}. Min: {np.min(rgb_arr)}, Max: {np.max(rgb_arr)}, dtype: {rgb_arr.dtype}")
        
        try:
            logging.info(f"Layer {layer}: Creating PIL Image from full resolution data for resizing.")
            if not rgb_arr.flags['C_CONTIGUOUS']:
                rgb_arr = np.ascontiguousarray(rgb_arr)
                logging.info(f"Layer {layer}: Made RGB data C_CONTIGUOUS for Pillow.")
            pil_image_full_res = Image.fromarray(rgb_arr, 'RGB')
            preview_max_size = (1024, 1024) 
            logging.info(f"Layer {layer}: Resizing RGB image to max dimensions {preview_max_size} for PNG preview using LANCZOS.")
        
            pil_image_resized = pil_image_full_res.copy() 
            pil_image_resized.thumbnail(preview_max_size, Image.Resampling.LANCZOS) 
            
            logging.info(f"Layer {layer}: Resized RGB image dimensions for PNG: {pil_image_resized.size}. Mode: {pil_image_resized.mode}")

            buf = io.BytesIO()
            logging.info(f"Layer {layer}: Calling pil_image.save() on RESIZED image to buffer for RGB PNG.")
            pil_image_resized.save(buf, format='PNG')
            buf.seek(0) 
            
            png_buffer_size = buf.getbuffer().nbytes
            logging.info(f"Layer {layer}: RGB PNG preview (resized) saved to buffer. Buffer size: {png_buffer_size} bytes.")

            if png_buffer_size == 0:
                logging.warning(f"Layer {layer}: RGB PNG preview buffer is 0 bytes after save. Skipping upload.")
            else:
                logging.info(f"Layer {layer}: Uploading RGB PNG preview (resized) from buffer.")
                _upload(buf.getvalue(), _s3_key(layer, "png"), "image/png")
                logging.info(f"Layer {layer}: RGB PNG preview (resized) uploaded to s3://{args.bucket}/{_s3_key(layer, 'png')}")
                s3_path_png = f"s3://{args.bucket}/{_s3_key(layer, 'png')}"
                print(s3_path_png) 

        except Exception as e:
            logging.error(f"Layer {layer}: Error creating or uploading RGB PNG preview: {e}")

if "ndvi" in args.layers:
    ndvi = (arr["nir"]-arr["red"])/(arr["nir"]+arr["red"])
    save("NDVI", np.clip(ndvi,-1,1), "float32")
if "nbr" in args.layers:
    nbr = (arr["nir"]-arr["swir2"])/(arr["nir"]+arr["swir2"])
    save("NBR", np.clip(nbr,-1,1), "float32")
if "rgb" in args.layers:
    logging.info(f"Attempting to process RGB layer for date {args.date}, location {args.location}")
    try:
        required_bands = ["red", "green", "blue"]
        missing_bands = [band for band in required_bands if band not in arr]
        if missing_bands:
            logging.error(f"⚠️ Missing bands for RGB: {missing_bands}. Available bands: {list(arr.keys())}")
            print(f"⚠️ Skipping RGB due to missing bands: {missing_bands}")
        else:
            logging.info(f"All required RGB bands found: red, green, blue.")
            logging.info(f"Red band shape: {arr['red'].shape}, dtype: {arr['red'].dtype}")
            logging.info(f"Green band shape: {arr['green'].shape}, dtype: {arr['green'].dtype}")
            logging.info(f"Blue band shape: {arr['blue'].shape}, dtype: {arr['blue'].dtype}")
            rgb = np.stack([arr["red"], arr["green"], arr["blue"]])
            logging.info(f"Stacked RGB array. Shape: {rgb.shape}, dtype: {rgb.dtype}")
            save("RGB", rgb, "uint8", scale=3500.0)
            logging.info(f"Successfully processed and saved RGB layer for date {args.date}.")
    except KeyError as e:
        logging.error(f"⚠️ KeyError during RGB processing: {e}. Available bands: {list(arr.keys())}")
        print(f"⚠️ Skipping RGB due to missing band: {e}")
    except Exception as e:
        logging.error(f"⚠️ An unexpected error occurred during RGB processing: {e}", exc_info=True)
        print(f"⚠️ An unexpected error occurred during RGB processing for date {args.date}: {e}")

print("Finished.")