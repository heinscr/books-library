"""
Lambda handlers for admin operations (upload, delete)

These handlers require admin role and provide book management operations.
"""

from __future__ import annotations

import logging
import os
from urllib.parse import urlparse

from botocore.exceptions import ClientError

# Support both Lambda deployment and local development
try:
    # Lambda deployment
    import config
    from utils.auth import get_user_id, is_admin
    from utils.response import api_response, error_response
    from utils.validation import get_path_param, parse_json_body, validate_string_field
except ImportError:
    # Local development
    import gateway_backend.config as config
    from gateway_backend.utils.auth import get_user_id, is_admin
    from gateway_backend.utils.response import api_response, error_response
    from gateway_backend.utils.validation import get_path_param, parse_json_body, validate_string_field

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def _delete_s3_object(s3_url: str) -> None:
    """
    Delete an object from S3.

    Args:
        s3_url: S3 URL (format: s3://bucket/key)

    Raises:
        ClientError: If S3 deletion fails (logged but not fatal)
    """
    try:
        # Parse S3 URL to get bucket and key
        # Format: s3://bucket-name/path/to/object
        parsed_url = urlparse(str(s3_url))  # type: ignore[arg-type]
        bucket = parsed_url.netloc
        s3_key = parsed_url.path.lstrip("/")

        logger.info(f"Deleting S3 object: s3://{bucket}/{s3_key}")

        config.s3_client.delete_object(Bucket=bucket, Key=s3_key)

        logger.info(f"Successfully deleted S3 object: {s3_key}")

    except ClientError as e:
        # Log error but don't fail the entire operation
        logger.error(f"S3 deletion error: {str(e)}", exc_info=True)
        raise


def _cleanup_user_books(book_id: str) -> int:
    """
    Delete all UserBooks entries for a specific book.

    Args:
        book_id: Book identifier

    Returns:
        int: Number of user book entries deleted

    Raises:
        ClientError: If UserBooks cleanup fails (logged but not fatal)
    """
    try:
        # Query all users who have this book in their UserBooks table
        # We need to scan since we're querying by bookId (which is the sort key)
        scan_response = config.user_books_table.scan(
            FilterExpression="bookId = :bid", ExpressionAttributeValues={":bid": book_id}
        )

        user_book_items = scan_response.get("Items", [])

        # Delete each user's entry for this book
        for item in user_book_items:
            config.user_books_table.delete_item(
                Key={"userId": item["userId"], "bookId": item["bookId"]}
            )

        if user_book_items:
            logger.info(
                f"Deleted {len(user_book_items)} UserBooks entries for book: {book_id}"
            )

        return len(user_book_items)

    except ClientError as e:
        # Log error but don't fail the entire operation
        logger.error(f"Error deleting UserBooks entries: {str(e)}", exc_info=True)
        raise


def _delete_book_record(book_id: str) -> None:
    """
    Delete book record from Books table.

    Args:
        book_id: Book identifier

    Raises:
        ClientError: If book not found or DynamoDB error
    """
    config.books_table.delete_item(
        Key={"id": book_id}, ConditionExpression="attribute_exists(id)"
    )
    logger.info(f"Successfully deleted DynamoDB record: {book_id}")


