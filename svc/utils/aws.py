import os
import boto3


def get_boto3_session() -> boto3.Session:
    """
    Creates a Boto3 session using environment variables for AWS credentials.

    This function initializes a Boto3 session with the AWS credentials and region
    specified in the environment variables. It is used to interact with AWS services
    such as S3.

    Returns:
        boto3.Session: A Boto3 session object configured with AWS credentials.
    """

    return (
        boto3.Session(profile_name="bfl")
        if os.getenv("ENV") == "local"
        else boto3.Session()
    )
