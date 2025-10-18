"""
E2E tests for book grid and filtering functionality.

These tests verify the frontend UI behavior, including:
- Book display and rendering
- Filter state preservation
- Special character handling (apostrophes, quotes)
"""

import pytest


@pytest.mark.e2e
class TestBookGrid:
    """Tests for the book grid display and interactions."""

    def test_page_loads(self, page, base_url):
        """Test that the main page loads successfully."""
        page.goto(base_url)

        # Wait for the page to load
        page.wait_for_selector("#booksContainer", timeout=10000)

        # Check that essential elements are present
        assert page.locator("h1").text_content() == "📚 Books Library"
        assert page.locator("#hideReadBooks").is_visible()

    def test_books_display_in_grid(self, page, base_url):
        """Test that books are displayed in a grid layout."""
        page.goto(base_url)

        # Wait for books to load
        page.wait_for_selector(".books-grid", timeout=10000)

        # Check that at least one book card exists
        book_cards = page.locator(".book-card").count()
        assert book_cards > 0, "No books found in the grid"

    def test_book_card_has_required_elements(self, page, base_url):
        """Test that book cards contain all required elements."""
        page.goto(base_url)
        page.wait_for_selector(".book-card", timeout=10000)

        # Get the first book card
        first_card = page.locator(".book-card").first

        # Verify required elements are present
        assert first_card.locator(".book-name").is_visible()
        assert first_card.locator(".read-toggle").is_visible()
        assert first_card.locator(".book-meta").is_visible()


@pytest.mark.e2e
class TestReadToggle:
    """Tests for read status toggle functionality."""

    def test_read_toggle_exists_on_books(self, page, base_url):
        """Test that read toggle buttons exist on book cards."""
        page.goto(base_url)
        page.wait_for_selector(".book-card", timeout=10000)

        # Check that read toggles exist
        toggle_count = page.locator(".read-toggle").count()
        assert toggle_count > 0, "No read toggle buttons found"

    def test_read_toggle_clickable(self, page, base_url):
        """Test that read toggle buttons are clickable."""
        page.goto(base_url)
        page.wait_for_selector(".book-card", timeout=10000)

        # Get first toggle
        first_toggle = page.locator(".read-toggle").first

        # Verify it's clickable (has proper attributes)
        assert first_toggle.get_attribute(
            "data-book-id"
        ), "Read toggle missing data-book-id attribute"

    @pytest.mark.skip(
        reason="Requires authentication - implement after auth test setup"
    )
    def test_toggle_read_status_with_apostrophe(self, page, base_url):
        """Test toggling read status on a book with apostrophe in ID.

        This specifically tests the bug fix where apostrophes in book IDs
        would break the onclick handler.
        """
        page.goto(base_url)
        page.wait_for_selector(".book-card", timeout=10000)

        # Find a book with an apostrophe in the name (e.g., "Roald Dahl's Cookbook")
        book_with_apostrophe = page.locator(
            ".book-card:has-text(\"'\")"
        ).first  # Find first book with apostrophe

        if book_with_apostrophe.count() > 0:
            # Get the read toggle for this book
            toggle = book_with_apostrophe.locator(".read-toggle")
            initial_state = toggle.get_attribute("class")

            # Click to toggle
            toggle.click()

            # Wait for the state to update (API call and re-render)
            page.wait_for_timeout(1000)

            # Verify the state changed
            new_state = toggle.get_attribute("class")
            assert (
                initial_state != new_state
            ), "Read status did not toggle for book with apostrophe"


