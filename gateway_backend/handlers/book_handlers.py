"""
Lambda handlers for book read operations (list, get, update)

These handlers provide CRUD operations for books that authenticated users can access.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any
from urllib.parse import urlparse

from botocore.exceptions import ClientError

# Support both Lambda deployment and local development
try:
    # Lambda deployment
    import config
    from utils.auth import get_user_id, is_admin
    from utils.cover import update_cover_on_author_change
    from utils.dynamodb import build_update_expression, build_update_params
    from utils.response import api_response, error_response, serialize_book_response
    from utils.validation import (
        get_path_param,
        parse_json_body,
        validate_boolean_field,
        validate_series_order,
        validate_string_field,
    )
except ImportError:
    # Local development
    import gateway_backend.config as config
    from gateway_backend.utils.auth import get_user_id, is_admin
    from gateway_backend.utils.cover import update_cover_on_author_change
    from gateway_backend.utils.dynamodb import build_update_expression, build_update_params
    from gateway_backend.utils.response import api_response, error_response, serialize_book_response
    from gateway_backend.utils.validation import (
        get_path_param,
        parse_json_body,
        validate_boolean_field,
        validate_series_order,
        validate_string_field,
    )

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def _get_user_read_statuses(user_id: str) -> dict[str, bool]:
    """
    Get all read statuses for a user from UserBooks table.

    Args:
        user_id: Cognito user ID

    Returns:
        dict: Mapping of bookId -> read status
    """
    user_read_status = {}
    try:
        user_response = config.user_books_table.query(
            KeyConditionExpression="userId = :uid",
            ExpressionAttributeValues={":uid": user_id},
        )
        for item in user_response.get("Items", []):
            user_read_status[item["bookId"]] = item.get("read", False)
    except Exception as e:
        logger.warning(f"Error fetching user read status: {str(e)}")
        # Continue without user read status
    return user_read_status


def _get_user_read_status(user_id: str, book_id: str) -> bool:
    """
    Get read status for a specific book from UserBooks table.

    Args:
        user_id: Cognito user ID
        book_id: Book identifier

    Returns:
        bool: Read status (defaults to False if not found or error)
    """
    try:
        user_book_response = config.user_books_table.get_item(
            Key={"userId": user_id, "bookId": book_id}
        )
        if "Item" in user_book_response:
            return user_book_response["Item"].get("read", False)
    except ClientError as e:
        # Log error but continue - read status will default to False
        logger.error(f"Error fetching UserBooks record: {str(e)}", exc_info=True)
    return False


def _update_user_book_status(user_id: str, book_id: str, read: bool) -> None:
    """
    Update user-specific read status in UserBooks table.

    Args:
        user_id: Cognito user ID
        book_id: Book identifier
        read: Read status to set
    """
    try:
        config.user_books_table.put_item(
            Item={
                "userId": user_id,
                "bookId": book_id,
                "read": read,
                "updated": datetime.now(UTC).isoformat(),
            }
        )
        logger.info(f"Updated user read status for book {book_id}")
    except Exception as e:
        logger.error(f"Error updating user read status: {str(e)}")
        # Continue to update book metadata even if user status fails


def _update_book_metadata(book_id: str, metadata_fields: dict[str, Any]) -> dict:
    """
    Update book metadata in Books table.

    Args:
        book_id: Book identifier
        metadata_fields: Dictionary of fields to update

    Returns:
        dict: Updated book item from DynamoDB

    Raises:
        ClientError: If book not found or DynamoDB error
    """
    logger.info(f"Updating book metadata for {book_id} with fields: {list(metadata_fields.keys())}")

    # Build update parameters using utility function
    update_params = build_update_params(
        key={"id": book_id},
        fields=metadata_fields,
        allow_remove=True,
        condition_expression="attribute_exists(id)",
        return_values="ALL_NEW"
    )

    response = config.books_table.update_item(**update_params)

    logger.info(f"Successfully updated book metadata: {book_id}")
    return response["Attributes"]


def list_handler(event, context):
    """
    Lambda handler to list all books from DynamoDB with user-specific read status.
    Returns list of books with metadata from Books table and read status from UserBooks table.
    """
    logger.info("list_handler invoked")

    try:
        # Get user ID
        user_id = get_user_id(event)
        if not user_id:
            return error_response(401, "Unauthorized", "User not authenticated")

        # Check if user is admin
        user_is_admin = is_admin(event)

        # Scan the Books table
        response = config.books_table.scan()
        items = response.get("Items", [])

        # Handle pagination if needed
        while "LastEvaluatedKey" in response:
            response = config.books_table.scan(ExclusiveStartKey=response["LastEvaluatedKey"])
            items.extend(response.get("Items", []))

        logger.info(f"Retrieved {len(items)} books from DynamoDB")

        # Get user-specific read status for all books
        user_read_status = _get_user_read_statuses(user_id)

        # Convert DynamoDB items to API response format
        books = []
        for item in items:
            read_status = user_read_status.get(item.get("id"), False)
            book = serialize_book_response(item, read_status)
            books.append(book)

        # Sort by created date (most recent first)
        books.sort(key=lambda x: x.get("created", ""), reverse=True)

        # Add user info to response
        response_data = {"books": books, "isAdmin": user_is_admin}

        return api_response(200, response_data)

    except Exception as e:
        logger.error(f"Error listing books: {str(e)}", exc_info=True)
        return error_response(500, "Failed to list books", str(e))


def get_book_handler(event, context):
    """
    Lambda handler to generate a presigned URL for downloading a specific book.
    Looks up metadata from DynamoDB and generates presigned URL from S3.
    Expects book ID in path parameter 'id'.
    Returns presigned URL valid for 1 hour along with book metadata.
    """
    logger.info("get_book_handler invoked")

    try:
        # Get the book ID from path parameters
        book_id, error = get_path_param(event, "id")
        if error:
            return error

        # Get user ID for user-specific read status
        user_id = get_user_id(event)
        if not user_id:
            return error_response(401, "Unauthorized", "User not authenticated")

        logger.info(f"Fetching book: {book_id} for user: {user_id}")

        # Look up book in DynamoDB
        try:
            response = config.books_table.get_item(Key={"id": book_id})
            if "Item" not in response:
                logger.warning(f"Book not found: {book_id}")
                return error_response(404, "Not Found", f'Book "{book_id}" not found')

            book_item = response["Item"]

        except ClientError as e:
            logger.error(f"DynamoDB error: {str(e)}", exc_info=True)
            return error_response(500, "Database Error", str(e))

        # Get user-specific read status from UserBooks table
        read_status = _get_user_read_status(user_id, book_id)

        # Get S3 URL from DynamoDB record
        s3_url = book_item.get("s3_url")
        if not s3_url:
            logger.error(f"Book {book_id} missing S3 URL in DynamoDB")
            return error_response(500, "Invalid Data", "Book record missing S3 URL")

        # Extract bucket and key from S3 URL
        # Format: s3://bucket-name/path/to/object
        parsed_url = urlparse(str(s3_url))  # type: ignore[arg-type]
        bucket = parsed_url.netloc
        s3_key = parsed_url.path.lstrip("/")

        logger.info(f"Generating presigned download URL for: {book_id}")

        # Generate presigned URL (valid for 1 hour)
        presigned_url = config.s3_client.generate_presigned_url(
            "get_object",
            Params={"Bucket": bucket, "Key": s3_key},
            ExpiresIn=config.URL_EXPIRY_SECONDS,
        )

        # Return book metadata with presigned URL and user-specific read status
        book_response = serialize_book_response(book_item, read_status)
        book_response["downloadUrl"] = presigned_url
        book_response["expiresIn"] = config.URL_EXPIRY_SECONDS

        return api_response(200, book_response)

    except Exception as e:
        logger.error(f"Error generating presigned URL: {str(e)}", exc_info=True)
        return error_response(500, "Internal Server Error", str(e))


def update_book_handler(event, context):
    """
    Lambda handler to update book metadata and user-specific read status.
    Expects book ID in path parameter 'id'.
    Accepts JSON body with fields to update:
    - read: user-specific read status (stored in UserBooks table)
    - author, name, series_name, series_order: book metadata (stored in Books table)
    """
    logger.info("update_book_handler invoked")

    try:
        # Get user ID
        user_id = get_user_id(event)
        if not user_id:
            return error_response(401, "Unauthorized", "User not authenticated")

        # Get the book ID from path parameters
        book_id, error = get_path_param(event, "id")
        if error:
            return error

        logger.info(f"Updating book: {book_id} for user: {user_id}")

        # Parse request body
        body, error = parse_json_body(event)
        if error:
            return error

        # Validate fields
        error = validate_boolean_field(body, "read")
        if error:
            return error

        error = validate_string_field(body, "author", max_length=500)
        if error:
            return error

        error = validate_string_field(body, "name", max_length=500, required=False)
        if error:
            return error

        error = validate_string_field(body, "series_name", max_length=500)
        if error:
            return error

        # Additional validation for name (cannot be empty if provided)
        if "name" in body and not body["name"].strip():
            return error_response(400, "Bad Request", 'Field "name" cannot be empty')

        # Validate series_order if provided
        error = validate_series_order(body)
        if error:
            return error

        # Separate user-specific fields from book metadata fields
        user_specific_fields = {}
        book_metadata_fields = {}

        if "read" in body:
            user_specific_fields["read"] = bool(body["read"])
        if "author" in body:
            book_metadata_fields["author"] = str(body["author"])
        if "name" in body:
            book_metadata_fields["name"] = str(body["name"])
        if "series_name" in body:
            book_metadata_fields["series_name"] = str(body["series_name"])
        if "series_order" in body:
            series_order = body["series_order"]
            if series_order is None or series_order == "":
                book_metadata_fields["series_order"] = None  # Will be removed
            else:
                book_metadata_fields["series_order"] = int(series_order)

        if not user_specific_fields and not book_metadata_fields:
            return error_response(400, "Bad Request", "No valid fields to update")

        # Update user-specific read status if provided
        if user_specific_fields:
            _update_user_book_status(
                user_id, book_id, user_specific_fields.get("read", False)
            )

        # Update book metadata if provided
        updated_book = None
        if book_metadata_fields:
            # Check if author is changing - if so, fetch new cover
            if "author" in book_metadata_fields:
                try:
                    # Get current book to check existing author
                    get_response = config.books_table.get_item(Key={"id": book_id})
                    if "Item" in get_response:
                        current_book = get_response["Item"]
                        current_author = current_book.get("author", "")
                        title = current_book.get("name", book_id)
                        new_author = book_metadata_fields["author"]

                        # Update cover if author is changing
                        update_cover_on_author_change(current_author, new_author, title, book_metadata_fields)
                except ClientError as e:
                    logger.error(f"Error getting current book: {str(e)}")
                    # Continue with update anyway

            try:
                updated_book = _update_book_metadata(book_id, book_metadata_fields)
            except ClientError as e:
                if e.response["Error"]["Code"] == "ConditionalCheckFailedException":  # type: ignore[typeddict-item]
                    logger.warning(f"Book not found: {book_id}")
                    return error_response(404, "Not Found", f'Book "{book_id}" not found')
                raise
        else:
            # If only updating read status, fetch book metadata
            try:
                response = config.books_table.get_item(Key={"id": book_id})
                if "Item" not in response:
                    return error_response(404, "Not Found", f'Book "{book_id}" not found')
                updated_book = response["Item"]
            except ClientError as e:
                logger.error(f"Error fetching book: {str(e)}")
                raise

        # Return combined response
        read_status = (
            user_specific_fields.get("read", False) if user_specific_fields else False
        )
        book_response = serialize_book_response(updated_book, read_status)

        return api_response(200, book_response)

    except Exception as e:
        logger.error(f"Error updating book: {str(e)}", exc_info=True)
        return error_response(500, "Internal Server Error", str(e))
