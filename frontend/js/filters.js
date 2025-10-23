/**
 * Filtering module
 * Handles book filtering and search
 * Note: allBooks is defined globally in app.js
 */

function applyFilters() {
    const hideRead = document.getElementById('hideReadBooks').checked;
    const groupByAuthor = document.getElementById('groupByAuthor').checked;
    
    let filteredBooks = allBooks;
    
    // Filter out read books if checkbox is checked
    if (hideRead) {
        filteredBooks = allBooks.filter(book => !book.read);
    }
    
    // Re-render with filtered books (no toast on filter change)
    renderBooks(filteredBooks, groupByAuthor);
    
    // Only show message when actually hiding books
    if (hideRead && filteredBooks.length < allBooks.length) {
        const hiddenCount = allBooks.length - filteredBooks.length;
        showAlert(`📚 Showing ${filteredBooks.length} books (${hiddenCount} read books hidden)`, 'info');
    }
}

