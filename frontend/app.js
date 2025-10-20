// Configuration is loaded from config.js
// If config.js doesn't exist, create it from config.js.example

// Store books data for filtering
let allBooks = [];

// Check if user is already logged in
window.addEventListener('DOMContentLoaded', () => {
    const token = localStorage.getItem('idToken');
    const email = localStorage.getItem('userEmail');
    if (token && email) {
        // Check if token is expired or about to expire
        checkAndRefreshToken().then(isValid => {
            if (isValid) {
                showLoggedInState(email);
                // Auto-load books on page load if already logged in
                fetchBooks();
            } else {
                // Token expired and couldn't refresh, show login
                logout();
            }
        });
    }
    
    // Close user menu when clicking outside
    document.addEventListener('click', (e) => {
        const userMenu = document.getElementById('userMenu');
        const userAvatar = document.getElementById('userAvatar');
        if (!userMenu.contains(e.target) && !userAvatar.contains(e.target)) {
            userMenu.classList.remove('show');
        }
    });
    
    // Allow enter key to submit login
    document.getElementById('email').addEventListener('keypress', (e) => {
        if (e.key === 'Enter') login();
    });
    document.getElementById('password').addEventListener('keypress', (e) => {
        if (e.key === 'Enter') login();
    });
});

// Check if token needs refresh and refresh if necessary
async function checkAndRefreshToken() {
    const tokenExpiration = localStorage.getItem('tokenExpiration');
    const refreshToken = localStorage.getItem('refreshToken');
    
    if (!tokenExpiration || !refreshToken) {
        return false;
    }
    
    const expirationTime = parseInt(tokenExpiration);
    const now = Date.now();
    const timeUntilExpiry = expirationTime - now;
    
    // If token expires in less than 5 minutes, refresh it
    if (timeUntilExpiry < 5 * 60 * 1000) {
        return await refreshAuthToken();
    }
    
    // Token is still valid, schedule refresh
    scheduleTokenRefresh();
    return true;
}

// Refresh the authentication token using refresh token
async function refreshAuthToken() {
    const refreshToken = localStorage.getItem('refreshToken');
    
    if (!refreshToken) {
        return false;
    }
    
    try {
        const authUrl = `https://cognito-idp.${COGNITO_CONFIG.region}.amazonaws.com/`;
        
        const refreshData = {
            AuthFlow: 'REFRESH_TOKEN_AUTH',
            ClientId: COGNITO_CONFIG.clientId,
            AuthParameters: {
                REFRESH_TOKEN: refreshToken
            }
        };

        const response = await fetch(authUrl, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/x-amz-json-1.1',
                'X-Amz-Target': 'AWSCognitoIdentityProviderService.InitiateAuth'
            },
            body: JSON.stringify(refreshData)
        });

        const data = await response.json();

        if (response.ok && data.AuthenticationResult) {
            // Update tokens
            const expiresIn = data.AuthenticationResult.ExpiresIn || 3600;
            const expirationTime = Date.now() + (expiresIn * 1000);
            
            localStorage.setItem('idToken', data.AuthenticationResult.IdToken);
            localStorage.setItem('accessToken', data.AuthenticationResult.AccessToken);
            localStorage.setItem('tokenExpiration', expirationTime);
            
            // Schedule next refresh
            scheduleTokenRefresh();
            
            console.log('Token refreshed successfully');
            return true;
        } else {
            console.error('Token refresh failed:', data);
            return false;
        }
    } catch (error) {
        console.error('Error refreshing token:', error);
        return false;
    }
}

// Schedule automatic token refresh before expiration
function scheduleTokenRefresh() {
    // Clear any existing timer
    if (window.tokenRefreshTimer) {
        clearTimeout(window.tokenRefreshTimer);
    }
    
    const tokenExpiration = localStorage.getItem('tokenExpiration');
    if (!tokenExpiration) {
        return;
    }
    
    const expirationTime = parseInt(tokenExpiration);
    const now = Date.now();
    const timeUntilExpiry = expirationTime - now;
    
    // Refresh 5 minutes before expiration
    const refreshTime = Math.max(timeUntilExpiry - (5 * 60 * 1000), 0);
    
    window.tokenRefreshTimer = setTimeout(async () => {
        const success = await refreshAuthToken();
        if (!success) {
            showAlert('⚠️ Session expired. Please log in again.', 'error');
            logout();
        }
    }, refreshTime);
}

