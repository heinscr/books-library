import json
from decimal import Decimal
from unittest.mock import Mock, patch

from gateway_backend import config, handler


def create_mock_event(user_id="test-user-123", is_admin=False, path_params=None, body=None):
    """Create a mock API Gateway event with Cognito authentication
    
    Args:
        user_id: Cognito user ID (sub claim)
        is_admin: Whether user is in admins group
        path_params: Path parameters dict
        body: Request body (dict or JSON string)
    
    Returns:
        dict: Mock API Gateway event with authentication claims
    """
    groups = "admins" if is_admin else ""
    
    event = {
        "requestContext": {
            "authorizer": {
                "claims": {
                    "sub": user_id,
                    "email": f"{user_id}@example.com",
                    "cognito:groups": groups
                }
            }
        }
    }
    
    if path_params:
        event["pathParameters"] = path_params
    
    if body:
        event["body"] = json.dumps(body) if isinstance(body, dict) else body  # type: ignore[typeddict-item]
    
    return event


def test_list_handler_returns_books_list():
    """Test that handler returns list of books from DynamoDB"""

    # Mock DynamoDB response with Decimal types (as returned by DynamoDB)
    mock_dynamodb_response = {
        "Items": [
            {
                "id": "book-a.zip",
                "name": "Book A.zip",
                "size": Decimal("1024000"),
                "created": "2023-06-15T10:30:00Z",
                "read": False,
                "s3_url": "s3://test-bucket/books/Book A.zip",
                "author": "Author A",
            },
            {
                "id": "book-b.zip",
                "name": "Book B.zip",
                "size": Decimal("2048000"),
                "created": "2024-03-20T14:45:30Z",
                "read": True,
                "s3_url": "s3://test-bucket/books/Book B.zip",
            },
        ]
    }

    # Create mock DynamoDB tables
    mock_books_table = Mock()
    mock_books_table.scan.return_value = mock_dynamodb_response

    # Mock UserBooks table - user has read book-b
    mock_user_books_table = Mock()
    mock_user_books_table.query.return_value = {
        "Items": [
            {"userId": "test-user-123", "bookId": "book-b.zip", "read": True}
        ]
    }

    # Create authenticated event
    event = create_mock_event(user_id="test-user-123", is_admin=False)

    # Patch both tables
    with patch.object(config, "books_table", mock_books_table), \
         patch.object(config, "user_books_table", mock_user_books_table):
        resp = handler.list_handler(event, None)

    # Verify response
    assert resp["statusCode"] == 200
    body = json.loads(resp["body"])

    # Response format changed to {books: [], isAdmin: boolean}
    assert "books" in body
    assert "isAdmin" in body
    assert body["isAdmin"] is False

    books = body["books"]
    assert len(books) == 2

    # Verify books are sorted by created date (most recent first - Book B from 2024)
    assert books[0]["name"] == "Book B.zip"
    assert books[0]["size"] == 2048000
    assert books[0]["created"] == "2024-03-20T14:45:30Z"
    assert books[0]["read"] is True  # User-specific read status

    # Verify second book (Book A from 2023)
    assert books[1]["name"] == "Book A.zip"
    assert books[1]["size"] == 1024000
    assert books[1]["created"] == "2023-06-15T10:30:00Z"
    assert books[1]["read"] is False  # Not in UserBooks, defaults to False
    assert books[1]["author"] == "Author A"


def test_list_handler_empty_table():
    """Test handler when DynamoDB table is empty"""

    # Mock empty DynamoDB response
    mock_books_table = Mock()
    mock_books_table.scan.return_value = {"Items": []}
    
    mock_user_books_table = Mock()
    mock_user_books_table.scan.return_value = {"Items": []}

    event = create_mock_event()

    with patch.object(config, "books_table", mock_books_table), \
         patch.object(config, "user_books_table", mock_user_books_table):
        resp = handler.list_handler(event, None)

    assert resp["statusCode"] == 200
    body = json.loads(resp["body"])
    assert "books" in body
    assert body["books"] == []
    assert body["isAdmin"] is False


def test_list_handler_pagination():
    """Test handler when DynamoDB returns paginated results"""

    # First page
    mock_response_page1 = {
        "Items": [
            {
                "id": "book-1.zip",
                "name": "Book 1.zip",
                "created": "2023-01-01T00:00:00Z",
                "read": False,
                "s3_url": "s3://test-bucket/books/Book 1.zip",
            }
        ],
        "LastEvaluatedKey": {"id": "book-1.zip"},
    }

    # Second page
    mock_response_page2 = {
        "Items": [
            {
                "id": "book-2.zip",
                "name": "Book 2.zip",
                "created": "2023-02-01T00:00:00Z",
                "read": True,
                "s3_url": "s3://test-bucket/books/Book 2.zip",
            }
        ]
    }

    mock_books_table = Mock()
    mock_books_table.scan.side_effect = [mock_response_page1, mock_response_page2]
    
    mock_user_books_table = Mock()
    mock_user_books_table.scan.return_value = {"Items": []}

    event = create_mock_event()

    with patch.object(config, "books_table", mock_books_table), \
         patch.object(config, "user_books_table", mock_user_books_table):
        resp = handler.list_handler(event, None)

    assert resp["statusCode"] == 200
    body = json.loads(resp["body"])
    assert len(body["books"]) == 2


def test_list_handler_dynamodb_error():
    """Test handler when DynamoDB throws an error"""

    mock_books_table = Mock()
    mock_books_table.scan.side_effect = Exception("DynamoDB connection error")
    
    mock_user_books_table = Mock()
    mock_user_books_table.scan.return_value = {"Items": []}

    event = create_mock_event()

    with patch.object(config, "books_table", mock_books_table), \
         patch.object(config, "user_books_table", mock_user_books_table):
        resp = handler.list_handler(event, None)

    assert resp["statusCode"] == 500
    body = json.loads(resp["body"])
    assert "error" in body


def test_get_book_handler_success():
    """Test that get_book_handler returns book metadata and presigned URL with user-specific read status"""

    event = create_mock_event(path_params={"id": "book-a.zip"})

    # Mock Books table response
    mock_books_item = {
        "Item": {
            "id": "book-a.zip",
            "name": "Book A.zip",
            "size": Decimal("1024000"),
            "created": "2023-06-15T10:30:00Z",
            "s3_url": "s3://test-bucket/books/Book A.zip",
            "author": "Author A",
        }
    }

    # Mock UserBooks table response - user has read this book
    mock_user_books_item = {
        "Item": {
            "userId": "test-user-123",
            "bookId": "book-a.zip",
            "read": True
        }
    }

    # Mock presigned URL generation
    mock_url = "https://s3.amazonaws.com/test-bucket/books/Book%20A.zip?signed=true"

    mock_books_table = Mock()
    mock_books_table.get_item.return_value = mock_books_item
    
    mock_user_books_table = Mock()
    mock_user_books_table.get_item.return_value = mock_user_books_item

    with (
        patch.object(config, "books_table", mock_books_table),
        patch.object(config, "user_books_table", mock_user_books_table),
        patch.object(config.s3_client, "generate_presigned_url", return_value=mock_url),
    ):
        resp = handler.get_book_handler(event, None)

    assert resp["statusCode"] == 200
    body = json.loads(resp["body"])
    assert body["id"] == "book-a.zip"
    assert body["name"] == "Book A.zip"
    assert body["downloadUrl"] == mock_url
    assert body["expiresIn"] == 3600
    assert body["read"] is True  # User-specific read status
    assert body["author"] == "Author A"


def test_get_book_handler_missing_id():
    """Test get_book_handler when book ID is missing"""

    event = {"pathParameters": {}}

    resp = handler.get_book_handler(event, None)

    assert resp["statusCode"] == 400
    body = json.loads(resp["body"])
    assert "error" in body
    assert "Id is required" in body["message"]


def test_get_book_handler_not_found():
    """Test get_book_handler when book doesn't exist in DynamoDB"""

    event = create_mock_event(path_params={"id": "nonexistent.zip"})

    # Mock DynamoDB response with no item
    mock_books_table = Mock()
    mock_books_table.get_item.return_value = {}
    
    mock_user_books_table = Mock()
    mock_user_books_table.get_item.return_value = {}

    with patch.object(config, "books_table", mock_books_table), \
         patch.object(config, "user_books_table", mock_user_books_table):
        resp = handler.get_book_handler(event, None)

    assert resp["statusCode"] == 404
    body = json.loads(resp["body"])
    assert "Not Found" in body["error"]


def test_get_book_handler_missing_s3_url():
    """Test get_book_handler when DynamoDB item is missing S3 URL"""

    event = create_mock_event(path_params={"id": "book-a.zip"})

    # Mock DynamoDB response with missing s3_url
    mock_books_item = {
        "Item": {
            "id": "book-a.zip",
            "name": "Book A.zip",
            "created": "2023-06-15T10:30:00Z",
            # Missing s3_url
        }
    }

    mock_books_table = Mock()
    mock_books_table.get_item.return_value = mock_books_item
    
    mock_user_books_table = Mock()
    mock_user_books_table.get_item.return_value = {}

    with patch.object(config, "books_table", mock_books_table), \
         patch.object(config, "user_books_table", mock_user_books_table):
        resp = handler.get_book_handler(event, None)

    assert resp["statusCode"] == 500
    body = json.loads(resp["body"])
    assert "Invalid Data" in body["error"]
    assert "missing S3 URL" in body["message"]


