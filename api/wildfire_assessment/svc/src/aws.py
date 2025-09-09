import os

import boto3
from botocore.exceptions import ProfileNotFound


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
        return boto3.Session(profile_name="default")
    except ProfileNotFound:
        raise ValueError(
            "The 'default' profile is not configured in ~/.aws/credentials. "
            "Please run 'aws configure' to set it up or use environment variables."
        )
    
def generate_presigned_url(bucket_name: str, object_key: str, expiration=3600) -> str:
    """
    Generates a pre-signed URL for an S3 object.

    Args:
        bucket_name (str): The name of the S3 bucket.
        object_key (str): The key (path) of the object in the bucket.
        expiration (int): Time in seconds for the URL to remain valid (default: 3600 seconds = 1 hour).

    Returns:
        str: A pre-signed URL for the S3 object.

    Raises:
        ValueError: If credentials are invalid or the object does not exist.
    """
    try:
        s3_session = get_boto3_session()
        s3_client = s3_session.client('s3')
        url = s3_client.generate_presigned_url(
            'get_object',
            Params={
                'Bucket': bucket_name,
                'Key': object_key
            },
            ExpiresIn=expiration
        )
        return url
    except Exception as e:
        raise ValueError(f"Failed to generate pre-signed URL: {str(e)}")