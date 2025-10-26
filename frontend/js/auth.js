/**
 * Authentication module for Cognito user management
 */

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

    // Reset login button state
    const loginBtn = document.querySelector('.login-btn');
    if (loginBtn) {
        loginBtn.disabled = false;
        loginBtn.textContent = 'Login';
    }
}

/**
 * Toggle user menu dropdown and update ARIA state
 */
function toggleUserMenu() {
    const userMenu = document.getElementById('userMenu');
    const userAvatar = document.getElementById('userAvatar');
    const isShown = userMenu.classList.toggle('show');

    // Update ARIA expanded state
    if (userAvatar) {
        userAvatar.setAttribute('aria-expanded', isShown ? 'true' : 'false');
    }
}

// Close user menu when clicking outside
document.addEventListener('click', function(event) {
    const userMenu = document.getElementById('userMenu');
    const userAvatar = document.getElementById('userAvatar');

    if (userMenu && userAvatar) {
        if (!userAvatar.contains(event.target) && !userMenu.contains(event.target)) {
            userMenu.classList.remove('show');
            userAvatar.setAttribute('aria-expanded', 'false');
        }
    }
});

// Close user menu on Escape key
document.addEventListener('keydown', function(event) {
    if (event.key === 'Escape') {
        const userMenu = document.getElementById('userMenu');
        const userAvatar = document.getElementById('userAvatar');
        if (userMenu && userMenu.classList.contains('show')) {
            userMenu.classList.remove('show');
            if (userAvatar) {
                userAvatar.setAttribute('aria-expanded', 'false');
                userAvatar.focus(); // Return focus to button
            }
        }
    }
});