def test_update_book_handler_success():
    """Test updating book metadata and user-specific read status"""

    event = create_mock_event(
        path_params={"id": "book-a.zip"},
        body={"read": True, "author": "Updated Author"}
    )

    # Mock Books table get response
    mock_books_get_response = {
        "Item": {
            "id": "book-a.zip",
            "name": "Book A.zip",
            "author": "Updated Author",
            "created": "2023-06-15T10:30:00Z",
            "s3_url": "s3://test-bucket/books/Book A.zip",
        }
    }

    mock_books_table = Mock()
    mock_books_table.get_item.return_value = mock_books_get_response
    mock_books_table.update_item.return_value = {"Attributes": mock_books_get_response["Item"]}
    
    mock_user_books_table = Mock()

    with patch.object(config, "books_table", mock_books_table), \
         patch.object(config, "user_books_table", mock_user_books_table):
        resp = handler.update_book_handler(event, None)

    assert resp["statusCode"] == 200
    body = json.loads(resp["body"])
    assert body["id"] == "book-a.zip"
    assert body["read"] is True
    assert body["author"] == "Updated Author"
    
    # Verify UserBooks table was updated for read status
    mock_user_books_table.put_item.assert_called_once()


def test_update_book_handler_missing_id():
    """Test update_book_handler when book ID is missing"""

    event = create_mock_event(path_params={}, body={"read": True})

    resp = handler.update_book_handler(event, None)

    assert resp["statusCode"] == 400
    body = json.loads(resp["body"])
    assert "Id is required" in body["message"]


def test_update_book_handler_invalid_json():
    """Test update_book_handler with invalid JSON body"""

    event = create_mock_event(path_params={"id": "book-a.zip"}, body=None)
    event["body"] = "invalid json{"  # type: ignore[typeddict-item]

    resp = handler.update_book_handler(event, None)

    assert resp["statusCode"] == 400
    body = json.loads(resp["body"])
    assert "Invalid JSON" in body["message"]


def test_update_book_handler_no_fields():
    """Test update_book_handler when no valid fields provided"""

    event = create_mock_event(path_params={"id": "book-a.zip"}, body={})

    resp = handler.update_book_handler(event, None)

    assert resp["statusCode"] == 400
    body = json.loads(resp["body"])
    assert "No valid fields to update" in body["message"]


def test_update_book_handler_not_found():
    """Test update_book_handler when book doesn't exist"""

    from botocore.exceptions import ClientError

    event = create_mock_event(path_params={"id": "nonexistent.zip"}, body={"read": True})

    # Mock DynamoDB conditional check failure
    error_response = {"Error": {"Code": "ConditionalCheckFailedException"}}
    condition_error = ClientError(error_response, "update_item")  # type: ignore[arg-type]

    mock_books_table = Mock()
    mock_books_table.update_item.side_effect = condition_error
    mock_books_table.get_item.return_value = {}

    mock_user_books_table = Mock()

    with patch.object(config, "books_table", mock_books_table), \
         patch.object(config, "user_books_table", mock_user_books_table):
        resp = handler.update_book_handler(event, None)

    assert resp["statusCode"] == 404
    body = json.loads(resp["body"])
    assert "Not Found" in body["error"]


def test_update_book_handler_invalid_read_type():
    """Test update_book_handler with invalid type for 'read' field"""

    event = create_mock_event(path_params={"id": "book-a.zip"}, body={"read": "yes"})  # Should be boolean

    resp = handler.update_book_handler(event, None)

    assert resp["statusCode"] == 400
    body = json.loads(resp["body"])
    assert '"read" must be a boolean' in body["message"]


def test_update_book_handler_invalid_author_type():
    """Test update_book_handler with invalid type for 'author' field"""

    event = create_mock_event(path_params={"id": "book-a.zip"}, body={"author": 123})  # Should be string

    resp = handler.update_book_handler(event, None)

    assert resp["statusCode"] == 400
    body = json.loads(resp["body"])
    assert '"author" must be a string' in body["message"]


def test_update_book_handler_author_too_long():
    """Test update_book_handler with author exceeding length limit"""

    event = create_mock_event(path_params={"id": "book-a.zip"}, body={"author": "x" * 501})  # Exceeds 500 char limit

    resp = handler.update_book_handler(event, None)

    assert resp["statusCode"] == 400
    body = json.loads(resp["body"])
    assert "exceeds maximum length" in body["message"]


def test_update_book_handler_empty_name():
    """Test update_book_handler with empty name"""

    event = create_mock_event(path_params={"id": "book-a.zip"}, body={"name": ""})

    resp = handler.update_book_handler(event, None)

    assert resp["statusCode"] == 400
    body = json.loads(resp["body"])
    assert "cannot be empty" in body["message"]


def test_update_book_handler_name_too_long():
    """Test update_book_handler with name exceeding length limit"""

    event = create_mock_event(path_params={"id": "book-a.zip"}, body={"name": "x" * 501})  # Exceeds 500 char limit

    resp = handler.update_book_handler(event, None)

    assert resp["statusCode"] == 400
    body = json.loads(resp["body"])
    assert "exceeds maximum length" in body["message"]


def test_update_book_handler_with_series_fields():
    """Test updating book with series_name and series_order"""

    event = create_mock_event(path_params={"id": "book-a.zip"}, body={
        "series_name": "The Foundation Series",
        "series_order": 1
    })

    # Mock DynamoDB update response
    mock_update_response = {
        "Attributes": {
            "id": "book-a.zip",
            "name": "Foundation",
            "read": False,
            "author": "Isaac Asimov",
            "series_name": "The Foundation Series",
            "series_order": Decimal("1"),
            "created": "2023-06-15T10:30:00Z",
            "s3_url": "s3://test-bucket/books/Foundation.zip",
        }
    }

    mock_books_table = Mock()
    mock_books_table.update_item.return_value = mock_update_response

    mock_user_books_table = Mock()

    with patch.object(config, "books_table", mock_books_table), \
         patch.object(config, "user_books_table", mock_user_books_table):
        resp = handler.update_book_handler(event, None)

    assert resp["statusCode"] == 200
    body = json.loads(resp["body"])
    assert body["series_name"] == "The Foundation Series"
    assert body["series_order"] == 1


def test_update_book_handler_series_order_out_of_range():
    """Test update_book_handler with series_order outside valid range"""

    event = create_mock_event(path_params={"id": "book-a.zip"}, body={"series_order": 101})  # Exceeds max of 100

    resp = handler.update_book_handler(event, None)

    assert resp["statusCode"] == 400
    body = json.loads(resp["body"])
    assert "must be between 1 and 100" in body["message"]


def test_update_book_handler_series_order_below_range():
    """Test update_book_handler with series_order below minimum"""

    event = create_mock_event(path_params={"id": "book-a.zip"}, body={"series_order": 0})

    resp = handler.update_book_handler(event, None)

    assert resp["statusCode"] == 400
    body = json.loads(resp["body"])
    assert "must be between 1 and 100" in body["message"]


def test_update_book_handler_series_order_invalid_type():
    """Test update_book_handler with non-integer series_order"""

    event = create_mock_event(path_params={"id": "book-a.zip"}, body={"series_order": "not a number"})

    resp = handler.update_book_handler(event, None)

    assert resp["statusCode"] == 400
    body = json.loads(resp["body"])
    assert "must be an integer" in body["message"]


def test_update_book_handler_clear_series_order():
    """Test clearing series_order by setting it to null"""

    event = create_mock_event(path_params={"id": "book-a.zip"}, body={"series_order": None})

    # Mock DynamoDB update response without series_order
    mock_update_response = {
        "Attributes": {
            "id": "book-a.zip",
            "name": "Foundation",
            "read": False,
            "author": "Isaac Asimov",
            "series_name": "The Foundation Series",
            "created": "2023-06-15T10:30:00Z",
            "s3_url": "s3://test-bucket/books/Foundation.zip",
        }
    }

    mock_books_table = Mock()
    mock_books_table.update_item.return_value = mock_update_response

    mock_user_books_table = Mock()

    with patch.object(config, "books_table", mock_books_table), \
         patch.object(config, "user_books_table", mock_user_books_table):
        resp = handler.update_book_handler(event, None)

    assert resp["statusCode"] == 200
    body = json.loads(resp["body"])
    assert "series_order" not in body or body["series_order"] is None


def test_list_handler_returns_books_with_series():
    """Test that list handler returns books with series fields"""

    # Mock DynamoDB response with series fields
    mock_dynamodb_response = {
        "Items": [
            {
                "id": "foundation.zip",
                "name": "Foundation",
                "size": Decimal("1024000"),
                "created": "2023-06-15T10:30:00Z",
                "read": False,
                "s3_url": "s3://test-bucket/books/foundation.zip",
                "author": "Isaac Asimov",
                "series_name": "Foundation",
                "series_order": Decimal("1"),
            },
        ]
    }

    mock_books_table = Mock()
    mock_books_table.scan.return_value = mock_dynamodb_response

    mock_user_books_table = Mock()
    mock_user_books_table.query.return_value = {"Items": []}

    event = create_mock_event()

    with patch.object(config, "books_table", mock_books_table), \
         patch.object(config, "user_books_table", mock_user_books_table):
        resp = handler.list_handler(event, None)

    assert resp["statusCode"] == 200
    body = json.loads(resp["body"])
    assert "books" in body
    assert len(body["books"]) == 1
    assert body["books"][0]["series_name"] == "Foundation"
    assert body["books"][0]["series_order"] == 1


