# End-to-End (E2E) Tests

This directory contains end-to-end tests for the Books Library frontend using [Playwright](https://playwright.dev/).

## Overview

E2E tests verify the complete user experience by automating browser interactions. These tests:
- Test the actual UI and user interactions
- Verify frontend-backend integration
- Catch bugs that unit tests miss (like the apostrophe onclick handler bug)

## Setup

### Install Dependencies

```bash
# Install pytest-playwright
pipenv install --dev

# Install Playwright browsers (only needed once)
pipenv run playwright install chromium
```

If you see a warning about missing system dependencies, install them:
```bash
# On Ubuntu/Debian
sudo apt-get install libnspr4 libnss3 libasound2t64

# Or use Playwright's install script
sudo pipenv run playwright install-deps
```

## Running Tests

### Run All E2E Tests

```bash
# Headless (default, for CI/CD)
PYTHONPATH=. pipenv run pytest -m e2e

# With visible browser (for debugging)
PYTHONPATH=. pipenv run pytest -m e2e --headed

# With slow motion (easier to see what's happening)
PYTHONPATH=. pipenv run pytest -m e2e --headed --slowmo 1000
```

### Run Specific Test Files

```bash
PYTHONPATH=. pipenv run pytest tests/e2e/test_book_grid.py -v
```

### Run Specific Test Cases

```bash
PYTHONPATH=. pipenv run pytest tests/e2e/test_book_grid.py::TestBookGrid::test_page_loads -v
```

### Run with Different Browsers

```bash
# Firefox
PYTHONPATH=. pipenv run pytest -m e2e --browser firefox

# WebKit (Safari)
PYTHONPATH=. pipenv run pytest -m e2e --browser webkit
```

## Configuration

### Environment Variables

- `BASE_URL`: Frontend URL (default: https://books.crackpow.com)
- `API_URL`: Backend API URL (default: production API)

Example for local testing:
```bash
BASE_URL=http://localhost:8000 PYTHONPATH=. pipenv run pytest -m e2e
```

### Test Organization

Tests are organized by feature/functionality:
- `test_book_grid.py`: Book display, grid layout, filtering
- More test files can be added as needed

## Writing Tests

### Test Structure

```python
import pytest

@pytest.mark.e2e
class TestMyFeature:
    """Tests for my feature."""
    
    def test_something(self, page, base_url):
        """Test description."""
        # Navigate to page
        page.goto(base_url)
        
        # Wait for element
        page.wait_for_selector("#element")
        
        # Interact
        page.locator("#button").click()
        
        # Assert
        assert page.locator(".result").text_content() == "Expected"
```

### Common Patterns

**Waiting for elements:**
```python
page.wait_for_selector(".book-card", timeout=10000)
```

**Finding elements with special characters:**
```python
# Books with apostrophes
page.locator(".book-card:has-text(\"'\")")

# Specific book by name
page.locator(".book-name:has-text(\"Roald Dahl's\")")
```

**Checking attributes:**
```python
book_id = page.locator(".read-toggle").get_attribute("data-book-id")
```

**Clicking and waiting:**
```python
page.locator("#button").click()
page.wait_for_timeout(500)  # Wait for animation/API call
```

## Current Test Coverage

### ✅ Implemented (Basic Smoke Tests)
- Page loads successfully
- Books display in grid
- Book cards have required elements
- Read toggle buttons exist and have proper attributes
- Filter checkbox exists and toggles
- Group by author checkbox exists and toggles
- Group by author creates author sections
- Author sections show book counts
- Special characters (apostrophes, quotes) display correctly

### 🚧 Skipped (Requires Authentication)
- Toggle read status on books with apostrophes
- Filter hides read books
- Filter state preserved after editing
- Filter state preserved after deleting

### 📋 To Be Added
- Authentication flow tests
- Book upload tests
- Book deletion tests
- Author editing tests
- Download functionality tests
- Error handling tests
- Mobile/responsive tests

## Authentication in Tests

Many tests require authentication to modify data. To implement auth tests:

1. **Option A: Mock Authentication**
   - Store valid tokens in environment variables
   - Set tokens in browser's localStorage before tests

2. **Option B: Test User Flow**
   - Create a test Cognito user
   - Automate the login flow in tests

3. **Option C: Separate Auth Tests**
   - Keep destructive tests separate
   - Run against a test environment only

## CI/CD Integration

E2E tests can run in GitHub Actions:

```yaml
- name: Run E2E Tests
  run: |
    pipenv run playwright install chromium --with-deps
    PYTHONPATH=. pipenv run pytest -m e2e
  env:
    BASE_URL: ${{ secrets.FRONTEND_URL }}
```

## Debugging

### Screenshots on Failure

Playwright automatically captures screenshots on test failures in `test-results/`.

### Video Recording

Enable video recording:
```python
@pytest.fixture
def browser_context_args(browser_context_args):
    return {
        **browser_context_args,
        "record_video_dir": "test-results/videos/",
    }
```

### Playwright Inspector

Debug tests interactively:
```bash
PWDEBUG=1 PYTHONPATH=. pipenv run pytest tests/e2e/test_book_grid.py::test_name
```

### Pause Execution

Add a pause in your test:
```python
page.pause()  # Opens Playwright Inspector
```

## Best Practices

1. **Use Markers**: Tag tests with `@pytest.mark.e2e`
2. **Wait Properly**: Always wait for elements, don't use arbitrary sleeps
3. **Isolate Tests**: Each test should be independent
4. **Use Data Attributes**: Target elements by data attributes, not CSS classes
5. **Test Real Scenarios**: Focus on user journeys, not implementation details
6. **Handle Flakiness**: Add proper waits, avoid timing-dependent assertions
7. **Clean Up**: Reset state after tests (or use separate test environments)

## Resources

- [Playwright Python Docs](https://playwright.dev/python/)
- [pytest-playwright Plugin](https://github.com/microsoft/playwright-pytest)
- [Playwright Selectors](https://playwright.dev/python/docs/selectors)
- [Best Practices](https://playwright.dev/python/docs/best-practices)
