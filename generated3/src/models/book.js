const crypto = require('crypto');

// Book status constants
const BOOK_STATUS = {
  READ: 'read',
  UNREAD: 'unread'
};

/**
 * Generate UUID v4 using crypto.randomBytes for Node 14.0+ compatibility
 */
function generateUUID() {
  const bytes = crypto.randomBytes(16);
  
  // Set version (4) and variant bits
  bytes[6] = (bytes[6] & 0x0f) | 0x40;
  bytes[8] = (bytes[8] & 0x3f) | 0x80;
  
  // Format as UUID string
  const hex = bytes.toString('hex');
  return [
    hex.substring(0, 8),
    hex.substring(8, 12),
    hex.substring(12, 16),
    hex.substring(16, 20),
    hex.substring(20, 32)
  ].join('-');
}

/**
 * Validate book data
 * @param {Object} bookData - Book data to validate
 * @returns {Object} { valid: boolean, errors: string[] }
 */
function validateBook(bookData) {
  const errors = [];
  
  // Validate required fields
  if (!bookData.title || typeof bookData.title !== 'string') {
    errors.push('Title is required and must be a string');
  } else if (bookData.title.trim().length === 0) {
    errors.push('Title cannot be empty');
  } else if (bookData.title.trim().length > 200) {
    errors.push('Title must not exceed 200 characters');
  }
  
  if (!bookData.author || typeof bookData.author !== 'string') {
    errors.push('Author is required and must be a string');
  } else if (bookData.author.trim().length === 0) {
    errors.push('Author cannot be empty');
  } else if (bookData.author.trim().length > 100) {
    errors.push('Author must not exceed 100 characters');
  }
  
  // Validate optional fields
  if (bookData.isbn !== undefined && bookData.isbn !== null && bookData.isbn !== '') {
    if (typeof bookData.isbn !== 'string') {
      errors.push('ISBN must be a string');
    } else if (bookData.isbn.length > 20) {
      errors.push('ISBN must not exceed 20 characters');
    }
  }
  
  if (bookData.publicationYear !== undefined && bookData.publicationYear !== null && bookData.publicationYear !== '') {
    const year = Number(bookData.publicationYear);
    const currentYear = new Date().getFullYear();
    if (isNaN(year) || !Number.isInteger(year)) {
      errors.push('Publication year must be an integer');
    } else if (year < 1000 || year > currentYear) {
      errors.push(`Publication year must be between 1000 and ${currentYear}`);
    }
  }
  
  if (bookData.status !== undefined && bookData.status !== null && bookData.status !== '') {
    if (bookData.status !== BOOK_STATUS.READ && bookData.status !== BOOK_STATUS.UNREAD) {
      errors.push(`Status must be either '${BOOK_STATUS.READ}' or '${BOOK_STATUS.UNREAD}'`);
    }
  }
  
  return {
    valid: errors.length === 0,
    errors
  };
}

/**
 * Create a book object with defaults
 * @param {Object} data - Book data
 * @returns {Object} Complete book object
 */
function createBookObject(data) {
  return {
    id: generateUUID(),
    title: data.title ? data.title.trim() : '',
    author: data.author ? data.author.trim() : '',
    isbn: data.isbn ? data.isbn.trim() : '',
    publicationYear: data.publicationYear ? Number(data.publicationYear) : null,
    status: data.status || BOOK_STATUS.UNREAD,
    dateAdded: new Date().toISOString()
  };
}

module.exports = {
  BOOK_STATUS,
  validateBook,
  createBookObject
};