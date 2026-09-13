/* eslint-disable no-unused-vars */

// UI rendering and manipulation
const UI = {
  /**
   * Render book list
   * @param {Array} books - Array of book objects
   */
  renderBookList(books) {
    const bookList = document.getElementById('book-list');
    if (!bookList) return;
    
    if (books.length === 0) {
      bookList.innerHTML = '<div class="col-12"><div class="empty-state"><p>No books found. Add your first book to get started!</p></div></div>';
      return;
    }
    
    bookList.innerHTML = books.map(book => `
      <div class="col-md-6 col-lg-4">
        <div class="book-card" data-id="${this.escapeHtml(book.id)}" tabindex="0" role="button" aria-label="View details for ${this.escapeHtml(book.title)}">
          <h3>${this.escapeHtml(book.title)}</h3>
          <p class="author">by ${this.escapeHtml(book.author)}</p>
          <span class="status-badge ${book.status}">${book.status === 'read' ? 'Read' : 'Unread'}</span>
        </div>
      </div>
    `).join('');
  },
  
  /**
   * Render book detail in modal
   * @param {Object} book - Book object
   */
  renderBookDetail(book) {
    const form = document.getElementById('edit-book-form');
    if (!form) return;
    
    document.getElementById('edit-id').value = book.id;
    document.getElementById('edit-title').value = book.title || '';
    document.getElementById('edit-author').value = book.author || '';
    document.getElementById('edit-isbn').value = book.isbn || '';
    document.getElementById('edit-publicationYear').value = book.publicationYear || '';
    document.getElementById('edit-status').value = book.status || 'unread';
    
    const dateAdded = document.getElementById('edit-dateAdded');
    if (dateAdded && book.dateAdded) {
      const date = new Date(book.dateAdded);
      dateAdded.textContent = date.toLocaleDateString();
    }
  },
  
  /**
   * Show modal
   */
  showModal() {
    const modal = document.getElementById('book-detail-modal');
    if (modal) {
      modal.style.display = 'flex';
      // Focus first input
      const firstInput = modal.querySelector('input:not([type="hidden"])');
      if (firstInput) {
        setTimeout(() => firstInput.focus(), 100);
      }
    }
  },
  
  /**
   * Hide modal
   */
  hideModal() {
    const modal = document.getElementById('book-detail-modal');
    if (modal) {
      modal.style.display = 'none';
    }
    this.clearFeedback('modal-feedback');
  },
  
  /**
   * Show error message
   * @param {string} message - Error message
   */
  showError(message) {
    this.showToast(message, 'error');
  },
  
  /**
   * Show success message
   * @param {string} message - Success message
   */
  showSuccess(message) {
    this.showToast(message, 'success');
  },
  
  /**
   * Show toast notification
   * @param {string} message - Message to display
   * @param {string} type - Type of toast (success or error)
   */
  showToast(message, type) {
    const toast = document.getElementById('toast');
    if (!toast) return;
    
    toast.textContent = message;
    toast.className = `toast-notification ${type}`;
    toast.style.display = 'block';
    
    setTimeout(() => {
      toast.style.display = 'none';
    }, 3000);
  },
  
  /**
   * Update filter button active state
   * @param {string} activeStatus - Active filter status
   */
  updateFilterButtons(activeStatus) {
    document.querySelectorAll('.filter-btn').forEach(btn => {
      if (btn.dataset.status === activeStatus) {
        btn.classList.add('active');
      } else {
        btn.classList.remove('active');
      }
    });
  },
  
  /**
   * Clear form
   * @param {string} formId - Form element ID
   */
  clearForm(formId) {
    const form = document.getElementById(formId);
    if (form) {
      form.reset();
    }
  },
  
  /**
   * Clear feedback message
   * @param {string} elementId - Feedback element ID
   */
  clearFeedback(elementId) {
    const element = document.getElementById(elementId);
    if (element) {
      element.textContent = '';
      element.className = '';
    }
  },
  
  /**
   * Escape HTML to prevent XSS
   * @param {string} text - Text to escape
   * @returns {string} Escaped text
   */
  escapeHtml(text) {
    if (text === null || text === undefined) return '';
    const div = document.createElement('div');
    div.textContent = String(text);
    return div.innerHTML;
  }
};