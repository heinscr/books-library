"""
Lambda handlers for Books API

This module provides seven Lambda handlers for the Books Library application:
1. list_handler: Lists all books from DynamoDB
2. get_book_handler: Gets book metadata and generates presigned S3 download URL
3. update_book_handler: Updates book metadata (e.g., read status, author)
4. delete_book_handler: Deletes book from both DynamoDB and S3
5. upload_handler: Generates presigned S3 upload URL for authenticated users
6. set_upload_metadata_handler: Sets author metadata after upload completes
7. s3_trigger_handler: Auto-populates DynamoDB when books are uploaded to S3

Architecture:
- API Gateway → Lambda → DynamoDB (for metadata)
- API Gateway → Lambda → S3 (for presigned download/upload URLs)
- S3 Event → Lambda → DynamoDB (for auto-ingestion)
- Frontend → upload_handler → S3 direct upload → s3_trigger_handler → set_upload_metadata_handler
"""
from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any
from urllib.parse import unquote, urlparse

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError

# Configure structured logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize AWS clients
s3_client = boto3.client(
    's3',
    region_name='us-east-2',
    config=Config(signature_version='s3v4')
)
dynamodb = boto3.resource('dynamodb', region_name='us-east-2')

# Configuration
BUCKET_NAME = os.environ.get('BUCKET_NAME', 'YOUR_BUCKET')
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
            "Access-Control-Allow-Methods": "GET, POST, PATCH, DELETE, OPTIONS",
        },
    }


