/**
 * API communication module
 * Handles all backend API calls
 */

async function fetchBooks() {
    const booksContainer = document.getElementById('booksContainer');
    const loadingSpinner = document.getElementById('loading');
    
    const token = localStorage.getItem('idToken');
    if (!token) {
        showAlert('Please login first', 'error');
        return;
    }

    // Reset and show loading
    booksContainer.innerHTML = '';
    loadingSpinner.style.display = 'inline-flex';

    try {
        const response = await fetch(API_URL, {
            headers: {
                'Authorization': token
            }
        });
        
        if (response.status === 401 || response.status === 403) {
            // Try to refresh token and retry
            const refreshed = await refreshAuthToken();
            if (refreshed) {
                // Retry with new token
                return fetchBooks();
            } else {
                // Refresh failed, logout
                showAlert('⚠️ Session expired. Please log in again.', 'error');
                setTimeout(() => logout(), 2000);
                return;
            }
        }
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const data = await response.json();
        
        // Check for error response
        if (data.error) {
            throw new Error(data.error + ': ' + (data.message || ''));
        }
        
        // Handle new response format: {books: [], isAdmin: boolean}
        let books;
        let isAdmin = false;
        
        if (Array.isArray(data)) {
            // Old format: direct array of books
            books = data;
        } else if (data.books && Array.isArray(data.books)) {
            // New format: {books: [], isAdmin: boolean}
            books = data.books;
            isAdmin = data.isAdmin || false;
        } else {
            console.error('Unexpected response format:', data);
            throw new Error('Unexpected response format from API');
        }
        
        // Store books globally for filtering
        allBooks = books;
        
        // Store admin status globally
        window.isUserAdmin = isAdmin;
        
        // Show/hide floating action button based on admin status
        const fabUpload = document.getElementById('fabUpload');
        if (fabUpload) {
            fabUpload.style.display = isAdmin ? 'flex' : 'none';
        }
        
        // Render the books (pass true to show success toast on initial fetch)
        renderBooks(books, false, true);
        
    } catch (error) {
        showAlert(`❌ Failed to load books: ${error.message}`, 'error');
        console.error('Error fetching books:', error);
    } finally {
        loadingSpinner.style.display = 'none';
    }
}

async function toggleReadStatus(bookId, event) {
    event.stopPropagation(); // Prevent download trigger
    
    // Validate bookId
    if (!bookId || bookId.trim() === '') {
        console.error('toggleReadStatus called with invalid bookId:', bookId);
        showAlert('❌ Error: Invalid book ID', 'error');
        return;
    }
    
    const token = localStorage.getItem('idToken');
    if (!token) {
        showAlert('Please login to update read status', 'error');
        return;
    }
    
    // Get current state from DOM
    const toggleButton = event.target.closest('.read-toggle');
    const currentReadStatus = toggleButton.classList.contains('read');
    const isNowRead = !currentReadStatus;
    
    // Update UI optimistically
    const bookCard = event.target.closest('.book-card');
    
    if (isNowRead) {
        toggleButton.classList.add('read');
        toggleButton.innerHTML = '✓';
        toggleButton.title = 'Mark as unread';
        bookCard.classList.add('read');
    } else {
        toggleButton.classList.remove('read');
        toggleButton.innerHTML = '○';
        toggleButton.title = 'Mark as read';
        bookCard.classList.remove('read');
    }
    
    try {
        // Update read status on backend
        const encodedBookId = encodeURIComponent(bookId);
        const response = await fetch(`${API_URL}/${encodedBookId}`, {
            method: 'PATCH',
            headers: {
                'Authorization': token,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ read: isNowRead })
        });
        
        if (response.status === 401 || response.status === 403) {
            // Try to refresh token and retry
            const refreshed = await refreshAuthToken();
            if (refreshed) {
                // Retry the update
                return toggleReadStatus(bookId, event);
            } else {
                // Refresh failed, revert UI and logout
                showAlert('⚠️ Session expired. Please log in again.', 'error');
                // Revert UI
                if (isNowRead) {
                    toggleButton.classList.remove('read');
                    toggleButton.innerHTML = '○';
                    bookCard.classList.remove('read');
                } else {
                    toggleButton.classList.add('read');
                    toggleButton.innerHTML = '✓';
                    bookCard.classList.add('read');
                }
                setTimeout(() => logout(), 2000);
                return;
            }
        }
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        // Success - backend is now in sync
        // Update the allBooks array to keep it in sync
        const bookIndex = allBooks.findIndex(b => b.id === bookId);
        if (bookIndex !== -1) {
            allBooks[bookIndex].read = isNowRead;
        }
        
        // Reapply filters (in case "hide read" is active, book might need to disappear)
        applyFilters();
        
    } catch (error) {
        console.error('Error updating read status:', error);
        showAlert(`❌ Failed to update read status: ${error.message}`, 'error');
        
        // Revert UI on error
        if (isNowRead) {
            toggleButton.classList.remove('read');
            toggleButton.innerHTML = '○';
            toggleButton.title = 'Mark as read';
            bookCard.classList.remove('read');
        } else {
            toggleButton.classList.add('read');
            toggleButton.innerHTML = '✓';
            toggleButton.title = 'Mark as unread';
            bookCard.classList.add('read');
        }
    }
}

async function downloadBook(bookId) {
    const token = localStorage.getItem('idToken');
    if (!token) {
        showAlert('Please login first', 'error');
        return;
    }

    try {
        // Show loading state
        showAlert(`📥 Preparing download...`, 'success');
        
        // Encode the book ID for the URL
        const encodedBookId = encodeURIComponent(bookId);
        
        // Fetch presigned URL from API
        const response = await fetch(`${API_URL}/${encodedBookId}`, {
            headers: {
                'Authorization': token
            }
        });
        
        if (response.status === 401 || response.status === 403) {
            // Try to refresh token and retry
            const refreshed = await refreshAuthToken();
            if (refreshed) {
                // Retry download with new token
                return downloadBook(bookId);
            } else {
                // Refresh failed, logout
                showAlert('⚠️ Session expired. Please log in again.', 'error');
                setTimeout(() => logout(), 2000);
                return;
            }
        }
        
        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.message || `HTTP error! status: ${response.status}`);
        }
        
        const data = await response.json();
        
        // Open the presigned URL in a new window to trigger download
        const link = document.createElement('a');
        link.href = data.downloadUrl;
        link.download = data.name || bookId;
        link.target = '_blank';
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        
        showAlert(`✅ Download started for ${data.name || bookId}`, 'success');
        
    } catch (error) {
        showAlert(`❌ Download failed: ${error.message}`, 'error');
        console.error('Error downloading book:', error);
    }
}

