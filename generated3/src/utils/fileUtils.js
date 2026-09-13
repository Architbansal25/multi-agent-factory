const fs = require('fs').promises;
const path = require('path');
const logger = require('./logger');

/**
 * Validate path doesn't contain directory traversal
 * @param {string} filePath - Path to validate
 */
function validatePath(filePath) {
  const normalized = path.normalize(filePath);
  if (normalized.includes('..')) {
    throw new Error('Path contains directory traversal');
  }
}

/**
 * Atomic write using temp file + rename pattern
 * @param {string} filePath - Target file path
 * @param {string} data - Data to write
 */
async function atomicWrite(filePath, data) {
  validatePath(filePath);
  
  const tempPath = `${filePath}.tmp`;
  
  try {
    // Write to temp file
    await fs.writeFile(tempPath, data, 'utf8');
    
    // Rename to target (atomic on POSIX)
    await fs.rename(tempPath, filePath);
    
    logger.debug('Atomic write completed', { filePath });
  } catch (error) {
    // Clean up temp file on error
    try {
      await fs.unlink(tempPath);
    } catch (unlinkError) {
      // Ignore unlink errors
    }
    
    logger.error('Atomic write failed', { filePath, error: error.message });
    throw error;
  }
}

/**
 * Ensure directory exists, create recursively if needed
 * @param {string} dirPath - Directory path
 */
async function ensureDirectory(dirPath) {
  validatePath(dirPath);
  
  try {
    await fs.mkdir(dirPath, { recursive: true });
    logger.debug('Directory ensured', { dirPath });
  } catch (error) {
    logger.error('Failed to ensure directory', { dirPath, error: error.message });
    throw error;
  }
}

/**
 * Backup file by copying to .backup
 * @param {string} filePath - File to backup
 */
async function backupFile(filePath) {
  validatePath(filePath);
  
  const backupPath = `${filePath}.backup`;
  
  try {
    await fs.copyFile(filePath, backupPath);
    logger.info('File backed up', { filePath, backupPath });
  } catch (error) {
    logger.error('Failed to backup file', { filePath, error: error.message });
    throw error;
  }
}

module.exports = {
  atomicWrite,
  ensureDirectory,
  backupFile
};