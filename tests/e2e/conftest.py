"""
Pytest configuration for E2E tests using Playwright.
"""

import os
import time

import pytest


@pytest.fixture(scope="session")
def base_url():
    """Get base URL from environment variable or use default"""
    return os.getenv("BASE_URL", "https://d2zmecmv6nn8xx.cloudfront.net")


@pytest.fixture(scope="session")
def api_url():
    """API URL for the backend."""
    return os.getenv(
        "API_URL", "https://vlii8j82ug.execute-api.us-east-2.amazonaws.com/Prod"
    )


@pytest.fixture(scope="session")
def test_credentials():
    """Test user credentials from environment variables."""
    email = os.getenv("TEST_USER_EMAIL")
    password = os.getenv("TEST_USER_PASSWORD")

    if not email or not password:
        pytest.skip("Test credentials not provided. Set TEST_USER_EMAIL and TEST_USER_PASSWORD environment variables.")

    return {"email": email, "password": password}


@pytest.fixture
def browser_context_args(browser_context_args):
    """Configure browser context for tests."""
    return {
        **browser_context_args,
        "viewport": {"width": 1280, "height": 720},
        "ignore_https_errors": True,  # For local testing
    }


@pytest.fixture
def authenticated_page(page, base_url, test_credentials):
    """Create an authenticated page by logging in with test credentials.

    This fixture:
    1. Navigates to the login page
    2. Performs login with test credentials
    3. Waits for authentication to complete
    4. Returns the authenticated page

    Use this fixture for tests that require authentication.
    """
    # Navigate to the site
    page.goto(base_url)

    # Wait for login form to be visible
    page.wait_for_selector("#loginForm", state="visible", timeout=10000)

    # Fill in credentials
    page.fill("#email", test_credentials["email"])
    page.fill("#password", test_credentials["password"])

    # Click login button
    page.click(".login-btn")

    # Wait for login to complete - user avatar should appear
    page.wait_for_selector("#userAvatar", state="visible", timeout=15000)

    # Wait for books to load
    page.wait_for_selector("#booksContainer", timeout=10000)

    # Give the UI a moment to stabilize
    time.sleep(1)

    return page


@pytest.fixture
def authenticated_context(context, base_url, test_credentials):
    """Create an authenticated browser context by injecting tokens.

    This is a faster alternative to authenticated_page that injects
    tokens directly into localStorage without going through the login UI.

    Note: You need to manually extract tokens first by logging in once.
    This fixture is currently a placeholder for future implementation.
    """
    # TODO: Implement token injection approach for faster tests
    # For now, use authenticated_page fixture instead
    return context
