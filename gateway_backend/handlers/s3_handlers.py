"""
Lambda handlers for S3 event processing (trigger, metadata setting)

These handlers process S3 upload events and set book metadata after upload.
"""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from urllib.parse import unquote

from botocore.exceptions import ClientError

# Support both Lambda deployment and local development
try:
    # Lambda deployment
    import config
    from utils.auth import is_admin
    from utils.cover import fetch_cover_url as _fetch_cover_url_util, update_cover_on_author_change
    from utils.dynamodb import build_update_params
    from utils.response import api_response, error_response
    from utils.validation import parse_json_body, validate_series_order, validate_string_field
except ImportError:
    # Local development
    import gateway_backend.config as config
    from gateway_backend.utils.auth import is_admin
    from gateway_backend.utils.cover import fetch_cover_url as _fetch_cover_url_util, update_cover_on_author_change
    from gateway_backend.utils.dynamodb import build_update_params
    from gateway_backend.utils.response import api_response, error_response
    from gateway_backend.utils.validation import parse_json_body, validate_series_order, validate_string_field

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def _parse_s3_event(record: dict) -> tuple[str | None, str | None, int]:
    """
    Extract bucket, key, and size from S3 event record.

    Args:
        record: S3 event record

    Returns:
        tuple: (bucket_name, s3_key, size)
    """
    s3_info = record.get("s3", {})
    bucket_name = s3_info.get("bucket", {}).get("name")

    # S3 keys come URL-encoded, decode them properly
    # Note: unquote handles %20 but + is used for spaces in form encoding
    s3_key = unquote(s3_info.get("object", {}).get("key", ""))
    # Also replace + with space (from form-encoded uploads)
    s3_key = s3_key.replace("+", " ")

    s3_size = s3_info.get("object", {}).get("size", 0)

    return bucket_name, s3_key, s3_size


def _extract_book_metadata(filename: str) -> dict[str, str]:
    """
    Extract metadata from filename.

    Format: "Author Name - Book Title.zip" -> {"author": "Author Name", "name": "Book Title"}
    Otherwise: "Book Title.zip" -> {"name": "Book Title"}

    Args:
        filename: Filename (without extension)

    Returns:
        dict: Metadata extracted from filename
    """
    metadata = {}

    # Try to extract author from filename if it contains a dash
    # Format: "Author Name - Book Title.zip"
    if " - " in filename:
        parts = filename.split(" - ", 1)
        metadata["author"] = parts[0].strip()
        metadata["name"] = parts[1].strip()
    else:
        metadata["name"] = filename

    return metadata


# Alias the utility function for backward compatibility
_fetch_cover_url = _fetch_cover_url_util


def s3_trigger_handler(event, context):
    """
    Lambda handler triggered by S3 when a new file is uploaded to books/.
    Creates a DynamoDB record for the new book.
    Reads S3 object tags for author, series_name, and series_order metadata.
    """
    try:
        for record in event.get("Records", []):
            # Get S3 event details
            bucket_name, s3_key, s3_size = _parse_s3_event(record)

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

            # Extract metadata from filename (fallback if tags not present)
            metadata = _extract_book_metadata(friendly_name)
            item.update(metadata)

            # Read S3 object tags for author, series_name, and series_order
            try:
                tagging_response = config.s3_client.get_object_tagging(
                    Bucket=bucket_name,
                    Key=s3_key
                )
                tags = tagging_response.get("TagSet", [])

                # Extract metadata from tags (override filename-based metadata)
                for tag in tags:
                    tag_key = tag.get("Key")
                    tag_value = tag.get("Value")

                    if tag_key == "author" and tag_value:
                        item["author"] = tag_value
                        logger.info(f"Found author tag: {tag_value}")
                    elif tag_key == "series_name" and tag_value:
                        item["series_name"] = tag_value
                        logger.info(f"Found series_name tag: {tag_value}")
                    elif tag_key == "series_order" and tag_value:
                        try:
                            item["series_order"] = int(tag_value)
                            logger.info(f"Found series_order tag: {tag_value}")
                        except (ValueError, TypeError):
                            logger.warning(f"Invalid series_order tag value: {tag_value}")

            except ClientError as e:
                logger.warning(f"Error reading S3 object tags: {str(e)}")
                # Continue without tags - we already have filename-based metadata

            # Fetch cover image URL from Google Books API
            title = item.get("name", "")
            author = item.get("author")
            try:
                cover_url = _fetch_cover_url(title, author)
                if cover_url:
                    item["coverImageUrl"] = cover_url
                    logger.info(f"Found cover for '{title}': {cover_url[:60]}...")
                else:
                    logger.info(f"No cover found for '{title}'")
            except Exception as e:
                logger.warning(f"Error fetching cover for '{title}': {str(e)}")
                # Continue without cover URL

            # Put item in DynamoDB
            try:
                config.books_table.put_item(Item=item)
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


