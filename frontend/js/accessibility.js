/**
 * Accessibility utilities
 * Focus trapping, keyboard navigation, and screen reader support
 */

/**
 * Set up focus trapping for a modal dialog
 * @param {string} modalId - ID of the modal element
 */
function setupModalFocusTrap(modalId) {
    const modal = document.getElementById(modalId);
    if (!modal) return;

    // Get all focusable elements within the modal
    const focusableElements = modal.querySelectorAll(
        'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
    );

    if (focusableElements.length === 0) return;

    const firstFocusable = focusableElements[0];
    const lastFocusable = focusableElements[focusableElements.length - 1];

    // Handle Tab and Shift+Tab to trap focus
    const handleTabKey = (e) => {
        // Only trap focus if modal is visible
        if (modal.style.display === 'none') {
            return;
        }

        if (e.key === 'Tab') {
            if (e.shiftKey) {
                // Shift+Tab: If on first element, go to last
                if (document.activeElement === firstFocusable) {
                    lastFocusable.focus();
                    e.preventDefault();
                }
            } else {
                // Tab: If on last element, go to first
                if (document.activeElement === lastFocusable) {
                    firstFocusable.focus();
                    e.preventDefault();
                }
            }
        }
    };

    // Store the handler on the modal element so we can remove it later
    modal._focusTrapHandler = handleTabKey;

    // Add event listener for Tab key
    document.addEventListener('keydown', handleTabKey);
}

/**
 * Remove focus trap for a modal dialog
 * @param {string} modalId - ID of the modal element
 */
function removeModalFocusTrap(modalId) {
    const modal = document.getElementById(modalId);
    if (!modal || !modal._focusTrapHandler) return;

    document.removeEventListener('keydown', modal._focusTrapHandler);
    modal._focusTrapHandler = null;
}

/**
 * Global keyboard event handler for modal dialogs
 * Handles Escape key to close modals
 */
document.addEventListener('keydown', function(event) {
    if (event.key === 'Escape') {
        // Check if upload modal is open
        const uploadModal = document.getElementById('uploadModal');
        if (uploadModal && uploadModal.style.display === 'flex') {
            closeUploadModal();
            return;
        }

        // Check if book details modal is open
        const bookDetailsModal = document.getElementById('bookDetailsModal');
        if (bookDetailsModal && bookDetailsModal.style.display === 'flex') {
            closeBookDetailsModal();
            return;
        }
    }
});

/**
 * Add keyboard navigation to book cards
 * Allow Enter key to open book details
 */
document.addEventListener('DOMContentLoaded', function() {
    // Delegate keyboard events for book cards (dynamically added)
    document.addEventListener('keydown', function(event) {
        if (event.key === 'Enter') {
            const target = event.target;

            // Check if user pressed Enter on a book card
            if (target.classList.contains('book-card') || target.closest('.book-card')) {
                const bookCard = target.classList.contains('book-card')
                    ? target
                    : target.closest('.book-card');

                // Trigger click to open details modal
                if (bookCard && typeof bookCard.onclick === 'function') {
                    bookCard.onclick.call(bookCard, event);
                }
            }
        }
    });

    // Make book cards keyboard accessible
    // This will be called by bookRenderer.js when cards are created
    window.makeBookCardAccessible = function(cardElement) {
        if (!cardElement.hasAttribute('tabindex')) {
            cardElement.setAttribute('tabindex', '0');
        }
        cardElement.setAttribute('role', 'button');
    };
});
