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
        
        const books = await response.json();
        
        // Store books globally for filtering
        allBooks = books;
        
        // Controls row is already shown when logged in (contains upload button)
        // No need to show/hide it here
        
        // Render the books
        renderBooks(books);
        
    } catch (error) {
        showAlert(`❌ Failed to load books: ${error.message}`, 'error');
        console.error('Error fetching books:', error);
    } finally {
        loadingSpinner.style.display = 'none';
    }
}

function renderBooks(books) {
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
    
    // Display books in grid
    const booksGrid = document.createElement('div');
    booksGrid.className = 'books-grid';
    
    books.forEach(book => {
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
                <div class="read-toggle ${isRead ? 'read' : ''}" onclick="toggleReadStatus('${escapeHtml(book.id)}', event)" title="${isRead ? 'Mark as unread' : 'Mark as read'}">
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
        
        // Add click handler for the card - opens details modal, unless clicking special elements
        bookCard.addEventListener('click', (e) => {
            // Don't open modal if clicking the read toggle
            if (e.target.closest('.read-toggle')) {
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
        
        booksGrid.appendChild(bookCard);
    });
    
    booksContainer.appendChild(booksGrid);
    showAlert(`✅ Loaded ${books.length} books successfully`, 'success');
}

// Apply filters based on filter controls
function applyFilters() {
    const hideRead = document.getElementById('hideReadBooks').checked;
    
    let filteredBooks = allBooks;
    
    // Filter out read books if checkbox is checked
    if (hideRead) {
        filteredBooks = allBooks.filter(book => !book.read);
    }
    
    // Re-render with filtered books
    renderBooks(filteredBooks);
    
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
    } else {
        selectedFile = null;
        uploadButton.disabled = true;
        fileInfo.classList.remove('show');
    }
}

async function uploadBook() {
    if (!selectedFile) {
        showAlert('❌ Please select a file', 'error');
        return;
    }
    
    const authorInput = document.getElementById('authorName');
    const author = authorInput.value.trim();
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
        
        // Step 3: Set author metadata if provided
        if (author) {
            try {
                // Extract book ID from filename (remove .zip extension)
                const bookId = selectedFile.name.replace('.zip', '');
                
                const metadataUrl = API_URL.replace('/books', '') + '/upload/metadata';
                
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
                        body: JSON.stringify({
                            bookId: bookId,
                            author: author
                        })
                    });
                    
                    if (metadataResponse.ok) {
                        console.log(`Successfully set author metadata for ${bookId}`);
                        success = true;
                    } else if (metadataResponse.status === 404) {
                        // Record not found yet, S3 trigger still processing
                        console.log(`Book record not ready yet, retrying... (${retries} attempts left)`);
                        retries--;
                        if (retries > 0) {
                            await new Promise(resolve => setTimeout(resolve, 1000));
                        }
                    } else {
                        console.warn(`Failed to set author metadata: ${metadataResponse.status}`);
                        break;
                    }
                }
                
                if (!success) {
                    console.warn('Failed to set author metadata after retries');
                }
            } catch (metadataError) {
                // Don't fail the entire upload if metadata update fails
                console.warn('Failed to set author metadata:', metadataError);
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
    const saveButton = document.getElementById('saveDetailsButton');
    
    // Check if author actually changed
    const oldAuthor = currentEditingBook.author || '';
    if (newAuthor === oldAuthor) {
        showAlert('ℹ️ No changes to save', 'success');
        closeBookDetailsModal();
        return;
    }
    
    try {
        // Disable save button
        saveButton.disabled = true;
        saveButton.textContent = 'Saving...';
        
        // Prepare update body
        const updateBody = {
            author: newAuthor  // Send empty string if cleared
        };
        
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
            allBooks[bookIndex] = { ...allBooks[bookIndex], author: updatedBook.author };
        }
        
        // Re-render just the updated book card
        renderBooks(allBooks);
        
        showAlert('✅ Author updated successfully', 'success');
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
        
        // Re-render books
        renderBooks(allBooks);
        
        showAlert('✅ Book deleted successfully', 'success');
        closeBookDetailsModal();
        
    } catch (error) {
        showAlert(`❌ Failed to delete: ${error.message}`, 'error');
        console.error('Error deleting book:', error);
        deleteButton.disabled = false;
        deleteButton.textContent = '🗑️ Delete Book';
    }
}
