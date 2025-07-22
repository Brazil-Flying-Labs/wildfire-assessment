import os
from dotenv import load_dotenv
from sentinelhub import (
    SHConfig,
    DataCollection,
    SentinelHubRequest,
    SentinelHubCatalog,
    BBox,
    filter_times,
    bbox_to_dimensions,
    CRS,
    MimeType,
)
from PIL import Image
import numpy as np
import io
import boto3


def get_evalscript_true_color():
    """
    Evalscript for generating a true color image using Sentinel-2 data.

    This script selects bands B04 (red), B03 (green), and B02 (blue) and outputs them
    in RGB order to produce a natural-color image, similar to what the human eye sees.
    It is compatible with Evalscript Version 3 used by Sentinel Hub services.
    """
    return """
    //VERSION=3

    function setup() {
        return {
            input: [{
                bands: ["B02", "B03", "B04"]
            }],
            output: {
                bands: 3
            }
        };
    }

    function evaluatePixel(sample) {
        return [sample.B04, sample.B03, sample.B02];
    }
    """


def create_true_color_request(
    aoi_bbox, aoi_size, config, timestamp, data_collection: DataCollection
):
    """
    Creates a SentinelHubRequest for retrieving a true color (RGB) image from Sentinel-2
    data.

    The request uses bands defined in the `get_evalscript_true_color` function to
    generate a natural-color image.
    It queries data from the Copernicus Data Space Ecosystem (CDSE) for the specified
    bounding box and size, using the least-cloud-coverage mosaicking strategy within the
    date range 2022-07-01 to 2022-07-20.

    Args:
        aoi_bbox (BBox): Area of interest bounding box in WGS84 coordinates.
        aoi_size (tuple): Image size in pixels (width, height) based on resolution.
        config (SHConfig): Sentinel Hub configuration with access credentials.
        timestamp (str): Timestamp for the image request in ISO format.
        data_collection (DataCollection): Sentinel Hub data collection to use for the
        request.

    Returns:
        SentinelHubRequest: Configured request object ready to be executed.
    """
    return SentinelHubRequest(
        evalscript=get_evalscript_true_color(),
        input_data=[
            SentinelHubRequest.input_data(
                data_collection=data_collection,
                time_interval=(timestamp, timestamp),
            )
        ],
        responses=[SentinelHubRequest.output_response("default", MimeType.PNG)],
        bbox=aoi_bbox,
        size=aoi_size,
        config=config,
    )


def get_sh_config():
    """
    Retrieves Sentinel Hub configuration from environment variables.

    Returns:
        SHConfig: Configured Sentinel Hub configuration object.
    """
    config = SHConfig()
    config.sh_client_id = str(os.getenv("SENTINEL_HUB_CLIENT_ID"))
    config.sh_client_secret = str(os.getenv("SENTINEL_HUB_CLIENT_SECRET"))
    config.sh_token_url = "https://identity.dataspace.copernicus.eu/auth/realms/CDSE/protocol/openid-connect/token"  # noqa: E501
    config.sh_base_url = "https://sh.dataspace.copernicus.eu"
    config.save("cdse")

    return config


def get_catalog_of_images_by_date(
    from_date: str,
    to_date: str,
    data_collection: DataCollection,
    aoi_bbox: BBox,
    config: SHConfig,
):
    """
    Retrieves a catalog of images from Sentinel Hub by date.

    Args:
        from_date (str): Start date for the image search in ISO format (YYYY-MM-DD
        to_date (str): End date for the image search in ISO format (YYYY-MM-DD).
        data_collection (DataCollection): Sentinel Hub data collection to search in.
        aoi_bbox (BBox): Area of interest bounding box in WGS84 coordinates.
        config (SHConfig): Sentinel Hub configuration with access credentials.

    Returns:
        SentinelHubCatalog: Catalog object containing search results for images
        within the specified date range and area of interest.
    """

    catalog = SentinelHubCatalog(config=config)

    return list(
        catalog.search(
            collection=data_collection,
            bbox=aoi_bbox,
            time=(from_date, to_date),
            filter="eo:cloud_cover < 5",
        )
    )
