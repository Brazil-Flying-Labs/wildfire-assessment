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

def upload_to_s3(data: bytes, bucket_name: str, s3_key: str, content_type: str, expiration: int = 3600) -> tuple:
    """
    Faz upload de dados para o S3 e retorna tanto a URL do objeto quanto um pre-signed URL
    expiration: tempo em segundos que o pre-signed URL será válido (padrão: 1 hora)
    """
    session = get_boto3_session()
    s3 = session.client('s3')
    
    try:
        # Faz o upload do objeto
        s3.put_object(
            Bucket=bucket_name,
            Key=s3_key,
            Body=data,
            ContentType=content_type,
            Metadata={
                'generated_by': 'wildfire_analyser',
                'timestamp': time.strftime('%Y-%m-%dT%H:%M:%SZ')
            }
        )
        
        # Gera o pre-signed URL
        presigned_url = s3.generate_presigned_url(
            'get_object',
            Params={
                'Bucket': bucket_name,
                'Key': s3_key
            },
            ExpiresIn=expiration
        )
        
        # URL padrão do S3
        s3_object_url = f"s3://{bucket_name}/{s3_key}"
        
        return s3_object_url, presigned_url
        
    except ClientError as e:
        logger.error(f"Erro no upload para S3: {e}")
        raise
