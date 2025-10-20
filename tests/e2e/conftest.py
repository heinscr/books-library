"""
Pytest configuration for E2E tests using Playwright.
"""

import os

import pytest


@pytest.fixture(scope="session")
def base_url():
    """Get base URL from environment variable or use default"""
    return os.getenv("BASE_URL", "https://books.example.com")


@pytest.fixture(scope="session")
def api_url():
    """API URL for the backend."""
    return os.getenv(
        "API_URL", "https://vlii8j82ug.execute-api.us-east-2.amazonaws.com/Prod"
    )


@pytest.fixture
def browser_context_args(browser_context_args):
    """Configure browser context for tests."""
    return {
        **browser_context_args,
        "viewport": {"width": 1280, "height": 720},
        "ignore_https_errors": True,  # For local testing
    }
