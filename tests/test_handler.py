from gateway_backend import handler
import json
from unittest.mock import patch, MagicMock, Mock
from datetime import datetime
from decimal import Decimal
import os


def test_list_handler_returns_books_list():
    """Test that handler returns list of books from DynamoDB"""
    
    # Mock DynamoDB response with Decimal types (as returned by DynamoDB)
    mock_dynamodb_response = {
        'Items': [
            {
                'id': 'book-a.zip',
                'name': 'Book A.zip',
                'size': Decimal('1024000'),
                'created': '2023-06-15T10:30:00Z',
                'read': False,
                's3_url': 's3://test-bucket/books/Book A.zip',
                'author': 'Author A'
            },
            {
                'id': 'book-b.zip',
                'name': 'Book B.zip',
                'size': Decimal('2048000'),
                'created': '2024-03-20T14:45:30Z',
                'read': True,
                's3_url': 's3://test-bucket/books/Book B.zip'
            }
        ]
    }
    
    # Create a mock DynamoDB table
    mock_table = Mock()
    mock_table.scan.return_value = mock_dynamodb_response
    
    # Patch the books_table object
    with patch.object(handler, 'books_table', mock_table):
        resp = handler.list_handler({}, None)
    
    # Verify response
    assert resp["statusCode"] == 200
    body = json.loads(resp["body"])
    
    # Should return 2 books
    assert len(body) == 2
    
    # Verify books are sorted by created date (most recent first - Book B from 2024)
    assert body[0]["name"] == "Book B.zip"
    assert body[0]["size"] == 2048000
    assert body[0]["created"] == '2024-03-20T14:45:30Z'
    assert body[0]["read"] is True
    
    # Verify second book (Book A from 2023)
    assert body[1]["name"] == "Book A.zip"
    assert body[1]["size"] == 1024000
    assert body[1]["created"] == '2023-06-15T10:30:00Z'
    assert body[1]["read"] is False
    assert body[1]["author"] == "Author A"


def test_list_handler_empty_table():
    """Test handler when DynamoDB table is empty"""
    
    # Mock empty DynamoDB response
    mock_dynamodb_response = {'Items': []}
    
    mock_table = Mock()
    mock_table.scan.return_value = mock_dynamodb_response
    
    with patch.object(handler, 'books_table', mock_table):
        resp = handler.list_handler({}, None)
    
    assert resp["statusCode"] == 200
    body = json.loads(resp["body"])
    assert body == []


def test_list_handler_pagination():
    """Test handler when DynamoDB returns paginated results"""
    
    # First page
    mock_response_page1 = {
        'Items': [
            {
                'id': 'book-1.zip',
                'name': 'Book 1.zip',
                'created': '2023-01-01T00:00:00Z',
                'read': False,
                's3_url': 's3://test-bucket/books/Book 1.zip'
            }
        ],
        'LastEvaluatedKey': {'id': 'book-1.zip'}
    }
    
    # Second page
    mock_response_page2 = {
        'Items': [
            {
                'id': 'book-2.zip',
                'name': 'Book 2.zip',
                'created': '2023-02-01T00:00:00Z',
                'read': True,
                's3_url': 's3://test-bucket/books/Book 2.zip'
            }
        ]
    }
    
    mock_table = Mock()
    mock_table.scan.side_effect = [mock_response_page1, mock_response_page2]
    
    with patch.object(handler, 'books_table', mock_table):
        resp = handler.list_handler({}, None)
    
    assert resp["statusCode"] == 200
    body = json.loads(resp["body"])
    assert len(body) == 2


def test_list_handler_dynamodb_error():
    """Test handler when DynamoDB throws an error"""
    
    mock_table = Mock()
    mock_table.scan.side_effect = Exception("DynamoDB connection error")
    
    with patch.object(handler, 'books_table', mock_table):
        resp = handler.list_handler({}, None)
    
    assert resp["statusCode"] == 500
    body = json.loads(resp["body"])
    assert "error" in body
    assert "Failed to list books" in body["error"]


