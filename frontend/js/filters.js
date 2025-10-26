/**
 * Filtering module
 * Handles book filtering and search
 * Note: allBooks is defined globally in app.js
 */

// Filter state
let filterState = {
    hideReadBooks: false,
    groupByAuthor: false
};

function toggleFilter(filterName) {
    filterState[filterName] = !filterState[filterName];

    // Update button active state and ARIA pressed attribute
    const btn = document.getElementById(filterName + 'Btn');
    if (btn) {
        if (filterState[filterName]) {
            btn.classList.add('active');
            btn.setAttribute('aria-pressed', 'true');
        } else {
            btn.classList.remove('active');
            btn.setAttribute('aria-pressed', 'false');
        }
    }

    applyFilters();
}

function applyFilters() {
    const hideRead = filterState.hideReadBooks;
    const groupByAuthor = filterState.groupByAuthor;
    const searchInput = document.getElementById('searchInput');
    const searchQuery = searchInput ? searchInput.value.trim().toLowerCase() : '';

    let filteredBooks = allBooks;

    // Apply search filter
    if (searchQuery) {
        filteredBooks = filteredBooks.filter(book => {
            const title = (book.name || '').toLowerCase();
            const author = (book.author || '').toLowerCase();
            const seriesName = (book.series_name || '').toLowerCase();

            return title.includes(searchQuery) ||
                   author.includes(searchQuery) ||
                   seriesName.includes(searchQuery);
        });
    }

    // Filter out read books if checkbox is checked
    if (hideRead) {
        filteredBooks = filteredBooks.filter(book => !book.read);
    }

    // Re-render with filtered books (no toast on filter change)
    renderBooks(filteredBooks, groupByAuthor);

    // Show status message
    let message = '';
    if (searchQuery && hideRead) {
        const hiddenCount = allBooks.length - filteredBooks.length;
        message = `🔍 Found ${filteredBooks.length} books matching "${searchQuery}" (${hiddenCount} read books hidden)`;
    } else if (searchQuery) {
        message = `🔍 Found ${filteredBooks.length} books matching "${searchQuery}"`;
    } else if (hideRead && filteredBooks.length < allBooks.length) {
        const hiddenCount = allBooks.length - filteredBooks.length;
        message = `📚 Showing ${filteredBooks.length} books (${hiddenCount} read books hidden)`;
    }

    if (message) {
        showAlert(message, 'info');
    }

    // Announce to screen readers
    announceToScreenReader(message || `Displaying ${filteredBooks.length} books`);
}

/**
 * Announce dynamic content changes to screen readers
 * @param {string} message - Message to announce
 */
function announceToScreenReader(message) {
    const srAnnouncements = document.getElementById('srAnnouncements');
    if (srAnnouncements) {
        srAnnouncements.textContent = message;
        // Clear after announcement is made
        setTimeout(() => {
            srAnnouncements.textContent = '';
        }, 1000);
    }
}

