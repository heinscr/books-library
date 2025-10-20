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
  - ✅ Validates `series_name` field must be string
  - ✅ Validates `series_name` length limit (500 chars)
  - ✅ Validates `series_order` must be integer
  - ✅ Validates `series_order` range (1-100)
  - ✅ Supports clearing `series_order` with null
- ✅ **Series Fields Tests**:
  - ✅ Successfully updates series_name and series_order
  - ✅ List handler returns series fields
  - ✅ Handles Decimal serialization for series_order

### Upload Metadata Handler Tests
- ✅ Successfully sets author metadata
- ✅ Validates missing book ID
- ✅ Handles book not found
- ✅ Handles empty author (no update)
- ✅ Validates author length limit (500 chars)
- ✅ Validates invalid JSON
- ✅ **Series Fields Tests**:
  - ✅ Successfully sets all fields (author, series_name, series_order)
  - ✅ Validates `series_order` range (1-100)
  - ✅ Validates `series_order` must be integer
  - ✅ Handles partial field updates (only some fields provided)
  - ✅ Returns all updated fields in response

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
| `series_name` | string | Max 500 characters |
| `series_order` | integer | Between 1 and 100 (inclusive), can be null to clear |

## Continuous Integration

To integrate with CI/CD:

```yaml
# Example GitHub Actions workflow
- name: Run tests
  run: |
    pip install pytest boto3 moto
    pytest tests/test_handler.py -v
```

## End-to-End (E2E) Tests

### Overview

E2E tests verify the complete user experience using Playwright to automate browser interactions.

**Location**: `tests/e2e/`
**Framework**: Playwright + pytest-playwright

### Setup E2E Tests

```bash
# Install dependencies
pipenv install --dev

# Install Playwright browsers
pipenv run playwright install chromium

# Install system dependencies (Linux only, one-time setup)
sudo apt-get install libnspr4 libnss3 libasound2t64
# Or use: sudo pipenv run playwright install-deps
```

### Run E2E Tests

```bash
# Headless mode (for CI/CD)
PYTHONPATH=. pipenv run pytest -m e2e

# With visible browser (for debugging)
PYTHONPATH=. pipenv run pytest -m e2e --headed

# Slow motion (easier to see)
PYTHONPATH=. pipenv run pytest -m e2e --headed --slowmo 1000

# Against local development server
BASE_URL=http://localhost:8000 PYTHONPATH=. pipenv run pytest -m e2e
```

### E2E Test Coverage

**Implemented (Smoke Tests):**
- ✅ Page loads successfully
- ✅ Books display in grid layout
- ✅ Book cards have required elements
- ✅ Read toggle buttons exist and have proper attributes
- ✅ Filter checkbox exists and toggles
- ✅ Special characters (apostrophes, quotes) display correctly

**Skipped (Requires Authentication):**
- ⏭️ Toggle read status on books with apostrophes
- ⏭️ Filter hides read books  
- ⏭️ Filter state preserved after editing
- ⏭️ Filter state preserved after deleting

See `tests/e2e/README.md` for detailed E2E testing documentation.

## Test Results

Current status: **58 backend tests, all passing** ✅

Backend unit tests:
```
====== 58 passed in 4.40s ======
```

E2E tests: **9 smoke tests, 3 skipped (auth required)**
- Tests require system dependencies (see E2E setup above)
- Can run in CI/CD or on machines with browser dependencies installed