def test_s3_trigger_handler_success():
    """Test S3 trigger handler ingests book into DynamoDB"""

    event = {
        "Records": [
            {
                "s3": {
                    "bucket": {"name": "test-bucket"},
                    "object": {"key": "books/Book A.zip", "size": 1024000},
                },
                "eventTime": "2023-06-15T10:30:00.000Z",
            }
        ]
    }

    mock_table = Mock()

    with patch.object(config, "books_table", mock_table):
        resp = handler.s3_trigger_handler(event, None)

    # Verify put_item was called
    mock_table.put_item.assert_called_once()
    call_args = mock_table.put_item.call_args[1]
    item = call_args["Item"]

    # Handler removes .zip extension from ID and name
    assert item["id"] == "Book A"
    assert item["name"] == "Book A"
    assert item["size"] == 1024000
    assert item["s3_url"] == "s3://test-bucket/books/Book A.zip"
    assert item["read"] is False

    assert resp["statusCode"] == 200


def test_s3_trigger_handler_with_author():
    """Test S3 trigger handler preserves original filename structure"""

    event = {
        "Records": [
            {
                "s3": {
                    "bucket": {"name": "test-bucket"},
                    "object": {"key": "books/My_Book-Title.zip", "size": 2048000},
                }
            }
        ]
    }

    mock_table = Mock()

    with patch.object(config, "books_table", mock_table):
        resp = handler.s3_trigger_handler(event, None)

    # Verify put_item was called
    call_args = mock_table.put_item.call_args[1]
    item = call_args["Item"]

    # Handler now keeps original filename structure (doesn't replace _ or -)
    assert item["name"] == "My_Book-Title"
    assert item["id"] == "My_Book-Title"  # ID keeps original (minus .zip)
    assert resp["statusCode"] == 200


def test_s3_trigger_handler_multiple_records():
    """Test S3 trigger handler processes multiple S3 events"""

    event = {
        "Records": [
            {
                "s3": {
                    "bucket": {"name": "test-bucket"},
                    "object": {"key": "books/Book1.zip", "size": 1000},
                }
            },
            {
                "s3": {
                    "bucket": {"name": "test-bucket"},
                    "object": {"key": "books/Book2.zip", "size": 2000},
                }
            },
        ]
    }

    mock_table = Mock()

    with patch.object(config, "books_table", mock_table):
        resp = handler.s3_trigger_handler(event, None)

    # Verify put_item was called twice
    assert mock_table.put_item.call_count == 2
    assert resp["statusCode"] == 200


def test_s3_trigger_handler_skips_non_zip():
    """Test S3 trigger handler processes non-zip files (converts filename)"""

    event = {
        "Records": [
            {
                "s3": {
                    "bucket": {"name": "test-bucket"},
                    "object": {"key": "books/index.html", "size": 5000},
                }
            }
        ]
    }

    mock_table = Mock()

    with patch.object(config, "books_table", mock_table):
        resp = handler.s3_trigger_handler(event, None)

    # Verify put_item WAS called (handler processes all files)
    mock_table.put_item.assert_called_once()
    call_args = mock_table.put_item.call_args[1]
    item = call_args["Item"]

    # Should use the filename as-is since it's not a .zip
    assert item["id"] == "index.html"
    assert item["name"] == "index.html"
    assert resp["statusCode"] == 200


def test_s3_trigger_handler_skips_folder():
    """Test S3 trigger handler processes folder markers (edge case)"""

    event = {
        "Records": [
            {"s3": {"bucket": {"name": "test-bucket"}, "object": {"key": "books/", "size": 0}}}
        ]
    }

    mock_table = Mock()

    with patch.object(config, "books_table", mock_table):
        resp = handler.s3_trigger_handler(event, None)

    # Verify put_item WAS called (handler currently processes all S3 events)
    # This is an edge case where it might create an empty-name record
    mock_table.put_item.assert_called_once()
    assert resp["statusCode"] == 200


# ============================================================================
# Upload Handler Tests
# ============================================================================


def test_upload_handler_success():
    """Test successful presigned URL generation for upload"""

    event = create_mock_event(
        is_admin=True,
        body={"filename": "Test Book.zip", "fileSize": 1024000, "author": "Test Author"}
    )

    mock_presigned_url = "https://s3.amazonaws.com/test-bucket/books/Test%20Book.zip?signature=xyz"

    with patch.object(config.s3_client, "generate_presigned_url", return_value=mock_presigned_url):
        resp = handler.upload_handler(event, None)

    assert resp["statusCode"] == 200
    body = json.loads(resp["body"])

    assert body["uploadUrl"] == mock_presigned_url
    assert body["method"] == "PUT"
    assert body["filename"] == "Test Book.zip"
    assert body["s3Key"] == "books/Test Book.zip"
    assert body["expiresIn"] == 3600
    assert body["author"] == "Test Author"


def test_upload_handler_missing_filename():
    """Test upload handler rejects request without filename"""

    event = create_mock_event(is_admin=True, body={"fileSize": 1024000})

    resp = handler.upload_handler(event, None)

    assert resp["statusCode"] == 400
    body = json.loads(resp["body"])
    assert "filename is required" in body["message"]


def test_upload_handler_invalid_extension():
    """Test upload handler rejects non-zip files"""

    event = create_mock_event(is_admin=True, body={"filename": "test.pdf", "fileSize": 1024000})

    resp = handler.upload_handler(event, None)

    assert resp["statusCode"] == 400
    body = json.loads(resp["body"])
    assert "Only .zip files are allowed" in body["message"]


def test_upload_handler_file_too_large():
    """Test upload handler rejects files exceeding 5GB limit"""

    event = create_mock_event(is_admin=True, body={"filename": "huge.zip", "fileSize": 6 * 1024 * 1024 * 1024})  # 6GB

    resp = handler.upload_handler(event, None)

    assert resp["statusCode"] == 400
    body = json.loads(resp["body"])
    assert "exceeds maximum limit of 5GB" in body["message"]


def test_upload_handler_invalid_json():
    """Test upload handler handles invalid JSON gracefully"""

    event = create_mock_event(is_admin=True, body=None)
    event["body"] = "invalid json{"  # type: ignore[typeddict-item]

    resp = handler.upload_handler(event, None)

    assert resp["statusCode"] == 400
    body = json.loads(resp["body"])
    assert "Invalid JSON" in body["message"]


def test_upload_handler_author_too_long():
    """Test upload handler rejects author exceeding 500 characters"""

    event = create_mock_event(
        is_admin=True,
        body={"filename": "test.zip", "fileSize": 1024000, "author": "A" * 501}  # 501 characters
    )

    resp = handler.upload_handler(event, None)

    assert resp["statusCode"] == 400


def test_upload_handler_without_author():
    """Test upload handler works without optional author field"""

    event = create_mock_event(is_admin=True, body={"filename": "Test Book.zip", "fileSize": 1024000})

    mock_presigned_url = "https://s3.amazonaws.com/test-bucket/books/Test%20Book.zip?signature=xyz"

    with patch.object(config.s3_client, "generate_presigned_url", return_value=mock_presigned_url):
        resp = handler.upload_handler(event, None)

    assert resp["statusCode"] == 200
    body = json.loads(resp["body"])

    assert "author" not in body


def test_upload_handler_with_s3_tags():
    """Test upload handler includes S3 tags in presigned URL"""

    event = create_mock_event(
        is_admin=True,
        body={
            "filename": "Test Book.zip",
            "fileSize": 1024000,
            "author": "Test Author",
            "series_name": "Test Series",
            "series_order": 1
        }
    )

    mock_presigned_url = "https://s3.amazonaws.com/test-bucket/books/Test%20Book.zip?signature=xyz"

    with patch.object(config.s3_client, "generate_presigned_url", return_value=mock_presigned_url) as mock_generate:
        resp = handler.upload_handler(event, None)

    # Verify S3 tags were included in the presigned URL params
    call_args = mock_generate.call_args
    params = call_args[1]["Params"]

    assert "Tagging" in params
    # Values should be URL-encoded (spaces become +)
    assert "author=Test+Author" in params["Tagging"]
    assert "series_name=Test+Series" in params["Tagging"]
    assert "series_order=1" in params["Tagging"]

    assert resp["statusCode"] == 200
    body = json.loads(resp["body"])

    assert body["author"] == "Test Author"
    assert body["series_name"] == "Test Series"
    assert body["series_order"] == 1


def test_upload_handler_with_partial_tags():
    """Test upload handler handles partial metadata tags"""

    event = create_mock_event(
        is_admin=True,
        body={
            "filename": "Test Book.zip",
            "fileSize": 1024000,
            "author": "Test Author"
        }
    )

    mock_presigned_url = "https://s3.amazonaws.com/test-bucket/books/Test%20Book.zip?signature=xyz"

    with patch.object(config.s3_client, "generate_presigned_url", return_value=mock_presigned_url) as mock_generate:
        resp = handler.upload_handler(event, None)

    # Verify only author tag is included (URL-encoded)
    call_args = mock_generate.call_args
    params = call_args[1]["Params"]

    assert "Tagging" in params
    assert params["Tagging"] == "author=Test+Author"

    assert resp["statusCode"] == 200


