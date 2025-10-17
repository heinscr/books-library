from gateway_backend import handler
import json
from unittest.mock import patch, MagicMock
from datetime import datetime


def test_list_handler_returns_books_list():
    """Test that handler returns list of books from S3"""
    
    # Mock S3 response
    mock_s3_response = {
        'Contents': [
            {
                'Key': 'books/',  # Folder itself, should be skipped
                'Size': 0,
                'LastModified': datetime(2020, 1, 1)
            },
            {
                'Key': 'books/Book A.zip',
                'Size': 1024000,
                'LastModified': datetime(2023, 6, 15, 10, 30, 0)
            },
            {
                'Key': 'books/Book B.zip',
                'Size': 2048000,
                'LastModified': datetime(2024, 3, 20, 14, 45, 30)
            },
            {
                'Key': 'books/index.html',  # Non-zip file, should be skipped
                'Size': 5000,
                'LastModified': datetime(2024, 1, 1)
            }
        ]
    }
    
    # Patch the S3 client
    with patch.object(handler.s3_client, 'list_objects_v2', return_value=mock_s3_response):
        resp = handler.list_handler({}, None)
    
    # Verify response
    assert resp["statusCode"] == 200
    body = json.loads(resp["body"])
    
    # Should return 2 books (excluding folder and non-zip file)
    assert len(body) == 2
    
    # Verify first book (sorted by date, most recent first - Book B from 2024)
    assert body[0]["name"] == "Book B.zip"
    assert body[0]["size"] == 2048000
    assert "2024-03-20" in body[0]["lastModified"]
    
    # Verify second book (Book A from 2023)
    assert body[1]["name"] == "Book A.zip"
    assert body[1]["size"] == 1024000
    assert "2023-06-15" in body[1]["lastModified"]


def test_list_handler_empty_bucket():
    """Test handler when S3 bucket is empty"""
    
    # Mock empty S3 response
    mock_s3_response = {}
    
    with patch.object(handler.s3_client, 'list_objects_v2', return_value=mock_s3_response):
        resp = handler.list_handler({}, None)
    
    assert resp["statusCode"] == 200
    body = json.loads(resp["body"])
    assert body == []


def test_list_handler_s3_error():
    """Test handler when S3 throws an error"""
    
    # Mock S3 error
    with patch.object(handler.s3_client, 'list_objects_v2', side_effect=Exception("S3 connection error")):
        resp = handler.list_handler({}, None)
    
    assert resp["statusCode"] == 500
    body = json.loads(resp["body"])
    assert "error" in body
    assert "Failed to list books" in body["error"]


def test_get_book_handler_success():
    """Test that get_book_handler generates presigned URL successfully"""
    
    event = {
        'pathParameters': {
            'id': 'Book A.zip'
        }
    }
    
    # Mock S3 head_object (to check if book exists)
    mock_head = MagicMock()
    
    # Mock presigned URL generation
    mock_url = "https://s3.amazonaws.com/crackpow/books/Book%20A.zip?signed=true"
    
    with patch.object(handler.s3_client, 'head_object', return_value=mock_head), \
         patch.object(handler.s3_client, 'generate_presigned_url', return_value=mock_url):
        resp = handler.get_book_handler(event, None)
    
    assert resp["statusCode"] == 200
    body = json.loads(resp["body"])
    assert body["bookId"] == "Book A.zip"
    assert body["downloadUrl"] == mock_url
    assert body["expiresIn"] == 3600


def test_get_book_handler_missing_id():
    """Test get_book_handler when book ID is missing"""
    
    event = {
        'pathParameters': {}
    }
    
    resp = handler.get_book_handler(event, None)
    
    assert resp["statusCode"] == 400
    body = json.loads(resp["body"])
    assert "error" in body
    assert "Book ID is required" in body["message"]


def test_get_book_handler_invalid_id():
    """Test get_book_handler with path traversal attempt"""
    
    event = {
        'pathParameters': {
            'id': '../../../etc/passwd'
        }
    }
    
    resp = handler.get_book_handler(event, None)
    
    assert resp["statusCode"] == 400
    body = json.loads(resp["body"])
    assert "Invalid book ID" in body["message"]


def test_get_book_handler_not_found():
    """Test get_book_handler when book doesn't exist"""
    
    event = {
        'pathParameters': {
            'id': 'NonExistent.zip'
        }
    }
    
    # Create a mock NoSuchKey exception
    from botocore.exceptions import ClientError
    error_response = {'Error': {'Code': 'NoSuchKey', 'Message': 'The specified key does not exist.'}}
    no_such_key = ClientError(error_response, 'head_object')
    
    with patch.object(handler.s3_client, 'head_object', side_effect=no_such_key):
        resp = handler.get_book_handler(event, None)
    
    assert resp["statusCode"] == 404
    body = json.loads(resp["body"])
    assert "Not Found" in body["error"]


def test_get_book_handler_adds_zip_extension():
    """Test that handler adds .zip extension if missing"""
    
    event = {
        'pathParameters': {
            'id': 'Book A'  # No .zip extension
        }
    }
    
    mock_head = MagicMock()
    mock_url = "https://s3.amazonaws.com/presigned"
    
    with patch.object(handler.s3_client, 'head_object', return_value=mock_head) as mock_head_call, \
         patch.object(handler.s3_client, 'generate_presigned_url', return_value=mock_url):
        resp = handler.get_book_handler(event, None)
    
    # Verify it checked for "Book A.zip"
    mock_head_call.assert_called_once()
    call_args = mock_head_call.call_args
    assert call_args[1]['Key'] == 'books/Book A.zip'
    
    assert resp["statusCode"] == 200
    body = json.loads(resp["body"])
    assert body["bookId"] == "Book A.zip"
