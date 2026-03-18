import json
import logging
import os

import boto3
from botocore.exceptions import ClientError, ProfileNotFound
from django.conf import settings

logger = logging.getLogger(__name__)


def get_boto3_session() -> boto3.Session:
    """
    Creates a Boto3 session using environment variables for AWS credentials.

    This function initializes a Boto3 session with the AWS credentials and region
    specified in the environment variables. It is used to interact with AWS services
    such as S3.

    Returns:
        boto3.Session: A Boto3 session object configured with AWS credentials.
    """

    try:
        return boto3.Session()
    except ProfileNotFound:
        raise ValueError(
            "The 'default' profile is not configured in ~/.aws/credentials. "
            "Please run 'aws configure' to set it up or use environment variables."
        )


def get_aws_secret_manager_secret(secret_name: str) -> str:
    """
    Retrieves a secret value from AWS Secrets Manager.

    Args:
        secret_name (str): The name of the secret to retrieve.

    Returns:
        str: The value of the secret.

    Raises:
        ValueError: If the secret cannot be retrieved.
    """
    try:
        session = get_boto3_session()
        client = session.client("secretsmanager")
        response = client.get_secret_value(SecretId=secret_name)
        return response["SecretString"]
    except Exception as e:
        raise ValueError(f"Failed to retrieve secret '{secret_name}': {str(e)}")


def upload_polygon_to_s3(filename: str, geojson_data) -> None:
    """Upload GeoJSON data to S3 under the polygons/ prefix."""
    session = get_boto3_session()
    client = session.client("s3")
    body = (
        json.dumps(geojson_data) if not isinstance(geojson_data, str) else geojson_data
    )
    client.put_object(
        Bucket=settings.S3_BUCKET_NAME,
        Key=f"polygons/{filename}",
        Body=body,
        ContentType="application/json",
    )


def download_polygon_from_s3(filename: str) -> str:
    """Download a polygon GeoJSON file from S3 and return its content as a string."""
    filename = os.path.basename(filename)
    session = get_boto3_session()
    client = session.client("s3")
    response = client.get_object(
        Bucket=settings.S3_BUCKET_NAME,
        Key=f"polygons/{filename}",
    )
    return response["Body"].read().decode("utf-8")


def upload_image_to_s3(
    key: str, image_data: bytes, content_type: str = "image/jpeg"
) -> None:
    """Upload image binary data to S3 under the images/ prefix."""
    session = get_boto3_session()
    client = session.client("s3")
    client.put_object(
        Bucket=settings.S3_BUCKET_NAME,
        Key=f"images/{key}",
        Body=image_data,
        ContentType=content_type,
    )


def get_presigned_image_url(key: str, expiration: int = 3600) -> str:
    """Generate a pre-signed URL for an image stored in S3."""
    session = get_boto3_session()
    client = session.client("s3")
    return client.generate_presigned_url(
        "get_object",
        Params={"Bucket": settings.S3_BUCKET_NAME, "Key": f"images/{key}"},
        ExpiresIn=expiration,
    )


def delete_image_from_s3(key: str) -> bool:
    """Delete an image from S3 under the images/ prefix. Returns True on success."""
    try:
        session = get_boto3_session()
        client = session.client("s3")
        client.delete_object(
            Bucket=settings.S3_BUCKET_NAME,
            Key=f"images/{key}",
        )
        return True
    except Exception as e:
        logger.warning(f"Failed to delete image from S3: {e}")
        return False


def delete_polygon_from_s3(filename: str) -> bool:
    """Delete a polygon GeoJSON file from S3. Returns True on success, False on failure."""
    filename = os.path.basename(filename)
    try:
        session = get_boto3_session()
        client = session.client("s3")
        client.delete_object(
            Bucket=settings.S3_BUCKET_NAME,
            Key=f"polygons/{filename}",
        )
        return True
    except Exception as e:
        logger.warning(f"Failed to delete polygon from S3: {e}")
        return False
