"""
Unit tests for utility modules
"""

import json
from unittest.mock import Mock, patch
import urllib.request

import pytest

from gateway_backend.utils.cover import fetch_cover_url, update_cover_on_author_change
from gateway_backend.utils.dynamodb import build_update_expression, build_update_params


# ============================================================================
# Cover Utility Tests
# ============================================================================


def test_fetch_cover_url_success():
    """Test successful cover URL fetch from Google Books API"""

    mock_response_data = {
        "items": [{
            "volumeInfo": {
                "imageLinks": {
                    "thumbnail": "http://books.google.com/cover.jpg"
                }
            }
        }]
    }

    mock_response = Mock()
    mock_response.read.return_value = json.dumps(mock_response_data).encode()
    mock_response.__enter__ = Mock(return_value=mock_response)
    mock_response.__exit__ = Mock(return_value=False)

    with patch.object(urllib.request, 'urlopen', return_value=mock_response):
        url = fetch_cover_url("Foundation", "Isaac Asimov")

    assert url == "https://books.google.com/cover.jpg"  # HTTP upgraded to HTTPS


def test_fetch_cover_url_prefers_medium():
    """Test that fetch_cover_url prefers medium quality image"""

    mock_response_data = {
        "items": [{
            "volumeInfo": {
                "imageLinks": {
                    "smallThumbnail": "http://books.google.com/small.jpg",
                    "thumbnail": "http://books.google.com/thumb.jpg",
                    "medium": "http://books.google.com/medium.jpg"
                }
            }
        }]
    }

    mock_response = Mock()
    mock_response.read.return_value = json.dumps(mock_response_data).encode()
    mock_response.__enter__ = Mock(return_value=mock_response)
    mock_response.__exit__ = Mock(return_value=False)

    with patch.object(urllib.request, 'urlopen', return_value=mock_response):
        url = fetch_cover_url("Test Book")

    assert "medium.jpg" in url


def test_fetch_cover_url_fallback_to_thumbnail():
    """Test that fetch_cover_url falls back to thumbnail if no medium"""

    mock_response_data = {
        "items": [{
            "volumeInfo": {
                "imageLinks": {
                    "smallThumbnail": "http://books.google.com/small.jpg",
                    "thumbnail": "http://books.google.com/thumb.jpg"
                }
            }
        }]
    }

    mock_response = Mock()
    mock_response.read.return_value = json.dumps(mock_response_data).encode()
    mock_response.__enter__ = Mock(return_value=mock_response)
    mock_response.__exit__ = Mock(return_value=False)

    with patch.object(urllib.request, 'urlopen', return_value=mock_response):
        url = fetch_cover_url("Test Book")

    assert "thumb.jpg" in url


def test_fetch_cover_url_not_found():
    """Test fetch_cover_url returns None when no results"""

    mock_response_data = {"items": []}

    mock_response = Mock()
    mock_response.read.return_value = json.dumps(mock_response_data).encode()
    mock_response.__enter__ = Mock(return_value=mock_response)
    mock_response.__exit__ = Mock(return_value=False)

    with patch.object(urllib.request, 'urlopen', return_value=mock_response):
        url = fetch_cover_url("Nonexistent Book")

    assert url is None


def test_fetch_cover_url_no_image_links():
    """Test fetch_cover_url returns None when no image links"""

    mock_response_data = {
        "items": [{
            "volumeInfo": {}
        }]
    }

    mock_response = Mock()
    mock_response.read.return_value = json.dumps(mock_response_data).encode()
    mock_response.__enter__ = Mock(return_value=mock_response)
    mock_response.__exit__ = Mock(return_value=False)

    with patch.object(urllib.request, 'urlopen', return_value=mock_response):
        url = fetch_cover_url("Test Book")

    assert url is None


def test_fetch_cover_url_handles_timeout():
    """Test fetch_cover_url handles timeout gracefully"""

    with patch.object(urllib.request, 'urlopen', side_effect=TimeoutError("Timeout")):
        url = fetch_cover_url("Test Book")

    assert url is None


def test_fetch_cover_url_handles_network_error():
    """Test fetch_cover_url handles network errors gracefully"""

    with patch.object(urllib.request, 'urlopen', side_effect=Exception("Network error")):
        url = fetch_cover_url("Test Book")

    assert url is None


