const express = require('express');
const path = require('path');
const config = require('./config/config');
const logger = require('./utils/logger');
const bookRoutes = require('./routes/bookRoutes');
const bookRepository = require('./data/bookRepository');

const app = express();

// Middleware
app.use(express.json());
app.use(express.static(path.join(__dirname, 'public')));

// API Routes
app.use('/api/books', bookRoutes);

// Error handling middleware
app.use((err, req, res, next) => {
  const statusCode = err.statusCode || 500;
  const message = err.message || 'Internal Server Error';
  
  logger.error('Request error', {
    statusCode,
    message,
    stack: err.stack,
    path: req.path,
    method: req.method
  });
  
  res.status(statusCode).json({
    error: {
      message,
      code: err.code
    }
  });
});

// Initialize repository and start server
async function startServer() {
  try {
    await bookRepository.initialize();
    logger.info('Book repository initialized successfully');
    
    const server = app.listen(config.PORT, () => {
      logger.info(`Server running on port ${config.PORT}`);
    });
    
    // Graceful shutdown handlers
    const shutdown = (signal) => {
      logger.info(`${signal} received, shutting down gracefully`);
      server.close(() => {
        logger.info('Server closed');
        process.exit(0);
      });
    };
    
    process.on('SIGTERM', () => shutdown('SIGTERM'));
    process.on('SIGINT', () => shutdown('SIGINT'));
    
  } catch (error) {
    logger.error('Failed to start server', { error: error.message, stack: error.stack });
    process.exit(1);
  }
}

startServer();