def set_upload_metadata_handler(event, context):
    """
    Lambda handler to set metadata (author, series_name, series_order) after S3 upload completes.
    This is called by the frontend after the S3 upload finishes successfully.
    Requires admin permissions.

    Expects JSON body with:
    - bookId: The ID of the book (filename without .zip)
    - author: (optional) Author name to set
    - series_name: (optional) Series name to set
    - series_order: (optional) Series order to set (1-100)

    Returns success/failure status.
    """
    logger.info("set_upload_metadata_handler invoked")

    try:
        # Check if user is admin
        if not is_admin(event):
            logger.warning("Non-admin user attempted to set upload metadata")
            return error_response(
                403, "Forbidden", "Only administrators can set upload metadata"
            )

        # Verify user is authenticated
        authorizer = event.get("requestContext", {}).get("authorizer", {})
        claims = authorizer.get("claims", {})
        user_email = claims.get("email", "unknown")

        logger.info(f"Set metadata request from admin user: {user_email}")

        # Parse request body
        body, error = parse_json_body(event)
        if error:
            return error

        # Validate bookId
        book_id = body.get("bookId")
        if not book_id:
            logger.warning("Missing bookId in request")
            return error_response(400, "Bad Request", "bookId is required")

        # Validate optional fields
        error = validate_string_field(body, "author", max_length=500)
        if error:
            return error

        error = validate_string_field(body, "series_name", max_length=500)
        if error:
            return error

        error = validate_series_order(body)
        if error:
            return error

        author = body.get("author", "").strip()
        series_name = body.get("series_name", "").strip()
        series_order = body.get("series_order")

        # Build metadata fields dictionary
        metadata_fields = {}
        if author:
            metadata_fields["author"] = author
        if series_name:
            metadata_fields["series_name"] = series_name
        if series_order is not None:
            metadata_fields["series_order"] = int(series_order)

        if not metadata_fields:
            # Nothing to update
            return api_response(200, {"message": "No metadata to update"})

        logger.info(f"Setting metadata for book: {book_id}")

        # First, get the current book record to check if author is changing
        try:
            get_response = config.books_table.get_item(Key={"id": book_id})
            if "Item" not in get_response:
                logger.warning(f"Book not found: {book_id}")
                return error_response(
                    404, "Not Found", f"Book with id {book_id} not found"
                )

            current_book = get_response["Item"]
            current_author = current_book.get("author", "")
            title = current_book.get("name", book_id)

            # Update cover if author is changing
            if author:
                update_cover_on_author_change(current_author, author, title, metadata_fields)

        except ClientError as e:
            logger.error(f"Error getting current book: {str(e)}", exc_info=True)
            return error_response(500, "Database Error", str(e))

        # Update DynamoDB item
        update_params = build_update_params(
            key={"id": book_id},
            fields=metadata_fields,
            allow_remove=True,
            condition_expression="attribute_exists(id)",
            return_values="NONE"
        )

        try:
            config.books_table.update_item(**update_params)

            logger.info(f"Successfully updated metadata for book: {book_id}")

            response_data = {
                "message": "Metadata updated successfully",
                "bookId": book_id,
            }
            response_data.update(metadata_fields)

            return api_response(200, response_data)

        except ClientError as e:
            if e.response["Error"]["Code"] == "ConditionalCheckFailedException":  # type: ignore[typeddict-item]
                logger.warning(f"Book not found: {book_id}")
                return error_response(
                    404, "Not Found", f"Book with id {book_id} not found"
                )
            raise

    except Exception as e:
        logger.error(f"Error setting upload metadata: {str(e)}", exc_info=True)
        return error_response(500, "Internal Server Error", str(e))
