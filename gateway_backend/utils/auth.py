"""
Authentication and authorization utilities for Books API

Provides functions to extract user identity and permissions from
AWS Cognito authorizer context in API Gateway events.
"""


def get_user_id(event: dict) -> str | None:
    """
    Extract user ID (sub) from Cognito authorizer context.

    Args:
        event: API Gateway event with Cognito authorization

    Returns:
        str: The user's Cognito sub (unique identifier), or None if not authenticated
    """
    authorizer = event.get("requestContext", {}).get("authorizer", {})
    claims = authorizer.get("claims", {})
    return claims.get("sub")


def get_user_groups(event: dict) -> list[str]:
    """
    Extract user groups from Cognito authorizer context.

    Args:
        event: API Gateway event with Cognito authorization

    Returns:
        list: List of group names the user belongs to (e.g., ['admins'])
    """
    authorizer = event.get("requestContext", {}).get("authorizer", {})
    claims = authorizer.get("claims", {})
    groups_str = claims.get("cognito:groups", "")
    if not groups_str:
        return []
    # Groups come as comma-separated string
    return [g.strip() for g in groups_str.split(",") if g.strip()]


def is_admin(event: dict) -> bool:
    """
    Check if the user is in the admins group.

    Args:
        event: API Gateway event with Cognito authorization

    Returns:
        bool: True if user is in admins group, False otherwise
    """
    return "admins" in get_user_groups(event)
