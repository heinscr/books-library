/**
 * Book card component module
 * Creates individual book cards with interactions
 */

function createBookCard(book) {
    const bookCard = document.createElement('div');
    bookCard.className = 'book-card';

    // Make card keyboard accessible
    bookCard.setAttribute('tabindex', '0');
    bookCard.setAttribute('role', 'button');
    bookCard.setAttribute('aria-label', `Book: ${book.name}${book.author ? ' by ' + book.author : ''}`);

    // Check if book is marked as read (from backend)
    const isRead = book.read || false;
    if (isRead) {
        bookCard.classList.add('read');
        bookCard.setAttribute('aria-label', `${bookCard.getAttribute('aria-label')} (read)`);
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

    // Build cover image HTML
    let coverHTML = '';
    if (book.coverImageUrl) {
        coverHTML = `
            <div class="book-cover" aria-hidden="true">
                <img src="${escapeHtml(book.coverImageUrl)}"
                     alt=""
                     onerror="this.parentElement.classList.add('no-cover'); this.style.display='none';">
            </div>
        `;
    } else {
        coverHTML = `
            <div class="book-cover no-cover" aria-hidden="true">
            </div>
        `;
    }

    // Build book info HTML
    let bookInfo = coverHTML + `
        <div class="book-info-content">
            <div class="book-header">
                <div class="book-name" aria-hidden="true">${escapeHtml(book.name)}</div>
                <button class="read-toggle ${isRead ? 'read' : ''}"
                        data-book-id=""
                        aria-label="${isRead ? 'Mark as unread' : 'Mark as read'}"
                        title="${isRead ? 'Mark as unread' : 'Mark as read'}">
                    <span aria-hidden="true">${isRead ? '✓' : '○'}</span>
                </button>
            </div>
    `;
    
    // Add author if available
    if (book.author) {
        bookInfo += `
            <div class="book-author" aria-hidden="true">
                <span aria-hidden="true">✍️</span> ${escapeHtml(book.author)}
            </div>
        `;
    }

    // Add series info if available
    if (book.series_name) {
        const seriesText = book.series_order
            ? `${escapeHtml(book.series_name)} #${book.series_order}`
            : escapeHtml(book.series_name);
        bookInfo += `
            <div class="book-series" aria-hidden="true">
                <span aria-hidden="true">📚</span> ${seriesText}
            </div>
        `;
    }

    bookInfo += `
            <div class="book-meta" aria-hidden="true">
                <div class="book-size"><span aria-hidden="true">📦</span> ${sizeInMB} MB</div>
                <div class="book-date"><span aria-hidden="true">📅</span> ${formattedDate}</div>
            </div>
            <div class="book-download" aria-hidden="true">
                <span class="download-icon" aria-hidden="true">⬇️</span>
            </div>
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
            e.stopPropagation(); // Prevent card click
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

    // Add keyboard handler for Enter/Space on the card
    bookCard.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' || e.key === ' ') {
            e.preventDefault();
            showBookDetailsModal(book);
        }
    });

    return bookCard;
}

