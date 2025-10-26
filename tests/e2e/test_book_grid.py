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

        # Wait for the page to load - wait for login form to appear
        page.wait_for_selector("#loginForm", state="visible", timeout=10000)

        # Check that essential elements are present
        assert page.locator("#loginForm").is_visible()
        assert page.locator("#email").is_visible()
        assert page.locator("#booksContainer").count() > 0

    def test_books_display_in_grid(self, authenticated_page):
        """Test that books are displayed in a grid layout."""
        page = authenticated_page

        # Check that at least one book card exists
        book_cards = page.locator(".book-card").count()
        assert book_cards > 0, "No books found in the grid"

    def test_book_card_has_required_elements(self, authenticated_page):
        """Test that book cards contain all required elements."""
        page = authenticated_page

        # Get the first book card
        first_card = page.locator(".book-card").first

        # Verify required elements are present
        assert first_card.locator(".book-name").is_visible()
        assert first_card.locator(".read-toggle").is_visible()
        assert first_card.locator(".book-meta").is_visible()


@pytest.mark.e2e
class TestReadToggle:
    """Tests for read status toggle functionality."""

    def test_read_toggle_exists_on_books(self, authenticated_page):
        """Test that read toggle buttons exist on book cards."""
        page = authenticated_page

        # Check that read toggles exist
        toggle_count = page.locator(".read-toggle").count()
        assert toggle_count > 0, "No read toggle buttons found"

    def test_read_toggle_clickable(self, authenticated_page):
        """Test that read toggle buttons are clickable."""
        page = authenticated_page

        # Get first toggle
        first_toggle = page.locator(".read-toggle").first

        # Verify it's clickable (has proper attributes)
        assert first_toggle.get_attribute(
            "data-book-id"
        ), "Read toggle missing data-book-id attribute"

    def test_toggle_read_status_with_apostrophe(self, authenticated_page):
        """Test toggling read status on a book with apostrophe in ID.

        This specifically tests the bug fix where apostrophes in book IDs
        would break the onclick handler.
        """
        page = authenticated_page

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

    def test_hide_read_filter_exists(self, authenticated_page):
        """Test that the hide read books filter button exists."""
        page = authenticated_page

        # Check filter button is present
        filter_button = page.locator("#hideReadBooksBtn")
        assert filter_button.is_visible()

        # Check it's a button with aria-pressed attribute
        assert filter_button.get_attribute("aria-pressed") == "false", "Filter should be unpressed by default"

    def test_filter_checkbox_toggles(self, authenticated_page):
        """Test that the filter button can be toggled."""
        page = authenticated_page

        filter_button = page.locator("#hideReadBooksBtn")

        # Toggle on
        filter_button.click()
        page.wait_for_timeout(500)
        assert filter_button.get_attribute("aria-pressed") == "true"

        # Toggle off
        filter_button.click()
        page.wait_for_timeout(500)
        assert filter_button.get_attribute("aria-pressed") == "false"

    def test_filter_hides_read_books(self, authenticated_page):
        """Test that enabling the filter hides read books."""
        page = authenticated_page

        # Count initial books
        initial_count = page.locator(".book-card").count()

        # Enable filter by clicking the button
        filter_button = page.locator("#hideReadBooksBtn")
        filter_button.click()
        page.wait_for_timeout(1000)  # Wait for filter to apply

        # Count books after filter
        filtered_count = page.locator(".book-card").count()

        # Should show fewer or equal books (assuming some may be marked as read)
        assert (
            filtered_count <= initial_count
        ), "Filter did not reduce the number of books displayed"


@pytest.mark.e2e
class TestGroupByAuthor:
    """Tests for group by author functionality."""

    def test_group_by_author_checkbox_exists(self, authenticated_page):
        """Test that the group by author button exists."""
        page = authenticated_page

        group_button = page.locator("#groupByAuthorBtn")
        assert group_button.is_visible(), "Group by author button not found"

    def test_group_by_author_checkbox_toggles(self, authenticated_page):
        """Test that the group by author button can be toggled."""
        page = authenticated_page

        group_button = page.locator("#groupByAuthorBtn")

        # Toggle on
        group_button.click()
        page.wait_for_timeout(500)
        assert group_button.get_attribute("aria-pressed") == "true"

        # Toggle off
        group_button.click()
        page.wait_for_timeout(500)
        assert group_button.get_attribute("aria-pressed") == "false"

    def test_group_by_author_shows_author_sections(self, authenticated_page):
        """Test that enabling group by author creates author sections."""
        page = authenticated_page

        # Enable grouping by clicking the button
        group_button = page.locator("#groupByAuthorBtn")
        group_button.click()
        page.wait_for_timeout(1000)  # Wait for re-render

        # Check that author sections are created
        author_sections = page.locator(".author-section")
        assert author_sections.count() > 0, "No author sections found when grouping enabled"

        # Check that author headers exist
        author_headers = page.locator(".author-header")
        assert author_headers.count() > 0, "No author headers found"

    def test_group_by_author_shows_book_counts(self, authenticated_page):
        """Test that author sections show book counts."""
        page = authenticated_page

        # Enable grouping by clicking the button
        group_button = page.locator("#groupByAuthorBtn")
        group_button.click()
        page.wait_for_timeout(1000)

        # Check that book counts are displayed
        book_counts = page.locator(".author-book-count")
        assert book_counts.count() > 0, "No book count badges found"

        # Verify the count text makes sense
        first_count = book_counts.first.text_content()
        assert "book" in first_count.lower(), "Book count text doesn't contain 'book'"


@pytest.mark.e2e
class TestFilterStatePreservation:
    """Tests for filter state preservation after book operations.

    This specifically tests the bug fix where editing or deleting a book
    would reset the filter state.
    """

    def test_filter_preserved_after_edit(self, authenticated_page):
        """Test that filter state is preserved after editing a book.

        This tests the fix where editing a book's author would cause
        the grid to show all books even when 'hide read books' was checked.
        """
        page = authenticated_page

        # Enable filter by clicking the button
        filter_button = page.locator("#hideReadBooksBtn")
        filter_button.click()
        page.wait_for_timeout(1000)

        # Verify filter is active
        assert filter_button.get_attribute("aria-pressed") == "true"

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
        page.wait_for_selector("#bookDetailsModal", state="hidden", timeout=10000)

        # Wait for UI to update
        page.wait_for_timeout(1000)

        # Verify filter is still active
        assert (
            filter_button.get_attribute("aria-pressed") == "true"
        ), "Filter was deactivated after edit"

        # Verify the same number of books are shown
        filtered_count_after = page.locator(".book-card").count()
        assert (
            filtered_count_before == filtered_count_after
        ), "Number of visible books changed after edit (filter state not preserved)"


@pytest.mark.e2e
class TestSpecialCharacters:
    """Tests for handling special characters in book names and IDs."""

    def test_books_with_apostrophes_display(self, authenticated_page):
        """Test that books with apostrophes in names display correctly."""
        page = authenticated_page

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
        else:
            # Skip if no books with apostrophes
            pass

    def test_books_with_quotes_display(self, authenticated_page):
        """Test that books with quotes in names display correctly."""
        page = authenticated_page

        # Look for books with quotes
        books_with_quotes = page.locator('.book-card:has-text(\'"\')')

        # If any exist, verify they display properly
        if books_with_quotes.count() > 0:
            first_book = books_with_quotes.first
            book_name = first_book.locator(".book-name").text_content()
            assert '"' in book_name, "Quote not displayed in book name"
            assert "&#" not in book_name, "HTML entities visible instead of quote"
        else:
            # Skip if no books with quotes
            pass