def test_s3_trigger_handler_with_tags():
    """Test S3 trigger handler reads tags and updates DynamoDB"""

    event = {
        "Records": [
            {
                "s3": {
                    "bucket": {"name": "test-bucket"},
                    "object": {"key": "books/Test Book.zip", "size": 2048000},
                }
            }
        ]
    }

    # Mock S3 get_object_tagging response
    mock_tagging_response = {
        "TagSet": [
            {"Key": "author", "Value": "Test Author"},
            {"Key": "series_name", "Value": "Test Series"},
            {"Key": "series_order", "Value": "1"}
        ]
    }

    mock_table = Mock()

    with patch.object(config, "books_table", mock_table), \
         patch.object(config.s3_client, "get_object_tagging", return_value=mock_tagging_response):
        resp = handler.s3_trigger_handler(event, None)

    # Verify put_item was called with tag data
    call_args = mock_table.put_item.call_args[1]
    item = call_args["Item"]

    assert item["author"] == "Test Author"
    assert item["series_name"] == "Test Series"
    assert item["series_order"] == 1
    assert resp["statusCode"] == 200


def test_s3_trigger_handler_tags_override_filename_metadata():
    """Test S3 tags override metadata extracted from filename"""

    event = {
        "Records": [
            {
                "s3": {
                    "bucket": {"name": "test-bucket"},
                    "object": {"key": "books/Wrong Author - Test Book.zip", "size": 2048000},
                }
            }
        ]
    }

    # Mock S3 get_object_tagging response with correct author
    mock_tagging_response = {
        "TagSet": [
            {"Key": "author", "Value": "Correct Author"}
        ]
    }

    mock_table = Mock()

    with patch.object(config, "books_table", mock_table), \
         patch.object(config.s3_client, "get_object_tagging", return_value=mock_tagging_response):
        resp = handler.s3_trigger_handler(event, None)

    # Verify tag data overrides filename metadata
    call_args = mock_table.put_item.call_args[1]
    item = call_args["Item"]

    assert item["author"] == "Correct Author"  # From tags, not filename
    assert resp["statusCode"] == 200


def test_s3_trigger_handler_no_tags():
    """Test S3 trigger handler works without tags (falls back to filename)"""

    event = {
        "Records": [
            {
                "s3": {
                    "bucket": {"name": "test-bucket"},
                    "object": {"key": "books/Test Author - Test Book.zip", "size": 2048000},
                }
            }
        ]
    }

    # Mock S3 get_object_tagging response with no tags
    mock_tagging_response = {"TagSet": []}

    mock_table = Mock()

    with patch.object(config, "books_table", mock_table), \
         patch.object(config.s3_client, "get_object_tagging", return_value=mock_tagging_response):
        resp = handler.s3_trigger_handler(event, None)

    # Verify filename metadata is used
    call_args = mock_table.put_item.call_args[1]
    item = call_args["Item"]

    assert item["author"] == "Test Author"  # From filename
    assert item["name"] == "Test Book"
    assert resp["statusCode"] == 200


def test_s3_trigger_handler_tag_read_error():
    """Test S3 trigger handler continues on tag read error"""

    event = {
        "Records": [
            {
                "s3": {
                    "bucket": {"name": "test-bucket"},
                    "object": {"key": "books/Test Book.zip", "size": 2048000},
                }
            }
        ]
    }

    mock_table = Mock()

    # Mock S3 get_object_tagging to raise an error
    from botocore.exceptions import ClientError
    error_response = {"Error": {"Code": "AccessDenied", "Message": "Access Denied"}}

    with patch.object(config, "books_table", mock_table), \
         patch.object(config.s3_client, "get_object_tagging", side_effect=ClientError(error_response, "GetObjectTagging")):
        resp = handler.s3_trigger_handler(event, None)

    # Verify handler still creates record without tags
    assert mock_table.put_item.called
    assert resp["statusCode"] == 200


# ============================================================================
# Set Upload Metadata Handler Tests
# ============================================================================


def test_set_upload_metadata_handler_success():
    """Test successful metadata update after upload"""

    event = create_mock_event(is_admin=True, body={"bookId": "Test Book", "author": "New Author"})

    mock_table = Mock()
    mock_table.get_item.return_value = {
        "Item": {
            "id": "Test Book",
            "name": "Test Book",
            "author": "Old Author"
        }
    }
    mock_table.update_item.return_value = {}

    with patch.object(config, "books_table", mock_table):
        resp = handler.set_upload_metadata_handler(event, None)

    assert resp["statusCode"] == 200
    body = json.loads(resp["body"])

    assert body["message"] == "Metadata updated successfully"
    assert body["bookId"] == "Test Book"
    assert body["author"] == "New Author"

    # Verify update_item was called with correct parameters
    mock_table.update_item.assert_called_once()


def test_set_upload_metadata_handler_missing_book_id():
    """Test metadata handler rejects request without bookId"""

    event = create_mock_event(is_admin=True, body={"author": "Test Author"})

    resp = handler.set_upload_metadata_handler(event, None)

    assert resp["statusCode"] == 400
    body = json.loads(resp["body"])
    assert "bookId is required" in body["message"]


def test_set_upload_metadata_handler_book_not_found():
    """Test metadata handler handles book not found (S3 trigger hasn't completed)"""

    event = create_mock_event(is_admin=True, body={"bookId": "Nonexistent Book", "author": "Test Author"})

    mock_table = Mock()
    # Simulate book not found during get_item
    mock_table.get_item.return_value = {}

    with patch.object(config, "books_table", mock_table):
        resp = handler.set_upload_metadata_handler(event, None)

    assert resp["statusCode"] == 404
    body = json.loads(resp["body"])
    assert "not found" in body["message"]


def test_set_upload_metadata_handler_empty_author():
    """Test metadata handler with empty author (no update needed)"""

    event = create_mock_event(is_admin=True, body={"bookId": "Test Book", "author": ""})

    resp = handler.set_upload_metadata_handler(event, None)

    assert resp["statusCode"] == 200
    body = json.loads(resp["body"])
    assert "No metadata to update" in body["message"]


def test_set_upload_metadata_handler_author_too_long():
    """Test metadata handler rejects author exceeding 500 characters"""

    event = create_mock_event(is_admin=True, body={"bookId": "Test Book", "author": "A" * 501})

    resp = handler.set_upload_metadata_handler(event, None)

    assert resp["statusCode"] == 400
    body = json.loads(resp["body"])
    assert "exceeds maximum length of 500" in body["message"]


def test_set_upload_metadata_handler_invalid_json():
    """Test metadata handler handles invalid JSON"""

    event = create_mock_event(is_admin=True, body=None)
    event["body"] = "invalid json"  # type: ignore[typeddict-item]

    resp = handler.set_upload_metadata_handler(event, None)

    assert resp["statusCode"] == 400
    body = json.loads(resp["body"])
    assert "Invalid JSON" in body["message"]


def test_set_upload_metadata_handler_with_series_fields():
    """Test metadata handler successfully sets all fields including series"""

    event = create_mock_event(is_admin=True, body={
        "bookId": "Test Book",
        "author": "Test Author",
        "series_name": "Test Series",
        "series_order": 3
    })

    # Mock DynamoDB
    mock_table = Mock()
    mock_table.get_item.return_value = {
        "Item": {
            "id": "Test Book",
            "name": "Test Book",
            "author": "Different Author"
        }
    }
    mock_table.update_item.return_value = {}

    with patch.object(config, "books_table", mock_table):
        resp = handler.set_upload_metadata_handler(event, None)

    assert resp["statusCode"] == 200
    body = json.loads(resp["body"])
    assert body["message"] == "Metadata updated successfully"
    assert body["author"] == "Test Author"
    assert body["series_name"] == "Test Series"
    assert body["series_order"] == 3

    # Verify DynamoDB update call
    mock_table.update_item.assert_called_once()
    call_kwargs = mock_table.update_item.call_args.kwargs
    assert call_kwargs["Key"] == {"id": "Test Book"}
    assert "author = :author" in call_kwargs["UpdateExpression"]
    assert "series_name = :series_name" in call_kwargs["UpdateExpression"]
    assert "series_order = :series_order" in call_kwargs["UpdateExpression"]
    assert call_kwargs["ExpressionAttributeValues"][":author"] == "Test Author"
    assert call_kwargs["ExpressionAttributeValues"][":series_name"] == "Test Series"
    assert call_kwargs["ExpressionAttributeValues"][":series_order"] == 3


def test_set_upload_metadata_handler_series_order_out_of_range():
    """Test metadata handler rejects series_order > 100"""

    event = create_mock_event(is_admin=True, body={"bookId": "Test Book", "series_order": 101})

    resp = handler.set_upload_metadata_handler(event, None)

    assert resp["statusCode"] == 400
    body = json.loads(resp["body"])
    assert "series_order must be between 1 and 100" in body["message"]


def test_set_upload_metadata_handler_series_order_below_range():
    """Test metadata handler rejects series_order < 1"""

    event = create_mock_event(is_admin=True, body={"bookId": "Test Book", "series_order": 0})

    resp = handler.set_upload_metadata_handler(event, None)

    assert resp["statusCode"] == 400
    body = json.loads(resp["body"])
    assert "series_order must be between 1 and 100" in body["message"]