@pytest.mark.e2e
class TestFilterFunctionality:
    """Tests for the 'hide read books' filter functionality."""

    def test_hide_read_filter_exists(self, page, base_url):
        """Test that the hide read books filter checkbox exists."""
        page.goto(base_url)

        # Check filter checkbox is present
        filter_checkbox = page.locator("#hideReadBooks")
        assert filter_checkbox.is_visible()
        assert not filter_checkbox.is_checked(), "Filter should be unchecked by default"

    def test_filter_checkbox_toggles(self, page, base_url):
        """Test that the filter checkbox can be toggled."""
        page.goto(base_url)

        filter_checkbox = page.locator("#hideReadBooks")

        # Toggle on
        filter_checkbox.check()
        assert filter_checkbox.is_checked()

        # Toggle off
        filter_checkbox.uncheck()
        assert not filter_checkbox.is_checked()

    @pytest.mark.skip(reason="Requires books with read status to test filtering")
    def test_filter_hides_read_books(self, page, base_url):
        """Test that enabling the filter hides read books."""
        page.goto(base_url)
        page.wait_for_selector(".book-card", timeout=10000)

        # Count initial books
        initial_count = page.locator(".book-card").count()

        # Enable filter
        page.locator("#hideReadBooks").check()
        page.wait_for_timeout(500)  # Wait for filter to apply

        # Count books after filter
        filtered_count = page.locator(".book-card").count()

        # Should show fewer books (assuming some are marked as read)
        assert (
            filtered_count <= initial_count
        ), "Filter did not reduce the number of books displayed"


@pytest.mark.e2e
class TestFilterStatePreservation:
    """Tests for filter state preservation after book operations.

    This specifically tests the bug fix where editing or deleting a book
    would reset the filter state.
    """

    @pytest.mark.skip(
        reason="Requires authentication and read books - implement after auth setup"
    )
    def test_filter_preserved_after_edit(self, page, base_url):
        """Test that filter state is preserved after editing a book.

        This tests the fix where editing a book's author would cause
        the grid to show all books even when 'hide read books' was checked.
        """
        page.goto(base_url)
        page.wait_for_selector(".book-card", timeout=10000)

        # Enable filter
        filter_checkbox = page.locator("#hideReadBooks")
        filter_checkbox.check()
        assert filter_checkbox.is_checked()

        page.wait_for_timeout(500)
        filtered_count_before = page.locator(".book-card").count()

        # Click on first visible book to open details modal
        first_book = page.locator(".book-card").first
        first_book.click()

        # Wait for modal to open
        page.wait_for_selector("#bookDetailsModal", state="visible")

        # Edit author field
        author_input = page.locator("#editAuthor")
        original_author = author_input.input_value()
        author_input.fill(original_author + " (Edited)")

        # Save
        page.locator("#saveDetailsButton").click()

        # Wait for save to complete and modal to close
        page.wait_for_selector("#bookDetailsModal", state="hidden", timeout=5000)

        # Verify filter is still checked
        assert (
            filter_checkbox.is_checked()
        ), "Filter checkbox was unchecked after edit"

        # Verify the same number of books are shown
        filtered_count_after = page.locator(".book-card").count()
        assert (
            filtered_count_before == filtered_count_after
        ), "Number of visible books changed after edit (filter state not preserved)"


@pytest.mark.e2e
class TestSpecialCharacters:
    """Tests for handling special characters in book names and IDs."""

    def test_books_with_apostrophes_display(self, page, base_url):
        """Test that books with apostrophes in names display correctly."""
        page.goto(base_url)
        page.wait_for_selector(".book-card", timeout=10000)

        # Look for books with apostrophes
        books_with_apostrophe = page.locator(".book-card:has-text(\"'\")")

        # If any exist, verify they display properly
        if books_with_apostrophe.count() > 0:
            first_book = books_with_apostrophe.first
            book_name = first_book.locator(".book-name").text_content()
            assert "'" in book_name, "Apostrophe not displayed in book name"
            assert (
                "&#" not in book_name
            ), "HTML entities visible instead of apostrophe"

    def test_books_with_quotes_display(self, page, base_url):
        """Test that books with quotes in names display correctly."""
        page.goto(base_url)
        page.wait_for_selector(".book-card", timeout=10000)

        # Look for books with quotes
        books_with_quotes = page.locator('.book-card:has-text(\'"\')')

        # If any exist, verify they display properly
        if books_with_quotes.count() > 0:
            first_book = books_with_quotes.first
            book_name = first_book.locator(".book-name").text_content()
            assert '"' in book_name, "Quote not displayed in book name"
            assert "&#" not in book_name, "HTML entities visible instead of quote"