def test_fetch_cover_url_cleans_filename_artifacts():
    """Test that fetch_cover_url cleans up filename artifacts"""

    mock_response = Mock()
    mock_response.read.return_value = json.dumps({"items": []}).encode()
    mock_response.__enter__ = Mock(return_value=mock_response)
    mock_response.__exit__ = Mock(return_value=False)

    with patch.object(urllib.request, 'urlopen', return_value=mock_response) as mock_urlopen:
        fetch_cover_url("Test_Book-Name", "Author_Name")

        # Check that underscores and hyphens were replaced with spaces
        called_url = mock_urlopen.call_args[0][0]
        assert "Test%20Book%20Name" in called_url or "Test+Book+Name" in called_url


def test_update_cover_on_author_change_fetches_when_changed():
    """Test update_cover_on_author_change fetches cover when author changes"""

    metadata_fields = {}

    with patch('gateway_backend.utils.cover.fetch_cover_url', return_value="https://new-cover.jpg") as mock_fetch:
        update_cover_on_author_change(
            current_author="Old Author",
            new_author="New Author",
            title="Test Book",
            metadata_fields=metadata_fields
        )

    assert metadata_fields["coverImageUrl"] == "https://new-cover.jpg"
    mock_fetch.assert_called_once_with("Test Book", "New Author")


def test_update_cover_on_author_change_removes_when_not_found():
    """Test update_cover_on_author_change sets None when cover not found"""

    metadata_fields = {}

    with patch('gateway_backend.utils.cover.fetch_cover_url', return_value=None):
        update_cover_on_author_change(
            current_author="Old Author",
            new_author="New Author",
            title="Test Book",
            metadata_fields=metadata_fields
        )

    assert metadata_fields["coverImageUrl"] is None


def test_update_cover_on_author_change_skips_when_no_change():
    """Test update_cover_on_author_change skips fetch when author unchanged"""

    metadata_fields = {}

    with patch('gateway_backend.utils.cover.fetch_cover_url') as mock_fetch:
        update_cover_on_author_change(
            current_author="Same Author",
            new_author="Same Author",
            title="Test Book",
            metadata_fields=metadata_fields
        )

    mock_fetch.assert_not_called()
    assert "coverImageUrl" not in metadata_fields


def test_update_cover_on_author_change_skips_when_empty_new_author():
    """Test update_cover_on_author_change skips fetch when new author is empty"""

    metadata_fields = {}

    with patch('gateway_backend.utils.cover.fetch_cover_url') as mock_fetch:
        update_cover_on_author_change(
            current_author="Old Author",
            new_author="",
            title="Test Book",
            metadata_fields=metadata_fields
        )

    mock_fetch.assert_not_called()
    assert "coverImageUrl" not in metadata_fields


# ============================================================================
# DynamoDB Utility Tests
# ============================================================================


def test_build_update_expression_basic():
    """Test build_update_expression with basic fields"""

    fields = {"author": "New Author", "series_name": "New Series"}

    expr, values, names = build_update_expression(fields)

    assert "SET" in expr
    assert "#author = :author" in expr
    assert "#series_name = :series_name" in expr
    assert values[":author"] == "New Author"
    assert values[":series_name"] == "New Series"
    assert names["#author"] == "author"
    assert names["#series_name"] == "series_name"


def test_build_update_expression_with_remove():
    """Test build_update_expression removes None values when allow_remove=True"""

    fields = {"author": "New Author", "series_order": None}

    expr, values, names = build_update_expression(fields, allow_remove=True)

    assert "SET" in expr
    assert "REMOVE" in expr
    assert "#author = :author" in expr
    assert "#series_order" in expr
    assert ":author" in values
    assert ":series_order" not in values


def test_build_update_expression_removes_empty_string():
    """Test build_update_expression removes empty strings when allow_remove=True"""

    fields = {"author": ""}

    expr, values, names = build_update_expression(fields, allow_remove=True)

    assert "REMOVE" in expr
    assert "SET" not in expr
    assert "#author" in expr
    assert len(values) == 0


def test_build_update_expression_without_allow_remove():
    """Test build_update_expression keeps None values when allow_remove=False"""

    fields = {"author": None}

    expr, values, names = build_update_expression(fields, allow_remove=False)

    assert "SET" in expr
    assert "REMOVE" not in expr
    assert ":author" in values
    assert values[":author"] is None


def test_build_update_params_basic():
    """Test build_update_params creates correct DynamoDB params"""

    params = build_update_params(
        key={"id": "test-123"},
        fields={"author": "New Author"},
        allow_remove=False,
        condition_expression="attribute_exists(id)",
        return_values="ALL_NEW"
    )

    assert params["Key"] == {"id": "test-123"}
    assert "SET" in params["UpdateExpression"]
    assert ":author" in params["ExpressionAttributeValues"]
    assert params["ConditionExpression"] == "attribute_exists(id)"
    assert params["ReturnValues"] == "ALL_NEW"