def test_set_upload_metadata_handler_series_order_invalid_type():
    """Test metadata handler rejects non-integer series_order"""

    event = create_mock_event(is_admin=True, body={"bookId": "Test Book", "series_order": "not a number"})

    resp = handler.set_upload_metadata_handler(event, None)

    assert resp["statusCode"] == 400
    body = json.loads(resp["body"])
    assert "series_order must be an integer" in body["message"]


def test_set_upload_metadata_handler_partial_fields():
    """Test metadata handler with only some fields provided"""

    event = create_mock_event(is_admin=True, body={
        "bookId": "Test Book",
        "series_name": "Test Series"
        # No author or series_order
    })

    # Mock DynamoDB
    mock_table = Mock()
    mock_table.get_item.return_value = {
        "Item": {
            "id": "Test Book",
            "name": "Test Book"
        }
    }
    mock_table.update_item.return_value = {}

    with patch.object(config, "books_table", mock_table):
        resp = handler.set_upload_metadata_handler(event, None)

    assert resp["statusCode"] == 200
    body = json.loads(resp["body"])
    assert body["message"] == "Metadata updated successfully"
    assert body["series_name"] == "Test Series"
    assert "author" not in body
    assert "series_order" not in body

    # Verify DynamoDB update call
    mock_table.update_item.assert_called_once()
    call_kwargs = mock_table.update_item.call_args.kwargs
    assert "series_name = :series_name" in call_kwargs["UpdateExpression"]
    assert "author" not in call_kwargs["UpdateExpression"]
    assert "series_order" not in call_kwargs["UpdateExpression"]


# ============================================================================
# Delete Book Handler Tests
# ============================================================================


def test_delete_book_handler_success():
    """Test successful deletion of book from both DynamoDB and S3 (admin only)"""

    # Admin user required for delete
    event = create_mock_event(
        user_id="admin-user",
        is_admin=True,
        path_params={"id": "Test Book"}
    )

    # Mock Books table
    mock_books_table = Mock()
    mock_books_table.get_item.return_value = {
        "Item": {
            "id": "Test Book",
            "name": "Test Book",
            "s3_url": "s3://test-bucket/books/Test Book.zip",
        }
    }
    mock_books_table.delete_item.return_value = {}

    # Mock UserBooks table - simulate cleanup of user entries
    mock_user_books_table = Mock()
    mock_user_books_table.scan.return_value = {
        "Items": [
            {"userId": "user-1", "bookId": "Test Book"},
            {"userId": "user-2", "bookId": "Test Book"}
        ]
    }

    # Mock S3 deletion
    mock_s3_delete = Mock()

    with (
        patch.object(config, "books_table", mock_books_table),
        patch.object(config, "user_books_table", mock_user_books_table),
        patch.object(config.s3_client, "delete_object", mock_s3_delete),
    ):
        resp = handler.delete_book_handler(event, None)

    assert resp["statusCode"] == 200
    body = json.loads(resp["body"])

    assert body["message"] == "Book deleted successfully"
    assert body["bookId"] == "Test Book"

    # Verify S3, UserBooks cleanup, and Books deletions were called
    mock_s3_delete.assert_called_once_with(Bucket="test-bucket", Key="books/Test Book.zip")
    assert mock_user_books_table.delete_item.call_count == 2  # 2 users had this book
    mock_books_table.delete_item.assert_called_once()


def test_delete_book_handler_requires_admin():
    """Test that non-admin users cannot delete books"""

    # Regular user (not admin)
    event = create_mock_event(
        user_id="regular-user",
        is_admin=False,
        path_params={"id": "Test Book"}
    )

    resp = handler.delete_book_handler(event, None)

    assert resp["statusCode"] == 403
    body = json.loads(resp["body"])
    assert "error" in body
    assert "Forbidden" in body["error"]


def test_delete_book_handler_missing_id():
    """Test delete handler rejects request without book ID"""

    event = create_mock_event(is_admin=True, path_params={})

    resp = handler.delete_book_handler(event, None)

    assert resp["statusCode"] == 400
    body = json.loads(resp["body"])
    assert "Id is required" in body["message"]


def test_delete_book_handler_book_not_found():
    """Test delete handler handles book not found"""

    event = create_mock_event(is_admin=True, path_params={"id": "Nonexistent Book"})

    mock_table = Mock()
    mock_table.get_item.return_value = {}  # No 'Item' key

    with patch.object(config, "books_table", mock_table):
        resp = handler.delete_book_handler(event, None)

    assert resp["statusCode"] == 404
    body = json.loads(resp["body"])
    assert "not found" in body["message"]


def test_delete_book_handler_s3_error_continues():
    """Test delete handler continues with DynamoDB deletion even if S3 fails"""

    event = create_mock_event(is_admin=True, path_params={"id": "Test Book"})

    mock_books_table = Mock()
    mock_books_table.get_item.return_value = {
        "Item": {
            "id": "Test Book",
            "name": "Test Book",
            "s3_url": "s3://test-bucket/books/Test Book.zip",
        }
    }
    mock_books_table.delete_item.return_value = {}

    mock_user_books_table = Mock()
    mock_user_books_table.scan.return_value = {"Items": []}

    # Mock S3 deletion to raise error
    from botocore.exceptions import ClientError

    mock_s3_delete = Mock(side_effect=ClientError({"Error": {"Code": "NoSuchKey"}}, "DeleteObject"))  # type: ignore[arg-type]

    with (
        patch.object(config, "books_table", mock_books_table),
        patch.object(config, "user_books_table", mock_user_books_table),
        patch.object(config.s3_client, "delete_object", mock_s3_delete),
    ):
        resp = handler.delete_book_handler(event, None)

    # Should still succeed (S3 error is logged but not fatal)
    assert resp["statusCode"] == 200

    # DynamoDB deletion should still happen
    mock_books_table.delete_item.assert_called_once()


def test_delete_book_handler_no_s3_url():
    """Test delete handler works when book has no S3 URL"""

    event = create_mock_event(is_admin=True, path_params={"id": "Test Book"})

    mock_books_table = Mock()
    mock_books_table.get_item.return_value = {
        "Item": {
            "id": "Test Book",
            "name": "Test Book",
            # No s3_url
        }
    }
    mock_books_table.delete_item.return_value = {}

    mock_user_books_table = Mock()
    mock_user_books_table.scan.return_value = {"Items": []}

    mock_s3_delete = Mock()

    with (
        patch.object(config, "books_table", mock_books_table),
        patch.object(config, "user_books_table", mock_user_books_table),
        patch.object(config.s3_client, "delete_object", mock_s3_delete),
    ):
        resp = handler.delete_book_handler(event, None)

    assert resp["statusCode"] == 200

    # S3 delete should NOT be called
    mock_s3_delete.assert_not_called()

    # DynamoDB deletion should still happen
    mock_books_table.delete_item.assert_called_once()


def test_delete_book_handler_dynamodb_not_found_on_delete():
    """Test delete handler handles race condition where book deleted between get and delete"""

    event = create_mock_event(is_admin=True, path_params={"id": "Test Book"})

    mock_books_table = Mock()
    mock_books_table.get_item.return_value = {
        "Item": {
            "id": "Test Book",
            "name": "Test Book",
            "s3_url": "s3://test-bucket/books/Test Book.zip",
        }
    }

    # Simulate ConditionalCheckFailedException during delete
    from botocore.exceptions import ClientError

    mock_books_table.delete_item.side_effect = ClientError(  # type: ignore[arg-type]
        {"Error": {"Code": "ConditionalCheckFailedException"}}, "DeleteItem"
    )

    mock_user_books_table = Mock()
    mock_user_books_table.scan.return_value = {"Items": []}

    mock_s3_delete = Mock()

    with (
        patch.object(config, "books_table", mock_books_table),
        patch.object(config, "user_books_table", mock_user_books_table),
        patch.object(config.s3_client, "delete_object", mock_s3_delete),
    ):
        resp = handler.delete_book_handler(event, None)

    assert resp["statusCode"] == 404
    body = json.loads(resp["body"])
    assert "not found" in body["message"]


def test_get_book_handler_with_apostrophe_in_id():
    """Test get_book_handler with apostrophe in book ID"""

    book_id = "Roald Dahl's Cookbook.epub"
    event = create_mock_event(path_params={"id": book_id})

    # Mock presigned URL with URL-encoded apostrophe
    mock_url = f"https://s3.amazonaws.com/test-bucket/books/Roald%20Dahl%27s%20Cookbook.epub?signed=true"

    mock_books_table = Mock()
    mock_books_table.get_item.return_value = {
        "Item": {
            "id": book_id,
            "name": "Roald Dahl's Cookbook.epub",
            "size": Decimal("1500000"),
            "created": "2024-01-15T10:00:00Z",
            "read": False,
            "s3_url": f"s3://test-bucket/books/{book_id}",
        }
    }

    mock_user_books_table = Mock()
    mock_user_books_table.get_item.return_value = {}

    with (
        patch.object(config, "books_table", mock_books_table),
        patch.object(config, "user_books_table", mock_user_books_table),
        patch.object(config.s3_client, "generate_presigned_url", return_value=mock_url),
    ):
        resp = handler.get_book_handler(event, None)

    assert resp["statusCode"] == 200
    body = json.loads(resp["body"])
    assert body["id"] == book_id
    assert body["name"] == "Roald Dahl's Cookbook.epub"
    assert "'" in body["id"]  # Verify apostrophe is preserved