def upload_handler(event, context):
    """
    Lambda handler to generate presigned S3 upload URL for admin users only.
    Expects JSON body with:
    - filename: The name of the file to upload (must end with .zip)
    - author: (optional) Author name to associate with the book

    Returns presigned PUT URL for uploading directly to S3.
    """
    logger.info("upload_handler invoked")

    try:
        # Check if user is admin
        if not is_admin(event):
            logger.warning("Non-admin user attempted to upload")
            return error_response(
                403, "Forbidden", "Only administrators can upload books"
            )

        # Verify user is authenticated (Cognito authorizer adds this)
        authorizer = event.get("requestContext", {}).get("authorizer", {})
        claims = authorizer.get("claims", {})
        user_email = claims.get("email", "unknown")

        logger.info(f"Upload request from admin user: {user_email}")

        # Parse request body
        body, error = parse_json_body(event)
        if error:
            return error

        # Validate filename is present
        filename = body.get("filename")
        if not filename:
            logger.warning("Missing filename in request")
            return error_response(400, "Bad Request", "filename is required")

        # Validate file extension
        if not filename.lower().endswith(".zip"):
            logger.warning(f"Invalid file extension: {filename}")
            return error_response(400, "Bad Request", "Only .zip files are allowed")

        # Sanitize filename (remove path traversal attempts)
        filename = os.path.basename(filename)

        # Validate optional author field
        error = validate_string_field(body, "author", max_length=500)
        if error:
            return error

        author = body.get("author", "").strip()

        # Get optional file size for validation
        file_size = body.get("fileSize", 0)
        if file_size > config.MAX_FILE_SIZE_BYTES:
            return error_response(
                400, "Bad Request", "File size exceeds maximum limit of 5GB"
            )

        # Generate S3 key
        s3_key = f"{config.BOOKS_PREFIX}{filename}"

        logger.info(f"Generating presigned PUT URL for: {s3_key} ({file_size} bytes)")

        # Generate presigned PUT URL (valid for 60 minutes for large files)
        # We don't include Metadata in params because it would require the client
        # to send exact matching headers (signature validation issue causing 403)
        presigned_url = config.s3_client.generate_presigned_url(
            "put_object",
            Params={
                "Bucket": config.BUCKET_NAME,
                "Key": s3_key,
                "ContentType": "application/zip",
            },
            ExpiresIn=config.URL_EXPIRY_SECONDS,  # 60 minutes for large file uploads
        )

        logger.info(f"Successfully generated presigned PUT URL for {filename}")

        # Return the URL and metadata
        response_data = {
            "uploadUrl": presigned_url,
            "method": "PUT",
            "filename": filename,
            "s3Key": s3_key,
            "expiresIn": config.URL_EXPIRY_SECONDS,
        }

        if author:
            response_data["author"] = author
            logger.info(f"Author will be set via metadata endpoint: {author}")

        return api_response(200, response_data)

    except Exception as e:
        logger.error(f"Error generating upload URL: {str(e)}", exc_info=True)
        return error_response(500, "Internal Server Error", str(e))


def delete_book_handler(event, context):
    """
    Lambda handler to delete a book from both DynamoDB and S3.
    Requires admin role to perform deletion.
    Expects book ID in path parameter 'id'.

    Deletes:
    1. DynamoDB record with book metadata (Books table)
    2. All user-specific records (UserBooks table)
    3. S3 object (the .zip file)

    Returns success/failure status.
    """
    logger.info("delete_book_handler invoked")

    try:
        # Verify user is authenticated
        user_id = get_user_id(event)
        if not user_id:
            return error_response(401, "Unauthorized", "User not authenticated")

        # Check if user is admin
        if not is_admin(event):
            logger.warning(f"Non-admin user {user_id} attempted to delete book")
            return error_response(
                403, "Forbidden", "Only administrators can delete books"
            )

        logger.info(f"Delete request from admin user: {user_id}")

        # Get the book ID from path parameters
        book_id, error = get_path_param(event, "id")
        if error:
            return error

        logger.info(f"Deleting book: {book_id}")

        # First, get the book record to find the S3 URL
        try:
            response = config.books_table.get_item(Key={"id": book_id})
            if "Item" not in response:
                logger.warning(f"Book not found: {book_id}")
                return error_response(
                    404, "Not Found", f'Book with id "{book_id}" not found'
                )

            book_item = response["Item"]
            s3_url = book_item.get("s3_url")

        except ClientError as e:
            logger.error(f"DynamoDB error: {str(e)}", exc_info=True)
            return error_response(500, "Database Error", str(e))

        # Delete from S3 if S3 URL exists
        if s3_url:
            try:
                _delete_s3_object(s3_url)
            except ClientError:
                # Error logged in helper, continue with DynamoDB deletion
                pass
        else:
            logger.warning(f"No S3 URL found for book: {book_id}")

        # Delete all UserBooks entries for this book
        try:
            _cleanup_user_books(book_id)
        except ClientError:
            # Error logged in helper, continue with Books table deletion
            pass

        # Delete from DynamoDB Books table
        try:
            _delete_book_record(book_id)

            return api_response(
                200, {"message": "Book deleted successfully", "bookId": book_id}
            )

        except ClientError as e:
            if e.response["Error"]["Code"] == "ConditionalCheckFailedException":  # type: ignore[typeddict-item]
                logger.warning(f"Book not found during deletion: {book_id}")
                return error_response(
                    404, "Not Found", f'Book with id "{book_id}" not found'
                )
            raise

    except Exception as e:
        logger.error(f"Error deleting book: {str(e)}", exc_info=True)
        return error_response(500, "Internal Server Error", str(e))