function toggleUserMenu() {
    const menu = document.getElementById('userMenu');
    menu.classList.toggle('show');
}

async function login() {
    const email = document.getElementById('email').value.trim();
    const password = document.getElementById('password').value;
    const alertDiv = document.getElementById('alert');

    if (!email || !password) {
        showAlert('Please enter email and password', 'error');
        return;
    }

    // Disable login button during request
    const loginBtn = document.querySelector('.login-btn');
    loginBtn.disabled = true;
    loginBtn.textContent = 'Logging in...';

    try {
        const authUrl = `https://cognito-idp.${COGNITO_CONFIG.region}.amazonaws.com/`;
        
        const authData = {
            AuthFlow: 'USER_PASSWORD_AUTH',
            ClientId: COGNITO_CONFIG.clientId,
            AuthParameters: {
                USERNAME: email,
                PASSWORD: password
            }
        };

        const response = await fetch(authUrl, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/x-amz-json-1.1',
                'X-Amz-Target': 'AWSCognitoIdentityProviderService.InitiateAuth'
            },
            body: JSON.stringify(authData)
        });

        const data = await response.json();

        if (response.ok && data.AuthenticationResult) {
            // Store tokens and expiration time
            const expiresIn = data.AuthenticationResult.ExpiresIn || 3600; // Default 1 hour
            const expirationTime = Date.now() + (expiresIn * 1000);
            
            localStorage.setItem('idToken', data.AuthenticationResult.IdToken);
            localStorage.setItem('accessToken', data.AuthenticationResult.AccessToken);
            localStorage.setItem('refreshToken', data.AuthenticationResult.RefreshToken);
            localStorage.setItem('tokenExpiration', expirationTime);
            localStorage.setItem('userEmail', email);

            showLoggedInState(email);
            showAlert('✅ Login successful!', 'success');
            
            // Start token refresh timer
            scheduleTokenRefresh();
            
            // Clear password field
            document.getElementById('password').value = '';
            
            // Auto-load books after successful login
            setTimeout(() => fetchBooks(), 500);
        } else {
            throw new Error(data.message || 'Invalid credentials');
        }
    } catch (error) {
        showAlert(`❌ Login failed: ${error.message}`, 'error');
        console.error('Login error:', error);
        loginBtn.disabled = false;
        loginBtn.textContent = 'Login';
    }
}

function logout() {
    localStorage.removeItem('idToken');
    localStorage.removeItem('accessToken');
    localStorage.removeItem('refreshToken');
    localStorage.removeItem('tokenExpiration');
    localStorage.removeItem('userEmail');
    
    // Clear any scheduled token refresh
    if (window.tokenRefreshTimer) {
        clearTimeout(window.tokenRefreshTimer);
    }
    
    // Hide admin-only UI elements
    const fabUpload = document.getElementById('fabUpload');
    if (fabUpload) {
        fabUpload.style.display = 'none';
    }
    window.isUserAdmin = false;
    
    showLoggedOutState();
    document.getElementById('userMenu').classList.remove('show');
    document.getElementById('booksContainer').innerHTML = '';
    showAlert('Logged out successfully', 'success');
}

function showLoggedInState(email) {
    document.getElementById('loginForm').style.display = 'none';
    document.getElementById('userAvatar').style.display = 'flex';
    document.getElementById('menuEmail').textContent = email;
    document.getElementById('controlsRow').style.display = 'flex';
    
    // Set avatar initial (first letter of email)
    const initial = email.charAt(0).toUpperCase();
    document.getElementById('avatarInitial').textContent = initial;
}

function showLoggedOutState() {
    document.getElementById('loginForm').style.display = 'flex';
    document.getElementById('userAvatar').style.display = 'none';
    document.getElementById('controlsRow').style.display = 'none';
    allBooks = [];
}

function showAlert(message, type) {
    const alertDiv = document.getElementById('alert');
    alertDiv.className = `alert ${type}`;
    alertDiv.textContent = message;
    alertDiv.style.display = 'block';
    
    // Auto-hide after 5 seconds
    setTimeout(() => {
        alertDiv.style.display = 'none';
    }, 5000);
}

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
        
        // Render the books
        renderBooks(books);
        
    } catch (error) {
        showAlert(`❌ Failed to load books: ${error.message}`, 'error');
        console.error('Error fetching books:', error);
    } finally {
        loadingSpinner.style.display = 'none';
    }
}

