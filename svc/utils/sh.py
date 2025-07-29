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

from sentinelhub import Geometry

from PIL import Image
import numpy as np
import io
import boto3

def get_evalscript_by_band(band:str):

    return """
    //VERSION=3
    function setup() {
        return {
            input: ["{band}"],
            output: { bands: 1, sampleType: "FLOAT32" }
        };
    }

    function evaluatePixel(sample) {
    return [ sample.{band} ];}
    """.replace("{band}", band)

def get_geometry():

    geojson = {
        "type":"Polygon",
        "coordinates":[[
                [-47.725124,-21.615861],[-47.678089,-21.631979],[-47.678604,-21.634053],[-47.681866,-21.633255],[-47.689934,-21.642191],[-47.690964,-21.641553],
                [-47.729244,-21.676173],[-47.731476,-21.675216],[-47.732506,-21.671866],[-47.733536,-21.665166],[-47.733192,-21.662773],[-47.734394,-21.660539],
                [-47.735767,-21.659263],[-47.737999,-21.656551],[-47.740059,-21.652243],[-47.740917,-21.64969],[-47.740574,-21.648733],[-47.736282,-21.648095],
                [-47.726154,-21.618095],[-47.728043,-21.61634],[-47.730446,-21.615382],[-47.732677,-21.61618],[-47.734909,-21.616659],[-47.736969,-21.616021],
                [-47.739372,-21.615542],[-47.741089,-21.616021],[-47.742462,-21.618415],[-47.742462,-21.620489],[-47.744179,-21.622085],[-47.746067,-21.622404],
                [-47.748814,-21.622085],[-47.753448,-21.622404],[-47.757397,-21.621925],[-47.759285,-21.622404],[-47.762375,-21.622085],[-47.764435,-21.62001],
                [-47.767353,-21.618734],[-47.767181,-21.616978],[-47.768898,-21.61634],[-47.769928,-21.617457],[-47.771816,-21.617297],[-47.771988,-21.618255],
                [-47.774563,-21.618095],[-47.776451,-21.618734],[-47.776794,-21.62017],[-47.777481,-21.622404],[-47.780399,-21.623362],[-47.782631,-21.625277],
                [-47.785378,-21.624319],[-47.787094,-21.624798],[-47.789841,-21.626553],[-47.795162,-21.624319],[-47.801857,-21.626713],[-47.805634,-21.627511],
                [-47.806492,-21.625915],[-47.808037,-21.62384],[-47.810612,-21.622723],[-47.812672,-21.622245],[-47.813358,-21.620489],[-47.8125,-21.618255],
                [-47.814045,-21.617457],[-47.816105,-21.61618],[-47.818851,-21.615223],[-47.820053,-21.613787],[-47.820568,-21.611073],[-47.823315,-21.611073],
                [-47.82692,-21.611073],[-47.829666,-21.612829],[-47.831554,-21.615063],[-47.833271,-21.613308],[-47.834301,-21.610914],[-47.832413,-21.608839],
                [-47.830524,-21.607084],[-47.830353,-21.605009],[-47.831898,-21.602774],[-47.830524,-21.601817],[-47.828293,-21.602295],[-47.827263,-21.601019],
                [-47.829151,-21.599582],[-47.832241,-21.599423],[-47.834129,-21.601019],[-47.834644,-21.602774],[-47.836189,-21.604211],[-47.837906,-21.603253],
                [-47.838249,-21.601497],[-47.838078,-21.599901],[-47.838421,-21.598465],[-47.840996,-21.598305],[-47.841854,-21.599742],[-47.841682,-21.602136],
                [-47.842884,-21.601338],[-47.845116,-21.599423],[-47.845631,-21.597028],[-47.848206,-21.595752],[-47.850266,-21.597826],[-47.851639,-21.599582],
                [-47.853527,-21.597507],[-47.854385,-21.59623],[-47.854042,-21.593357],[-47.851124,-21.591921],[-47.848549,-21.592879],[-47.847176,-21.591921],
                [-47.844429,-21.591602],[-47.843571,-21.589367],[-47.842369,-21.586973],[-47.840309,-21.58378],[-47.839794,-21.57947],[-47.838421,-21.576118],
                [-47.837391,-21.569254],[-47.836361,-21.56654],[-47.835331,-21.559196],[-47.796707,-21.558877],[-47.795334,-21.560313],[-47.794476,-21.562708],
                [-47.793102,-21.564305],[-47.791729,-21.567019],[-47.790699,-21.570211],[-47.789841,-21.571648],[-47.789326,-21.573404],[-47.787609,-21.574681],
                [-47.785034,-21.576278],[-47.781258,-21.577235],[-47.773361,-21.57947],[-47.76495,-21.584259],[-47.761173,-21.586813],[-47.759972,-21.590963],
                [-47.759628,-21.5924],[-47.757397,-21.591761],[-47.756538,-21.600859],[-47.734737,-21.599103],[-47.726841,-21.597188],[-47.725296,-21.594475],
                [-47.726498,-21.59224],[-47.726326,-21.589686],[-47.721691,-21.587771],[-47.717915,-21.587771],[-47.715683,-21.590165],[-47.712765,-21.591282],
                [-47.71122,-21.593198],[-47.709332,-21.595113],[-47.711391,-21.598305],[-47.712593,-21.60054],[-47.713795,-21.602455],[-47.712936,-21.603732],
                [-47.712765,-21.605009],[-47.715168,-21.607562],[-47.717056,-21.608201],[-47.720318,-21.609956],[-47.722893,-21.612191],[-47.725124,-21.615861]
            ]]
        }

    geometry = Geometry(geojson, crs="EPSG:4326")

    return geometry

# def get_evalscript_true_color():
#     """
#     Evalscript for generating a true color image using Sentinel-2 data.

#     This script selects bands B04 (red), B03 (green), and B02 (blue) and outputs them
#     in RGB order to produce a natural-color image, similar to what the human eye sees.
#     It is compatible with Evalscript Version 3 used by Sentinel Hub services.
#     """
#     return """
#     //VERSION=3

#     function setup() {
#         return {
#             input: [{
#                 bands: ["B04"]
#             }],
#             output: {
#                 bands: 1,
#                 sampleType: "FLOAT32"
#             }
#         };
#     }

#     function evaluatePixel(sample) {
#         return [sample.B04];
#     }
#     """


def create_true_color_request(
    aoi_bbox, aoi_size, config, timestamp, data_collection: DataCollection, bands
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
    band_requests = {}
    for band in bands:
        evalscript = get_evalscript_by_band(band)

        request = SentinelHubRequest(
            evalscript=evalscript,
            input_data=[
                SentinelHubRequest.input_data(
                    data_collection=data_collection,
                    time_interval=(timestamp, timestamp),
                )
            ],
            responses=[
                SentinelHubRequest.output_response("default", MimeType.TIFF)
            ],
            geometry=get_geometry(),  # ou use bbox=aoi_bbox
            size=aoi_size,
            config=config,
        )

        band_requests[band] = request
    return band_requests


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
