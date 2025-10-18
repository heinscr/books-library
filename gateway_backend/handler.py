"""
Lambda handlers for Books API

This module provides four Lambda handlers for the Books Library application:
1. list_handler: Lists all books from DynamoDB
2. get_book_handler: Gets book metadata and generates presigned S3 download URL
3. update_book_handler: Updates book metadata (e.g., read status)
4. s3_trigger_handler: Auto-populates DynamoDB when books are uploaded to S3

Architecture:
- API Gateway → Lambda → DynamoDB (for metadata)
- API Gateway → Lambda → S3 (for presigned download URLs)
- S3 Event → Lambda → DynamoDB (for auto-ingestion)
"""
from __future__ import annotations

import json
import os
from typing import Any
import boto3
from botocore.exceptions import ClientError
from botocore.config import Config
from datetime import datetime
from urllib.parse import unquote, urlparse
from decimal import Decimal

# Initialize AWS clients
s3_client = boto3.client(
    's3',
    region_name='us-east-2',
    config=Config(signature_version='s3v4')
)
dynamodb = boto3.resource('dynamodb', region_name='us-east-2')

# Configuration
BUCKET_NAME = os.environ.get('BUCKET_NAME', 'crackpow')
BOOKS_PREFIX = os.environ.get('BOOKS_PREFIX', 'books/')
BOOKS_TABLE_NAME = os.environ.get('BOOKS_TABLE')
books_table = dynamodb.Table(BOOKS_TABLE_NAME) if BOOKS_TABLE_NAME else None


def _response(status_code: int, body: Any) -> dict:
    """Helper to format API Gateway response"""
    return {
        "statusCode": status_code,
        "body": json.dumps(body),
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "Content-Type,Authorization",
            "Access-Control-Allow-Methods": "GET, PATCH, OPTIONS",
        },
    }