def test_build_update_params_with_remove_only():
    """Test build_update_params handles REMOVE-only operations"""

    params = build_update_params(
        key={"id": "test-123"},
        fields={"author": ""},
        allow_remove=True
    )

    assert params["Key"] == {"id": "test-123"}
    assert "REMOVE" in params["UpdateExpression"]
    # ExpressionAttributeValues should not be present when empty
    assert "ExpressionAttributeValues" not in params


def test_build_update_params_mixed_set_and_remove():
    """Test build_update_params with both SET and REMOVE operations"""

    params = build_update_params(
        key={"id": "test-123"},
        fields={"author": "New Author", "series_order": None},
        allow_remove=True
    )

    assert "SET" in params["UpdateExpression"]
    assert "REMOVE" in params["UpdateExpression"]
    assert ":author" in params["ExpressionAttributeValues"]
    assert ":series_order" not in params["ExpressionAttributeValues"]


def test_build_update_params_default_return_values():
    """Test build_update_params uses ALL_NEW as default return value"""

    params = build_update_params(
        key={"id": "test-123"},
        fields={"author": "Test"}
    )

    assert params["ReturnValues"] == "ALL_NEW"


def test_build_update_params_optional_condition():
    """Test build_update_params handles optional condition expression"""

    params_with = build_update_params(
        key={"id": "test-123"},
        fields={"author": "Test"},
        condition_expression="attribute_exists(id)"
    )

    params_without = build_update_params(
        key={"id": "test-123"},
        fields={"author": "Test"}
    )

    assert "ConditionExpression" in params_with
    assert "ConditionExpression" not in params_without


def test_build_update_params_custom_return_values():
    """Test build_update_params with custom return values option"""

    params = build_update_params(
        key={"id": "test-123"},
        fields={"author": "Test"},
        return_values="UPDATED_NEW"
    )

    assert params["ReturnValues"] == "UPDATED_NEW"


def test_build_update_expression_multiple_removes():
    """Test build_update_expression with multiple fields to remove"""

    fields = {
        "author": None,
        "series_name": "",
        "series_order": None
    }

    expr, values, names = build_update_expression(fields, allow_remove=True)

    assert "REMOVE" in expr
    assert "SET" not in expr
    assert "#author" in expr
    assert "#series_name" in expr
    assert "#series_order" in expr
    assert len(values) == 0


def test_update_cover_on_author_change_modifies_dict_in_place():
    """Test that update_cover_on_author_change modifies the dict in place"""

    metadata_fields = {"series_name": "Test Series"}

    with patch('gateway_backend.utils.cover.fetch_cover_url', return_value="https://cover.jpg"):
        update_cover_on_author_change(
            current_author="Old",
            new_author="New",
            title="Test",
            metadata_fields=metadata_fields
        )

    # Should have both original field and new cover
    assert metadata_fields["series_name"] == "Test Series"
    assert metadata_fields["coverImageUrl"] == "https://cover.jpg"


def test_fetch_cover_url_with_only_small_thumbnail():
    """Test fetch_cover_url falls back to smallThumbnail if that's all that's available"""

    mock_response_data = {
        "items": [{
            "volumeInfo": {
                "imageLinks": {
                    "smallThumbnail": "http://books.google.com/small.jpg"
                }
            }
        }]
    }

    mock_response = Mock()
    mock_response.read.return_value = json.dumps(mock_response_data).encode()
    mock_response.__enter__ = Mock(return_value=mock_response)
    mock_response.__exit__ = Mock(return_value=False)

    with patch.object(urllib.request, 'urlopen', return_value=mock_response):
        url = fetch_cover_url("Test Book")

    assert "small.jpg" in url
    assert url.startswith("https://")


def test_fetch_cover_url_without_author():
    """Test fetch_cover_url works with just title (no author)"""

    mock_response_data = {
        "items": [{
            "volumeInfo": {
                "imageLinks": {
                    "thumbnail": "http://books.google.com/cover.jpg"
                }
            }
        }]
    }

    mock_response = Mock()
    mock_response.read.return_value = json.dumps(mock_response_data).encode()
    mock_response.__enter__ = Mock(return_value=mock_response)
    mock_response.__exit__ = Mock(return_value=False)

    with patch.object(urllib.request, 'urlopen', return_value=mock_response) as mock_urlopen:
        url = fetch_cover_url("Test Book", author=None)

    assert url is not None
    # Should only query with title, not author
    called_url = mock_urlopen.call_args[0][0]
    assert "Test" in called_url
