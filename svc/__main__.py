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
import numpy as np
import io

from utils.validators import initial_validation
from utils.aws import get_boto3_session
from utils.sh import (
    create_true_color_request,
    get_catalog_of_images_by_date,
    get_sh_config,
)


def save_image_from_request(request, timestamp, prefix) -> str:
    """
    Uploads the image data from a SentinelHubRequest to an S3 bucket.

    Args:
        request (SentinelHubRequest): The request object containing the image data.
        timestamp (datetime): The timestamp for naming the saved image file.
        prefix (str): The prefix to use for the S3 object key.

    Returns:
        str: The S3 URI of the uploaded image.
    """
    file_name = f"s2-l2a-cdse_{timestamp.strftime('%Y-%m-%d_%H-%M-%S')}.png"
    image = Image.fromarray(np.uint8(request.get_data()[0]))
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    buffer.seek(0)

    session = get_boto3_session()

    s3 = session.client("s3")

    bucket_name = os.getenv("S3_BUCKET_NAME")

    s3.upload_fileobj(buffer, bucket_name, f"{prefix}/{file_name}")

    return f"s3://{bucket_name}/{prefix}/{file_name}"


if __name__ == "__main__":
    load_dotenv()
    initial_validation()

    aoi_prefix = "preservacao_jatai"
    aoi_coords_wgs84 = [-47.88, -21.68, -47.67, -21.51]
    resolution = 10  # Resolution in meters per pixel

    config = get_sh_config()

    aoi_bbox = BBox(bbox=aoi_coords_wgs84, crs=CRS.WGS84)
    aoi_size = bbox_to_dimensions(aoi_bbox, resolution=resolution)
    data_collection = DataCollection.SENTINEL2_L2A.define_from(
        name="s2-l2a-cdse", service_url="https://sh.dataspace.copernicus.eu"
    )

    from_date = "2025-01-01"
    today_date = datetime.now().strftime("%Y-%m-%d")

    search_iterator = get_catalog_of_images_by_date(
        from_date=from_date,
        to_date=today_date,
        data_collection=data_collection,
        aoi_bbox=aoi_bbox,
        config=config,
    )

    timestamps = [
        datetime.fromisoformat(result["properties"]["datetime"].replace("Z", "+00:00"))
        for result in search_iterator
    ]
    timestamps = filter_times(timestamps=timestamps, time_difference=timedelta(hours=1))

    # 2. Fazer requests separados para cada timestamp
    for i, timestamp in enumerate(timestamps, start=1):
        request = create_true_color_request(
            aoi_bbox=aoi_bbox,
            aoi_size=aoi_size,
            config=config,
            timestamp=timestamp,
            data_collection=data_collection,
        )
        image = save_image_from_request(
            request=request,
            timestamp=timestamp,
            prefix=aoi_prefix,
        )
        print(f"Image {i} saved: {image} for timestamp {timestamp.isoformat()}")