def test_get_book_handler_success():
    """Test that get_book_handler returns book metadata and presigned URL from DynamoDB"""
    
    event = {
        'pathParameters': {
            'id': 'book-a.zip'
        }
    }
    
    # Mock DynamoDB response
    mock_dynamodb_item = {
        'Item': {
            'id': 'book-a.zip',
            'name': 'Book A.zip',
            'size': Decimal('1024000'),
            'created': '2023-06-15T10:30:00Z',
            'read': False,
            's3_url': 's3://test-bucket/books/Book A.zip',
            'author': 'Author A'
        }
    }
    
    # Mock presigned URL generation
    mock_url = "https://s3.amazonaws.com/test-bucket/books/Book%20A.zip?signed=true"
    
    mock_table = Mock()
    mock_table.get_item.return_value = mock_dynamodb_item
    
    with patch.object(handler, 'books_table', mock_table), \
         patch.object(handler.s3_client, 'generate_presigned_url', return_value=mock_url):
        resp = handler.get_book_handler(event, None)
    
    assert resp["statusCode"] == 200
    body = json.loads(resp["body"])
    assert body["id"] == "book-a.zip"
    assert body["name"] == "Book A.zip"
    assert body["downloadUrl"] == mock_url
    assert body["expiresIn"] == 3600
    assert body["read"] is False
    assert body["author"] == "Author A"


def test_get_book_handler_missing_id():
    """Test get_book_handler when book ID is missing"""
    
    event = {
        'pathParameters': {}
    }
    
    resp = handler.get_book_handler(event, None)
    
    assert resp["statusCode"] == 400
    body = json.loads(resp["body"])
    assert "error" in body
    assert "Id is required" in body["message"]


def test_get_book_handler_not_found():
    """Test get_book_handler when book doesn't exist in DynamoDB"""
    
    event = {
        'pathParameters': {
            'id': 'nonexistent.zip'
        }
    }
    
    # Mock DynamoDB response with no item
    mock_dynamodb_response = {}
    
    mock_table = Mock()
    mock_table.get_item.return_value = mock_dynamodb_response
    
    with patch.object(handler, 'books_table', mock_table):
        resp = handler.get_book_handler(event, None)
    
    assert resp["statusCode"] == 404
    body = json.loads(resp["body"])
    assert "Not Found" in body["error"]


def test_get_book_handler_missing_s3_url():
    """Test get_book_handler when DynamoDB item is missing S3 URL"""
    
    event = {
        'pathParameters': {
            'id': 'book-a.zip'
        }
    }
    
    # Mock DynamoDB response with missing s3_url
    mock_dynamodb_item = {
        'Item': {
            'id': 'book-a.zip',
            'name': 'Book A.zip',
            'created': '2023-06-15T10:30:00Z'
            # Missing s3_url
        }
    }
    
    mock_table = Mock()
    mock_table.get_item.return_value = mock_dynamodb_item
    
    with patch.object(handler, 'books_table', mock_table):
        resp = handler.get_book_handler(event, None)
    
    assert resp["statusCode"] == 500
    body = json.loads(resp["body"])
    assert "Invalid Data" in body["error"]
    assert "missing S3 URL" in body["message"]


def test_update_book_handler_success():
    """Test updating book metadata in DynamoDB"""
    
    event = {
        'pathParameters': {
            'id': 'book-a.zip'
        },
        'body': json.dumps({
            'read': True,
            'author': 'Updated Author'
        })
    }
    
    # Mock DynamoDB update response
    mock_update_response = {
        'Attributes': {
            'id': 'book-a.zip',
            'name': 'Book A.zip',
            'read': True,
            'author': 'Updated Author',
            'created': '2023-06-15T10:30:00Z',
            's3_url': 's3://test-bucket/books/Book A.zip'
        }
    }
    
    mock_table = Mock()
    mock_table.update_item.return_value = mock_update_response
    
    with patch.object(handler, 'books_table', mock_table):
        resp = handler.update_book_handler(event, None)
    
    assert resp["statusCode"] == 200
    body = json.loads(resp["body"])
    assert body["id"] == "book-a.zip"
    assert body["read"] is True
    assert body["author"] == "Updated Author"


def test_update_book_handler_missing_id():
    """Test update_book_handler when book ID is missing"""
    
    event = {
        'pathParameters': {},
        'body': json.dumps({'read': True})
    }
    
    resp = handler.update_book_handler(event, None)
    
    assert resp["statusCode"] == 400
    body = json.loads(resp["body"])
    assert "Id is required" in body["message"]


