"""S3 client utilities."""

import boto3
from django.conf import settings


def s3_client():
    """Get configured S3 client."""
    return boto3.client(
        "s3",
        endpoint_url=settings.S3_ENDPOINT or None,
        aws_access_key_id=settings.S3_ACCESS_KEY or None,
        aws_secret_access_key=settings.S3_SECRET_KEY or None,
        region_name=settings.S3_REGION or None,
        use_ssl=settings.S3_USE_SSL,
    )
