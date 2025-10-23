/**
 * Book rendering module
 * Handles book list display and grouping
 */

function renderBooks(books, groupByAuthor = false, showSuccessToast = false) {
    const booksContainer = document.getElementById('booksContainer');
    booksContainer.innerHTML = '';
    
    if (books.length === 0) {
        booksContainer.innerHTML = `
            <div class="empty-state">
                <div class="empty-state-icon">📚</div>
                <h3>No books found</h3>
                <p>Your library is empty.</p>
            </div>
        `;
        return;
    }
    
    if (groupByAuthor) {
        renderBooksGroupedByAuthor(books);
    } else {
        renderBooksAsGrid(books);
    }
    
    // Only show success toast on initial fetch, not on filter changes
    if (showSuccessToast) {
        showAlert(`✅ Loaded ${books.length} books successfully`, 'success');
    }
}

function renderBooksAsGrid(books) {
    const booksContainer = document.getElementById('booksContainer');
    
    // Display books in grid
    const booksGrid = document.createElement('div');
    booksGrid.className = 'books-grid';
    
    books.forEach(book => {
        const bookCard = createBookCard(book);
        booksGrid.appendChild(bookCard);
    });
    
    booksContainer.appendChild(booksGrid);
}

function renderBooksGroupedByAuthor(books) {
    const booksContainer = document.getElementById('booksContainer');
    
    // Group books by author
    const booksByAuthor = {};
    const unknownAuthor = 'Unknown Author';
    
    books.forEach(book => {
        const author = book.author || unknownAuthor;
        if (!booksByAuthor[author]) {
            booksByAuthor[author] = [];
        }
        booksByAuthor[author].push(book);
    });
    
    // Sort authors alphabetically, but put "Unknown Author" last
    const sortedAuthors = Object.keys(booksByAuthor).sort((a, b) => {
        if (a === unknownAuthor) return 1;
        if (b === unknownAuthor) return -1;
        return a.localeCompare(b);
    });
    
    // Create grouped display
    sortedAuthors.forEach(author => {
        const authorSection = document.createElement('div');
        authorSection.className = 'author-section';
        
        const authorHeader = document.createElement('div');
        authorHeader.className = 'author-header';
        authorHeader.innerHTML = `
            <h3>✍️ ${escapeHtml(author)}</h3>
            <span class="author-book-count">${booksByAuthor[author].length} book${booksByAuthor[author].length !== 1 ? 's' : ''}</span>
        `;
        
        const booksGrid = document.createElement('div');
        booksGrid.className = 'books-grid';
        
        // Sort books within author by series order, then by title
        const sortedBooks = booksByAuthor[author].sort((a, b) => {
            // If both books have series info and same series name, sort by series_order
            if (a.series_name && b.series_name && a.series_name === b.series_name) {
                const orderA = a.series_order || 0;
                const orderB = b.series_order || 0;
                if (orderA !== orderB) {
                    return orderA - orderB;
                }
            }
            
            // If only one has series info, put series books first
            if (a.series_name && !b.series_name) return -1;
            if (!a.series_name && b.series_name) return 1;
            
            // Different series or no series - sort by series name, then title
            if (a.series_name && b.series_name && a.series_name !== b.series_name) {
                return a.series_name.localeCompare(b.series_name);
            }
            
            // Fallback to sorting by book title
            return (a.name || '').localeCompare(b.name || '');
        });
        
        sortedBooks.forEach(book => {
            const bookCard = createBookCard(book);
            booksGrid.appendChild(bookCard);
        });
        
        authorSection.appendChild(authorHeader);
        authorSection.appendChild(booksGrid);
        booksContainer.appendChild(authorSection);
    });
}