function renderBooks(books, groupByAuthor = false) {
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
    
    showAlert(`✅ Loaded ${books.length} books successfully`, 'success');
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

// Apply filters based on filter controls
function applyFilters() {
    const hideRead = document.getElementById('hideReadBooks').checked;
    const groupByAuthor = document.getElementById('groupByAuthor').checked;
    
    let filteredBooks = allBooks;
    
    // Filter out read books if checkbox is checked
    if (hideRead) {
        filteredBooks = allBooks.filter(book => !book.read);
    }
    
    // Re-render with filtered books
    renderBooks(filteredBooks, groupByAuthor);
    
    // Update success message
    if (hideRead && filteredBooks.length < allBooks.length) {
        const hiddenCount = allBooks.length - filteredBooks.length;
        showAlert(`📚 Showing ${filteredBooks.length} books (${hiddenCount} read books hidden)`, 'success');
    }
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function formatBytes(bytes) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

// Read status management (synced with backend)
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

// Upload functionality
let selectedFile = null;

function showUploadModal() {
    // Check if user is admin
    if (!window.isUserAdmin) {
        showAlert('❌ Only administrators can upload books', 'error');
        return;
    }
    
    document.getElementById('uploadModal').style.display = 'flex';
    // Reset form
    document.getElementById('bookFile').value = '';
    document.getElementById('authorName').value = '';
    document.getElementById('fileInfo').classList.remove('show');
    document.getElementById('uploadButton').disabled = true;
    document.getElementById('uploadProgress').style.display = 'none';
    selectedFile = null;
}

function closeUploadModal() {
    document.getElementById('uploadModal').style.display = 'none';
}

function handleFileSelect() {
    const fileInput = document.getElementById('bookFile');
    const fileInfo = document.getElementById('fileInfo');
    const uploadButton = document.getElementById('uploadButton');
    
    if (fileInput.files.length > 0) {
        selectedFile = fileInput.files[0];
        
        // Validate file type
        if (!selectedFile.name.toLowerCase().endsWith('.zip')) {
            showAlert('❌ Please select a .zip file', 'error');
            fileInput.value = '';
            selectedFile = null;
            uploadButton.disabled = true;
            fileInfo.classList.remove('show');
            return;
        }
        
        // Validate file size (5GB max)
        const maxSize = 5 * 1024 * 1024 * 1024; // 5GB in bytes
        if (selectedFile.size > maxSize) {
            showAlert('❌ File size exceeds 5GB limit', 'error');
            fileInput.value = '';
            selectedFile = null;
            uploadButton.disabled = true;
            fileInfo.classList.remove('show');
            return;
        }
        
        // Show file info
        const sizeInMB = (selectedFile.size / (1024 * 1024)).toFixed(2);
        const sizeInGB = (selectedFile.size / (1024 * 1024 * 1024)).toFixed(2);
        const displaySize = selectedFile.size > 1024 * 1024 * 1024 ? `${sizeInGB} GB` : `${sizeInMB} MB`;
        fileInfo.textContent = `✓ ${selectedFile.name} (${displaySize})`;
        fileInfo.classList.add('show');
        uploadButton.disabled = false;
        
        // Try to auto-populate metadata from Google Books API
        const bookTitle = selectedFile.name.replace('.zip', '');
        fetchBookMetadata(bookTitle);
    } else {
        selectedFile = null;
        uploadButton.disabled = true;
        fileInfo.classList.remove('show');
    }
}

async function fetchBookMetadata(bookTitle) {
    const statusEl = document.getElementById('apiLookupStatus');
    const authorInput = document.getElementById('authorName');
    const seriesNameInput = document.getElementById('uploadSeriesName');
    const seriesOrderInput = document.getElementById('uploadSeriesOrder');
    
    // Show loading status
    statusEl.textContent = '🔍 Looking up book information...';
    statusEl.style.display = 'block';
    statusEl.style.color = '#7f8c8d';
    
    try {
        // Clean up the title for better search results
        let searchQuery = bookTitle;
        
        // If format is "Author - Title", extract just the title for search
        if (bookTitle.includes(' - ')) {
            const parts = bookTitle.split(' - ');
            searchQuery = parts[1] || parts[0];
        }
        
        // Call Google Books API
        const response = await fetch(
            `https://www.googleapis.com/books/v1/volumes?q=${encodeURIComponent(searchQuery)}&maxResults=1`
        );
        
        if (!response.ok) {
            throw new Error('API request failed');
        }
        
        const data = await response.json();
        
        if (data.items && data.items.length > 0) {
            const book = data.items[0].volumeInfo;
            
            // Auto-fill author if available and field is empty
            if (book.authors && book.authors.length > 0 && !authorInput.value) {
                authorInput.value = book.authors[0];
            }
            
            // Check for series information in the title or description
            const title = book.title || '';
            const subtitle = book.subtitle || '';
            const fullTitle = subtitle ? `${title}: ${subtitle}` : title;
            
            // Try to extract series info from title
            // Common patterns: "Series Name, Book 1", "Series Name #1", "(Series Name Book 1)"
            const seriesPatterns = [
                /\(([^)]+?)\s+(?:Book|#)\s*(\d+)\)/i,  // (Series Name Book 1) or (Series Name #1)
                /([^,]+),\s+(?:Book|Volume|Vol\.?)\s*(\d+)/i,  // Series Name, Book 1
                /:?\s*(?:Book|Volume|Vol\.?)\s*(\d+)\s+of\s+(.+)/i,  // Book 1 of Series Name
                /([^#]+)\s+#(\d+)/,  // Series Name #1
            ];
            
            let seriesFound = false;
            for (const pattern of seriesPatterns) {
                const match = fullTitle.match(pattern);
                if (match) {
                    if (!seriesNameInput.value) {
                        seriesNameInput.value = match[1].trim();
                    }
                    if (!seriesOrderInput.value) {
                        seriesOrderInput.value = match[2];
                    }
                    seriesFound = true;
                    break;
                }
            }
            
            statusEl.textContent = seriesFound 
                ? '✓ Found book information and series details' 
                : '✓ Found book information (no series detected)';
            statusEl.style.color = '#27ae60';
        } else {
            statusEl.textContent = 'ℹ️ No book information found - you can fill in manually';
            statusEl.style.color = '#7f8c8d';
        }
    } catch (error) {
        console.error('Error fetching book metadata:', error);
        statusEl.textContent = 'ℹ️ Could not fetch book information - you can fill in manually';
        statusEl.style.color = '#7f8c8d';
    }
    
    // Hide status after 5 seconds
    setTimeout(() => {
        statusEl.style.display = 'none';
    }, 5000);
}

async function uploadBook() {
    // Check if user is admin
    if (!window.isUserAdmin) {
        showAlert('❌ Only administrators can upload books', 'error');
        return;
    }
    
    if (!selectedFile) {
        showAlert('❌ Please select a file', 'error');
        return;
    }
    
    const authorInput = document.getElementById('authorName');
    const author = authorInput.value.trim();
    const seriesNameInput = document.getElementById('uploadSeriesName');
    const seriesName = seriesNameInput.value.trim();
    const seriesOrderInput = document.getElementById('uploadSeriesOrder');
    const seriesOrder = seriesOrderInput.value.trim();
    const uploadButton = document.getElementById('uploadButton');
    const progressDiv = document.getElementById('uploadProgress');
    const progressFill = document.getElementById('progressFill');
    const progressText = document.getElementById('progressText');
    
    try {
        // Disable upload button
        uploadButton.disabled = true;
        uploadButton.textContent = 'Uploading...';
        
        // Step 1: Get presigned upload URL from backend
        progressText.textContent = 'Preparing upload...';
        progressDiv.style.display = 'block';
        progressFill.style.width = '10%';
        
        const token = localStorage.getItem('idToken');
        if (!token) {
            throw new Error('Not authenticated. Please log in.');
        }
        
        const uploadRequestBody = {
            filename: selectedFile.name,
            fileSize: selectedFile.size,
            author: author || undefined
        };
        
        // Upload endpoint is at /upload (not /books/upload)
        const uploadUrl = API_URL.replace('/books', '') + '/upload';
        const response = await fetch(uploadUrl, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`
            },
            body: JSON.stringify(uploadRequestBody)
        });
        
        if (response.status === 401 || response.status === 403) {
            const refreshed = await refreshIdToken();
            if (refreshed) {
                return uploadBook(); // Retry with new token
            } else {
                throw new Error('Session expired. Please log in again.');
            }
        }
        
        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.message || `HTTP error! status: ${response.status}`);
        }
        
        const uploadData = await response.json();
        progressFill.style.width = '30%';
        
        // Step 2: Upload file to S3 using presigned PUT URL with XMLHttpRequest for progress tracking
        progressText.textContent = 'Uploading to S3...';
        
        await new Promise((resolve, reject) => {
            const xhr = new XMLHttpRequest();
            
            // Track upload progress
            xhr.upload.addEventListener('progress', (e) => {
                if (e.lengthComputable) {
                    const percentComplete = (e.loaded / e.total) * 60; // 30% to 90% range
                    progressFill.style.width = `${30 + percentComplete}%`;
                    
                    // Show upload size
                    const mbLoaded = (e.loaded / 1024 / 1024).toFixed(1);
                    const mbTotal = (e.total / 1024 / 1024).toFixed(1);
                    if (e.total > 1024 * 1024 * 1024) {
                        // Show in GB for large files
                        const gbLoaded = (e.loaded / 1024 / 1024 / 1024).toFixed(2);
                        const gbTotal = (e.total / 1024 / 1024 / 1024).toFixed(2);
                        progressText.textContent = `Uploading: ${gbLoaded} GB / ${gbTotal} GB`;
                    } else {
                        progressText.textContent = `Uploading: ${mbLoaded} MB / ${mbTotal} MB`;
                    }
                }
            });
            
            xhr.addEventListener('load', () => {
                if (xhr.status === 200) {
                    progressFill.style.width = '90%';
                    progressText.textContent = 'Processing...';
                    resolve();
                } else {
                    reject(new Error(`S3 upload failed: ${xhr.status} ${xhr.statusText}`));
                }
            });
            
            xhr.addEventListener('error', () => {
                reject(new Error('Network error during S3 upload'));
            });
            
            xhr.addEventListener('abort', () => {
                reject(new Error('Upload was aborted'));
            });
            
            xhr.addEventListener('timeout', () => {
                reject(new Error('Upload timed out'));
            });
            
            // Set a longer timeout for large files (30 minutes)
            xhr.timeout = 1800000;
            
            xhr.open('PUT', uploadData.uploadUrl);
            xhr.setRequestHeader('Content-Type', 'application/zip');
            xhr.send(selectedFile);
        });
        
        progressFill.style.width = '95%';
        progressText.textContent = 'Processing...';
        
        // Wait for S3 trigger to process and create DynamoDB record
        await new Promise(resolve => setTimeout(resolve, 2000));
        
        // Step 3: Set metadata (author, series fields) if provided
        if (author || seriesName || seriesOrder) {
            try {
                // Extract book ID from filename (remove .zip extension)
                const bookId = selectedFile.name.replace('.zip', '');
                
                const metadataUrl = API_URL.replace('/books', '') + '/upload/metadata';
                
                // Build metadata payload
                const metadataPayload = { bookId };
                if (author) metadataPayload.author = author;
                if (seriesName) metadataPayload.series_name = seriesName;
                if (seriesOrder) metadataPayload.series_order = parseInt(seriesOrder, 10);
                
                // Retry logic in case S3 trigger hasn't finished yet
                let retries = 3;
                let success = false;
                
                while (retries > 0 && !success) {
                    const metadataResponse = await fetch(metadataUrl, {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                            'Authorization': `Bearer ${token}`
                        },
                        body: JSON.stringify(metadataPayload)
                    });
                    
                    if (metadataResponse.ok) {
                        console.log(`Successfully set metadata for ${bookId}`);
                        success = true;
                    } else if (metadataResponse.status === 404) {
                        // Record not found yet, S3 trigger still processing
                        console.log(`Book record not ready yet, retrying... (${retries} attempts left)`);
                        retries--;
                        if (retries > 0) {
                            await new Promise(resolve => setTimeout(resolve, 1000));
                        }
                    } else {
                        console.warn(`Failed to set metadata: ${metadataResponse.status}`);
                        break;
                    }
                }
                
                if (!success) {
                    console.warn('Failed to set metadata after retries');
                }
            } catch (metadataError) {
                // Don't fail the entire upload if metadata update fails
                console.warn('Failed to set metadata:', metadataError);
            }
        }
        
        progressFill.style.width = '100%';
        progressText.textContent = 'Upload complete!';
        
        showAlert(`✅ Successfully uploaded ${selectedFile.name}`, 'success');
        
        // Close modal after short delay
        setTimeout(() => {
            closeUploadModal();
            // Refresh the books list
            fetchBooks();
        }, 1500);
        
    } catch (error) {
        showAlert(`❌ Upload failed: ${error.message}`, 'error');
        console.error('Error uploading book:', error);
        uploadButton.disabled = false;
        uploadButton.textContent = 'Upload';
        progressDiv.style.display = 'none';
    }
}

// Close modal when clicking outside
document.addEventListener('click', (e) => {
    const uploadModal = document.getElementById('uploadModal');
    if (e.target === uploadModal) {
        closeUploadModal();
    }
    
    const detailsModal = document.getElementById('bookDetailsModal');
    if (e.target === detailsModal) {
        closeBookDetailsModal();
    }
});

// Book details modal functionality
let currentEditingBook = null;

function showBookDetailsModal(book) {
    currentEditingBook = book;
    
    // Populate modal with book details
    document.getElementById('detailTitle').textContent = book.name || 'Unknown';
    
    // Format date
    if (book.created) {
        const date = new Date(book.created);
        const formattedDate = date.toLocaleDateString('en-US', {
            year: 'numeric',
            month: 'long',
            day: 'numeric',
            hour: '2-digit',
            minute: '2-digit'
        });
        document.getElementById('detailDate').textContent = formattedDate;
    } else {
        document.getElementById('detailDate').textContent = 'Unknown';
    }
    
    // Format file size
    if (book.size) {
        const sizeInMB = (book.size / (1024 * 1024)).toFixed(2);
        const sizeInGB = (book.size / (1024 * 1024 * 1024)).toFixed(2);
        const displaySize = book.size > 1024 * 1024 * 1024 
            ? `${sizeInGB} GB` 
            : `${sizeInMB} MB`;
        document.getElementById('detailSize').textContent = displaySize;
    } else {
        document.getElementById('detailSize').textContent = 'Unknown';
    }
    
    // Set author field
    document.getElementById('editAuthor').value = book.author || '';
    
    // Set series fields
    document.getElementById('editSeriesName').value = book.series_name || '';
    document.getElementById('editSeriesOrder').value = book.series_order || '';
    
    // Show/hide delete button based on admin status
    const deleteButton = document.getElementById('deleteBookButton');
    if (window.isUserAdmin) {
        deleteButton.style.display = 'inline-block';
    } else {
        deleteButton.style.display = 'none';
    }
    
    // Show modal
    document.getElementById('bookDetailsModal').style.display = 'flex';
}

function closeBookDetailsModal() {
    document.getElementById('bookDetailsModal').style.display = 'none';
    currentEditingBook = null;
}

async function saveBookDetails() {
    if (!currentEditingBook) {
        showAlert('❌ No book selected', 'error');
        return;
    }
    
    const token = localStorage.getItem('idToken');
    if (!token) {
        showAlert('❌ Not authenticated. Please log in.', 'error');
        return;
    }
    
    const newAuthor = document.getElementById('editAuthor').value.trim();
    const newSeriesName = document.getElementById('editSeriesName').value.trim();
    const newSeriesOrder = document.getElementById('editSeriesOrder').value.trim();
    const saveButton = document.getElementById('saveDetailsButton');
    
    // Validate series order if provided
    if (newSeriesOrder && !/^\d+$/.test(newSeriesOrder)) {
        showAlert('❌ Series order must be a number', 'error');
        return;
    }
    
    if (newSeriesOrder) {
        const orderNum = parseInt(newSeriesOrder, 10);
        if (orderNum < 1 || orderNum > 100) {
            showAlert('❌ Series order must be between 1 and 100', 'error');
            return;
        }
    }
    
    // Check if any field actually changed
    const oldAuthor = currentEditingBook.author || '';
    const oldSeriesName = currentEditingBook.series_name || '';
    const oldSeriesOrder = currentEditingBook.series_order ? String(currentEditingBook.series_order) : '';
    
    if (newAuthor === oldAuthor && newSeriesName === oldSeriesName && newSeriesOrder === oldSeriesOrder) {
        showAlert('ℹ️ No changes to save', 'success');
        closeBookDetailsModal();
        return;
    }
    
    try {
        // Disable save button
        saveButton.disabled = true;
        saveButton.textContent = 'Saving...';
        
        // Prepare update body with only changed fields
        const updateBody = {};
        
        if (newAuthor !== oldAuthor) {
            updateBody.author = newAuthor;  // Send empty string if cleared
        }
        
        if (newSeriesName !== oldSeriesName) {
            updateBody.series_name = newSeriesName;  // Send empty string if cleared
        }
        
        if (newSeriesOrder !== oldSeriesOrder) {
            // Convert to integer or null
            updateBody.series_order = newSeriesOrder ? parseInt(newSeriesOrder, 10) : null;
        }
        
        // Call PATCH /books/{id}
        const bookId = encodeURIComponent(currentEditingBook.id);
        const response = await fetch(`${API_URL}/${bookId}`, {
            method: 'PATCH',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': token
            },
            body: JSON.stringify(updateBody)
        });
        
        if (response.status === 401 || response.status === 403) {
            const refreshed = await refreshAuthToken();
            if (refreshed) {
                return saveBookDetails(); // Retry with new token
            } else {
                throw new Error('Session expired. Please log in again.');
            }
        }
        
        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.message || `HTTP error! status: ${response.status}`);
        }
        
        const updatedBook = await response.json();
        
        // Update the book in the local allBooks array
        const bookIndex = allBooks.findIndex(b => b.id === currentEditingBook.id);
        if (bookIndex !== -1) {
            allBooks[bookIndex] = { 
                ...allBooks[bookIndex], 
                author: updatedBook.author,
                series_name: updatedBook.series_name,
                series_order: updatedBook.series_order
            };
        }
        
        // Re-render with current filter state preserved
        applyFilters();
        
        showAlert('✅ Book details updated successfully', 'success');
        closeBookDetailsModal();
        
    } catch (error) {
        showAlert(`❌ Failed to update: ${error.message}`, 'error');
        console.error('Error updating book details:', error);
    } finally {
        saveButton.disabled = false;
        saveButton.textContent = 'Save Changes';
    }
}

async function deleteBook() {
    if (!currentEditingBook) {
        showAlert('❌ No book selected', 'error');
        return;
    }
    
    // Confirmation dialog
    const bookName = currentEditingBook.name || 'this book';
    const confirmMessage = `⚠️ Are you sure you want to delete "${bookName}"?\n\nThis action is PERMANENT and cannot be undone.\n\nThe book will be removed from both the database and storage.`;
    
    if (!confirm(confirmMessage)) {
        return; // User cancelled
    }
    
    const token = localStorage.getItem('idToken');
    if (!token) {
        showAlert('❌ Not authenticated. Please log in.', 'error');
        return;
    }
    
    const deleteButton = document.getElementById('deleteBookButton');
    
    try {
        // Disable delete button
        deleteButton.disabled = true;
        deleteButton.textContent = 'Deleting...';
        
        // Call DELETE /books/{id}
        const bookId = encodeURIComponent(currentEditingBook.id);
        const response = await fetch(`${API_URL}/${bookId}`, {
            method: 'DELETE',
            headers: {
                'Authorization': token
            }
        });
        
        if (response.status === 401 || response.status === 403) {
            const refreshed = await refreshAuthToken();
            if (refreshed) {
                return deleteBook(); // Retry with new token
            } else {
                throw new Error('Session expired. Please log in again.');
            }
        }
        
        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.message || `HTTP error! status: ${response.status}`);
        }
        
        // Remove the book from local allBooks array
        allBooks = allBooks.filter(b => b.id !== currentEditingBook.id);
        
        // Re-render with current filter state preserved
        applyFilters();
        
        showAlert('✅ Book deleted successfully', 'success');
        closeBookDetailsModal();
        
    } catch (error) {
        showAlert(`❌ Failed to delete: ${error.message}`, 'error');
        console.error('Error deleting book:', error);
        deleteButton.disabled = false;
        deleteButton.textContent = '🗑️ Delete Book';
    }
}
