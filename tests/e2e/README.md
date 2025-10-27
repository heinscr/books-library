# End-to-End (E2E) Tests

This directory contains end-to-end tests for the Books Library frontend using [Playwright](https://playwright.dev/).

## Overview

E2E tests verify the complete user experience by automating browser interactions. These tests:
- Test the actual UI and user interactions
- Verify frontend-backend integration
- Catch bugs that unit tests miss (like the apostrophe onclick handler bug)

## Setup

### 1. Install Dependencies

```bash
# Install pytest-playwright (already in Pipfile)
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

### 2. Set Up Test Credentials

E2E tests require a test user account for authentication. Set these environment variables:

```bash
export TEST_USER_EMAIL='your-test-user@example.com'
export TEST_USER_PASSWORD='your-test-password'
```

**Note:** Use a dedicated test account, not a production account. The tests will:
- Log in and out
- Edit book metadata (then restore it)
- Toggle read status on books

To persist these for your session, add to your `.bashrc` or `.zshrc`:
```bash
# Add to ~/.bashrc or ~/.zshrc
export TEST_USER_EMAIL='test@example.com'
export TEST_USER_PASSWORD='testpassword123'
```

## Running Tests

### Quick Start (Using the Helper Script)

```bash
# Set credentials first (if not already in environment)
export TEST_USER_EMAIL='your-test-user@example.com'
export TEST_USER_PASSWORD='your-test-password'

# Run all tests (headless)
./run-e2e-tests.sh

# Run with visible browser
./run-e2e-tests.sh --headed

# Run with slow motion for debugging
./run-e2e-tests.sh --slow

# Run specific test file
./run-e2e-tests.sh test_authentication.py

# Run with Playwright inspector (for debugging)
./run-e2e-tests.sh --debug
```

### Manual Test Execution

If you prefer to run tests manually without the script:

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
PYTHONPATH=. pipenv run pytest tests/e2e/test_authentication.py -v
PYTHONPATH=. pipenv run pytest tests/e2e/test_book_operations.py -v
```

### Run Specific Test Cases

```bash
PYTHONPATH=. pipenv run pytest tests/e2e/test_book_grid.py::TestBookGrid::test_page_loads -v
PYTHONPATH=. pipenv run pytest tests/e2e/test_authentication.py::TestAuthentication::test_successful_login -v
```

### Run with Different Browsers

```bash
# Firefox
./run-e2e-tests.sh --firefox

# WebKit (Safari)
./run-e2e-tests.sh --webkit

# Or manually:
PYTHONPATH=. pipenv run pytest -m e2e --browser firefox
PYTHONPATH=. pipenv run pytest -m e2e --browser webkit
```

## Configuration

### Environment Variables

**Required:**
- `TEST_USER_EMAIL`: Email address for test user account
- `TEST_USER_PASSWORD`: Password for test user account

**Optional:**
- `BASE_URL`: Frontend URL (default: configured in conftest.py)
- `API_URL`: Backend API URL (default: configured in conftest.py)

Example for local testing:
```bash
export TEST_USER_EMAIL='test@example.com'
export TEST_USER_PASSWORD='testpass123'
export BASE_URL='http://localhost:8000'
PYTHONPATH=. pipenv run pytest -m e2e
```

### Test Organization

Tests are organized by feature/functionality:
- `test_authentication.py`: Login, logout, session management, auth UI (12 tests)
- `test_book_grid.py`: Book display, grid layout, filtering, grouping (13 tests)
- `test_book_operations.py`: Book details modal, editing, read toggle, download, accessibility, delete menu (25 tests)
- More test files can be added as needed

**Total: 50 E2E tests** (7 new tests added for overflow menu delete functionality)

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

### ✅ Implemented Tests

**Authentication (test_authentication.py):**
- Login form visibility
- Successful login flow
- Invalid credentials handling
- Logout flow
- User avatar displays email initial
- User menu displays email
- User menu toggle functionality
- FAB button visibility (admin vs non-admin)
- Login form accessibility (labels, ARIA)
- User menu ARIA attributes
- Keyboard navigation (Escape key)

**Book Grid & Display (test_book_grid.py):**
- Page loads successfully
- Books display in grid
- Book cards have required elements
- Read toggle buttons exist and have proper attributes
- Toggle read status on books with apostrophes
- Filter checkbox exists and toggles
- Filter hides read books (with auth)
- Filter state preserved after editing (with auth)
- Group by author checkbox exists and toggles
- Group by author creates author sections
- Author sections show book counts
- Special characters (apostrophes, quotes) display correctly

**Book Operations (test_book_operations.py):**
- Book details modal opens on click
- Modal shows complete metadata
- Modal closes on close button
- Modal closes on Escape key
- Edit book author
- Edit book series info
- Save button disabled during save
- No changes shows info message
- Read toggle changes state
- Download icon exists and is clickable
- Book cards keyboard accessible (tabindex, role, aria-label)
- Book card opens on Enter key
- Book card opens on Space key
- Modal has proper dialog role and ARIA attributes

### 📋 Future Enhancements
- Book upload flow tests
- Book deletion tests
- Error handling and edge cases
- Mobile/responsive layout tests
- Performance tests (load time, animations)
- Cross-browser compatibility tests

## Authentication in Tests

Tests use the `authenticated_page` fixture to handle authentication automatically.

### How It Works

1. **Test Credentials**: Set via environment variables (`TEST_USER_EMAIL`, `TEST_USER_PASSWORD`)
2. **Fixture**: The `authenticated_page` fixture automatically:
   - Navigates to the site
   - Fills in login credentials
   - Waits for authentication to complete
   - Returns the authenticated page object

### Using Authenticated Tests

```python
@pytest.mark.e2e
class TestMyFeature:
    def test_something_requiring_auth(self, authenticated_page):
        """Test that requires a logged-in user."""
        page = authenticated_page

        # Page is already logged in and ready
        page.locator(".some-element").click()
        # ... rest of test
```

### Test User Requirements

Your test user should:
- Be a valid Cognito user in the user pool
- Have access to view and edit books
- Ideally be an admin user to test all features (upload, delete)
- NOT be a production user with important data

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