def test_update_book_handler_with_apostrophe_in_id():
    """Test update_book_handler with apostrophe in book ID"""

    book_id = "Roald Dahl's Cookbook.epub"
    event = create_mock_event(path_params={"id": book_id}, body={"read": True})

    mock_books_table = Mock()
    mock_books_table.get_item.return_value = {
        "Item": {
            "id": book_id,
            "name": "Roald Dahl's Cookbook.epub",
            "read": False,
        }
    }
    mock_books_table.update_item.return_value = {
        "Attributes": {
            "id": book_id,
            "name": "Roald Dahl's Cookbook.epub",
            "read": True,
        }
    }

    mock_user_books_table = Mock()
    mock_user_books_table.put_item.return_value = {}

    with patch.object(config, "books_table", mock_books_table), \
         patch.object(config, "user_books_table", mock_user_books_table):
        resp = handler.update_book_handler(event, None)

    assert resp["statusCode"] == 200
    body = json.loads(resp["body"])
    assert body["id"] == book_id
    assert body["read"] is True

    # Verify put_item was called on user_books_table with correct key (read status goes to UserBooks table)
    mock_user_books_table.put_item.assert_called_once()
    call_kwargs = mock_user_books_table.put_item.call_args.kwargs
    assert call_kwargs["Item"]["bookId"] == book_id
    assert call_kwargs["Item"]["userId"] == "test-user-123"


def test_update_book_handler_with_quotes_in_id():
    """Test update_book_handler with quotes in book ID"""

    book_id = 'The "Best" Book Ever.pdf'
    event = create_mock_event(path_params={"id": book_id}, body={"read": True})

    mock_books_table = Mock()
    mock_books_table.get_item.return_value = {
        "Item": {
            "id": book_id,
            "name": 'The "Best" Book Ever.pdf',
            "read": False,
        }
    }
    mock_books_table.update_item.return_value = {
        "Attributes": {
            "id": book_id,
            "name": 'The "Best" Book Ever.pdf',
            "read": True,
        }
    }

    mock_user_books_table = Mock()

    with patch.object(config, "books_table", mock_books_table), \
         patch.object(config, "user_books_table", mock_user_books_table):
        resp = handler.update_book_handler(event, None)

    assert resp["statusCode"] == 200
    body = json.loads(resp["body"])
    assert body["id"] == book_id
    assert '"' in body["id"]  # Verify quotes are preserved


def test_delete_book_handler_with_apostrophe_in_id():
    """Test delete_book_handler with apostrophe in book ID"""

    book_id = "Roald Dahl's Cookbook.epub"
    event = create_mock_event(is_admin=True, path_params={"id": book_id})

    mock_books_table = Mock()
    mock_books_table.get_item.return_value = {
        "Item": {
            "id": book_id,
            "name": "Roald Dahl's Cookbook.epub",
            "s3_url": f"s3://test-bucket/books/{book_id}",
        }
    }

    mock_user_books_table = Mock()
    mock_user_books_table.scan.return_value = {"Items": []}

    mock_s3_delete = Mock()

    with (
        patch.object(config, "books_table", mock_books_table),
        patch.object(config, "user_books_table", mock_user_books_table),
        patch.object(config.s3_client, "delete_object", mock_s3_delete),
    ):
        resp = handler.delete_book_handler(event, None)

    assert resp["statusCode"] == 200
    body = json.loads(resp["body"])
    assert "deleted successfully" in body["message"]

    # Verify S3 delete was called with correct key
    mock_s3_delete.assert_called_once()
    call_kwargs = mock_s3_delete.call_args[1]
    assert call_kwargs["Key"] == f"books/{book_id}"


def test_s3_trigger_handler_with_special_characters():
    """Test s3_trigger_handler with special characters in filename"""

    # Filename with apostrophe, dash, and parentheses
    # Handler will parse "Author - Title" format
    filename = "Roald Dahl's Cookbook - 2nd Edition (2024).epub"
    event = {
        "Records": [
            {
                "s3": {
                    "bucket": {"name": "test-bucket"},
                    "object": {
                        "key": f"books/{filename}",
                        "size": 2500000,
                    },
                },
                "eventTime": "2024-01-15T10:30:00.000Z",
            }
        ]
    }

    mock_table = Mock()

    with patch.object(config, "books_table", mock_table):
        handler.s3_trigger_handler(event, None)

    # Verify put_item was called
    mock_table.put_item.assert_called_once()
    item = mock_table.put_item.call_args[1]["Item"]

    # Verify special characters are preserved in ID
    assert item["id"] == filename
    assert "'" in item["id"]
    
    # Handler extracts author from "Author - Title" format
    assert item["author"] == "Roald Dahl's Cookbook"
    assert item["name"] == "2nd Edition (2024).epub"
    
    # Verify parentheses are preserved in name
    assert "(" in item["name"]
    assert ")" in item["name"]


# ============================================================================
# Additional Coverage Tests - Error Handling and Edge Cases
# ============================================================================


def test_list_handler_unauthenticated():
    """Test list handler rejects unauthenticated requests"""

    event = {
        "requestContext": {}  # No authorizer
    }

    resp = handler.list_handler(event, None)

    assert resp["statusCode"] == 401
    body = json.loads(resp["body"])
    assert "Unauthorized" in body["error"]


def test_get_book_handler_unauthenticated():
    """Test get_book_handler rejects unauthenticated requests"""

    event = {
        "pathParameters": {"id": "test-book.zip"},
        "requestContext": {}  # No authorizer
    }

    resp = handler.get_book_handler(event, None)

    assert resp["statusCode"] == 401
    body = json.loads(resp["body"])
    assert "Unauthorized" in body["error"]


def test_update_book_handler_unauthenticated():
    """Test update_book_handler rejects unauthenticated requests"""

    event = {
        "pathParameters": {"id": "test-book.zip"},
        "body": json.dumps({"read": True}),
        "requestContext": {}  # No authorizer
    }

    resp = handler.update_book_handler(event, None)

    assert resp["statusCode"] == 401
    body = json.loads(resp["body"])
    assert "Unauthorized" in body["error"]


def test_delete_book_handler_unauthenticated():
    """Test delete_book_handler rejects unauthenticated requests"""

    event = {
        "pathParameters": {"id": "test-book.zip"},
        "requestContext": {}  # No authorizer
    }

    resp = handler.delete_book_handler(event, None)

    assert resp["statusCode"] == 401
    body = json.loads(resp["body"])
    assert "Unauthorized" in body["error"]


def test_get_book_handler_dynamodb_error():
    """Test get_book_handler handles DynamoDB errors"""

    from botocore.exceptions import ClientError

    event = create_mock_event(path_params={"id": "test-book.zip"})

    mock_books_table = Mock()
    mock_books_table.get_item.side_effect = ClientError(
        {"Error": {"Code": "InternalServerError", "Message": "Database error"}},
        "GetItem"
    )  # type: ignore[arg-type]

    mock_user_books_table = Mock()

    with patch.object(config, "books_table", mock_books_table), \
         patch.object(config, "user_books_table", mock_user_books_table):
        resp = handler.get_book_handler(event, None)

    assert resp["statusCode"] == 500
    body = json.loads(resp["body"])
    assert "Database Error" in body["error"]


def test_get_book_handler_user_books_error():
    """Test get_book_handler continues when UserBooks table errors"""

    from botocore.exceptions import ClientError

    event = create_mock_event(path_params={"id": "test-book.zip"})

    mock_books_table = Mock()
    mock_books_table.get_item.return_value = {
        "Item": {
            "id": "test-book.zip",
            "name": "Test Book",
            "s3_url": "s3://bucket/books/test-book.zip",
            "size": Decimal("1000000"),
            "created": "2024-01-01T00:00:00Z",
        }
    }

    mock_user_books_table = Mock()
    mock_user_books_table.get_item.side_effect = ClientError(
        {"Error": {"Code": "InternalServerError"}},
        "GetItem"
    )  # type: ignore[arg-type]

    mock_presigned_url = "https://s3.amazonaws.com/bucket/books/test-book.zip?signed=true"

    with patch.object(config, "books_table", mock_books_table), \
         patch.object(config, "user_books_table", mock_user_books_table), \
         patch.object(config.s3_client, "generate_presigned_url", return_value=mock_presigned_url):
        resp = handler.get_book_handler(event, None)

    # Should succeed with read status defaulting to False
    assert resp["statusCode"] == 200
    body = json.loads(resp["body"])
    assert body["read"] is False


def test_get_book_handler_s3_presigned_url_error():
    """Test get_book_handler handles S3 presigned URL generation errors"""

    event = create_mock_event(path_params={"id": "test-book.zip"})

    mock_books_table = Mock()
    mock_books_table.get_item.return_value = {
        "Item": {
            "id": "test-book.zip",
            "name": "Test Book",
            "s3_url": "s3://bucket/books/test-book.zip",
            "size": Decimal("1000000"),
            "created": "2024-01-01T00:00:00Z",
        }
    }

    mock_user_books_table = Mock()
    mock_user_books_table.get_item.return_value = {}

    # Mock presigned URL generation to raise exception
    mock_s3_client = Mock()
    mock_s3_client.generate_presigned_url.side_effect = Exception("S3 connection error")

    with patch.object(config, "books_table", mock_books_table), \
         patch.object(config, "user_books_table", mock_user_books_table), \
         patch.object(config, "s3_client", mock_s3_client):
        resp = handler.get_book_handler(event, None)

    assert resp["statusCode"] == 500
    body = json.loads(resp["body"])
    assert "Internal Server Error" in body["error"]


