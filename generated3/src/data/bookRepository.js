const fs = require('fs').promises;
const path = require('path');
const config = require('../config/config');
const logger = require('../utils/logger');
const fileUtils = require('../utils/fileUtils');

// In-memory cache
let booksCache = [];

/**
 * Initialize repository - load books from file or create empty file
 */
async function initialize() {
  try {
    // Ensure directory exists
    const dirPath = path.dirname(config.DATA_FILE_PATH);
    await fileUtils.ensureDirectory(dirPath);
    
    // Check if file exists
    try {
      await fs.access(config.DATA_FILE_PATH);
      
      // File exists, read and parse it
      const fileContent = await fs.readFile(config.DATA_FILE_PATH, 'utf8');
      
      try {
        booksCache = JSON.parse(fileContent);
        
        // Validate it's an array
        if (!Array.isArray(booksCache)) {
          throw new Error('Data file does not contain an array');
        }
        
        logger.info('Books loaded from file', { count: booksCache.length });
      } catch (parseError) {
        // Corrupted file - backup and start fresh
        logger.error('Corrupted JSON file detected', { error: parseError.message });
        await fileUtils.backupFile(config.DATA_FILE_PATH);
        logger.info('Corrupted file backed up');
        
        booksCache = [];
        await fileUtils.atomicWrite(config.DATA_FILE_PATH, JSON.stringify(booksCache, null, 2));
        logger.info('Started with empty book list');
      }
    } catch (accessError) {
      // File doesn't exist - create it
      booksCache = [];
      await fileUtils.atomicWrite(config.DATA_FILE_PATH, JSON.stringify(booksCache, null, 2));
      logger.info('Created new books data file');
    }
  } catch (error) {
    logger.error('Failed to initialize repository', { error: error.message, stack: error.stack });
    throw error;
  }
}

/**
 * Find all books
 * @returns {Array} Array of all books
 */
function findAll() {
  return [...booksCache];
}

/**
 * Find book by ID
 * @param {string} id - Book ID
 * @returns {Object|null} Book object or null if not found
 */
function findById(id) {
  return booksCache.find(book => book.id === id) || null;
}

/**
 * Save book (add or update)
 * @param {Object} book - Book object
 * @returns {Object} Saved book object
 */
async function save(book) {
  try {
    // Find existing book index
    const existingIndex = booksCache.findIndex(b => b.id === book.id);
    
    if (existingIndex >= 0) {
      // Update existing book
      booksCache[existingIndex] = book;
    } else {
      // Add new book
      booksCache.push(book);
    }
    
    // Write to file
    await fileUtils.atomicWrite(config.DATA_FILE_PATH, JSON.stringify(booksCache, null, 2));
    logger.info('Book saved', { id: book.id, title: book.title });
    
    return book;
  } catch (error) {
    logger.error('Failed to save book', { id: book.id, error: error.message });
    throw error;
  }
}

/**
 * Delete book by ID
 * @param {string} id - Book ID
 * @returns {boolean} True if deleted, false if not found
 */
async function deleteById(id) {
  try {
    const initialLength = booksCache.length;
    booksCache = booksCache.filter(book => book.id !== id);
    
    if (booksCache.length === initialLength) {
      // Book not found
      return false;
    }
    
    // Write to file
    await fileUtils.atomicWrite(config.DATA_FILE_PATH, JSON.stringify(booksCache, null, 2));
    logger.info('Book deleted', { id });
    
    return true;
  } catch (error) {
    logger.error('Failed to delete book', { id, error: error.message });
    throw error;
  }
}

module.exports = {
  initialize,
  findAll,
  findById,
  save,
  deleteById
};