def list_handler(event, context):
    """
    Lambda handler to list all books from DynamoDB
    Returns list of books with metadata from DynamoDB
    """
    try:
        # Scan the DynamoDB table
        response = books_table.scan()
        items = response.get('Items', [])
        
        # Handle pagination if needed
        while 'LastEvaluatedKey' in response:
            response = books_table.scan(ExclusiveStartKey=response['LastEvaluatedKey'])
            items.extend(response.get('Items', []))
        
        # Convert DynamoDB items to API response format
        books = []
        for item in items:
            # Convert Decimal to float/int for JSON serialization
            book = {
                'id': item.get('id'),
                'name': item.get('name'),
                'created': item.get('created'),
                'read': item.get('read', False),
                's3_url': item.get('s3_url')
            }
            if 'author' in item:
                book['author'] = item['author']
            if 'size' in item:
                # Convert Decimal to int
                book['size'] = int(item['size']) if item['size'] else None
            books.append(book)
        
        # Sort by created date (most recent first)
        books.sort(key=lambda x: x.get('created', ''), reverse=True)
        
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
    Looks up metadata from DynamoDB and generates presigned URL from S3
    Expects book ID in path parameter 'id'
    Returns presigned URL valid for 1 hour along with book metadata
    """
    try:
        # Get the book ID from path parameters
        path_parameters = event.get('pathParameters', {})
        if not path_parameters or 'id' not in path_parameters:
            return _response(400, {
                'error': 'Bad Request',
                'message': 'Book ID is required in path'
            })
        
        book_id = unquote(path_parameters['id'])
        
        # Look up book in DynamoDB
        try:
            response = books_table.get_item(Key={'id': book_id})
            if 'Item' not in response:
                return _response(404, {
                    'error': 'Not Found',
                    'message': f'Book "{book_id}" not found'
                })
            
            book_item = response['Item']
            
        except ClientError as e:
            print(f"DynamoDB error: {str(e)}")
            return _response(500, {
                'error': 'Database Error',
                'message': str(e)
            })
        
        # Get S3 URL from DynamoDB record
        s3_url = book_item.get('s3_url')
        if not s3_url:
            return _response(500, {
                'error': 'Invalid Data',
                'message': 'Book record missing S3 URL'
            })
        
        # Extract bucket and key from S3 URL
        # Format: s3://bucket-name/path/to/object
        parsed_url = urlparse(s3_url)
        bucket = parsed_url.netloc
        s3_key = parsed_url.path.lstrip('/')
        
        # Generate presigned URL (valid for 1 hour)
        presigned_url = s3_client.generate_presigned_url(
            'get_object',
            Params={
                'Bucket': bucket,
                'Key': s3_key
            },
            ExpiresIn=3600  # 1 hour
        )
        
        # Return book metadata with presigned URL
        return _response(200, {
            'id': book_id,
            'name': book_item.get('name'),
            'created': book_item.get('created'),
            'read': book_item.get('read', False),
            'author': book_item.get('author'),
            'size': int(book_item['size']) if book_item.get('size') else None,
            'downloadUrl': presigned_url,
            'expiresIn': 3600
        })
        
    except Exception as e:
        print(f"Error generating presigned URL: {str(e)}")
        return _response(500, {
            'error': 'Internal Server Error',
            'message': str(e)
        })


def update_book_handler(event, context):
    """
    Lambda handler to update book metadata in DynamoDB
    Expects book ID in path parameter 'id'
    Accepts JSON body with fields to update (e.g., read, author, name)
    """
    try:
        # Get the book ID from path parameters
        path_parameters = event.get('pathParameters', {})
        if not path_parameters or 'id' not in path_parameters:
            return _response(400, {
                'error': 'Bad Request',
                'message': 'Book ID is required in path'
            })
        
        book_id = unquote(path_parameters['id'])
        
        # Parse request body
        try:
            body = json.loads(event.get('body', '{}'))
        except json.JSONDecodeError:
            return _response(400, {
                'error': 'Bad Request',
                'message': 'Invalid JSON in request body'
            })
        
        # Build update expression dynamically
        update_expr_parts = []
        expr_attr_values = {}
        expr_attr_names = {}
        
        # Handle updatable fields
        if 'read' in body:
            update_expr_parts.append('#read = :read')
            expr_attr_values[':read'] = bool(body['read'])
            expr_attr_names['#read'] = 'read'
        
        if 'author' in body:
            update_expr_parts.append('#author = :author')
            expr_attr_values[':author'] = str(body['author'])
            expr_attr_names['#author'] = 'author'
        
        if 'name' in body:
            update_expr_parts.append('#name = :name')
            expr_attr_values[':name'] = str(body['name'])
            expr_attr_names['#name'] = 'name'
        
        if not update_expr_parts:
            return _response(400, {
                'error': 'Bad Request',
                'message': 'No valid fields to update'
            })
        
        update_expression = 'SET ' + ', '.join(update_expr_parts)
        
        # Update the item in DynamoDB
        try:
            response = books_table.update_item(
                Key={'id': book_id},
                UpdateExpression=update_expression,
                ExpressionAttributeValues=expr_attr_values,
                ExpressionAttributeNames=expr_attr_names,
                ReturnValues='ALL_NEW',
                ConditionExpression='attribute_exists(id)'
            )
            
            updated_item = response['Attributes']
            
            return _response(200, {
                'id': updated_item.get('id'),
                'name': updated_item.get('name'),
                'created': updated_item.get('created'),
                'read': updated_item.get('read', False),
                'author': updated_item.get('author'),
                's3_url': updated_item.get('s3_url')
            })
            
        except ClientError as e:
            if e.response['Error']['Code'] == 'ConditionalCheckFailedException':
                return _response(404, {
                    'error': 'Not Found',
                    'message': f'Book "{book_id}" not found'
                })
            raise
        
    except Exception as e:
        print(f"Error updating book: {str(e)}")
        return _response(500, {
            'error': 'Internal Server Error',
            'message': str(e)
        })


def s3_trigger_handler(event, context):
    """
    Lambda handler triggered by S3 when a new .zip file is uploaded to books/
    Creates a DynamoDB record for the new book
    """
    try:
        for record in event.get('Records', []):
            # Get S3 event details
            s3_info = record.get('s3', {})
            bucket_name = s3_info.get('bucket', {}).get('name')
            s3_key = unquote(s3_info.get('object', {}).get('key', ''))
            s3_size = s3_info.get('object', {}).get('size', 0)
            
            if not bucket_name or not s3_key:
                print(f"Invalid S3 event record: {record}")
                continue
            
            # Extract filename from S3 key
            filename = s3_key.split('/')[-1]
            
            # Create a friendly name (remove .zip extension)
            friendly_name = filename.replace('.zip', '').replace('_', ' ').replace('-', ' ')
            
            # Generate unique ID (use filename without extension)
            book_id = filename.replace('.zip', '')
            
            # Build S3 URL
            s3_url = f"s3://{bucket_name}/{s3_key}"
            
            # Get timestamp
            timestamp = datetime.utcnow().isoformat() + 'Z'
            
            # Create DynamoDB item
            item = {
                'id': book_id,
                's3_url': s3_url,
                'name': friendly_name,
                'created': timestamp,
                'read': False,
                'size': s3_size
            }
            
            # Try to extract author from filename if it contains a dash
            # Format: "Author Name - Book Title.zip"
            if ' - ' in friendly_name:
                parts = friendly_name.split(' - ', 1)
                item['author'] = parts[0].strip()
                item['name'] = parts[1].strip()
            
            # Put item in DynamoDB
            try:
                books_table.put_item(Item=item)
                print(f"Successfully added book to DynamoDB: {book_id}")
            except ClientError as e:
                print(f"Error adding book to DynamoDB: {str(e)}")
                # Continue processing other records even if one fails
                continue
        
        return {
            'statusCode': 200,
            'body': json.dumps({'message': 'Successfully processed S3 events'})
        }
        
    except Exception as e:
        print(f"Error processing S3 trigger: {str(e)}")
        # For S3 triggers, we should return success even on error to prevent retries
        # Errors are logged to CloudWatch
        return {
            'statusCode': 200,
            'body': json.dumps({'message': 'Completed with errors', 'error': str(e)})
        }

