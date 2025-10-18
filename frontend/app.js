// Cognito configuration
const COGNITO_CONFIG = {
    userPoolId: 'us-east-1_7RUbNyZe8',
    clientId: '4s3ffigml0qellh579al1oqifu',
    region: 'us-east-1'
};

const API_URL = 'https://vlii8j82ug.execute-api.us-east-2.amazonaws.com/Prod/books';

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
    
    // Set avatar initial (first letter of email)
    const initial = email.charAt(0).toUpperCase();
    document.getElementById('avatarInitial').textContent = initial;
}

function showLoggedOutState() {
    document.getElementById('loginForm').style.display = 'flex';
    document.getElementById('userAvatar').style.display = 'none';
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
        
        if (books.length === 0) {
            booksContainer.innerHTML = `
                <div class="empty-state">
                    <div class="empty-state-icon">📚</div>
                    <h3>No books found</h3>
                    <p>Your library is empty.</p>
                </div>
            `;
        } else {
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
                
                // Add click handler for download (but not on the read toggle)
                bookCard.addEventListener('click', (e) => {
                    if (!e.target.closest('.read-toggle')) {
                        downloadBook(book.id);
                    }
                });
                
                booksGrid.appendChild(bookCard);
            });
            
            booksContainer.appendChild(booksGrid);
            showAlert(`✅ Loaded ${books.length} books successfully`, 'success');
        }
        
    } catch (error) {
        showAlert(`❌ Error: ${error.message}`, 'error');
        console.error('Error fetching books:', error);
        
        // If auth error, logout
        if (error.message.includes('Authentication expired')) {
            setTimeout(() => logout(), 2000);
        }
    } finally {
        // Hide loading
        loadingSpinner.style.display = 'none';
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