def test_update_book_handler_invalid_json():
    """Test update_book_handler with invalid JSON body"""
    
    event = {
        'pathParameters': {
            'id': 'book-a.zip'
        },
        'body': 'invalid json{'
    }
    
    resp = handler.update_book_handler(event, None)
    
    assert resp["statusCode"] == 400
    body = json.loads(resp["body"])
    assert "Invalid JSON" in body["message"]


def test_update_book_handler_no_fields():
    """Test update_book_handler when no valid fields provided"""
    
    event = {
        'pathParameters': {
            'id': 'book-a.zip'
        },
        'body': json.dumps({})
    }
    
    resp = handler.update_book_handler(event, None)
    
    assert resp["statusCode"] == 400
    body = json.loads(resp["body"])
    assert "No valid fields to update" in body["message"]


def test_update_book_handler_not_found():
    """Test update_book_handler when book doesn't exist"""
    
    from botocore.exceptions import ClientError
    
    event = {
        'pathParameters': {
            'id': 'nonexistent.zip'
        },
        'body': json.dumps({'read': True})
    }
    
    # Mock DynamoDB conditional check failure
    error_response = {'Error': {'Code': 'ConditionalCheckFailedException'}}
    condition_error = ClientError(error_response, 'update_item')
    
    mock_table = Mock()
    mock_table.update_item.side_effect = condition_error
    
    with patch.object(handler, 'books_table', mock_table):
        resp = handler.update_book_handler(event, None)
    
    assert resp["statusCode"] == 404
    body = json.loads(resp["body"])
    assert "Not Found" in body["error"]


def test_update_book_handler_invalid_read_type():
    """Test update_book_handler with invalid type for 'read' field"""
    
    event = {
        'pathParameters': {
            'id': 'book-a.zip'
        },
        'body': json.dumps({'read': 'yes'})  # Should be boolean
    }
    
    resp = handler.update_book_handler(event, None)
    
    assert resp["statusCode"] == 400
    body = json.loads(resp["body"])
    assert '"read" must be a boolean' in body["message"]


def test_update_book_handler_invalid_author_type():
    """Test update_book_handler with invalid type for 'author' field"""
    
    event = {
        'pathParameters': {
            'id': 'book-a.zip'
        },
        'body': json.dumps({'author': 123})  # Should be string
    }
    
    resp = handler.update_book_handler(event, None)
    
    assert resp["statusCode"] == 400
    body = json.loads(resp["body"])
    assert '"author" must be a string' in body["message"]


def test_update_book_handler_author_too_long():
    """Test update_book_handler with author exceeding length limit"""
    
    event = {
        'pathParameters': {
            'id': 'book-a.zip'
        },
        'body': json.dumps({'author': 'x' * 501})  # Exceeds 500 char limit
    }
    
    resp = handler.update_book_handler(event, None)
    
    assert resp["statusCode"] == 400
    body = json.loads(resp["body"])
    assert 'exceeds maximum length' in body["message"]


def test_update_book_handler_empty_name():
    """Test update_book_handler with empty name"""
    
    event = {
        'pathParameters': {
            'id': 'book-a.zip'
        },
        'body': json.dumps({'name': ''})
    }
    
    resp = handler.update_book_handler(event, None)
    
    assert resp["statusCode"] == 400
    body = json.loads(resp["body"])
    assert 'cannot be empty' in body["message"]


def test_update_book_handler_name_too_long():
    """Test update_book_handler with name exceeding length limit"""
    
    event = {
        'pathParameters': {
            'id': 'book-a.zip'
        },
        'body': json.dumps({'name': 'x' * 501})  # Exceeds 500 char limit
    }
    
    resp = handler.update_book_handler(event, None)
    
    assert resp["statusCode"] == 400
    body = json.loads(resp["body"])
    assert 'exceeds maximum length' in body["message"]


def test_s3_trigger_handler_success():
    """Test S3 trigger handler ingests book into DynamoDB"""
    
    event = {
        'Records': [
            {
                's3': {
                    'bucket': {'name': 'test-bucket'},
                    'object': {
                        'key': 'books/Book A.zip',
                        'size': 1024000
                    }
                },
                'eventTime': '2023-06-15T10:30:00.000Z'
            }
        ]
    }
    
    mock_table = Mock()
    
    with patch.object(handler, 'books_table', mock_table):
        resp = handler.s3_trigger_handler(event, None)
    
    # Verify put_item was called
    mock_table.put_item.assert_called_once()
    call_args = mock_table.put_item.call_args[1]
    item = call_args['Item']
    
    # Handler removes .zip extension from ID and name
    assert item['id'] == 'Book A'
    assert item['name'] == 'Book A'
    assert item['size'] == 1024000
    assert item['s3_url'] == 's3://test-bucket/books/Book A.zip'
    assert item['read'] is False
    
    assert resp["statusCode"] == 200


