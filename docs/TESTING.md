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

E2E tests verify the complete user experience using Playwright to automate browser interactions against the deployed application.

**Location**: `tests/e2e/`
**Framework**: Playwright + pytest-playwright
**Test Count**: **43 tests, all passing** ✅

### Quick Start

```bash
# Set up credentials (one-time setup)
cp .env.example .env
# Edit .env and add TEST_USER_EMAIL and TEST_USER_PASSWORD

# Run all E2E tests
./run-e2e-tests.sh

# Run with visible browser for debugging
./run-e2e-tests.sh --headed

# Run specific test file
./run-e2e-tests.sh test_authentication.py
```

### Setup E2E Tests

**1. Install dependencies:**
```bash
pipenv install --dev
pipenv run playwright install chromium
```

**2. Install system dependencies (Linux only, one-time):**
```bash
sudo apt-get install libnspr4 libnss3 libasound2t64
# Or use: sudo pipenv run playwright install-deps
```

**3. Configure test credentials:**
```bash
cp .env.example .env
# Edit .env and set:
#   TEST_USER_EMAIL=your-test-user@example.com
#   TEST_USER_PASSWORD=your-test-password
```

**4. Configure BASE_URL (if needed):**
Edit `tests/e2e/conftest.py` to point to your deployment URL.

### E2E Test Coverage (43 tests - ALL PASSING ✅)

**Authentication Tests (12 tests):**
- ✅ Login form visibility and successful login flow
- ✅ Invalid credentials handling
- ✅ Logout flow and UI state changes
- ✅ User avatar displays email initial
- ✅ User menu toggle and email display
- ✅ FAB button visibility based on auth status
- ✅ Login form accessibility (labels, ARIA)
- ✅ User menu ARIA attributes
- ✅ Keyboard navigation (Escape key)

**Book Grid & Display Tests (13 tests):**
- ✅ Page loads and displays login form
- ✅ Books display in grid layout
- ✅ Book cards have required elements (name, toggle, metadata)
- ✅ Read toggle buttons exist with proper attributes
- ✅ Read toggle works with apostrophes in book names
- ✅ Filter button exists and toggles (aria-pressed)
- ✅ Filter hides read books
- ✅ Group by author button exists and toggles
- ✅ Grouping creates author sections with book counts
- ✅ Filter state preserved after editing
- ✅ Special characters display correctly (apostrophes, quotes)

**Book Operations Tests (18 tests):**
- ✅ Book details modal opens/closes (click, Escape key)
- ✅ Modal shows complete metadata
- ✅ Edit book author and series info
- ✅ Save button disabled during save
- ✅ No-changes handling
- ✅ Read toggle changes state
- ✅ Download icon exists and clickable
- ✅ Keyboard accessibility (Tab, Enter, Space)
- ✅ Book cards have proper ARIA labels
- ✅ Modal has proper dialog role and ARIA attributes

For detailed E2E documentation, see:
- `tests/e2e/README.md` - Complete E2E testing guide
- `docs/E2E_TEST_SETUP.md` - Setup and troubleshooting

### Manual Test Execution

```bash
# All tests
PYTHONPATH=. pipenv run pytest -m e2e

# With visible browser
PYTHONPATH=. pipenv run pytest -m e2e --headed

# Specific test file
PYTHONPATH=. pipenv run pytest tests/e2e/test_authentication.py -v

# Against different URL
BASE_URL=https://your-test-url.com ./run-e2e-tests.sh
```

## Test Results Summary

**Backend Unit Tests:** 120 tests, all passing ✅
```
====== 120 passed, 93% coverage ======
```

**E2E Tests:** 43 tests, all passing ✅
```
====== 43 passed in 139.10s (0:02:19) ======
```

**Total:** 163 tests passing
