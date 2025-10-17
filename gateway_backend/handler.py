"""Lambda handlers for Books API"""
from __future__ import annotations

import json
from typing import Any
import boto3
from botocore.exceptions import ClientError
from botocore.config import Config
from datetime import datetime
from urllib.parse import unquote

# Initialize S3 client with signature version 4
s3_client = boto3.client(
    's3',
    region_name='us-east-2',
    config=Config(signature_version='s3v4')
)

# S3 configuration
BUCKET_NAME = 'crackpow'
BOOKS_PREFIX = 'books/'


def _response(status_code: int, body: Any) -> dict:
    """Helper to format API Gateway response"""
    return {
        "statusCode": status_code,
        "body": json.dumps(body),
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "Content-Type,Authorization",
            "Access-Control-Allow-Methods": "GET, OPTIONS",
        },
    }


def list_handler(event, context):
    """
    Lambda handler to list all .zip files in the S3 books directory
    Returns list of books with name, size, and last modified timestamp
    """
    try:
        # List objects in the books folder
        response = s3_client.list_objects_v2(
            Bucket=BUCKET_NAME,
            Prefix=BOOKS_PREFIX
        )
        
        # Check if any objects were found
        if 'Contents' not in response:
            return _response(200, [])
        
        # Filter for .zip files and extract relevant information
        books = []
        for obj in response['Contents']:
            key = obj['Key']
            
            # Skip the folder itself and non-zip files
            if key == BOOKS_PREFIX or not key.endswith('.zip'):
                continue
            
            # Extract filename (remove prefix)
            filename = key.replace(BOOKS_PREFIX, '')
            
            books.append({
                'name': filename,
                'size': obj['Size'],
                'lastModified': obj['LastModified'].isoformat()
            })
        
        # Sort by date (most recent first)
        books.sort(key=lambda x: x['lastModified'], reverse=True)
        
        return _response(200, books)
        
    except Exception as e:
        print(f"Error listing books: {str(e)}")
        return _response(500, {
            'error': 'Failed to list books',
            'message': str(e)
        })


def get_book_handler(event, context):
    """
    Lambda handler to generate a presigned URL for downloading a specific book
    Expects book filename in path parameter 'id'
    Returns presigned URL valid for 1 hour
    """
    try:
        # Get the book ID from path parameters
        path_parameters = event.get('pathParameters', {})
        if not path_parameters or 'id' not in path_parameters:
            return _response(400, {
                'error': 'Bad Request',
                'message': 'Book ID is required in path'
            })
        
        # URL-decode the book ID (API Gateway doesn't decode path parameters)
        book_id = unquote(path_parameters['id'])
        
        # Validate that the book ID doesn't contain path traversal attempts
        if '..' in book_id or '/' in book_id:
            return _response(400, {
                'error': 'Bad Request',
                'message': 'Invalid book ID'
            })
        
        # Ensure the book ends with .zip
        if not book_id.endswith('.zip'):
            book_id = f"{book_id}.zip"
        
        # Construct the full S3 key
        s3_key = f"{BOOKS_PREFIX}{book_id}"
        
        # Check if the object exists
        try:
            s3_client.head_object(Bucket=BUCKET_NAME, Key=s3_key)
        except ClientError as e:
            if e.response['Error']['Code'] == '404' or e.response['Error']['Code'] == 'NoSuchKey':
                return _response(404, {
                    'error': 'Not Found',
                    'message': f'Book "{book_id}" not found'
                })
            raise
        
        # Generate presigned URL (valid for 1 hour)
        presigned_url = s3_client.generate_presigned_url(
            'get_object',
            Params={
                'Bucket': BUCKET_NAME,
                'Key': s3_key
            },
            ExpiresIn=3600  # 1 hour
        )
        
        return _response(200, {
            'bookId': book_id,
            'downloadUrl': presigned_url,
            'expiresIn': 3600
        })
        
    except Exception as e:
        print(f"Error generating presigned URL: {str(e)}")
        return _response(500, {
            'error': 'Internal Server Error',
            'message': str(e)
        })