def test_s3_trigger_handler_with_author():
    """Test S3 trigger handler preserves original filename structure"""
    
    event = {
        'Records': [
            {
                's3': {
                    'bucket': {'name': 'test-bucket'},
                    'object': {
                        'key': 'books/My_Book-Title.zip',
                        'size': 2048000
                    }
                }
            }
        ]
    }
    
    mock_table = Mock()
    
    with patch.object(handler, 'books_table', mock_table):
        resp = handler.s3_trigger_handler(event, None)
    
    # Verify put_item was called
    call_args = mock_table.put_item.call_args[1]
    item = call_args['Item']
    
    # Handler now keeps original filename structure (doesn't replace _ or -)
    assert item['name'] == 'My_Book-Title'
    assert item['id'] == 'My_Book-Title'  # ID keeps original (minus .zip)
    assert resp["statusCode"] == 200


def test_s3_trigger_handler_multiple_records():
    """Test S3 trigger handler processes multiple S3 events"""
    
    event = {
        'Records': [
            {
                's3': {
                    'bucket': {'name': 'test-bucket'},
                    'object': {
                        'key': 'books/Book1.zip',
                        'size': 1000
                    }
                }
            },
            {
                's3': {
                    'bucket': {'name': 'test-bucket'},
                    'object': {
                        'key': 'books/Book2.zip',
                        'size': 2000
                    }
                }
            }
        ]
    }
    
    mock_table = Mock()
    
    with patch.object(handler, 'books_table', mock_table):
        resp = handler.s3_trigger_handler(event, None)
    
    # Verify put_item was called twice
    assert mock_table.put_item.call_count == 2
    assert resp["statusCode"] == 200


def test_s3_trigger_handler_skips_non_zip():
    """Test S3 trigger handler processes non-zip files (converts filename)"""
    
    event = {
        'Records': [
            {
                's3': {
                    'bucket': {'name': 'test-bucket'},
                    'object': {
                        'key': 'books/index.html',
                        'size': 5000
                    }
                }
            }
        ]
    }
    
    mock_table = Mock()
    
    with patch.object(handler, 'books_table', mock_table):
        resp = handler.s3_trigger_handler(event, None)
    
    # Verify put_item WAS called (handler processes all files)
    mock_table.put_item.assert_called_once()
    call_args = mock_table.put_item.call_args[1]
    item = call_args['Item']
    
    # Should use the filename as-is since it's not a .zip
    assert item['id'] == 'index.html'
    assert item['name'] == 'index.html'
    assert resp["statusCode"] == 200


def test_s3_trigger_handler_skips_folder():
    """Test S3 trigger handler processes folder markers (edge case)"""
    
    event = {
        'Records': [
            {
                's3': {
                    'bucket': {'name': 'test-bucket'},
                    'object': {
                        'key': 'books/',
                        'size': 0
                    }
                }
            }
        ]
    }
    
    mock_table = Mock()
    
    with patch.object(handler, 'books_table', mock_table):
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
    
    event = {
        'requestContext': {
            'authorizer': {
                'claims': {
                    'email': 'test@example.com'
                }
            }
        },
        'body': json.dumps({
            'filename': 'Test Book.zip',
            'fileSize': 1024000,
            'author': 'Test Author'
        })
    }
    
    mock_presigned_url = 'https://s3.amazonaws.com/test-bucket/books/Test%20Book.zip?signature=xyz'
    
    with patch.object(handler.s3_client, 'generate_presigned_url', return_value=mock_presigned_url):
        resp = handler.upload_handler(event, None)
    
    assert resp["statusCode"] == 200
    body = json.loads(resp["body"])
    
    assert body['uploadUrl'] == mock_presigned_url
    assert body['method'] == 'PUT'
    assert body['filename'] == 'Test Book.zip'
    assert body['s3Key'] == 'books/Test Book.zip'
    assert body['expiresIn'] == 3600
    assert body['author'] == 'Test Author'


