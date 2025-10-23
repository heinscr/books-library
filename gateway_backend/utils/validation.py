"""
Request validation utilities for Books API

Provides functions to validate and extract data from API Gateway events.
"""

from __future__ import annotations

import json
import logging
from typing import Any
from urllib.parse import unquote

logger = logging.getLogger()


def get_path_param(event: dict, param: str) -> tuple[str | None, dict | None]:
    """
    Extract and URL-decode a path parameter from API Gateway event.

    Args:
        event: API Gateway event
        param: Parameter name to extract

    Returns:
        tuple: (decoded_value, error_response) - If successful, error_response is None
    """
    from .response import error_response

    path_params = event.get("pathParameters", {})
    if not path_params or param not in path_params:
        logger.warning(f"Missing {param} in path parameters")
        return None, error_response(
            400, "Bad Request", f"{param.capitalize()} is required in path"
        )
    return unquote(path_params[param]), None


def parse_json_body(event: dict) -> tuple[dict, dict | None]:
    """
    Parse JSON body from API Gateway event.

    Args:
        event: API Gateway event

    Returns:
        tuple: (parsed_body, error_response) - If successful, error_response is None
               If error, parsed_body is empty dict (caller should check error first)
    """
    from .response import error_response

    try:
        return json.loads(event.get("body", "{}")), None
    except json.JSONDecodeError:
        logger.warning("Invalid JSON in request body")
        return {}, error_response(400, "Bad Request", "Invalid JSON in request body")


def validate_string_field(
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
    from .response import error_response

    if field not in body:
        if required:
            return error_response(400, "Bad Request", f'Field "{field}" is required')
        return None

    value = body[field]
    if not isinstance(value, str):
        return error_response(400, "Bad Request", f'Field "{field}" must be a string')

    if len(value) > max_length:
        return error_response(
            400,
            "Bad Request",
            f'Field "{field}" exceeds maximum length of {max_length}',
        )

    if required and not value.strip():
        return error_response(400, "Bad Request", f'Field "{field}" cannot be empty')

    return None


def validate_boolean_field(body: dict, field: str) -> dict | None:
    """
    Validate a boolean field in request body.

    Args:
        body: Request body dictionary
        field: Field name to validate

    Returns:
        dict: Error response if validation fails, None if valid
    """
    from .response import error_response

    if field in body and not isinstance(body[field], bool):
        return error_response(400, "Bad Request", f'Field "{field}" must be a boolean')
    return None


def validate_series_order(body: dict, field: str = "series_order") -> dict | None:
    """
    Validate series_order field (integer between 1 and 100, or None to clear).

    Args:
        body: Request body dictionary
        field: Field name to validate (default: "series_order")

    Returns:
        dict: Error response if validation fails, None if valid
    """
    # Support both Lambda deployment and local development
    try:
        from config import MAX_SERIES_ORDER, MIN_SERIES_ORDER
        from utils.response import error_response
    except ImportError:
        from gateway_backend.config import MAX_SERIES_ORDER, MIN_SERIES_ORDER
        from .response import error_response

    if field not in body:
        return None

    series_order = body[field]

    # Allow None/null to clear the field
    if series_order is None:
        return None

    try:
        series_order_int = int(series_order)
        if series_order_int < MIN_SERIES_ORDER or series_order_int > MAX_SERIES_ORDER:
            return error_response(
                400,
                "Bad Request",
                f"series_order must be between {MIN_SERIES_ORDER} and {MAX_SERIES_ORDER}",
            )
    except (ValueError, TypeError):
        return error_response(400, "Bad Request", "series_order must be an integer")

    return None
