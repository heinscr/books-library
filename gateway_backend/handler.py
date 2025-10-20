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
- API Gateway -> Lambda -> DynamoDB (for metadata)
- API Gateway -> Lambda -> S3 (for presigned download/upload URLs)
- S3 Event -> Lambda -> DynamoDB (for auto-ingestion)
- Frontend -> upload_handler -> S3 direct upload -> s3_trigger_handler -> set_upload_metadata_handler

Updated: 2025-10-19 - Migrated to crackpow-books bucket
"""

from __future__ import annotations

import json
import logging
import os
from datetime import UTC, datetime
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
    "s3", 
    region_name="us-east-2",
    endpoint_url="https://s3.us-east-2.amazonaws.com",
    config=Config(signature_version="s3v4")
)
dynamodb = boto3.resource("dynamodb", region_name="us-east-2")

# Configuration
BUCKET_NAME = os.environ.get("BUCKET_NAME", "YOUR_BUCKET")
BOOKS_PREFIX = os.environ.get("BOOKS_PREFIX", "books/")
BOOKS_TABLE_NAME = os.environ.get("BOOKS_TABLE")
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


def _get_path_param(event: dict, param: str) -> tuple[str | None, dict | None]:
    """
    Extract and URL-decode a path parameter from API Gateway event.

    Returns:
        tuple: (decoded_value, error_response) - If successful, error_response is None
    """
    path_params = event.get("pathParameters", {})
    if not path_params or param not in path_params:
        logger.warning(f"Missing {param} in path parameters")
        return None, _response(
            400, {"error": "Bad Request", "message": f"{param.capitalize()} is required in path"}
        )
    return unquote(path_params[param]), None


def _parse_json_body(event: dict) -> tuple[dict, dict | None]:
    """
    Parse JSON body from API Gateway event.

    Returns:
        tuple: (parsed_body, error_response) - If successful, error_response is None
               If error, parsed_body is empty dict (caller should check error first)
    """
    try:
        return json.loads(event.get("body", "{}")), None
    except json.JSONDecodeError:
        logger.warning("Invalid JSON in request body")
        return {}, _response(
            400, {"error": "Bad Request", "message": "Invalid JSON in request body"}
        )


def _validate_string_field(
    body: dict, field: str, max_length: int = 500, required: bool = False
) -> dict | None:
    """
    Validate a string field in request body.

    Args:
        body: Request body dictionary
        field: Field name to validate
        max_length: Maximum allowed length
        required: Whether the field is required

    Returns:
        dict: Error response if validation fails, None if valid
    """
    if field not in body:
        if required:
            return _response(
                400, {"error": "Bad Request", "message": f'Field "{field}" is required'}
            )
        return None

    value = body[field]
    if not isinstance(value, str):
        return _response(
            400, {"error": "Bad Request", "message": f'Field "{field}" must be a string'}
        )

    if len(value) > max_length:
        return _response(
            400,
            {
                "error": "Bad Request",
                "message": f'Field "{field}" exceeds maximum length of {max_length}',
            },
        )

    if required and not value.strip():
        return _response(
            400, {"error": "Bad Request", "message": f'Field "{field}" cannot be empty'}
        )

    return None


def _validate_boolean_field(body: dict, field: str) -> dict | None:
    """
    Validate a boolean field in request body.

    Returns:
        dict: Error response if validation fails, None if valid
    """
    if field in body and not isinstance(body[field], bool):
        return _response(
            400, {"error": "Bad Request", "message": f'Field "{field}" must be a boolean'}
        )
    return None


def list_handler(event, context):
    """
    Lambda handler to list all books from DynamoDB
    Returns list of books with metadata from DynamoDB
    """
    logger.info("list_handler invoked", extra={"table": BOOKS_TABLE_NAME})

    try:
        # Scan the DynamoDB table
        response = books_table.scan()
        items = response.get("Items", [])

        # Handle pagination if needed
        while "LastEvaluatedKey" in response:
            response = books_table.scan(ExclusiveStartKey=response["LastEvaluatedKey"])
            items.extend(response.get("Items", []))

        logger.info(f"Retrieved {len(items)} books from DynamoDB")

        # Convert DynamoDB items to API response format
        books = []
        for item in items:
            # Convert Decimal to float/int for JSON serialization
            book = {
                "id": item.get("id"),
                "name": item.get("name"),
                "created": item.get("created"),
                "read": item.get("read", False),
                "s3_url": item.get("s3_url"),
            }
            if "author" in item:
                book["author"] = item["author"]
            if "size" in item:
                # Convert Decimal to int
                book["size"] = int(item["size"]) if item["size"] else None
            if "series_name" in item:
                book["series_name"] = item["series_name"]
            if "series_order" in item:
                book["series_order"] = int(item["series_order"]) if item["series_order"] else None
            books.append(book)

        # Sort by created date (most recent first)
        books.sort(key=lambda x: x.get("created", ""), reverse=True)

        return _response(200, books)

    except Exception as e:
        logger.error(f"Error listing books: {str(e)}", exc_info=True)
        return _response(500, {"error": "Failed to list books", "message": str(e)})


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
        book_id, error = _get_path_param(event, "id")
        if error:
            return error

        logger.info(f"Fetching book: {book_id}")

        # Look up book in DynamoDB
        try:
            response = books_table.get_item(Key={"id": book_id})
            if "Item" not in response:
                logger.warning(f"Book not found: {book_id}")
                return _response(
                    404, {"error": "Not Found", "message": f'Book "{book_id}" not found'}
                )

            book_item = response["Item"]

        except ClientError as e:
            logger.error(f"DynamoDB error: {str(e)}", exc_info=True)
            return _response(500, {"error": "Database Error", "message": str(e)})

        # Get S3 URL from DynamoDB record
        s3_url = book_item.get("s3_url")
        if not s3_url:
            logger.error(f"Book {book_id} missing S3 URL in DynamoDB")
            return _response(
                500, {"error": "Invalid Data", "message": "Book record missing S3 URL"}
            )

        # Extract bucket and key from S3 URL
        # Format: s3://bucket-name/path/to/object
        parsed_url = urlparse(s3_url)
        bucket = parsed_url.netloc
        s3_key = parsed_url.path.lstrip("/")

        logger.info(f"Generating presigned download URL for: {book_id}")

        # Generate presigned URL (valid for 1 hour)
        presigned_url = s3_client.generate_presigned_url(
            "get_object", 
            Params={"Bucket": bucket, "Key": s3_key}, 
            ExpiresIn=3600,  # 1 hour
        )

        # Return book metadata with presigned URL
        return _response(
            200,
            {
                "id": book_id,
                "name": book_item.get("name"),
                "created": book_item.get("created"),
                "read": book_item.get("read", False),
                "author": book_item.get("author"),
                "series_name": book_item.get("series_name"),
                "series_order": int(book_item["series_order"]) if book_item.get("series_order") else None,
                "size": int(book_item["size"]) if book_item.get("size") else None,
                "downloadUrl": presigned_url,
                "expiresIn": 3600,
            },
        )

    except Exception as e:
        logger.error(f"Error generating presigned URL: {str(e)}", exc_info=True)
        return _response(500, {"error": "Internal Server Error", "message": str(e)})


def update_book_handler(event, context):
    """
    Lambda handler to update book metadata in DynamoDB
    Expects book ID in path parameter 'id'
    Accepts JSON body with fields to update (e.g., read, author, name, series_name, series_order)
    """
    logger.info("update_book_handler invoked")

    try:
        # Get the book ID from path parameters
        book_id, error = _get_path_param(event, "id")
        if error:
            return error

        logger.info(f"Updating book: {book_id}")

        # Parse request body
        body, error = _parse_json_body(event)
        if error:
            return error

        # Validate fields
        error = _validate_boolean_field(body, "read")
        if error:
            return error

        error = _validate_string_field(body, "author", max_length=500)
        if error:
            return error

        error = _validate_string_field(body, "name", max_length=500, required=False)
        if error:
            return error

        error = _validate_string_field(body, "series_name", max_length=500)
        if error:
            return error

        # Additional validation for name (cannot be empty if provided)
        if "name" in body and not body["name"].strip():
            return _response(
                400, {"error": "Bad Request", "message": 'Field "name" cannot be empty'}
            )

        # Validate series_order if provided
        if "series_order" in body:
            series_order = body["series_order"]
            # Allow None/null to clear the field
            if series_order is not None:
                try:
                    series_order_int = int(series_order)
                    if series_order_int < 1 or series_order_int > 100:
                        return _response(
                            400,
                            {"error": "Bad Request", "message": "series_order must be between 1 and 100"}
                        )
                except (ValueError, TypeError):
                    return _response(
                        400,
                        {"error": "Bad Request", "message": "series_order must be an integer"}
                    )

        # Build update expression dynamically
        update_expr_parts = []
        remove_expr_parts = []
        expr_attr_values = {}
        expr_attr_names = {}

        # Handle updatable fields
        if "read" in body:
            update_expr_parts.append("#read = :read")
            expr_attr_values[":read"] = bool(body["read"])
            expr_attr_names["#read"] = "read"

        if "author" in body:
            update_expr_parts.append("#author = :author")
            expr_attr_values[":author"] = str(body["author"])
            expr_attr_names["#author"] = "author"

        if "name" in body:
            update_expr_parts.append("#name = :name")
            expr_attr_values[":name"] = str(body["name"])
            expr_attr_names["#name"] = "name"

        if "series_name" in body:
            update_expr_parts.append("#series_name = :series_name")
            expr_attr_values[":series_name"] = str(body["series_name"])
            expr_attr_names["#series_name"] = "series_name"

        if "series_order" in body:
            series_order = body["series_order"]
            if series_order is None or series_order == "":
                # Remove the attribute if null/empty
                remove_expr_parts.append("#series_order")
                expr_attr_names["#series_order"] = "series_order"
            else:
                update_expr_parts.append("#series_order = :series_order")
                expr_attr_values[":series_order"] = int(series_order)
                expr_attr_names["#series_order"] = "series_order"

        if not update_expr_parts and not remove_expr_parts:
            return _response(400, {"error": "Bad Request", "message": "No valid fields to update"})

        # Build the full update expression
        update_expression_parts = []
        if update_expr_parts:
            update_expression_parts.append("SET " + ", ".join(update_expr_parts))
        if remove_expr_parts:
            update_expression_parts.append("REMOVE " + ", ".join(remove_expr_parts))
        
        update_expression = " ".join(update_expression_parts)

        # Update the item in DynamoDB
        try:
            logger.info(
                f"Updating DynamoDB item {book_id} with fields: {list(expr_attr_names.values())}"
            )
            response = books_table.update_item(
                Key={"id": book_id},
                UpdateExpression=update_expression,
                ExpressionAttributeValues=expr_attr_values,
                ExpressionAttributeNames=expr_attr_names,
                ReturnValues="ALL_NEW",
                ConditionExpression="attribute_exists(id)",
            )

            updated_item = response["Attributes"]
            logger.info(f"Successfully updated book: {book_id}")

            return _response(
                200,
                {
                    "id": updated_item.get("id"),
                    "name": updated_item.get("name"),
                    "created": updated_item.get("created"),
                    "read": updated_item.get("read", False),
                    "author": updated_item.get("author"),
                    "series_name": updated_item.get("series_name"),
                    "series_order": int(updated_item["series_order"]) if updated_item.get("series_order") else None,
                    "s3_url": updated_item.get("s3_url"),
                },
            )

        except ClientError as e:
            if e.response["Error"]["Code"] == "ConditionalCheckFailedException":
                logger.warning(f"Book not found: {book_id}")
                return _response(
                    404, {"error": "Not Found", "message": f'Book "{book_id}" not found'}
                )
            raise

    except Exception as e:
        logger.error(f"Error updating book: {str(e)}", exc_info=True)
        return _response(500, {"error": "Internal Server Error", "message": str(e)})


def s3_trigger_handler(event, context):
    """
    Lambda handler triggered by S3 when a new .zip file is uploaded to books/
    Creates a DynamoDB record for the new book
    """
    try:
        for record in event.get("Records", []):
            # Get S3 event details
            s3_info = record.get("s3", {})
            bucket_name = s3_info.get("bucket", {}).get("name")
            # S3 keys come URL-encoded, decode them properly
            # Note: unquote handles %20 but + is used for spaces in form encoding
            s3_key = unquote(s3_info.get("object", {}).get("key", ""))
            # Also replace + with space (from form-encoded uploads)
            s3_key = s3_key.replace("+", " ")
            s3_size = s3_info.get("object", {}).get("size", 0)

            if not bucket_name or not s3_key:
                logger.warning(f"Invalid S3 event record: {record}")
                continue

            # Extract filename from S3 key
            filename = s3_key.split("/")[-1]

            # Create a friendly name (remove .zip extension)
            friendly_name = filename.replace(".zip", "")

            # Generate unique ID (use filename without extension)
            # For ID, keep original filename structure but URL-decode it
            book_id = filename.replace(".zip", "")

            # Build S3 URL
            s3_url = f"s3://{bucket_name}/{s3_key}"

            # Get timestamp (use timezone-aware UTC)
            timestamp = datetime.now(UTC).isoformat().replace("+00:00", "Z")

            # Create DynamoDB item
            item = {
                "id": book_id,
                "s3_url": s3_url,
                "name": friendly_name,
                "created": timestamp,
                "read": False,
                "size": s3_size,
            }

            # Try to extract author from filename if it contains a dash
            # Format: "Author Name - Book Title.zip"
            if " - " in friendly_name:
                parts = friendly_name.split(" - ", 1)
                item["author"] = parts[0].strip()
                item["name"] = parts[1].strip()

            # Put item in DynamoDB
            try:
                books_table.put_item(Item=item)
                logger.info(f"Successfully added book to DynamoDB: {book_id}")
            except ClientError as e:
                logger.error(f"Error adding book to DynamoDB: {str(e)}")
                # Continue processing other records even if one fails
                continue

        return {
            "statusCode": 200,
            "body": json.dumps({"message": "Successfully processed S3 events"}),
        }

    except Exception as e:
        logger.error(f"Error processing S3 trigger: {str(e)}", exc_info=True)
        # For S3 triggers, we should return success even on error to prevent retries
        # Errors are logged to CloudWatch
        return {
            "statusCode": 200,
            "body": json.dumps({"message": "Completed with errors", "error": str(e)}),
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
        authorizer = event.get("requestContext", {}).get("authorizer", {})
        claims = authorizer.get("claims", {})
        user_email = claims.get("email", "unknown")

        logger.info(f"Upload request from user: {user_email}")

        # Parse request body
        body, error = _parse_json_body(event)
        if error:
            return error

        # Validate filename is present
        filename = body.get("filename")
        if not filename:
            logger.warning("Missing filename in request")
            return _response(400, {"error": "Bad Request", "message": "filename is required"})

        # Validate file extension
        if not filename.lower().endswith(".zip"):
            logger.warning(f"Invalid file extension: {filename}")
            return _response(
                400, {"error": "Bad Request", "message": "Only .zip files are allowed"}
            )

        # Sanitize filename (remove path traversal attempts)
        filename = os.path.basename(filename)

        # Validate optional author field
        error = _validate_string_field(body, "author", max_length=500)
        if error:
            return error

        author = body.get("author", "").strip()

        # Get optional file size for validation
        file_size = body.get("fileSize", 0)
        max_size = 5 * 1024 * 1024 * 1024  # 5GB limit
        if file_size > max_size:
            return _response(
                400, {"error": "Bad Request", "message": "File size exceeds maximum limit of 5GB"}
            )

        # Generate S3 key
        s3_key = f"{BOOKS_PREFIX}{filename}"

        logger.info(f"Generating presigned PUT URL for: {s3_key} ({file_size} bytes)")

        # Generate presigned PUT URL (valid for 60 minutes for large files)
        # We don't include Metadata in params because it would require the client
        # to send exact matching headers (signature validation issue causing 403)
        presigned_url = s3_client.generate_presigned_url(
            "put_object",
            Params={"Bucket": BUCKET_NAME, "Key": s3_key, "ContentType": "application/zip"},
            ExpiresIn=3600,  # 60 minutes for large file uploads
        )

        logger.info(f"Successfully generated presigned PUT URL for {filename}")

        # Return the URL and metadata
        response_data = {
            "uploadUrl": presigned_url,
            "method": "PUT",
            "filename": filename,
            "s3Key": s3_key,
            "expiresIn": 3600,
        }

        if author:
            response_data["author"] = author
            logger.info(f"Author will be set via metadata endpoint: {author}")

        return _response(200, response_data)

    except Exception as e:
        logger.error(f"Error generating upload URL: {str(e)}", exc_info=True)
        return _response(500, {"error": "Internal Server Error", "message": str(e)})


def set_upload_metadata_handler(event, context):
    """
    Lambda handler to set metadata (author, series_name, series_order) after S3 upload completes
    This is called by the frontend after the S3 upload finishes successfully

    Expects JSON body with:
    - bookId: The ID of the book (filename without .zip)
    - author: (optional) Author name to set
    - series_name: (optional) Series name to set
    - series_order: (optional) Series order to set (1-100)

    Returns success/failure status
    """
    logger.info("set_upload_metadata_handler invoked")

    try:
        # Verify user is authenticated
        authorizer = event.get("requestContext", {}).get("authorizer", {})
        claims = authorizer.get("claims", {})
        user_email = claims.get("email", "unknown")

        logger.info(f"Set metadata request from user: {user_email}")

        # Parse request body
        body, error = _parse_json_body(event)
        if error:
            return error

        # Validate bookId
        book_id = body.get("bookId")
        if not book_id:
            logger.warning("Missing bookId in request")
            return _response(400, {"error": "Bad Request", "message": "bookId is required"})

        # Validate optional fields
        error = _validate_string_field(body, "author", max_length=500)
        if error:
            return error

        error = _validate_string_field(body, "series_name", max_length=500)
        if error:
            return error

        # Validate series_order if provided
        if "series_order" in body:
            series_order = body["series_order"]
            if series_order is not None:
                try:
                    series_order_int = int(series_order)
                    if series_order_int < 1 or series_order_int > 100:
                        return _response(
                            400,
                            {"error": "Bad Request", "message": "series_order must be between 1 and 100"}
                        )
                except (ValueError, TypeError):
                    return _response(
                        400,
                        {"error": "Bad Request", "message": "series_order must be an integer"}
                    )

        author = body.get("author", "").strip()
        series_name = body.get("series_name", "").strip()
        series_order = body.get("series_order")

        # Build update expression dynamically
        update_expr_parts = []
        expr_values = {}

        if author:
            update_expr_parts.append("author = :author")
            expr_values[":author"] = author

        if series_name:
            update_expr_parts.append("series_name = :series_name")
            expr_values[":series_name"] = series_name

        if series_order is not None:
            update_expr_parts.append("series_order = :series_order")
            expr_values[":series_order"] = int(series_order)

        if not update_expr_parts:
            # Nothing to update
            return _response(200, {"message": "No metadata to update"})

        logger.info(f"Setting metadata for book: {book_id}")

        # Update DynamoDB item
        update_expression = "SET " + ", ".join(update_expr_parts)

        try:
            books_table.update_item(
                Key={"id": book_id},
                UpdateExpression=update_expression,
                ExpressionAttributeValues=expr_values,
                ConditionExpression="attribute_exists(id)",
            )

            logger.info(f"Successfully updated metadata for book: {book_id}")

            response_data = {"message": "Metadata updated successfully", "bookId": book_id}
            if author:
                response_data["author"] = author
            if series_name:
                response_data["series_name"] = series_name
            if series_order is not None:
                response_data["series_order"] = int(series_order)

            return _response(200, response_data)

        except ClientError as e:
            if e.response["Error"]["Code"] == "ConditionalCheckFailedException":
                logger.warning(f"Book not found: {book_id}")
                return _response(
                    404, {"error": "Not Found", "message": f"Book with id {book_id} not found"}
                )
            raise

    except Exception as e:
        logger.error(f"Error setting upload metadata: {str(e)}", exc_info=True)
        return _response(500, {"error": "Internal Server Error", "message": str(e)})


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
        authorizer = event.get("requestContext", {}).get("authorizer", {})
        claims = authorizer.get("claims", {})
        user_email = claims.get("email", "unknown")

        logger.info(f"Delete request from user: {user_email}")

        # Get the book ID from path parameters
        book_id, error = _get_path_param(event, "id")
        if error:
            return error

        logger.info(f"Deleting book: {book_id}")

        # First, get the book record to find the S3 URL
        try:
            response = books_table.get_item(Key={"id": book_id})
            if "Item" not in response:
                logger.warning(f"Book not found: {book_id}")
                return _response(
                    404, {"error": "Not Found", "message": f'Book with id "{book_id}" not found'}
                )

            book_item = response["Item"]
            s3_url = book_item.get("s3_url")

        except ClientError as e:
            logger.error(f"DynamoDB error: {str(e)}", exc_info=True)
            return _response(500, {"error": "Database Error", "message": str(e)})

        # Delete from S3 if S3 URL exists
        if s3_url:
            try:
                # Parse S3 URL to get bucket and key
                # Format: s3://bucket-name/path/to/object
                parsed_url = urlparse(s3_url)
                bucket = parsed_url.netloc
                s3_key = parsed_url.path.lstrip("/")

                logger.info(f"Deleting S3 object: s3://{bucket}/{s3_key}")

                s3_client.delete_object(Bucket=bucket, Key=s3_key)

                logger.info(f"Successfully deleted S3 object: {s3_key}")

            except ClientError as e:
                # Log error but continue with DynamoDB deletion
                logger.error(f"S3 deletion error: {str(e)}", exc_info=True)
                # Don't fail the entire operation if S3 delete fails
        else:
            logger.warning(f"No S3 URL found for book: {book_id}")

        # Delete from DynamoDB
        try:
            books_table.delete_item(Key={"id": book_id}, ConditionExpression="attribute_exists(id)")

            logger.info(f"Successfully deleted DynamoDB record: {book_id}")

            return _response(200, {"message": "Book deleted successfully", "bookId": book_id})

        except ClientError as e:
            if e.response["Error"]["Code"] == "ConditionalCheckFailedException":
                logger.warning(f"Book not found during deletion: {book_id}")
                return _response(
                    404, {"error": "Not Found", "message": f'Book with id "{book_id}" not found'}
                )
            raise

    except Exception as e:
        logger.error(f"Error deleting book: {str(e)}", exc_info=True)
        return _response(500, {"error": "Internal Server Error", "message": str(e)})