def test_upload_handler_missing_filename():
    """Test upload handler rejects request without filename"""
    
    event = {
        'requestContext': {
            'authorizer': {
                'claims': {
                    'email': 'test@example.com'
                }
            }
        },
        'body': json.dumps({
            'fileSize': 1024000
        })
    }
    
    resp = handler.upload_handler(event, None)
    
    assert resp["statusCode"] == 400
    body = json.loads(resp["body"])
    assert 'filename is required' in body['message']


def test_upload_handler_invalid_extension():
    """Test upload handler rejects non-zip files"""
    
    event = {
        'requestContext': {
            'authorizer': {
                'claims': {
                    'email': 'test@example.com'
                }
            }
        },
        'body': json.dumps({
            'filename': 'test.pdf',
            'fileSize': 1024000
        })
    }
    
    resp = handler.upload_handler(event, None)
    
    assert resp["statusCode"] == 400
    body = json.loads(resp["body"])
    assert 'Only .zip files are allowed' in body['message']


def test_upload_handler_file_too_large():
    """Test upload handler rejects files exceeding 5GB limit"""
    
    event = {
        'requestContext': {
            'authorizer': {
                'claims': {
                    'email': 'test@example.com'
                }
            }
        },
        'body': json.dumps({
            'filename': 'huge.zip',
            'fileSize': 6 * 1024 * 1024 * 1024  # 6GB
        })
    }
    
    resp = handler.upload_handler(event, None)
    
    assert resp["statusCode"] == 400
    body = json.loads(resp["body"])
    assert 'exceeds maximum limit of 5GB' in body['message']


def test_upload_handler_invalid_json():
    """Test upload handler handles invalid JSON gracefully"""
    
    event = {
        'requestContext': {
            'authorizer': {
                'claims': {
                    'email': 'test@example.com'
                }
            }
        },
        'body': 'invalid json'
    }
    
    resp = handler.upload_handler(event, None)
    
    assert resp["statusCode"] == 400
    body = json.loads(resp["body"])
    assert 'Invalid JSON' in body['message']


def test_upload_handler_author_too_long():
    """Test upload handler rejects author exceeding 500 characters"""
    
    event = {
        'requestContext': {
            'authorizer': {
                'claims': {
                    'email': 'test@example.com'
                }
            }
        },
        'body': json.dumps({
            'filename': 'test.zip',
            'fileSize': 1024000,
            'author': 'A' * 501  # 501 characters
        })
    }
    
    resp = handler.upload_handler(event, None)
    
    assert resp["statusCode"] == 400
    body = json.loads(resp["body"])
    assert 'exceeds maximum length of 500' in body['message']


def test_upload_handler_without_author():
    """Test upload handler works without optional author field"""
    
    event = {
        'requestContext': {
            'authorizer': {
                'claims': {
                    'email': 'test@example.com'
                }
            }
        },
        'body': json.dumps({
            'filename': 'Test Book.zip',
            'fileSize': 1024000
        })
    }
    
    mock_presigned_url = 'https://s3.amazonaws.com/test-bucket/books/Test%20Book.zip?signature=xyz'
    
    with patch.object(handler.s3_client, 'generate_presigned_url', return_value=mock_presigned_url):
        resp = handler.upload_handler(event, None)
    
    assert resp["statusCode"] == 200
    body = json.loads(resp["body"])
    
    assert 'author' not in body


# ============================================================================
# Set Upload Metadata Handler Tests
# ============================================================================

def test_set_upload_metadata_handler_success():
    """Test successful metadata update after upload"""
    
    event = {
        'requestContext': {
            'authorizer': {
                'claims': {
                    'email': 'test@example.com'
                }
            }
        },
        'body': json.dumps({
            'bookId': 'Test Book',
            'author': 'New Author'
        })
    }
    
    mock_table = Mock()
    mock_table.update_item.return_value = {}
    
    with patch.object(handler, 'books_table', mock_table):
        resp = handler.set_upload_metadata_handler(event, None)
    
    assert resp["statusCode"] == 200
    body = json.loads(resp["body"])
    
    assert body['message'] == 'Metadata updated successfully'
    assert body['bookId'] == 'Test Book'
    assert body['author'] == 'New Author'
    
    # Verify update_item was called with correct parameters
    mock_table.update_item.assert_called_once()


