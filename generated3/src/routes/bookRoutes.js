const express = require('express');
const bookService = require('../services/bookService');
const logger = require('../utils/logger');

const router = express.Router();

/**
 * GET /api/books - Get all books with optional status filter
 */
router.get('/', async (req, res, next) => {
  try {
    const { status } = req.query;
    const filter = status ? { status } : {};
    
    const books = bookService.getBooks(filter);
    
    logger.info('GET /api/books', { count: books.length, filter });
    res.status(200).json({ books });
  } catch (error) {
    next(error);
  }
});

/**
 * GET /api/books/:id - Get single book by ID
 */
router.get('/:id', async (req, res, next) => {
  try {
    const { id } = req.params;
    const book = bookService.getBookById(id);
    
    logger.info('GET /api/books/:id', { id });
    res.status(200).json({ book });
  } catch (error) {
    next(error);
  }
});

/**
 * POST /api/books - Create new book
 */
router.post('/', async (req, res, next) => {
  try {
    if (!req.body || Object.keys(req.body).length === 0) {
      const error = new Error('Request body is required');
      error.statusCode = 400;
      throw error;
    }
    
    const book = await bookService.createBook(req.body);
    
    logger.info('POST /api/books', { id: book.id, title: book.title });
    res.status(201).json({ book });
  } catch (error) {
    next(error);
  }
});

/**
 * PUT /api/books/:id - Update book
 */
router.put('/:id', async (req, res, next) => {
  try {
    const { id } = req.params;
    
    if (!req.body || Object.keys(req.body).length === 0) {
      const error = new Error('Request body is required');
      error.statusCode = 400;
      throw error;
    }
    
    const book = await bookService.updateBook(id, req.body);
    
    logger.info('PUT /api/books/:id', { id, title: book.title });
    res.status(200).json({ book });
  } catch (error) {
    next(error);
  }
});

/**
 * DELETE /api/books/:id - Delete book
 */
router.delete('/:id', async (req, res, next) => {
  try {
    const { id } = req.params;
    await bookService.deleteBook(id);
    
    logger.info('DELETE /api/books/:id', { id });
    res.status(204).send();
  } catch (error) {
    next(error);
  }
});

module.exports = router;