const config = require('../config/config');

const LOG_LEVELS = {
  error: 0,
  warn: 1,
  info: 2,
  debug: 3
};

const currentLevel = LOG_LEVELS[config.LOG_LEVEL] || LOG_LEVELS.info;

/**
 * Log a message with level, timestamp, and metadata
 * @param {string} level - Log level (error, warn, info, debug)
 * @param {string} message - Log message
 * @param {Object} meta - Optional metadata
 */
function log(level, message, meta = {}) {
  try {
    const levelValue = LOG_LEVELS[level] || LOG_LEVELS.info;
    
    // Only log if level is enabled
    if (levelValue > currentLevel) {
      return;
    }
    
    const logEntry = {
      timestamp: new Date().toISOString(),
      level,
      message,
      ...meta
    };
    
    const output = JSON.stringify(logEntry);
    
    // Write to appropriate stream
    if (level === 'error' || level === 'warn') {
      console.error(output);
    } else {
      console.log(output);
    }
  } catch (error) {
    // Swallow logging errors to prevent app crashes
    console.error('Logger error:', error.message);
  }
}

/**
 * Convenience methods
 */
function error(message, meta) {
  log('error', message, meta);
}

function warn(message, meta) {
  log('warn', message, meta);
}

function info(message, meta) {
  log('info', message, meta);
}

function debug(message, meta) {
  log('debug', message, meta);
}

// Self-log initialization
info('Logger initialized', { level: config.LOG_LEVEL });

module.exports = {
  log,
  error,
  warn,
  info,
  debug
};