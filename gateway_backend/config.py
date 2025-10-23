"""
Configuration and AWS client initialization for Books API Lambda handlers

This module provides:
- AWS service clients (S3, DynamoDB)
- Environment variable configuration
- Constants used across handlers
"""

from __future__ import annotations

import os
from typing import TYPE_CHECKING

import boto3
from botocore.config import Config

if TYPE_CHECKING:
    from mypy_boto3_dynamodb.service_resource import DynamoDBServiceResource, Table
    from mypy_boto3_s3.client import S3Client

# Constants
URL_EXPIRY_SECONDS = 3600  # 1 hour for presigned URLs
MAX_STRING_LENGTH = 500  # Maximum length for string fields
MAX_FILE_SIZE_BYTES = 5 * 1024 * 1024 * 1024  # 5GB
MAX_SERIES_ORDER = 100
MIN_SERIES_ORDER = 1

# Initialize AWS clients with type hints
s3_client: "S3Client" = boto3.client(
    "s3",
    region_name="us-east-2",
    endpoint_url="https://s3.us-east-2.amazonaws.com",
    config=Config(signature_version="s3v4"),
)
dynamodb: "DynamoDBServiceResource" = boto3.resource("dynamodb", region_name="us-east-2")

# Environment configuration
BUCKET_NAME = os.environ.get("BUCKET_NAME", "YOUR_BUCKET")
BOOKS_PREFIX = os.environ.get("BOOKS_PREFIX", "books/")
BOOKS_TABLE_NAME = os.environ.get("BOOKS_TABLE")
USER_BOOKS_TABLE_NAME = os.environ.get("USER_BOOKS_TABLE")

# Initialize DynamoDB tables
# For type checking: treat as non-None (tests will mock these)
# For production: Lambda environment must have these env vars set
if BOOKS_TABLE_NAME:
    books_table: "Table" = dynamodb.Table(BOOKS_TABLE_NAME)
else:
    books_table = None  # type: ignore[assignment]

if USER_BOOKS_TABLE_NAME:
    user_books_table: "Table" = dynamodb.Table(USER_BOOKS_TABLE_NAME)
else:
    user_books_table = None  # type: ignore[assignment]
