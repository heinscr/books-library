"""
DynamoDB utilities for Books API

Provides functions for building DynamoDB update expressions and queries.
"""

from __future__ import annotations

from typing import Any, Dict


def build_update_expression(
    fields: dict[str, Any], allow_remove: bool = False
) -> tuple[str, dict[str, Any], dict[str, str]]:
    """
    Build DynamoDB update expression from a dictionary of fields.

    Args:
        fields: Dictionary of field names to values
        allow_remove: If True, None values will REMOVE the attribute

    Returns:
        tuple: (update_expression, expression_attribute_values, expression_attribute_names)

    Example:
        fields = {"author": "New Author", "series_order": None}
        expr, values, names = build_update_expression(fields, allow_remove=True)
        # expr = "SET #author = :author REMOVE #series_order"
        # values = {":author": "New Author"}
        # names = {"#author": "author", "#series_order": "series_order"}
    """
    update_expr_parts = []
    remove_expr_parts = []
    expr_attr_values: dict[str, Any] = {}
    expr_attr_names: dict[str, str] = {}

    for field, value in fields.items():
        # Use attribute name placeholders to avoid reserved word conflicts
        name_placeholder = f"#{field}"
        value_placeholder = f":{field}"

        expr_attr_names[name_placeholder] = field

        if allow_remove and (value is None or value == ""):
            # Remove the attribute if null/empty
            remove_expr_parts.append(name_placeholder)
        else:
            # Set the attribute value
            update_expr_parts.append(f"{name_placeholder} = {value_placeholder}")
            expr_attr_values[value_placeholder] = value

    # Build the full update expression
    update_expression_parts = []
    if update_expr_parts:
        update_expression_parts.append("SET " + ", ".join(update_expr_parts))
    if remove_expr_parts:
        update_expression_parts.append("REMOVE " + ", ".join(remove_expr_parts))

    update_expression = " ".join(update_expression_parts)

    return update_expression, expr_attr_values, expr_attr_names


def build_update_params(
    key: Dict[str, Any],
    fields: Dict[str, Any],
    allow_remove: bool = False,
    condition_expression: str | None = None,
    return_values: str = "ALL_NEW"
) -> Dict[str, Any]:
    """
    Build complete DynamoDB update_item parameters.

    Handles the common pattern of building update expressions and
    conditionally including ExpressionAttributeValues when not empty.

    Args:
        key: Primary key for the item to update
        fields: Dictionary of field names to values
        allow_remove: If True, None/empty values will REMOVE the attribute
        condition_expression: Optional condition expression
        return_values: Return values option (default: ALL_NEW)

    Returns:
        dict: Complete parameters for table.update_item()

    Example:
        params = build_update_params(
            key={"id": "book-123"},
            fields={"author": "New Author", "series_order": None},
            allow_remove=True,
            condition_expression="attribute_exists(id)"
        )
        response = table.update_item(**params)
    """
    update_expression, expr_values, expr_names = build_update_expression(
        fields, allow_remove=allow_remove
    )

    params = {
        "Key": key,
        "UpdateExpression": update_expression,
        "ExpressionAttributeNames": expr_names,
        "ReturnValues": return_values,
    }

    # Only add ExpressionAttributeValues if not empty (REMOVE-only operations have no values)
    if expr_values:
        params["ExpressionAttributeValues"] = expr_values

    # Add condition expression if provided
    if condition_expression:
        params["ConditionExpression"] = condition_expression

    return params