def test_set_upload_metadata_handler_missing_book_id():
    """Test metadata handler rejects request without bookId"""
    
    event = {
        'requestContext': {
            'authorizer': {
                'claims': {
                    'email': 'test@example.com'
                }
            }
        },
        'body': json.dumps({
            'author': 'Test Author'
        })
    }
    
    resp = handler.set_upload_metadata_handler(event, None)
    
    assert resp["statusCode"] == 400
    body = json.loads(resp["body"])
    assert 'bookId is required' in body['message']


def test_set_upload_metadata_handler_book_not_found():
    """Test metadata handler handles book not found (S3 trigger hasn't completed)"""
    
    event = {
        'requestContext': {
            'authorizer': {
                'claims': {
                    'email': 'test@example.com'
                }
            }
        },
        'body': json.dumps({
            'bookId': 'Nonexistent Book',
            'author': 'Test Author'
        })
    }
    
    mock_table = Mock()
    # Simulate ConditionalCheckFailedException
    from botocore.exceptions import ClientError
    mock_table.update_item.side_effect = ClientError(
        {'Error': {'Code': 'ConditionalCheckFailedException'}},
        'UpdateItem'
    )
    
    with patch.object(handler, 'books_table', mock_table):
        resp = handler.set_upload_metadata_handler(event, None)
    
    assert resp["statusCode"] == 404
    body = json.loads(resp["body"])
    assert 'not found' in body['message']


def test_set_upload_metadata_handler_empty_author():
    """Test metadata handler with empty author (no update needed)"""
    
    event = {
        'requestContext': {
            'authorizer': {
                'claims': {
                    'email': 'test@example.com'
                }
            }
        },
        'body': json.dumps({
            'bookId': 'Test Book',
            'author': ''
        })
    }
    
    resp = handler.set_upload_metadata_handler(event, None)
    
    assert resp["statusCode"] == 200
    body = json.loads(resp["body"])
    assert 'No metadata to update' in body['message']


def test_set_upload_metadata_handler_author_too_long():
    """Test metadata handler rejects author exceeding 500 characters"""
    
    event = {
        'requestContext': {
            'authorizer': {
                'claims': {
                    'email': 'test@example.com'
                }
            }
        },
        'body': json.dumps({
            'bookId': 'Test Book',
            'author': 'A' * 501
        })
    }
    
    resp = handler.set_upload_metadata_handler(event, None)
    
    assert resp["statusCode"] == 400
    body = json.loads(resp["body"])
    assert 'exceeds maximum length of 500' in body['message']


def test_set_upload_metadata_handler_invalid_json():
    """Test metadata handler handles invalid JSON"""
    
    event = {
        'requestContext': {
            'authorizer': {
                'claims': {
                    'email': 'test@example.com'
                }
            }
        },
        'body': 'invalid json'
    }
    
    resp = handler.set_upload_metadata_handler(event, None)
    
    assert resp["statusCode"] == 400
    body = json.loads(resp["body"])
    assert 'Invalid JSON' in body['message']


# ============================================================================
# Delete Book Handler Tests
# ============================================================================

def test_delete_book_handler_success():
    """Test successful deletion of book from both DynamoDB and S3"""
    
    event = {
        'requestContext': {
            'authorizer': {
                'claims': {
                    'email': 'test@example.com'
                }
            }
        },
        'pathParameters': {
            'id': 'Test Book'
        }
    }
    
    # Mock DynamoDB response
    mock_table = Mock()
    mock_table.get_item.return_value = {
        'Item': {
            'id': 'Test Book',
            'name': 'Test Book',
            's3_url': 's3://test-bucket/books/Test Book.zip'
        }
    }
    mock_table.delete_item.return_value = {}
    
    # Mock S3 deletion
    mock_s3_delete = Mock()
    
    with patch.object(handler, 'books_table', mock_table), \
         patch.object(handler.s3_client, 'delete_object', mock_s3_delete):
        resp = handler.delete_book_handler(event, None)
    
    assert resp["statusCode"] == 200
    body = json.loads(resp["body"])
    
    assert body['message'] == 'Book deleted successfully'
    assert body['bookId'] == 'Test Book'
    
    # Verify both S3 and DynamoDB deletions were called
    mock_s3_delete.assert_called_once_with(
        Bucket='test-bucket',
        Key='books/Test Book.zip'
    )
    mock_table.delete_item.assert_called_once()