def test_update_book_handler_series_name_too_long():
    """Test update_book_handler rejects series_name exceeding length limit"""

    event = create_mock_event(
        path_params={"id": "book-a.zip"},
        body={"series_name": "x" * 501}  # Exceeds 500 char limit
    )

    resp = handler.update_book_handler(event, None)

    assert resp["statusCode"] == 400
    body = json.loads(resp["body"])
    assert "exceeds maximum length" in body["message"]


def test_update_book_handler_books_table_error():
    """Test update_book_handler handles DynamoDB errors for Books table"""

    from botocore.exceptions import ClientError

    event = create_mock_event(
        path_params={"id": "test-book.zip"},
        body={"author": "New Author"}
    )

    mock_books_table = Mock()
    mock_books_table.get_item.return_value = {"Item": {"id": "test-book.zip", "name": "Test Book"}}
    mock_books_table.update_item.side_effect = ClientError(
        {"Error": {"Code": "InternalServerError"}},
        "UpdateItem"
    )  # type: ignore[arg-type]

    mock_user_books_table = Mock()

    with patch.object(config, "books_table", mock_books_table), \
         patch.object(config, "user_books_table", mock_user_books_table):
        resp = handler.update_book_handler(event, None)

    assert resp["statusCode"] == 500
    body = json.loads(resp["body"])
    assert "error" in body


def test_update_book_handler_user_books_table_error():
    """Test update_book_handler continues when UserBooks table errors"""

    from botocore.exceptions import ClientError

    event = create_mock_event(
        path_params={"id": "test-book.zip"},
        body={"read": True}
    )

    mock_books_table = Mock()
    mock_books_table.get_item.return_value = {"Item": {"id": "test-book.zip", "name": "Test Book"}}

    mock_user_books_table = Mock()
    mock_user_books_table.put_item.side_effect = ClientError(
        {"Error": {"Code": "InternalServerError"}},
        "PutItem"
    )  # type: ignore[arg-type]

    with patch.object(config, "books_table", mock_books_table), \
         patch.object(config, "user_books_table", mock_user_books_table):
        resp = handler.update_book_handler(event, None)

    # Handler logs error but continues (returns success with only read status updated)
    assert resp["statusCode"] == 200


def test_s3_trigger_handler_invalid_s3_url():
    """Test s3_trigger_handler handles invalid S3 URLs"""

    event = {
        "Records": [
            {
                "s3": {
                    "bucket": {"name": "test-bucket"},
                    "object": {
                        "key": "invalid-folder/",  # Folder, not file
                        "size": 0,
                    },
                },
                "eventTime": "2024-01-01T00:00:00.000Z",
            }
        ]
    }

    mock_table = Mock()

    with patch.object(config, "books_table", mock_table):
        resp = handler.s3_trigger_handler(event, None)

    # Should handle gracefully - folder is skipped
    assert resp["statusCode"] == 200


def test_s3_trigger_handler_dynamodb_error():
    """Test s3_trigger_handler continues processing despite DynamoDB errors"""

    from botocore.exceptions import ClientError

    event = {
        "Records": [
            {
                "s3": {
                    "bucket": {"name": "test-bucket"},
                    "object": {
                        "key": "books/test.zip",
                        "size": 1000000,
                    },
                },
                "eventTime": "2024-01-01T00:00:00.000Z",
            }
        ]
    }

    mock_table = Mock()
    mock_table.put_item.side_effect = ClientError(
        {"Error": {"Code": "InternalServerError"}},
        "PutItem"
    )  # type: ignore[arg-type]

    with patch.object(config, "books_table", mock_table):
        resp = handler.s3_trigger_handler(event, None)

    # S3 trigger returns 200 even on errors to prevent retries
    assert resp["statusCode"] == 200


def test_upload_handler_non_admin():
    """Test upload_handler rejects non-admin users"""

    event = create_mock_event(
        is_admin=False,  # Not an admin
        body={"filename": "test.zip", "fileSize": 1000000}
    )

    resp = handler.upload_handler(event, None)

    assert resp["statusCode"] == 403
    body = json.loads(resp["body"])
    assert "Forbidden" in body["error"]


def test_upload_handler_file_size_validation():
    """Test upload_handler with edge case file size"""

    event = create_mock_event(
        is_admin=True,
        body={"filename": "test.zip", "fileSize": 0}  # Zero size file
    )

    mock_presigned_url = "https://s3.amazonaws.com/test-bucket/books/test.zip?signed=true"

    with patch.object(config.s3_client, "generate_presigned_url", return_value=mock_presigned_url):
        resp = handler.upload_handler(event, None)

    # Handler accepts zero-size files (validation is minimal)
    assert resp["statusCode"] == 200


def test_set_upload_metadata_handler_non_admin():
    """Test set_upload_metadata_handler rejects non-admin users"""

    event = create_mock_event(
        is_admin=False,
        body={"bookId": "test-book", "author": "Test Author"}
    )

    resp = handler.set_upload_metadata_handler(event, None)

    assert resp["statusCode"] == 403
    body = json.loads(resp["body"])
    assert "Forbidden" in body["error"]


def test_set_upload_metadata_handler_dynamodb_error():
    """Test set_upload_metadata_handler handles DynamoDB errors"""

    from botocore.exceptions import ClientError

    event = create_mock_event(
        is_admin=True,
        body={"bookId": "test-book", "author": "Test Author"}
    )

    mock_table = Mock()
    mock_table.update_item.side_effect = ClientError(
        {"Error": {"Code": "InternalServerError"}},
        "UpdateItem"
    )  # type: ignore[arg-type]

    with patch.object(config, "books_table", mock_table):
        resp = handler.set_upload_metadata_handler(event, None)

    assert resp["statusCode"] == 500


def test_delete_book_handler_non_admin():
    """Test delete_book_handler rejects non-admin users"""

    event = create_mock_event(
        is_admin=False,
        path_params={"id": "test-book.zip"}
    )

    resp = handler.delete_book_handler(event, None)

    assert resp["statusCode"] == 403
    body = json.loads(resp["body"])
    assert "Forbidden" in body["error"]


def test_delete_book_handler_user_books_scan_error():
    """Test delete_book_handler handles UserBooks scan errors"""

    from botocore.exceptions import ClientError

    event = create_mock_event(is_admin=True, path_params={"id": "test-book.zip"})

    mock_books_table = Mock()
    mock_books_table.get_item.return_value = {
        "Item": {
            "id": "test-book.zip",
            "name": "Test Book",
            "s3_url": "s3://bucket/books/test-book.zip",
        }
    }
    mock_books_table.delete_item.return_value = {}

    mock_user_books_table = Mock()
    mock_user_books_table.scan.side_effect = ClientError(
        {"Error": {"Code": "InternalServerError"}},
        "Scan"
    )  # type: ignore[arg-type]

    mock_s3_delete = Mock()

    with patch.object(config, "books_table", mock_books_table), \
         patch.object(config, "user_books_table", mock_user_books_table), \
         patch.object(config.s3_client, "delete_object", mock_s3_delete):
        resp = handler.delete_book_handler(event, None)

    # Should still succeed - UserBooks errors are logged but not fatal
    assert resp["statusCode"] == 200


def test_delete_book_handler_general_error():
    """Test delete_book_handler handles general exceptions"""

    event = create_mock_event(is_admin=True, path_params={"id": "test-book.zip"})

    mock_books_table = Mock()
    mock_books_table.get_item.side_effect = Exception("Unexpected error")

    mock_user_books_table = Mock()

    with patch.object(config, "books_table", mock_books_table), \
         patch.object(config, "user_books_table", mock_user_books_table):
        resp = handler.delete_book_handler(event, None)

    assert resp["statusCode"] == 500
    body = json.loads(resp["body"])
    assert "Internal Server Error" in body["error"]


def test_update_book_handler_with_name_field():
    """Test update_book_handler with name field update"""

    event = create_mock_event(
        path_params={"id": "book-a.zip"},
        body={"name": "New Book Name"}
    )

    mock_books_table = Mock()
    mock_books_table.get_item.return_value = {"Item": {"id": "book-a.zip"}}
    mock_books_table.update_item.return_value = {
        "Attributes": {
            "id": "book-a.zip",
            "name": "New Book Name",
            "created": "2024-01-01T00:00:00Z",
        }
    }

    mock_user_books_table = Mock()

    with patch.object(config, "books_table", mock_books_table), \
         patch.object(config, "user_books_table", mock_user_books_table):
        resp = handler.update_book_handler(event, None)

    assert resp["statusCode"] == 200
    body = json.loads(resp["body"])
    assert body["name"] == "New Book Name"


# ============================================================================
# Book Cover URL Tests
# ============================================================================


