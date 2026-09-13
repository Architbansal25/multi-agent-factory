const bookModel = require('../models/book');
const bookRepository = require('../data/bookRepository');
const logger = require('../utils/logger');

/**
 * UUID validation regex
 */
const UUID_REGEX = /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;

/**
 * Create a new book
 * @param {Object} bookData - Book data
 * @returns {Object} Created book
 */
async function createBook(bookData) {
  // Validate input
  const validation = bookModel.validateBook(bookData);
  if (!validation.valid) {
    const error = new Error(validation.errors.join(', '));
    error.statusCode = 400;
    logger.warn('Book validation failed', { errors: validation.errors });
    throw error;
  }
  
  // Create book object with generated ID and defaults
  const book = bookModel.createBookObject(bookData);
  
  // Save to repository
  const savedBook = await bookRepository.save(book);
  logger.info('Book created', { id: savedBook.id, title: savedBook.title });
  
  return savedBook;
}

/**
 * Get all books with optional filtering
 * @param {Object} filter - Filter options (e.g., { status: 'read' })
 * @returns {Array} Array of books
 */
function getBooks(filter = {}) {
  let books = bookRepository.findAll();
  
  // Filter by status if provided
  if (filter.status) {
    books = books.filter(book => book.status === filter.status);
  }
  
  return books;
}

/**
 * Get book by ID
 * @param {string} id - Book ID
 * @returns {Object} Book object
 */
function getBookById(id) {
  // Validate ID format
  if (!UUID_REGEX.test(id)) {
    const error = new Error('Invalid book ID format');
    error.statusCode = 400;
    throw error;
  }
  
  const book = bookRepository.findById(id);
  
  if (!book) {
    const error = new Error('Book not found');
    error.statusCode = 404;
    logger.warn('Book not found', { id });
    throw error;
  }
  
  return book;
}

/**
 * Update book
 * @param {string} id - Book ID
 * @param {Object} updates - Fields to update
 * @returns {Object} Updated book
 */
async function updateBook(id, updates) {
  // Validate ID format
  if (!UUID_REGEX.test(id)) {
    const error = new Error('Invalid book ID format');
    error.statusCode = 400;
    throw error;
  }
  
  // Get existing book
  const existingBook = bookRepository.findById(id);
  
  if (!existingBook) {
    const error = new Error('Book not found');
    error.statusCode = 404;
    logger.warn('Book not found for update', { id });
    throw error;
  }
  
  // Merge updates with existing book
  const updatedData = {
    ...existingBook,
    ...updates,
    id: existingBook.id, // Preserve ID
    dateAdded: existingBook.dateAdded // Preserve creation date
  };
  
  // Validate merged data
  const validation = bookModel.validateBook(updatedData);
  if (!validation.valid) {
    const error = new Error(validation.errors.join(', '));
    error.statusCode = 400;
    logger.warn('Book update validation failed', { id, errors: validation.errors });
    throw error;
  }
  
  // Sanitize and save
  const bookToSave = {
    id: updatedData.id,
    title: updatedData.title.trim(),
    author: updatedData.author.trim(),
    isbn: updatedData.isbn ? updatedData.isbn.trim() : '',
    publicationYear: updatedData.publicationYear ? Number(updatedData.publicationYear) : null,
    status: updatedData.status,
    dateAdded: updatedData.dateAdded
  };
  
  const savedBook = await bookRepository.save(bookToSave);
  logger.info('Book updated', { id: savedBook.id, title: savedBook.title });
  
  return savedBook;
}

/**
 * Delete book
 * @param {string} id - Book ID
 * @returns {boolean} True if deleted
 */
async function deleteBook(id) {
  // Validate ID format
  if (!UUID_REGEX.test(id)) {
    const error = new Error('Invalid book ID format');
    error.statusCode = 400;
    throw error;
  }
  
  const deleted = await bookRepository.deleteById(id);
  
  if (!deleted) {
    const error = new Error('Book not found');
    error.statusCode = 404;
    logger.warn('Book not found for deletion', { id });
    throw error;
  }
  
  logger.info('Book deleted', { id });
  return true;
}

module.exports = {
  createBook,
  getBooks,
  getBookById,
  updateBook,
  deleteBook
};