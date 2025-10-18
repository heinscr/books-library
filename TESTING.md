# Testing Guide

This document describes the test suite for the Books Library application.

## Test Framework

- **Framework**: pytest
- **Test Location**: `tests/test_handler.py`
- **Coverage**: All Lambda handler functions (list, get, update, S3 trigger)

## Running Tests

### Install Test Dependencies

```bash
# Activate virtual environment
source .venv/bin/activate

# Install test dependencies
pip install pytest boto3 moto
```

### Run All Tests

```bash
pytest tests/test_handler.py -v
```

### Run Specific Tests

```bash
# Run tests for a specific handler
pytest tests/test_handler.py -k "test_list_handler" -v

# Run tests for input validation
pytest tests/test_handler.py -k "test_update_book_handler_invalid" -v
```

## Test Coverage

### List Handler Tests
- ✅ Returns books from DynamoDB
- ✅ Handles empty table
- ✅ Handles pagination
- ✅ Handles DynamoDB errors

### Get Book Handler Tests
- ✅ Returns book metadata and presigned URL
- ✅ Validates missing book ID
- ✅ Handles book not found
- ✅ Handles missing S3 URL in metadata

### Update Book Handler Tests
- ✅ Successfully updates book metadata
- ✅ Validates missing book ID
- ✅ Validates invalid JSON
- ✅ Validates empty update payload
- ✅ Handles book not found
- ✅ **Input Validation Tests**:
  - ✅ Validates `read` field must be boolean
  - ✅ Validates `author` field must be string
  - ✅ Validates `author` length limit (500 chars)
  - ✅ Validates `name` field must be string
  - ✅ Validates `name` cannot be empty
  - ✅ Validates `name` length limit (500 chars)

### S3 Trigger Handler Tests
- ✅ Ingests new books into DynamoDB
- ✅ Replaces underscores/dashes in friendly names
- ✅ Handles multiple S3 events
- ✅ Processes all file types (not just .zip)
- ✅ Handles folder markers

## Test Architecture

### Mocking Strategy

Tests use Python's `unittest.mock` to mock AWS service calls:

```python
from unittest.mock import patch, Mock

# Mock DynamoDB table
mock_table = Mock()
mock_table.scan.return_value = {'Items': [...]}

with patch.object(handler, 'books_table', mock_table):
    response = handler.list_handler({}, None)
```

### Test Data

Tests use realistic DynamoDB data structures including:
- `Decimal` types for numeric fields (as returned by DynamoDB)
- Proper ISO 8601 timestamps
- S3 URLs in `s3://bucket/key` format

## Input Validation Rules

The test suite validates these constraints:

| Field | Type | Constraints |
|-------|------|-------------|
| `read` | boolean | Required to be boolean type |
| `author` | string | Max 500 characters |
| `name` | string | Max 500 characters, cannot be empty |

## Continuous Integration

To integrate with CI/CD:

```yaml
# Example GitHub Actions workflow
- name: Run tests
  run: |
    pip install pytest boto3 moto
    pytest tests/test_handler.py -v
```

## Future Test Enhancements

Potential improvements to consider:

- [ ] Add integration tests with LocalStack
- [ ] Add API Gateway integration tests
- [ ] Add end-to-end tests with real AWS resources (dev environment)
- [ ] Add performance/load tests
- [ ] Add coverage reporting (pytest-cov)
- [ ] Add mutation testing (mutpy)

## Test Results

Current status: **23 tests, all passing** ✅

```
====== 23 passed in 4.29s ======
```
