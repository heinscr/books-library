/**
 * Book card component module
 * Creates individual book cards with interactions
 */

function createBookCard(book) {
    const bookCard = document.createElement('div');
    bookCard.className = 'book-card';
    
    // Check if book is marked as read (from backend)
    const isRead = book.read || false;
    if (isRead) {
        bookCard.classList.add('read');
    }
    
    // Format date
    const date = new Date(book.created);
    const formattedDate = date.toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric'
    });
    
    // Format file size
    const sizeInMB = book.size ? (book.size / (1024 * 1024)).toFixed(2) : '?';
    
    // Build book info HTML
    let bookInfo = `
        <div class="book-header">
            <div class="book-name">${escapeHtml(book.name)}</div>
            <div class="read-toggle ${isRead ? 'read' : ''}" data-book-id="" title="${isRead ? 'Mark as unread' : 'Mark as read'}">
                ${isRead ? '✓' : '○'}
            </div>
        </div>
    `;
    
    // Add author if available
    if (book.author) {
        bookInfo += `
            <div class="book-author">
                ✍️ ${escapeHtml(book.author)}
            </div>
        `;
    }
    
    // Add series info if available
    if (book.series_name) {
        const seriesText = book.series_order 
            ? `${escapeHtml(book.series_name)} #${book.series_order}`
            : escapeHtml(book.series_name);
        bookInfo += `
            <div class="book-series">
                📚 ${seriesText}
            </div>
        `;
    }
    
    bookInfo += `
        <div class="book-meta">
            <div class="book-size">📦 ${sizeInMB} MB</div>
            <div class="book-date">📅 ${formattedDate}</div>
        </div>
        <div class="book-download">
            <span class="download-icon">⬇️</span>
        </div>
    `;
    
    bookCard.innerHTML = bookInfo;

    // Ensure the data-book-id attribute stores the raw book id (not HTML-escaped)
    const readToggleEl = bookCard.querySelector('.read-toggle');
    if (readToggleEl) {
        readToggleEl.setAttribute('data-book-id', book.id);
        
        // Debug: verify the attribute was set correctly
        const verifyId = readToggleEl.getAttribute('data-book-id');
        if (verifyId !== book.id) {
            console.error('Data attribute mismatch!', {
                expected: book.id,
                actual: verifyId,
                bookName: book.name
            });
        }
    } else {
        console.error('Could not find read-toggle element for book:', book.name);
    }
    
    // Add click handler for the card
    bookCard.addEventListener('click', (e) => {
        // Handle read toggle click
        const readToggle = e.target.closest('.read-toggle');
        if (readToggle) {
            const bookId = readToggle.getAttribute('data-book-id');
            if (!bookId) {
                console.error('Read toggle clicked but data-book-id is empty or null');
                showAlert('❌ Error: Book ID not found', 'error');
                return;
            }
            toggleReadStatus(bookId, e);
            return;
        }
        
        // Don't open modal if clicking the download icon
        if (e.target.closest('.book-download')) {
            downloadBook(book.id);
            return;
        }
        
        // Open details modal for any other click
        showBookDetailsModal(book);
    });
    
    return bookCard;
}