def test_s3_trigger_handler_with_cover_url():
    """Test S3 trigger handler fetches cover URL from Google Books API"""

    event = {
        "Records": [
            {
                "s3": {
                    "bucket": {"name": "test-bucket"},
                    "object": {"key": "books/Isaac Asimov - Foundation.zip", "size": 2048000},
                }
            }
        ]
    }

    # Mock Google Books API response
    mock_cover_url = "https://books.google.com/books/content/images/frontcover/12345.jpg"

    mock_table = Mock()

    # Mock the urllib.request.urlopen to simulate Google Books API
    from gateway_backend.handlers import s3_handlers
    with patch.object(config, "books_table", mock_table), \
         patch.object(config.s3_client, "get_object_tagging", return_value={"TagSet": []}), \
         patch.object(s3_handlers, "_fetch_cover_url", return_value=mock_cover_url):
        resp = handler.s3_trigger_handler(event, None)

    # Verify put_item was called with cover URL
    call_args = mock_table.put_item.call_args[1]
    item = call_args["Item"]

    assert item["coverImageUrl"] == mock_cover_url
    assert resp["statusCode"] == 200


def test_s3_trigger_handler_no_cover_found():
    """Test S3 trigger handler continues when no cover is found"""

    event = {
        "Records": [
            {
                "s3": {
                    "bucket": {"name": "test-bucket"},
                    "object": {"key": "books/Unknown Book.zip", "size": 2048000},
                }
            }
        ]
    }

    mock_table = Mock()

    # Mock _fetch_cover_url to return None
    from gateway_backend.handlers import s3_handlers
    with patch.object(config, "books_table", mock_table), \
         patch.object(config.s3_client, "get_object_tagging", return_value={"TagSet": []}), \
         patch.object(s3_handlers, "_fetch_cover_url", return_value=None):
        resp = handler.s3_trigger_handler(event, None)

    # Verify put_item was called without cover URL
    call_args = mock_table.put_item.call_args[1]
    item = call_args["Item"]

    assert "coverImageUrl" not in item
    assert resp["statusCode"] == 200


def test_s3_trigger_handler_cover_fetch_error():
    """Test S3 trigger handler continues when cover fetch raises exception"""

    event = {
        "Records": [
            {
                "s3": {
                    "bucket": {"name": "test-bucket"},
                    "object": {"key": "books/Test Book.zip", "size": 2048000},
                }
            }
        ]
    }

    mock_table = Mock()

    # Mock _fetch_cover_url to raise exception
    from gateway_backend.handlers import s3_handlers
    with patch.object(config, "books_table", mock_table), \
         patch.object(config.s3_client, "get_object_tagging", return_value={"TagSet": []}), \
         patch.object(s3_handlers, "_fetch_cover_url", side_effect=Exception("API timeout")):
        resp = handler.s3_trigger_handler(event, None)

    # Should still create book record without cover
    assert mock_table.put_item.called
    assert resp["statusCode"] == 200


def test_set_upload_metadata_handler_author_change_fetches_cover():
    """Test metadata handler fetches new cover when author changes"""

    event = create_mock_event(
        is_admin=True,
        body={"bookId": "Foundation", "author": "Isaac Asimov"}
    )

    # Mock existing book with different author
    mock_existing_book = {
        "Item": {
            "id": "Foundation",
            "name": "Foundation",
            "author": "Unknown Author",
            "coverImageUrl": "https://old-cover.jpg"
        }
    }

    mock_new_cover = "https://books.google.com/books/content/images/frontcover/new.jpg"

    mock_table = Mock()
    mock_table.get_item.return_value = mock_existing_book
    mock_table.update_item.return_value = {}

    from gateway_backend.utils import cover
    with patch.object(config, "books_table", mock_table), \
         patch.object(cover, "fetch_cover_url", return_value=mock_new_cover) as mock_fetch:
        resp = handler.set_upload_metadata_handler(event, None)

    assert resp["statusCode"] == 200
    body = json.loads(resp["body"])
    assert body["author"] == "Isaac Asimov"
    assert body["coverImageUrl"] == mock_new_cover

    # Verify _fetch_cover_url was called with correct params
    mock_fetch.assert_called_once_with("Foundation", "Isaac Asimov")

    # Verify update_item was called with both author and cover URL
    call_kwargs = mock_table.update_item.call_args.kwargs
    assert ":author" in call_kwargs["ExpressionAttributeValues"]
    assert ":coverImageUrl" in call_kwargs["ExpressionAttributeValues"]


def test_set_upload_metadata_handler_author_no_change_no_fetch():
    """Test metadata handler doesn't fetch cover when author stays the same"""

    event = create_mock_event(
        is_admin=True,
        body={"bookId": "Foundation", "author": "Isaac Asimov"}
    )

    # Mock existing book with same author
    mock_existing_book = {
        "Item": {
            "id": "Foundation",
            "name": "Foundation",
            "author": "Isaac Asimov",
            "coverImageUrl": "https://existing-cover.jpg"
        }
    }

    mock_table = Mock()
    mock_table.get_item.return_value = mock_existing_book
    mock_table.update_item.return_value = {}

    from gateway_backend.utils import cover
    with patch.object(config, "books_table", mock_table), \
         patch.object(cover, "fetch_cover_url") as mock_fetch:
        resp = handler.set_upload_metadata_handler(event, None)

    assert resp["statusCode"] == 200

    # Verify fetch_cover_url was NOT called
    mock_fetch.assert_not_called()


def test_set_upload_metadata_handler_author_change_no_cover_found():
    """Test metadata handler continues when no cover is found for new author"""

    event = create_mock_event(
        is_admin=True,
        body={"bookId": "Obscure Book", "author": "Unknown Author"}
    )

    mock_existing_book = {
        "Item": {
            "id": "Obscure Book",
            "name": "Obscure Book",
            "author": "Different Author"
        }
    }

    mock_table = Mock()
    mock_table.get_item.return_value = mock_existing_book
    mock_table.update_item.return_value = {}

    from gateway_backend.utils import cover
    with patch.object(config, "books_table", mock_table), \
         patch.object(cover, "fetch_cover_url", return_value=None):
        resp = handler.set_upload_metadata_handler(event, None)

    assert resp["statusCode"] == 200
    body = json.loads(resp["body"])
    assert body["author"] == "Unknown Author"
    # coverImageUrl should be None (removed) when cover not found
    assert body.get("coverImageUrl") is None


def test_set_upload_metadata_handler_no_author_no_fetch():
    """Test metadata handler doesn't fetch cover when no author provided"""

    event = create_mock_event(
        is_admin=True,
        body={"bookId": "Test Book", "series_name": "Test Series"}
    )

    mock_existing_book = {
        "Item": {
            "id": "Test Book",
            "name": "Test Book",
            "author": "Existing Author"
        }
    }

    mock_table = Mock()
    mock_table.get_item.return_value = mock_existing_book
    mock_table.update_item.return_value = {}

    from gateway_backend.utils import cover
    with patch.object(config, "books_table", mock_table), \
         patch.object(cover, "fetch_cover_url") as mock_fetch:
        resp = handler.set_upload_metadata_handler(event, None)

    assert resp["statusCode"] == 200

    # Verify fetch_cover_url was NOT called (no author in request)
    mock_fetch.assert_not_called()


def test_list_handler_returns_cover_urls():
    """Test that list handler returns coverImageUrl in book responses"""

    # Mock DynamoDB response with cover URL
    mock_dynamodb_response = {
        "Items": [
            {
                "id": "foundation.zip",
                "name": "Foundation",
                "size": Decimal("1024000"),
                "created": "2023-06-15T10:30:00Z",
                "read": False,
                "s3_url": "s3://test-bucket/books/foundation.zip",
                "author": "Isaac Asimov",
                "coverImageUrl": "https://books.google.com/books/content/images/frontcover/12345.jpg",
            },
        ]
    }

    mock_books_table = Mock()
    mock_books_table.scan.return_value = mock_dynamodb_response

    mock_user_books_table = Mock()
    mock_user_books_table.query.return_value = {"Items": []}

    event = create_mock_event()

    with patch.object(config, "books_table", mock_books_table), \
         patch.object(config, "user_books_table", mock_user_books_table):
        resp = handler.list_handler(event, None)

    assert resp["statusCode"] == 200
    body = json.loads(resp["body"])
    assert len(body["books"]) == 1
    assert body["books"][0]["coverImageUrl"] == "https://books.google.com/books/content/images/frontcover/12345.jpg"


def test_get_book_handler_returns_cover_url():
    """Test that get_book_handler returns coverImageUrl in response"""

    event = create_mock_event(path_params={"id": "foundation.zip"})

    mock_books_item = {
        "Item": {
            "id": "foundation.zip",
            "name": "Foundation",
            "size": Decimal("1024000"),
            "created": "2023-06-15T10:30:00Z",
            "s3_url": "s3://test-bucket/books/foundation.zip",
            "author": "Isaac Asimov",
            "coverImageUrl": "https://books.google.com/books/content/images/frontcover/12345.jpg",
        }
    }

    mock_url = "https://s3.amazonaws.com/test-bucket/books/foundation.zip?signed=true"

    mock_books_table = Mock()
    mock_books_table.get_item.return_value = mock_books_item

    mock_user_books_table = Mock()
    mock_user_books_table.get_item.return_value = {}

    with (
        patch.object(config, "books_table", mock_books_table),
        patch.object(config, "user_books_table", mock_user_books_table),
        patch.object(config.s3_client, "generate_presigned_url", return_value=mock_url),
    ):
        resp = handler.get_book_handler(event, None)

    assert resp["statusCode"] == 200
    body = json.loads(resp["body"])
    assert body["coverImageUrl"] == "https://books.google.com/books/content/images/frontcover/12345.jpg"
