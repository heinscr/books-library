#!/usr/bin/env python3
"""
Refactor frontend/app.js into modular architecture
Splits 1,425 lines into organized modules
"""

import os
import re

FRONTEND_DIR = "/home/craig/projects/books/frontend"
JS_DIR = os.path.join(FRONTEND_DIR, "js")

# Read the original app.js
with open(os.path.join(FRONTEND_DIR, "app.js"), 'r') as f:
    original_content = f.read()

# Create backups
with open(os.path.join(FRONTEND_DIR, "app.js.backup"), 'w') as f:
    f.write(original_content)

print("✓ Created app.js.backup")

# Module definitions - which functions go in which file
modules = {
    'auth.js': {
        'functions': [
            'checkAndRefreshToken', 'refreshAuthToken', 'scheduleTokenRefresh',
            'login', 'logout', 'showLoggedInState', 'showLoggedOutState'
        ],
        'variables': [],
        'header': '/**\n * Authentication module for Cognito user management\n */'
    },
    'api.js': {
        'functions': [
            'fetchBooks', 'toggleReadStatus', 'downloadBook',
            'saveBookDetails', 'deleteBook'
        ],
        'variables': [],
        'header': '/**\n * API communication module\n * Handles all backend API calls\n */'
    },
    'ui.js': {
        'functions': ['showAlert', 'toggleUserMenu'],
        'variables': [],
        'header': '/**\n * UI utilities module\n * Generic UI helper functions\n */'
    },
    'bookRenderer.js': {
        'functions': ['renderBooks', 'renderBooksAsGrid', 'renderBooksGroupedByAuthor'],
        'variables': [],
        'header': '/**\n * Book rendering module\n * Handles book list display and grouping\n */'
    },
    'bookCard.js': {
        'functions': ['createBookCard'],
        'variables': [],
        'header': '/**\n * Book card component module\n * Creates individual book cards with interactions\n */'
    },
    'filters.js': {
        'functions': ['applyFilters'],
        'variables': ['allBooks'],
        'header': '/**\n * Filtering module\n * Handles book filtering and search\n */'
    },
    'upload.js': {
        'functions': [
            'showUploadModal', 'closeUploadModal', 'handleFileSelect',
            'fetchBookMetadata', 'uploadBook'
        ],
        'variables': ['selectedFile'],
        'header': '/**\n * Upload module\n * Handles book upload functionality\n */'
    },
    'bookDetails.js': {
        'functions': ['showBookDetailsModal', 'closeBookDetailsModal'],
        'variables': ['currentEditingBook'],
        'header': '/**\n * Book details modal module\n * Handles book details viewing and editing\n */'
    }
}

def extract_function(content, func_name):
    """Extract a function definition from content"""
    # Match async function or regular function
    patterns = [
        rf'(async\s+function\s+{func_name}\s*\([^)]*\)\s*\{{)',
        rf'(function\s+{func_name}\s*\([^)]*\)\s*\{{)'
    ]

    for pattern in patterns:
        match = re.search(pattern, content)
        if match:
            start = match.start()
            # Find the matching closing brace
            brace_count = 0
            in_function = False
            end = start

            for i in range(start, len(content)):
                if content[i] == '{':
                    brace_count += 1
                    in_function = True
                elif content[i] == '}':
                    brace_count -= 1
                    if in_function and brace_count == 0:
                        end = i + 1
                        break

            return content[start:end]

    return None

def extract_variable(content, var_name):
    """Extract a variable declaration"""
    patterns = [
        rf'(let\s+{var_name}\s*=\s*[^;]+;)',
        rf'(const\s+{var_name}\s*=\s*[^;]+;)',
        rf'(var\s+{var_name}\s*=\s*[^;]+;)'
    ]

    for pattern in patterns:
        match = re.search(pattern, content, re.MULTILINE)
        if match:
            return match.group(1)

    return None

# Create utils.js (already created)
print("✓ utils.js already created")

# Create each module
for module_name, module_info in modules.items():
    module_path = os.path.join(JS_DIR, module_name)
    with open(module_path, 'w') as f:
        f.write(module_info['header'] + '\n\n')

        # Extract variables
        for var_name in module_info['variables']:
            var_code = extract_variable(original_content, var_name)
            if var_code:
                f.write(var_code + '\n\n')

        # Extract functions
        for func_name in module_info['functions']:
            func_code = extract_function(original_content, func_name)
            if func_code:
                f.write(func_code + '\n\n')
            else:
                print(f"  Warning: Could not find function {func_name}")

    print(f"✓ Created {module_name}")

# Create new minimal app.js
new_app_content = '''// Books Library Application
// Main application orchestrator

// Store books data for filtering (shared with filters.js)
let allBooks = [];

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
'''

with open(os.path.join(FRONTEND_DIR, "app.js"), 'w') as f:
    f.write(new_app_content)

print("✓ Created new minimal app.js (50 lines)")
print(f"\n✅ Refactoring complete!")
print(f"  Original: 1,425 lines → Now split into 10 files")
print(f"  Backup saved as: app.js.backup")
