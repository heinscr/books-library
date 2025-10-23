"""
Response building utilities for Books API

Provides functions to create standardized API Gateway responses.
"""

from __future__ import annotations

import json
from decimal import Decimal
from typing import Any


def api_response(status_code: int, body: Any) -> dict:
    """
    Helper to format API Gateway response with CORS headers.

    Args:
        status_code: HTTP status code
        body: Response body (will be JSON serialized)

    Returns:
        dict: API Gateway response with headers
    """
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


def error_response(status_code: int, error: str, message: str) -> dict:
    """
    Helper to create error response.

    Args:
        status_code: HTTP status code
        error: Error type/category
        message: Error message

    Returns:
        dict: API Gateway error response
    """
    return api_response(status_code, {"error": error, "message": message})


def convert_decimal(value: Any) -> Any:
    """
    Convert Decimal types (from DynamoDB) to int or float for JSON serialization.

    Args:
        value: Value that might be a Decimal

    Returns:
        Converted value (int if whole number, otherwise original value)
    """
    if isinstance(value, Decimal):
        return int(value) if value % 1 == 0 else float(value)
    return value


def serialize_book_response(book_item: dict, read_status: bool = False) -> dict:
    """
    Convert DynamoDB book item to API response format.

    Handles Decimal conversion and standardizes field format.

    Args:
        book_item: DynamoDB item (Books table)
        read_status: User-specific read status (from UserBooks table)

    Returns:
        dict: Book object for API response
    """
    book: dict[str, Any] = {
        "id": book_item.get("id"),
        "name": book_item.get("name"),
        "created": book_item.get("created"),
        "read": read_status,
        "s3_url": book_item.get("s3_url"),
    }

    # Add optional fields if present
    if "author" in book_item:
        book["author"] = book_item["author"]

    if "size" in book_item:
        book["size"] = convert_decimal(book_item["size"])

    if "series_name" in book_item:
        book["series_name"] = book_item["series_name"]

    if "series_order" in book_item:
        book["series_order"] = convert_decimal(book_item["series_order"])

    return book
