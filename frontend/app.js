// Books Library Application
// Main application orchestrator

// Store books data for filtering (shared with filters.js and other modules)
var allBooks = [];

// Initialize application when DOM is loaded
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

// Close modals when clicking outside
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
