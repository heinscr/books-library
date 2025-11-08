/**
 * Book details modal module
 * Handles book details viewing and editing
 */

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

    // Show/hide more options menu based on admin status
    const moreOptionsContainer = document.getElementById('moreOptionsContainer');
    if (window.isUserAdmin) {
        moreOptionsContainer.style.display = 'block';
    } else {
        moreOptionsContainer.style.display = 'none';
    }

    // Close dropdown menu if it was open
    const deleteMenu = document.getElementById('deleteMenu');
    if (deleteMenu) {
        deleteMenu.style.display = 'none';
    }

    // Show modal
    const modal = document.getElementById('bookDetailsModal');
    modal.style.display = 'flex';

    // Store element that had focus before modal opened
    window.lastFocusedElement = document.activeElement;

    // Focus the author input when modal opens
    setTimeout(() => {
        document.getElementById('editAuthor').focus();
    }, 100);

    // Set up focus trapping
    setupModalFocusTrap('bookDetailsModal');
}

function closeBookDetailsModal() {
    document.getElementById('bookDetailsModal').style.display = 'none';
    currentEditingBook = null;

    // Close dropdown menu if open
    const deleteMenu = document.getElementById('deleteMenu');
    if (deleteMenu) {
        deleteMenu.style.display = 'none';
    }

    const moreOptionsButton = document.getElementById('moreOptionsButton');
    if (moreOptionsButton) {
        moreOptionsButton.setAttribute('aria-expanded', 'false');
    }

    // Return focus to element that opened the modal
    if (window.lastFocusedElement) {
        window.lastFocusedElement.focus();
        window.lastFocusedElement = null;
    }
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
            // Replace with the full updated book object from the server
            allBooks[bookIndex] = updatedBook;
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

    // Get the delete menu item button
    const deleteMenu = document.getElementById('deleteMenu');
    const deleteMenuItem = deleteMenu ? deleteMenu.querySelector('.menu-item-danger') : null;
    const deleteMenuTextSpan = deleteMenuItem ? deleteMenuItem.querySelector('span:last-child') : null;
    const originalText = deleteMenuTextSpan ? deleteMenuTextSpan.textContent : '';

    try {
        // Disable delete menu item during deletion
        if (deleteMenuItem) {
            deleteMenuItem.disabled = true;
            if (deleteMenuTextSpan) {
                deleteMenuTextSpan.textContent = 'Deleting...';
            }
        }

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
                // Re-enable button before retry
                if (deleteMenuItem) {
                    deleteMenuItem.disabled = false;
                    if (deleteMenuTextSpan) {
                        deleteMenuTextSpan.textContent = originalText;
                    }
                }
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
        // Re-enable delete menu item on error
        if (deleteMenuItem) {
            deleteMenuItem.disabled = false;
            if (deleteMenuTextSpan) {
                deleteMenuTextSpan.textContent = originalText;
            }
        }
        showAlert(`❌ Failed to delete: ${error.message}`, 'error');
        console.error('Error deleting book:', error);
    }
}

function toggleDeleteMenu(event) {
    event.stopPropagation();

    const deleteMenu = document.getElementById('deleteMenu');
    const moreOptionsButton = document.getElementById('moreOptionsButton');
    const isOpen = deleteMenu.style.display === 'block';

    if (isOpen) {
        deleteMenu.style.display = 'none';
        moreOptionsButton.setAttribute('aria-expanded', 'false');
    } else {
        deleteMenu.style.display = 'block';
        moreOptionsButton.setAttribute('aria-expanded', 'true');

        // Focus first menu item for keyboard accessibility
        const firstMenuItem = deleteMenu.querySelector('.menu-item-danger');
        if (firstMenuItem) {
            setTimeout(() => firstMenuItem.focus(), 100);
        }
    }
}

// Close dropdown when clicking outside
document.addEventListener('click', function(event) {
    const moreOptionsContainer = document.getElementById('moreOptionsContainer');
    const deleteMenu = document.getElementById('deleteMenu');
    const moreOptionsButton = document.getElementById('moreOptionsButton');

    if (moreOptionsContainer && deleteMenu && moreOptionsButton) {
        if (!moreOptionsContainer.contains(event.target)) {
            deleteMenu.style.display = 'none';
            moreOptionsButton.setAttribute('aria-expanded', 'false');
        }
    }
});
