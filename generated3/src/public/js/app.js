/* global UI */

// API client
const API = {
  async getBooks(status = null) {
    try {
      const url = status ? `/api/books?status=${encodeURIComponent(status)}` : '/api/books';
      const response = await fetch(url);
      
      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.error?.message || 'Failed to fetch books');
      }
      
      const data = await response.json();
      return data.books;
    } catch (error) {
      console.error('API Error (getBooks):', error);
      throw error;
    }
  },
  
  async getBook(id) {
    try {
      const response = await fetch(`/api/books/${encodeURIComponent(id)}`);
      
      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.error?.message || 'Failed to fetch book');
      }
      
      const data = await response.json();
      return data.book;
    } catch (error) {
      console.error('API Error (getBook):', error);
      throw error;
    }
  },
  
  async createBook(bookData) {
    try {
      const response = await fetch('/api/books', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(bookData)
      });
      
      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.error?.message || 'Failed to create book');
      }
      
      const data = await response.json();
      return data.book;
    } catch (error) {
      console.error('API Error (createBook):', error);
      throw error;
    }
  },
  
  async updateBook(id, updates) {
    try {
      const response = await fetch(`/api/books/${encodeURIComponent(id)}`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(updates)
      });
      
      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.error?.message || 'Failed to update book');
      }
      
      const data = await response.json();
      return data.book;
    } catch (error) {
      console.error('API Error (updateBook):', error);
      throw error;
    }
  },
  
  async deleteBook(id) {
    try {
      const response = await fetch(`/api/books/${encodeURIComponent(id)}`, {
        method: 'DELETE'
      });
      
      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.error?.message || 'Failed to delete book');
      }
      
      return true;
    } catch (error) {
      console.error('API Error (deleteBook):', error);
      throw error;
    }
  }
};

// Application state
const state = {
  books: [],
  currentFilter: 'all',
  selectedBook: null
};

// Initialize application
async function init() {
  try {
    // Load initial books
    await loadBooks();
    
    // Set up event listeners
    setupEventListeners();
    
    console.log('Application initialized');
  } catch (error) {
    console.error('Initialization error:', error);
    UI.showError('Failed to initialize application');
  }
}

// Set up event listeners
function setupEventListeners() {
  // Filter buttons
  document.querySelectorAll('.filter-btn').forEach(btn => {
    btn.addEventListener('click', handleFilterClick);
  });
  
  // Add book form
  const addForm = document.getElementById('add-book-form');
  if (addForm) {
    addForm.addEventListener('submit', handleAddBook);
  }
  
  // Edit book form
  const editForm = document.getElementById('edit-book-form');
  if (editForm) {
    editForm.addEventListener('submit', handleUpdateBook);
  }
  
  // Delete book button
  const deleteBtn = document.getElementById('delete-book-btn');
  if (deleteBtn) {
    deleteBtn.addEventListener('click', handleDeleteBook);
  }
  
  // Modal close button
  const closeBtn = document.querySelector('.btn-close');
  if (closeBtn) {
    closeBtn.addEventListener('click', () => UI.hideModal());
  }
  
  // Close modal on overlay click
  const modalOverlay = document.getElementById('book-detail-modal');
  if (modalOverlay) {
    modalOverlay.addEventListener('click', (e) => {
      if (e.target === modalOverlay) {
        UI.hideModal();
      }
    });
  }
}

// Load books with optional filter
async function loadBooks(status = null) {
  try {
    const filterStatus = status || (state.currentFilter === 'all' ? null : state.currentFilter);
    state.books = await API.getBooks(filterStatus);
    UI.renderBookList(state.books);
    
    // Attach click handlers to book cards
    document.querySelectorAll('.book-card').forEach(card => {
      card.addEventListener('click', () => handleBookClick(card.dataset.id));
      card.addEventListener('keypress', (e) => {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault();
          handleBookClick(card.dataset.id);
        }
      });
    });
  } catch (error) {
    console.error('Load books error:', error);
    UI.showError(error.message);
  }
}

// Handle filter button click
function handleFilterClick(event) {
  const status = event.target.dataset.status;
  state.currentFilter = status;
  
  UI.updateFilterButtons(status);
  loadBooks(status === 'all' ? null : status);
}

// Handle add book form submission
async function handleAddBook(event) {
  event.preventDefault();
  
  const formData = new FormData(event.target);
  const bookData = {
    title: formData.get('title'),
    author: formData.get('author'),
    isbn: formData.get('isbn') || '',
    publicationYear: formData.get('publicationYear') || null,
    status: formData.get('status')
  };
  
  try {
    await API.createBook(bookData);
    UI.showSuccess('Book added successfully');
    UI.clearForm('add-book-form');
    await loadBooks();
  } catch (error) {
    console.error('Add book error:', error);
    UI.showError(error.message);
  }
}

// Handle book card click
async function handleBookClick(id) {
  try {
    const book = await API.getBook(id);
    state.selectedBook = book;
    UI.renderBookDetail(book);
    UI.showModal();
  } catch (error) {
    console.error('Load book detail error:', error);
    UI.showError(error.message);
  }
}

// Handle update book form submission
async function handleUpdateBook(event) {
  event.preventDefault();
  
  const formData = new FormData(event.target);
  const id = formData.get('id');
  const updates = {
    title: formData.get('title'),
    author: formData.get('author'),
    isbn: formData.get('isbn') || '',
    publicationYear: formData.get('publicationYear') || null,
    status: formData.get('status')
  };
  
  try {
    await API.updateBook(id, updates);
    UI.showSuccess('Book updated successfully');
    UI.hideModal();
    await loadBooks();
  } catch (error) {
    console.error('Update book error:', error);
    UI.showError(error.message);
  }
}

// Handle delete book button click
async function handleDeleteBook() {
  if (!state.selectedBook) return;
  
  const confirmed = confirm(`Are you sure you want to delete "${state.selectedBook.title}"?`);
  if (!confirmed) return;
  
  try {
    await API.deleteBook(state.selectedBook.id);
    UI.showSuccess('Book deleted successfully');
    UI.hideModal();
    state.selectedBook = null;
    await loadBooks();
  } catch (error) {
    console.error('Delete book error:', error);
    UI.showError(error.message);
  }
}

// Start application when DOM is ready
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', init);
} else {
  init();
}