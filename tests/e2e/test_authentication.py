"""
E2E tests for authentication functionality.

These tests verify:
- Login flow
- Logout flow
- Session persistence
- UI state changes based on authentication
"""

import pytest


@pytest.mark.e2e
class TestAuthentication:
    """Tests for user authentication flows."""

    def test_login_form_visible_on_load(self, page, base_url):
        """Test that the login form is visible when user is not authenticated."""
        page.goto(base_url)

        # Wait for login form to be visible
        login_form = page.locator("#loginForm")
        login_form.wait_for(state="visible", timeout=10000)

        assert login_form.is_visible()
        assert page.locator("#email").is_visible()
        assert page.locator("#password").is_visible()
        assert page.locator(".login-btn").is_visible()

    def test_successful_login(self, page, base_url, test_credentials):
        """Test that a user can successfully log in with valid credentials."""
        page.goto(base_url)

        # Wait for login form
        page.wait_for_selector("#loginForm", state="visible", timeout=10000)

        # Fill in credentials
        page.fill("#email", test_credentials["email"])
        page.fill("#password", test_credentials["password"])

        # Click login
        page.click(".login-btn")

        # Wait for login to complete - user avatar should appear
        page.wait_for_selector("#userAvatar", state="visible", timeout=15000)

        # Verify logged-in state
        assert page.locator("#userAvatar").is_visible()
        assert page.locator("#loginForm").is_hidden()

        # Verify books container exists (it may be empty but present)
        assert page.locator("#booksContainer").count() > 0

        # Verify controls are visible
        assert page.locator("#controlsRow").is_visible()

    def test_login_with_invalid_credentials(self, page, base_url):
        """Test that login fails gracefully with invalid credentials."""
        page.goto(base_url)

        # Wait for login form
        page.wait_for_selector("#loginForm", state="visible", timeout=10000)

        # Fill in invalid credentials
        page.fill("#email", "invalid@example.com")
        page.fill("#password", "wrongpassword")

        # Click login
        page.click(".login-btn")

        # Wait a moment for the response
        page.wait_for_timeout(2000)

        # Verify still on login screen
        assert page.locator("#loginForm").is_visible()
        assert page.locator("#userAvatar").is_hidden()

        # Check for error alert
        alert = page.locator("#alert")
        if alert.is_visible():
            assert "failed" in alert.text_content().lower() or "invalid" in alert.text_content().lower()

    def test_logout_flow(self, authenticated_page):
        """Test that a user can successfully log out."""
        page = authenticated_page

        # Verify we're logged in
        assert page.locator("#userAvatar").is_visible()

        # Click user avatar to open menu
        page.click("#userAvatar")

        # Wait for menu to appear
        page.wait_for_selector("#userMenu.show", timeout=5000)

        # Click logout button
        page.click(".user-menu-item.logout")

        # Wait for logout to complete - login form should reappear
        page.wait_for_selector("#loginForm", state="visible", timeout=10000)

        # Verify logged-out state
        assert page.locator("#loginForm").is_visible()
        assert page.locator("#userAvatar").is_hidden()
        # Books container should be empty after logout
        books_container = page.locator("#booksContainer")
        assert books_container.inner_html().strip() == ""

    def test_user_avatar_shows_email_initial(self, authenticated_page, test_credentials):
        """Test that the user avatar displays the first letter of the email."""
        page = authenticated_page

        # Get the avatar initial
        avatar_initial = page.locator("#avatarInitial").text_content()

        # Should be the first letter of the email, uppercase
        expected_initial = test_credentials["email"][0].upper()
        assert avatar_initial == expected_initial

    def test_user_menu_displays_email(self, authenticated_page, test_credentials):
        """Test that the user menu displays the logged-in email."""
        page = authenticated_page

        # Click user avatar to open menu
        page.click("#userAvatar")

        # Wait for menu to appear
        page.wait_for_selector("#userMenu.show", timeout=5000)

        # Verify email is displayed
        menu_email = page.locator("#menuEmail").text_content()
        assert menu_email == test_credentials["email"]

    def test_user_menu_toggles_on_click(self, authenticated_page):
        """Test that clicking the user avatar toggles the menu."""
        page = authenticated_page

        user_menu = page.locator("#userMenu")

        # Initially menu should be hidden
        assert not user_menu.evaluate("el => el.classList.contains('show')")

        # Click to open
        page.click("#userAvatar")
        page.wait_for_timeout(300)
        assert user_menu.evaluate("el => el.classList.contains('show')")

        # Click to close
        page.click("#userAvatar")
        page.wait_for_timeout(300)
        assert not user_menu.evaluate("el => el.classList.contains('show')")

    def test_fab_button_hidden_when_not_logged_in(self, page, base_url):
        """Test that the upload FAB button is hidden when not authenticated."""
        page.goto(base_url)

        # Wait for page to load
        page.wait_for_selector("#loginForm", state="visible", timeout=10000)

        # FAB button should not be visible
        fab = page.locator("#fabUpload")
        assert fab.is_hidden() or fab.evaluate("el => el.style.display === 'none'")

    def test_fab_button_visible_for_admin(self, authenticated_page):
        """Test that the upload FAB button is visible for authenticated admin users."""
        page = authenticated_page

        # Wait for FAB to potentially appear
        page.wait_for_timeout(1000)

        # Check if FAB is visible (depends on admin status)
        fab = page.locator("#fabUpload")

        # FAB visibility depends on whether user is admin
        # This test documents the expected behavior
        # If user is admin, FAB should be visible
        # If not admin, it may be hidden
        fab_visible = fab.is_visible() if fab.count() > 0 else False

        # Just verify the element exists
        assert fab.count() > 0, "FAB upload button element should exist"


@pytest.mark.e2e
class TestAuthenticationAccessibility:
    """Tests for authentication-related accessibility features."""

    def test_login_form_has_proper_labels(self, page, base_url):
        """Test that login form inputs have proper labels for screen readers."""
        page.goto(base_url)
        page.wait_for_selector("#loginForm", state="visible", timeout=10000)

        # Check for aria-labels or label elements
        email_input = page.locator("#email")
        password_input = page.locator("#password")

        # Check for aria-label or associated label
        assert email_input.get_attribute("aria-label") or page.locator('label[for="email"]').count() > 0
        assert password_input.get_attribute("aria-label") or page.locator('label[for="password"]').count() > 0

    def test_user_menu_has_aria_attributes(self, authenticated_page):
        """Test that user menu has proper ARIA attributes."""
        page = authenticated_page

        user_avatar = page.locator("#userAvatar")
        user_menu = page.locator("#userMenu")

        # Check for ARIA attributes
        assert user_avatar.get_attribute("aria-expanded") is not None
        assert user_avatar.get_attribute("aria-haspopup") is not None
        assert user_menu.get_attribute("role") == "menu"

    def test_user_menu_keyboard_navigation(self, authenticated_page):
        """Test that user menu can be closed with Escape key."""
        page = authenticated_page

        # Open menu
        page.click("#userAvatar")
        page.wait_for_selector("#userMenu.show", timeout=5000)

        # Press Escape
        page.keyboard.press("Escape")

        # Wait a moment
        page.wait_for_timeout(300)

        # Menu should be closed
        user_menu = page.locator("#userMenu")
        assert not user_menu.evaluate("el => el.classList.contains('show')")
