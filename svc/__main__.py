from datetime import timedelta, datetime
import os
from dotenv import load_dotenv
from sentinelhub import (
    DataCollection,
    BBox,
    filter_times,
    bbox_to_dimensions,
    CRS,
)
from PIL import Image
import matplotlib.pyplot as plt
import numpy as np
import io
from rasterio import open as rio_open

from utils.validators import initial_validation
from utils.aws import get_boto3_session
from utils.sh import (
    create_true_color_request,
    get_catalog_of_images_by_date,
    get_sh_config,
)
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)





def save_image_from_request(request, timestamp, prefix, band) -> str:
    """
    Uploads the image data from a SentinelHubRequest to an S3 bucket.

    Args:
        request (SentinelHubRequest): The request object containing the image data.
        timestamp (datetime): The timestamp for naming the saved image file.
        prefix (str): The prefix to use for the S3 object key.

    Returns:
        str: The S3 URI of the uploaded image.
    """
    
    file_name = f"{band}.tiff"
    folder_name = f"s2-l2a-cdse_{timestamp.strftime('%Y-%m-%d_%H-%M-%S')}"
    # breakpoint()
    image = Image.fromarray(np.float32(request.get_data()[0]))
    buffer = io.BytesIO()
    image.save(buffer, format="TIFF")
    buffer.seek(0)

    session = get_boto3_session()


    if os.getenv("ENV") != "local":
        logger.info("Uploading image to S3...")
        session = get_boto3_session()

        s3 = session.client("s3")

        bucket_name = os.getenv("S3_BUCKET_NAME")

        s3.upload_fileobj(buffer, bucket_name, f"{prefix}/{folder_name}/{file_name}")

        return f"s3://{bucket_name}/{prefix}/{file_name}"
    else:
        logger.info("Saving image locally...")
        local_path = os.path.join(".", prefix, folder_name, file_name)
        os.makedirs(os.path.dirname(local_path), exist_ok=True)
        image.save(local_path)
        return local_path


if __name__ == "__main__":
    logger.info("Starting SentinelHub image processing...")
    logger.info("Loading environment variables...")
    load_dotenv()
    initial_validation()
    logger.info("Environment variables loaded successfully.")

    logger.info("Setting up AOI and configuration...")
    aoi_prefix = "preservacao_jatai"
    aoi_coords_wgs84 = [
    -47.842541,
    -21.639239,
    -47.709332,
    -21.541873
    ]
    resolution = 10  # Resolution in meters per pixel
    aoi_bbox = BBox(bbox=aoi_coords_wgs84, crs=CRS.WGS84)
    aoi_size = bbox_to_dimensions(aoi_bbox, resolution=resolution)
    bands = ["B04", "B08", "B12"]

    logger.info("Getting SentinelHub configuration...")
    config = get_sh_config()

    logger.info("Defining data collection...")
    data_collection = DataCollection.SENTINEL2_L2A.define_from(
        name="s2-l2a-cdse", service_url="https://sh.dataspace.copernicus.eu"
    )

    from_date = "2025-07-27"
    today_date = datetime.now().strftime("%Y-%m-%d")
    logger.info(f"Searching for images from {from_date} to {today_date}...")

    search_iterator = get_catalog_of_images_by_date(
        from_date=from_date,
        to_date=today_date,
        data_collection=data_collection,
        aoi_bbox=aoi_bbox,
        config=config,
    )
    logger.info(f"Catalog search completed. Found {len(search_iterator)} images.")
    timestamps = [
        datetime.fromisoformat(result["properties"]["datetime"].replace("Z", "+00:00"))
        for result in search_iterator
    ]
    timestamps = filter_times(timestamps=timestamps, time_difference=timedelta(hours=1))
    logger.info(f"Filtered timestamps: {len(timestamps)} valid timestamps found.")

    logger.info("Processing images...")
    for i, timestamp in enumerate(timestamps, start=1):
        logger.info(
            f">>>> Processing image {i} for timestamp {timestamp.isoformat()}..."
        )
        
        request = create_true_color_request(
            aoi_bbox=aoi_bbox,
            aoi_size=aoi_size,
            config=config,
            timestamp=timestamp,
            data_collection=data_collection,
            bands=bands
        )
        
        for band, req in request.items():
            logger.info(f">>>> Saving image {i} for timestamp {timestamp.isoformat()}")
            image = save_image_from_request(
                request=req,
                timestamp=timestamp,
                prefix=aoi_prefix,
                band=band
            )
            logger.info(
                f">>>> Image {i} saved: {image} for timestamp {timestamp.isoformat()}"
            )
