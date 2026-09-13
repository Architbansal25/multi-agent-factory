const path = require('path');

// Validate PORT is a valid number
const PORT = process.env.PORT ? parseInt(process.env.PORT, 10) : 3000;

if (isNaN(PORT) || PORT < 1 || PORT > 65535) {
  throw new Error(`Invalid PORT: ${process.env.PORT}. Must be a number between 1 and 65535.`);
}

module.exports = {
  PORT,
  DATA_FILE_PATH: process.env.DATA_FILE_PATH || path.join(__dirname, '../data/books.json'),
  LOG_LEVEL: process.env.LOG_LEVEL || 'info'
};