def list_handler(event, context):
    """
    Lambda handler to list all books from DynamoDB
    Returns list of books with metadata from DynamoDB
    """
    logger.info("list_handler invoked", extra={"table": BOOKS_TABLE_NAME})
    
    try:
        # Scan the DynamoDB table
        response = books_table.scan()
        items = response.get('Items', [])
        
        # Handle pagination if needed
        while 'LastEvaluatedKey' in response:
            response = books_table.scan(ExclusiveStartKey=response['LastEvaluatedKey'])
            items.extend(response.get('Items', []))
        
        logger.info(f"Retrieved {len(items)} books from DynamoDB")
        
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
        logger.error(f"Error listing books: {str(e)}", exc_info=True)
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
    logger.info("get_book_handler invoked")
    
    try:
        # Get the book ID from path parameters
        path_parameters = event.get('pathParameters', {})
        if not path_parameters or 'id' not in path_parameters:
            logger.warning("Missing book ID in path parameters")
            return _response(400, {
                'error': 'Bad Request',
                'message': 'Book ID is required in path'
            })
        
        book_id = unquote(path_parameters['id'])
        logger.info(f"Fetching book: {book_id}")
        
        # Look up book in DynamoDB
        try:
            response = books_table.get_item(Key={'id': book_id})
            if 'Item' not in response:
                logger.warning(f"Book not found: {book_id}")
                return _response(404, {
                    'error': 'Not Found',
                    'message': f'Book "{book_id}" not found'
                })
            
            book_item = response['Item']
            
        except ClientError as e:
            logger.error(f"DynamoDB error: {str(e)}", exc_info=True)
            return _response(500, {
                'error': 'Database Error',
                'message': str(e)
            })
        
        # Get S3 URL from DynamoDB record
        s3_url = book_item.get('s3_url')
        if not s3_url:
            logger.error(f"Book {book_id} missing S3 URL in DynamoDB")
            return _response(500, {
                'error': 'Invalid Data',
                'message': 'Book record missing S3 URL'
            })
        
        # Extract bucket and key from S3 URL
        # Format: s3://bucket-name/path/to/object
        parsed_url = urlparse(s3_url)
        bucket = parsed_url.netloc
        s3_key = parsed_url.path.lstrip('/')
        
        logger.info(f"Generating presigned URL for s3://{bucket}/{s3_key}")
        
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
        logger.error(f"Error generating presigned URL: {str(e)}", exc_info=True)
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
    logger.info("update_book_handler invoked")
    
    try:
        # Get the book ID from path parameters
        path_parameters = event.get('pathParameters', {})
        if not path_parameters or 'id' not in path_parameters:
            logger.warning("Missing book ID in path parameters")
            return _response(400, {
                'error': 'Bad Request',
                'message': 'Book ID is required in path'
            })
        
        book_id = unquote(path_parameters['id'])
        logger.info(f"Updating book: {book_id}")
        
        # Parse request body
        try:
            body = json.loads(event.get('body', '{}'))
        except json.JSONDecodeError:
            logger.warning("Invalid JSON in request body")
            return _response(400, {
                'error': 'Bad Request',
                'message': 'Invalid JSON in request body'
            })
        
        # Validate input types and constraints
        if 'read' in body:
            if not isinstance(body['read'], bool):
                return _response(400, {
                    'error': 'Bad Request',
                    'message': 'Field "read" must be a boolean'
                })
        
        if 'author' in body:
            if not isinstance(body['author'], str):
                return _response(400, {
                    'error': 'Bad Request',
                    'message': 'Field "author" must be a string'
                })
            if len(body['author']) > 500:
                return _response(400, {
                    'error': 'Bad Request',
                    'message': 'Field "author" exceeds maximum length of 500 characters'
                })
        
        if 'name' in body:
            if not isinstance(body['name'], str):
                return _response(400, {
                    'error': 'Bad Request',
                    'message': 'Field "name" must be a string'
                })
            if len(body['name']) > 500:
                return _response(400, {
                    'error': 'Bad Request',
                    'message': 'Field "name" exceeds maximum length of 500 characters'
                })
            if len(body['name']) == 0:
                return _response(400, {
                    'error': 'Bad Request',
                    'message': 'Field "name" cannot be empty'
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
            logger.info(f"Updating DynamoDB item {book_id} with fields: {list(expr_attr_names.values())}")
            response = books_table.update_item(
                Key={'id': book_id},
                UpdateExpression=update_expression,
                ExpressionAttributeValues=expr_attr_values,
                ExpressionAttributeNames=expr_attr_names,
                ReturnValues='ALL_NEW',
                ConditionExpression='attribute_exists(id)'
            )
            
            updated_item = response['Attributes']
            logger.info(f"Successfully updated book: {book_id}")
            
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
                logger.warning(f"Book not found: {book_id}")
                return _response(404, {
                    'error': 'Not Found',
                    'message': f'Book "{book_id}" not found'
                })
            raise
        
    except Exception as e:
        logger.error(f"Error updating book: {str(e)}", exc_info=True)
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
            # S3 keys come URL-encoded, decode them properly
            # Note: unquote handles %20 but + is used for spaces in form encoding
            s3_key = unquote(s3_info.get('object', {}).get('key', ''))
            # Also replace + with space (from form-encoded uploads)
            s3_key = s3_key.replace('+', ' ')
            s3_size = s3_info.get('object', {}).get('size', 0)
            
            if not bucket_name or not s3_key:
                print(f"Invalid S3 event record: {record}")
                continue
            
            # Extract filename from S3 key
            filename = s3_key.split('/')[-1]
            
            # Create a friendly name (remove .zip extension)
            friendly_name = filename.replace('.zip', '')
            
            # Generate unique ID (use filename without extension)
            # For ID, keep original filename structure but URL-decode it
            book_id = filename.replace('.zip', '')
            
            # Build S3 URL
            s3_url = f"s3://{bucket_name}/{s3_key}"
            
            # Get timestamp (use timezone-aware UTC)
            timestamp = datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
            
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


def upload_handler(event, context):
    """
    Lambda handler to generate presigned S3 upload URL for authenticated users
    Expects JSON body with:
    - filename: The name of the file to upload (must end with .zip)
    - author: (optional) Author name to associate with the book
    
    Returns presigned POST URL and fields for uploading directly to S3
    """
    logger.info("upload_handler invoked")
    
    try:
        # Verify user is authenticated (Cognito authorizer adds this)
        authorizer = event.get('requestContext', {}).get('authorizer', {})
        claims = authorizer.get('claims', {})
        user_email = claims.get('email', 'unknown')
        
        logger.info(f"Upload request from user: {user_email}")
        
        # Parse request body
        try:
            body = json.loads(event.get('body', '{}'))
        except json.JSONDecodeError:
            logger.warning("Invalid JSON in request body")
            return _response(400, {
                'error': 'Bad Request',
                'message': 'Invalid JSON in request body'
            })
        
        # Validate filename
        filename = body.get('filename')
        if not filename:
            logger.warning("Missing filename in request")
            return _response(400, {
                'error': 'Bad Request',
                'message': 'filename is required'
            })
        
        # Validate file extension
        if not filename.lower().endswith('.zip'):
            logger.warning(f"Invalid file extension: {filename}")
            return _response(400, {
                'error': 'Bad Request',
                'message': 'Only .zip files are allowed'
            })
        
        # Sanitize filename (remove path traversal attempts)
        filename = os.path.basename(filename)
        
        # Get optional author
        author = body.get('author', '').strip()
        if author and len(author) > 500:
            return _response(400, {
                'error': 'Bad Request',
                'message': 'Author name exceeds maximum length of 500 characters'
            })
        
        # Get optional file size for validation
        file_size = body.get('fileSize', 0)
        max_size = 5 * 1024 * 1024 * 1024  # 5GB limit
        if file_size > max_size:
            return _response(400, {
                'error': 'Bad Request',
                'message': f'File size exceeds maximum limit of 5GB'
            })
        
        # Generate S3 key
        s3_key = f"{BOOKS_PREFIX}{filename}"
        
        logger.info(f"Generating presigned PUT URL for: {s3_key} ({file_size} bytes)")
        
        # Generate presigned PUT URL (valid for 60 minutes for large files)
        # We don't include Metadata in params because it would require the client
        # to send exact matching headers (signature validation issue causing 403)
        presigned_url = s3_client.generate_presigned_url(
            'put_object',
            Params={
                'Bucket': BUCKET_NAME,
                'Key': s3_key,
                'ContentType': 'application/zip'
            },
            ExpiresIn=3600  # 60 minutes for large file uploads
        )
        
        logger.info(f"Successfully generated presigned PUT URL for {filename}")
        
        # Return the URL and metadata
        response_data = {
            'uploadUrl': presigned_url,
            'method': 'PUT',
            'filename': filename,
            's3Key': s3_key,
            'expiresIn': 3600
        }
        
        if author:
            response_data['author'] = author
            logger.info(f"Author will be set via metadata endpoint: {author}")
        
        return _response(200, response_data)
        
    except Exception as e:
        logger.error(f"Error generating upload URL: {str(e)}", exc_info=True)
        return _response(500, {
            'error': 'Internal Server Error',
            'message': str(e)
        })


def set_upload_metadata_handler(event, context):
    """
    Lambda handler to set metadata (author, etc.) after S3 upload completes
    This is called by the frontend after the S3 upload finishes successfully
    
    Expects JSON body with:
    - bookId: The ID of the book (filename without .zip)
    - author: (optional) Author name to set
    
    Returns success/failure status
    """
    logger.info("set_upload_metadata_handler invoked")
    
    try:
        # Verify user is authenticated
        authorizer = event.get('requestContext', {}).get('authorizer', {})
        claims = authorizer.get('claims', {})
        user_email = claims.get('email', 'unknown')
        
        logger.info(f"Set metadata request from user: {user_email}")
        
        # Parse request body
        try:
            body = json.loads(event.get('body', '{}'))
        except json.JSONDecodeError:
            logger.warning("Invalid JSON in request body")
            return _response(400, {
                'error': 'Bad Request',
                'message': 'Invalid JSON in request body'
            })
        
        # Validate bookId
        book_id = body.get('bookId')
        if not book_id:
            logger.warning("Missing bookId in request")
            return _response(400, {
                'error': 'Bad Request',
                'message': 'bookId is required'
            })
        
        # Get optional author
        author = body.get('author', '').strip()
        if author and len(author) > 500:
            return _response(400, {
                'error': 'Bad Request',
                'message': 'Author name exceeds maximum length of 500 characters'
            })
        
        if not author:
            # Nothing to update
            return _response(200, {
                'message': 'No metadata to update'
            })
        
        logger.info(f"Setting author '{author}' for book: {book_id}")
        
        # Update DynamoDB item with author
        update_expression = "SET author = :author"
        expression_values = {':author': author}
        
        try:
            books_table.update_item(
                Key={'id': book_id},
                UpdateExpression=update_expression,
                ExpressionAttributeValues=expression_values,
                ConditionExpression='attribute_exists(id)'
            )
            
            logger.info(f"Successfully updated author for book: {book_id}")
            
            return _response(200, {
                'message': 'Metadata updated successfully',
                'bookId': book_id,
                'author': author
            })
            
        except ClientError as e:
            if e.response['Error']['Code'] == 'ConditionalCheckFailedException':
                logger.warning(f"Book not found: {book_id}")
                return _response(404, {
                    'error': 'Not Found',
                    'message': f'Book with id {book_id} not found'
                })
            raise
        
    except Exception as e:
        logger.error(f"Error setting upload metadata: {str(e)}", exc_info=True)
        return _response(500, {
            'error': 'Internal Server Error',
            'message': str(e)
        })


def delete_book_handler(event, context):
    """
    Lambda handler to delete a book from both DynamoDB and S3
    Expects book ID in path parameter 'id'
    
    Deletes:
    1. DynamoDB record with book metadata
    2. S3 object (the .zip file)
    
    Returns success/failure status
    """
    logger.info("delete_book_handler invoked")
    
    try:
        # Verify user is authenticated
        authorizer = event.get('requestContext', {}).get('authorizer', {})
        claims = authorizer.get('claims', {})
        user_email = claims.get('email', 'unknown')
        
        logger.info(f"Delete request from user: {user_email}")
        
        # Get the book ID from path parameters
        path_parameters = event.get('pathParameters', {})
        if not path_parameters or 'id' not in path_parameters:
            logger.warning("Missing book ID in path parameters")
            return _response(400, {
                'error': 'Bad Request',
                'message': 'Book ID is required in path'
            })
        
        book_id = unquote(path_parameters['id'])
        logger.info(f"Deleting book: {book_id}")
        
        # First, get the book record to find the S3 URL
        try:
            response = books_table.get_item(Key={'id': book_id})
            if 'Item' not in response:
                logger.warning(f"Book not found: {book_id}")
                return _response(404, {
                    'error': 'Not Found',
                    'message': f'Book with id "{book_id}" not found'
                })
            
            book_item = response['Item']
            s3_url = book_item.get('s3_url')
            
        except ClientError as e:
            logger.error(f"DynamoDB error: {str(e)}", exc_info=True)
            return _response(500, {
                'error': 'Database Error',
                'message': str(e)
            })
        
        # Delete from S3 if S3 URL exists
        if s3_url:
            try:
                # Parse S3 URL to get bucket and key
                # Format: s3://bucket-name/path/to/object
                parsed_url = urlparse(s3_url)
                bucket = parsed_url.netloc
                s3_key = parsed_url.path.lstrip('/')
                
                logger.info(f"Deleting S3 object: s3://{bucket}/{s3_key}")
                
                s3_client.delete_object(
                    Bucket=bucket,
                    Key=s3_key
                )
                
                logger.info(f"Successfully deleted S3 object: {s3_key}")
                
            except ClientError as e:
                # Log error but continue with DynamoDB deletion
                logger.error(f"S3 deletion error: {str(e)}", exc_info=True)
                # Don't fail the entire operation if S3 delete fails
        else:
            logger.warning(f"No S3 URL found for book: {book_id}")
        
        # Delete from DynamoDB
        try:
            books_table.delete_item(
                Key={'id': book_id},
                ConditionExpression='attribute_exists(id)'
            )
            
            logger.info(f"Successfully deleted DynamoDB record: {book_id}")
            
            return _response(200, {
                'message': 'Book deleted successfully',
                'bookId': book_id
            })
            
        except ClientError as e:
            if e.response['Error']['Code'] == 'ConditionalCheckFailedException':
                logger.warning(f"Book not found during deletion: {book_id}")
                return _response(404, {
                    'error': 'Not Found',
                    'message': f'Book with id "{book_id}" not found'
                })
            raise
        
    except Exception as e:
        logger.error(f"Error deleting book: {str(e)}", exc_info=True)
        return _response(500, {
            'error': 'Internal Server Error',
            'message': str(e)
        })

