import logging
import time

import boto3
from botocore.exceptions import ClientError, ProfileNotFound

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
