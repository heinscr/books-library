"""
DynamoDB utilities for Books API

Provides functions for building DynamoDB update expressions and queries.
"""

from __future__ import annotations

from typing import Any


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
