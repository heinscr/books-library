/**
 * Filtering module
 * Handles book filtering and search
 * Note: allBooks is defined globally in app.js
 */

function applyFilters() {
    const hideRead = document.getElementById('hideReadBooks').checked;
    const groupByAuthor = document.getElementById('groupByAuthor').checked;
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
}

