import json
import logging

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
    body = json.dumps(geojson_data) if not isinstance(geojson_data, str) else geojson_data
    client.put_object(
        Bucket=settings.S3_BUCKET_NAME,
        Key=f"polygons/{filename}",
        Body=body,
        ContentType="application/json",
    )


def download_polygon_from_s3(filename: str) -> str:
    """Download a polygon GeoJSON file from S3 and return its content as a string."""
    session = get_boto3_session()
    client = session.client("s3")
    response = client.get_object(
        Bucket=settings.S3_BUCKET_NAME,
        Key=f"polygons/{filename}",
    )
    return response["Body"].read().decode("utf-8")


def delete_polygon_from_s3(filename: str) -> bool:
    """Delete a polygon GeoJSON file from S3. Returns True on success, False on failure."""
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