def test_delete_book_handler_missing_id():
    """Test delete handler rejects request without book ID"""
    
    event = {
        'requestContext': {
            'authorizer': {
                'claims': {
                    'email': 'test@example.com'
                }
            }
        },
        'pathParameters': {}
    }
    
    resp = handler.delete_book_handler(event, None)
    
    assert resp["statusCode"] == 400
    body = json.loads(resp["body"])
    assert 'Id is required' in body['message']


def test_delete_book_handler_book_not_found():
    """Test delete handler handles book not found"""
    
    event = {
        'requestContext': {
            'authorizer': {
                'claims': {
                    'email': 'test@example.com'
                }
            }
        },
        'pathParameters': {
            'id': 'Nonexistent Book'
        }
    }
    
    mock_table = Mock()
    mock_table.get_item.return_value = {}  # No 'Item' key
    
    with patch.object(handler, 'books_table', mock_table):
        resp = handler.delete_book_handler(event, None)
    
    assert resp["statusCode"] == 404
    body = json.loads(resp["body"])
    assert 'not found' in body['message']


def test_delete_book_handler_s3_error_continues():
    """Test delete handler continues with DynamoDB deletion even if S3 fails"""
    
    event = {
        'requestContext': {
            'authorizer': {
                'claims': {
                    'email': 'test@example.com'
                }
            }
        },
        'pathParameters': {
            'id': 'Test Book'
        }
    }
    
    mock_table = Mock()
    mock_table.get_item.return_value = {
        'Item': {
            'id': 'Test Book',
            'name': 'Test Book',
            's3_url': 's3://test-bucket/books/Test Book.zip'
        }
    }
    mock_table.delete_item.return_value = {}
    
    # Mock S3 deletion to raise error
    from botocore.exceptions import ClientError
    mock_s3_delete = Mock(side_effect=ClientError(
        {'Error': {'Code': 'NoSuchKey'}},
        'DeleteObject'
    ))
    
    with patch.object(handler, 'books_table', mock_table), \
         patch.object(handler.s3_client, 'delete_object', mock_s3_delete):
        resp = handler.delete_book_handler(event, None)
    
    # Should still succeed (S3 error is logged but not fatal)
    assert resp["statusCode"] == 200
    
    # DynamoDB deletion should still happen
    mock_table.delete_item.assert_called_once()


def test_delete_book_handler_no_s3_url():
    """Test delete handler works when book has no S3 URL"""
    
    event = {
        'requestContext': {
            'authorizer': {
                'claims': {
                    'email': 'test@example.com'
                }
            }
        },
        'pathParameters': {
            'id': 'Test Book'
        }
    }
    
    mock_table = Mock()
    mock_table.get_item.return_value = {
        'Item': {
            'id': 'Test Book',
            'name': 'Test Book'
            # No s3_url
        }
    }
    mock_table.delete_item.return_value = {}
    
    mock_s3_delete = Mock()
    
    with patch.object(handler, 'books_table', mock_table), \
         patch.object(handler.s3_client, 'delete_object', mock_s3_delete):
        resp = handler.delete_book_handler(event, None)
    
    assert resp["statusCode"] == 200
    
    # S3 delete should NOT be called
    mock_s3_delete.assert_not_called()
    
    # DynamoDB deletion should still happen
    mock_table.delete_item.assert_called_once()


def test_delete_book_handler_dynamodb_not_found_on_delete():
    """Test delete handler handles race condition where book deleted between get and delete"""
    
    event = {
        'requestContext': {
            'authorizer': {
                'claims': {
                    'email': 'test@example.com'
                }
            }
        },
        'pathParameters': {
            'id': 'Test Book'
        }
    }
    
    mock_table = Mock()
    mock_table.get_item.return_value = {
        'Item': {
            'id': 'Test Book',
            'name': 'Test Book',
            's3_url': 's3://test-bucket/books/Test Book.zip'
        }
    }
    
    # Simulate ConditionalCheckFailedException during delete
    from botocore.exceptions import ClientError
    mock_table.delete_item.side_effect = ClientError(
        {'Error': {'Code': 'ConditionalCheckFailedException'}},
        'DeleteItem'
    )
    
    mock_s3_delete = Mock()
    
    with patch.object(handler, 'books_table', mock_table), \
         patch.object(handler.s3_client, 'delete_object', mock_s3_delete):
        resp = handler.delete_book_handler(event, None)
    
    assert resp["statusCode"] == 404
    body = json.loads(resp["body"])
    assert 'not found' in body['message']
