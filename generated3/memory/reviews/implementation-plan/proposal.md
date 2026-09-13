# Implementation Plan

## Stack And Tree Confirmation

**Locked Stack (verbatim from context.json):**
- **Language**: JavaScript
- **Framework**: Express.js
- **Database**: JSON file on disk
- **Infrastructure**: Local filesystem
- **Locked at stage**: requirements
- **Locked by**: human_approved

**Approved File Tree (all paths to be produced):**
1. `src/server.js`
2. `src/config/config.js`
3. `src/models/book.js`
4. `src/data/bookRepository.js`
5. `src/services/bookService.js`
6. `src/routes/bookRoutes.js`
7. `src/utils/logger.js`
8. `src/utils/fileUtils.js`
9. `src/public/index.html`
10. `src/public/css/styles.css`
11. `src/public/js/app.js`
12. `src/public/js/ui.js`
13. `src/package.json`
14. `src/.gitignore`
15. `src/.eslintrc.json`
16. `src/README.md`
17. `src/data/books.json`
18. `src/data/.gitkeep`

## Module Plan

### src/server.js
**Responsibility**: Application entry point; initializes and starts the Express server.

**Exports/Functions**:
- No exports (entry point script)
- Initializes Express app
- Configures middleware: `express.json()`, `express.static('public')` for serving frontend files
- Mounts `/api/books` routes from bookRoutes
- Implements centralized error handling middleware
- Calls `bookRepository.initialize()` before starting server
- Starts HTTP server on port from config
- Implements graceful shutdown handlers (SIGTERM, SIGINT)

**Error Handling**:
- Catches repository initialization failures and exits with error code
- Catches server startup failures (port in use, etc.)
- Global error middleware catches unhandled route errors and returns 500 with error message
- Logs all errors using logger utility

**Logging**:
- Server startup message with port number
- Repository initialization status
- Graceful shutdown messages
- All caught errors

**Satisfies**: 
- Acceptance Criteria #1 (Starting server with npm start)
- Acceptance Criteria #2 (Serves application on configured port)
- Architecture component "Express Server"
- FR-3.1 (Load books from JSON on server start)

---

### src/config/config.js
**Responsibility**: Centralized configuration management; loads environment variables with defaults.

**Exports/Functions**:
- `module.exports = { PORT, DATA_FILE_PATH, LOG_LEVEL }`
- `PORT`: `process.env.PORT || 3000` (number)
- `DATA_FILE_PATH`: `process.env.DATA_FILE_PATH || path.join(__dirname, '../data/books.json')`
- `LOG_LEVEL`: `process.env.LOG_LEVEL || 'info'`

**Error Handling**:
- No runtime errors expected; provides safe defaults for all values
- Validates PORT is a valid number (1-65535), throws error if invalid

**Logging**:
- None (configuration module)

**Satisfies**:
- Architecture component "Configuration"
- Acceptance Criteria #1 (Configurable port)
- Architecture decision "Environment variable PORT with default 3000"

---

### src/models/book.js
**Responsibility**: Defines book data model schema and validation functions.

**Exports/Functions**:
- `validateBook(bookData)`: Returns `{ valid: boolean, errors: string[] }`
  - Validates required fields: title (string, 1-200 chars), author (string, 1-100 chars)
  - Validates optional fields: isbn (string, max 20 chars), publicationYear (number, 1000-current year), status (enum: 'read'|'unread')
  - Returns validation result object
- `createBookObject(data)`: Creates a book object with defaults
  - Sets id (UUID v4), dateAdded (ISO timestamp), status ('unread' default)
  - Returns complete book object
- `BOOK_STATUS`: Object constant `{ READ: 'read', UNREAD: 'unread' }`

**Error Handling**:
- Validation functions return error arrays, never throw
- Input sanitization: trims strings, coerces types where safe

**Logging**:
- None (pure validation logic)

**Satisfies**:
- Architecture component "Data Models"
- FR-1.1 (Create book with required and optional fields)
- FR-2.1, FR-2.2 (Mark as read/unread)
- Security boundary "Input Validation" (string length limits, enum validation)

---

### src/data/bookRepository.js
**Responsibility**: Data access layer; manages JSON file I/O and in-memory cache.

**Exports/Functions**:
- `initialize()`: Async function, loads books from file or creates empty file
  - Checks if DATA_FILE_PATH exists
  - If missing, creates directory and empty JSON array file
  - If exists, reads and parses JSON
  - If corrupted, backs up to `.backup`, starts with empty array, logs error
  - Populates in-memory cache
  - Returns void, throws on unrecoverable errors
- `findAll()`: Returns array of all books from cache (synchronous)
- `findById(id)`: Returns book object or null (synchronous)
- `save(book)`: Async function, adds/updates book in cache and writes to file
  - Uses atomic write pattern (write to temp file, rename)
  - Returns saved book object
  - Throws on file write failure
- `deleteById(id)`: Async function, removes book from cache and writes to file
  - Returns boolean (true if deleted, false if not found)
  - Throws on file write failure
- Internal cache: `let booksCache = []`

**Error Handling**:
- `initialize()`: Catches JSON parse errors, creates backup, logs, continues with empty array
- `save()` and `deleteById()`: Catch file write errors, log, throw to caller (keeps cache unchanged)
- File system errors (permissions, disk full) propagate to caller
- Directory traversal validation on all file paths

**Logging**:
- Initialization success/failure
- Corrupted file detection and backup creation
- Every write operation (success/failure)
- File system errors with full details

**Satisfies**:
- Architecture component "Data Access Layer"
- FR-3.1, FR-3.2, FR-3.3 (Data persistence and error handling)
- ADR-0003 (Write-through cache)
- ADR-0004 (Atomic file writes)
- Failure mode #1 (Corrupted JSON file)
- Failure mode #2 (File system write failure)

---

### src/services/bookService.js
**Responsibility**: Business logic layer; orchestrates CRUD operations with validation.

**Exports/Functions**:
- `createBook(bookData)`: Async function
  - Validates input using `book.validateBook()`
  - Generates UUID using `book.createBookObject()`
  - Calls `bookRepository.save()`
  - Returns created book object
  - Throws validation errors with 400 status code property
- `getBooks(filter = {})`: Async function
  - Calls `bookRepository.findAll()`
  - If `filter.status` provided, filters by status
  - Returns filtered array
- `getBookById(id)`: Async function
  - Validates id format (UUID pattern)
  - Calls `bookRepository.findById()`
  - Returns book or throws 404 error
- `updateBook(id, updates)`: Async function
  - Validates id and fetches existing book
  - Validates update fields using `book.validateBook()`
  - Merges updates with existing book
  - Calls `bookRepository.save()`
  - Returns updated book
  - Throws 404 if not found, 400 if validation fails
- `deleteBook(id)`: Async function
  - Validates id format
  - Calls `bookRepository.deleteById()`
  - Returns boolean success
  - Throws 404 if not found

**Error Handling**:
- All validation errors thrown with `statusCode: 400` property
- Not found errors thrown with `statusCode: 404` property
- Repository errors propagate with `statusCode: 500`
- Input sanitization before validation

**Logging**:
- Each operation (create, update, delete) with book id
- Validation failures with details
- Not found attempts

**Satisfies**:
- Architecture component "Book Service"
- FR-1.1 through FR-1.5 (All book management operations)
- FR-2.3 (Filter by status)
- ADR-0005 (UUID v4 for book IDs)
- Failure mode #3 (Invalid book data)
- Failure mode #5 (Missing book ID)

---

### src/routes/bookRoutes.js
**Responsibility**: REST API route definitions; maps HTTP requests to service layer.

**Exports/Functions**:
- `module.exports = router` (Express Router instance)
- `GET /`: Calls `bookService.getBooks()` with optional `?status=` query param
  - Returns 200 with `{ books: [...] }`
- `GET /:id`: Calls `bookService.getBookById(id)`
  - Returns 200 with `{ book: {...} }` or 404
- `POST /`: Calls `bookService.createBook(req.body)`
  - Returns 201 with `{ book: {...} }` or 400
- `PUT /:id`: Calls `bookService.updateBook(id, req.body)`
  - Returns 200 with `{ book: {...} }` or 400/404
- `DELETE /:id`: Calls `bookService.deleteBook(id)`
  - Returns 204 (no content) or 404

**Error Handling**:
- Wraps all route handlers in try-catch
- Catches errors with `statusCode` property and returns appropriate HTTP status
- Catches unexpected errors and returns 500
- Validates request body exists for POST/PUT
- Validates id parameter format

**Logging**:
- Each request with method, path, status code
- Request body for POST/PUT (sanitized)
- Errors with full stack trace

**Satisfies**:
- Architecture component "API Routes"
- FR-5.1 through FR-5.5 (All API endpoints)
- ADR-0007 (Express middleware for error handling)
- Acceptance Criteria #4, #5, #6, #7, #8 (All user operations)

---

### src/utils/logger.js
**Responsibility**: Centralized logging utility; provides consistent log formatting.

**Exports/Functions**:
- `log(level, message, meta = {})`: Logs message with timestamp, level, and optional metadata
  - Levels: 'error', 'warn', 'info', 'debug'
  - Formats as JSON for structured logging
  - Writes to console.error (error/warn) or console.log (info/debug)
  - Respects LOG_LEVEL from config
- `error(message, meta)`: Convenience wrapper for error level
- `warn(message, meta)`: Convenience wrapper for warn level
- `info(message, meta)`: Convenience wrapper for info level
- `debug(message, meta)`: Convenience wrapper for debug level

**Error Handling**:
- Never throws; catches and swallows logging errors to prevent app crashes

**Logging**:
- Self-logs initialization

**Satisfies**:
- Architecture component "Configuration" (logging)
- Non-functional target "Maintainability" (consistent logging)

---

### src/utils/fileUtils.js
**Responsibility**: File system utility functions; provides atomic write operations.

**Exports/Functions**:
- `atomicWrite(filePath, data)`: Async function
  - Writes data to temporary file (`${filePath}.tmp`)
  - Renames temp file to target (atomic on POSIX)
  - Cleans up temp file on error
  - Returns void, throws on failure
- `ensureDirectory(dirPath)`: Async function
  - Creates directory recursively if it doesn't exist
  - Returns void, throws on failure
- `backupFile(filePath)`: Async function
  - Copies file to `${filePath}.backup`
  - Returns void, throws on failure

**Error Handling**:
- All functions throw on file system errors
- Validates paths don't contain `..` (directory traversal prevention)
- Cleans up partial writes on failure

**Logging**:
- Each operation with file paths
- Errors with full details

**Satisfies**:
- ADR-0004 (Atomic file writes using temp file pattern)
- Security boundary "File System" (path validation)
- Failure mode #1 (Backup on corruption)

---

### src/public/index.html
**Responsibility**: Main HTML page structure; provides UI layout and Bootstrap CSS.

**Content**:
- DOCTYPE html5, semantic HTML structure
- `<head>`: Title "Book Library", Bootstrap CSS CDN link (CSS only, no JS), custom styles.css link
- `<body>`: Container with centered content
  - Header: "Book Library" title
  - Filter section: Three buttons (All, Read, Unread) with data-status attributes
  - Add book form: Input fields for title (required), author (required), isbn, publicationYear, status dropdown
  - Book list section: Empty `<div id="book-list">` for dynamic rendering
  - Book detail modal: Hidden `<div id="book-detail">` for viewing/editing single book
- Script tags: app.js, ui.js (in that order)
- No Bootstrap JS or other framework JS

**Error Handling**:
- Form validation attributes (required, maxlength, pattern)
- Accessible error messages via ARIA attributes

**Logging**:
- None (static HTML)

**Satisfies**:
- Architecture component "Frontend Static Files"
- FR-4.1, FR-4.2, FR-4.6 (UI display, form, filters)
- Acceptance Criteria #2, #3 (Display interface, clean/readable UI)
- ADR-0006 (Bootstrap CSS only)
- Constraint "Bootstrap CSS only — no JS"

---

### src/public/css/styles.css
**Responsibility**: Custom CSS styling; enhances Bootstrap with app-specific styles.

**Content**:
- Body: Centered layout, max-width 1200px, padding
- Header: Styled title, margin
- Filter buttons: Active state styling, spacing
- Book list: Card layout, grid for responsive display
- Book cards: Hover effects, status badges (read=green, unread=orange)
- Forms: Styled inputs, validation feedback
- Modal: Overlay styling, centered content, close button
- Responsive breakpoints: Tablet (768px), mobile (480px)
- Accessibility: Focus states, high contrast, keyboard navigation indicators

**Error Handling**:
- None (CSS)

**Logging**:
- None (CSS)

**Satisfies**:
- Architecture component "Frontend Static Files"
- Acceptance Criteria #3 (Clean, readable, centered UI)
- Non-functional target "Usability" (responsive design, accessible)

---

### src/public/js/app.js
**Responsibility**: Main frontend application logic; API client and state management.

**Exports/Functions**:
- `API` object with methods:
  - `getBooks(status = null)`: Fetches books from GET /api/books?status=
  - `getBook(id)`: Fetches single book from GET /api/books/:id
  - `createBook(bookData)`: Posts to POST /api/books
  - `updateBook(id, updates)`: Puts to PUT /api/books/:id
  - `deleteBook(id)`: Deletes to DELETE /api/books/:id
  - All methods return promises, handle fetch errors
- `state` object: `{ books: [], currentFilter: 'all', selectedBook: null }`
- `init()`: Initializes app, loads initial books, sets up event listeners
- `loadBooks(status)`: Fetches books and updates state and UI
- `handleFilterClick(status)`: Updates filter and reloads books
- `handleAddBook(formData)`: Creates book via API and refreshes list
- `handleBookClick(id)`: Loads book detail and shows modal
- `handleUpdateBook(id, updates)`: Updates book via API and refreshes
- `handleDeleteBook(id)`: Confirms and deletes book via API

**Error Handling**:
- All API calls wrapped in try-catch
- Network errors displayed to user via UI.showError()
- Validation errors from API displayed in form
- 404 errors handled gracefully (show message, don't crash)

**Logging**:
- Console logs for all API calls (debug mode)
- Errors logged to console

**Satisfies**:
- Architecture component "Frontend Static Files"
- FR-4.2, FR-4.3, FR-4.4, FR-4.5 (All UI interactions)
- Acceptance Criteria #4, #5, #6, #7, #8 (All user operations)
- Flow #1, #2 (Add book, filter books)

---

### src/public/js/ui.js
**Responsibility**: DOM manipulation and rendering; updates UI based on state.

**Exports/Functions**:
- `renderBookList(books)`: Renders book cards in grid layout
  - Creates card HTML for each book with title, author, status badge
  - Attaches click handlers
  - Shows empty state if no books
- `renderBookDetail(book)`: Populates modal with book details
  - Shows all fields in editable form
  - Attaches save/delete handlers
- `showModal()`: Displays book detail modal with overlay
- `hideModal()`: Hides modal
- `showError(message)`: Displays error toast/banner
- `showSuccess(message)`: Displays success toast/banner
- `updateFilterButtons(activeStatus)`: Updates active state on filter buttons
- `clearForm()`: Resets add book form
- `validateForm(formElement)`: Client-side validation before submit

**Error Handling**:
- Validates all DOM elements exist before manipulation
- Sanitizes user input before rendering (prevent XSS)
- Handles missing data gracefully (show placeholder)

**Logging**:
- None (UI rendering)

**Satisfies**:
- Architecture component "Frontend Static Files"
- FR-4.1, FR-4.3, FR-4.4, FR-4.5 (Display, detail view, edit, delete)
- Non-functional target "Usability" (error feedback, accessible)
- Security boundary "Input Validation" (sanitize inputs)

---

### src/package.json
**Responsibility**: Node.js project manifest; defines dependencies and scripts.

**Content**:
```json
{
  "name": "book-library",
  "version": "1.0.0",
  "description": "A Book Library web application",
  "main": "server.js",
  "scripts": {
    "start": "node server.js",
    "dev": "nodemon server.js",
    "lint": "eslint ."
  },
  "dependencies": {
    "express": "^4.18.2"
  },
  "devDependencies": {
    "eslint": "^8.50.0",
    "eslint-config-airbnb-base": "^15.0.0",
    "eslint-plugin-import": "^2.28.1",
    "nodemon": "^3.0.1"
  },
  "engines": {
    "node": ">=14.0.0"
  }
}
```

**Error Handling**:
- None (manifest file)

**Logging**:
- None (manifest file)

**Satisfies**:
- Acceptance Criteria #1 (npm start command)
- ADR-0010 (ESLint with Airbnb style guide)

---

### src/.gitignore
**Responsibility**: Git ignore patterns; excludes generated and sensitive files.

**Content**:
```
node_modules/
data/books.json
data/*.backup
*.log
.env
.DS_Store
```

**Error Handling**:
- None (git configuration)

**Logging**:
- None (git configuration)

**Satisfies**:
- Non-functional target "Maintainability" (version control best practices)

---

### src/.eslintrc.json
**Responsibility**: ESLint configuration; enforces code style.

**Content**:
```json
{
  "extends": "airbnb-base",
  "env": {
    "node": true,
    "es6": true,
    "browser": true
  },
  "rules": {
    "no-console": "off",
    "consistent-return": "warn"
  }
}
```

**Error Handling**:
- None (linter configuration)

**Logging**:
- None (linter configuration)

**Satisfies**:
- ADR-0010 (ESLint with Airbnb style guide)
- Non-functional target "Maintainability" (code quality)

---

### src/README.md
**Responsibility**: Project documentation; setup and usage instructions.

**Content**:
- Project overview and features
- Prerequisites (Node.js 14+)
- Installation steps:
  1. Clone repository
  2. `cd src`
  3. `npm install`
- Running the application:
  - `npm start` (production)
  - `npm run dev` (development with auto-reload)
- Usage instructions:
  - Open `http://localhost:3000`
  - Add books via form
  - Filter by status
  - Click book to view/edit/delete
- Configuration:
  - PORT environment variable
  - DATA_FILE_PATH environment variable
- Data persistence:
  - Books stored in `data/books.json`
  - Automatic backup on corruption
- Architecture overview (brief)
- Troubleshooting common issues
- Browser compatibility (Chrome, Firefox, Safari, Edge)

**Error Handling**:
- None (documentation)

**Logging**:
- None (documentation)

**Satisfies**:
- Acceptance Criteria #10 (README with clear instructions)
- Constraint "README.md is required"
- Non-functional target "Maintainability" (documentation)

---

### src/data/books.json
**Responsibility**: Initial data file; empty JSON array for books.

**Content**:
```json
[]
```

**Error Handling**:
- None (data file)

**Logging**:
- None (data file)

**Satisfies**:
- FR-3.1 (Data file initialization)
- Architecture "Data file path configuration"

---

### src/data/.gitkeep
**Responsibility**: Git placeholder; ensures data directory is tracked.

**Content**:
(Empty file)

**Error Handling**:
- None (placeholder)

**Logging**:
- None (placeholder)

**Satisfies**:
- Non-functional target "Maintainability" (directory structure in version control)

---

## Dependencies

**express** (^4.18.2)
- Manifest: `src/package.json` dependencies
- Reason: Required web framework per locked stack; provides HTTP server, routing, middleware
- Usage: Core application framework

**eslint** (^8.50.0)
- Manifest: `src/package.json` devDependencies
- Reason: Code quality and style enforcement per ADR-0010
- Usage: Development linting

**eslint-config-airbnb-base** (^15.0.0)
- Manifest: `src/package.json` devDependencies
- Reason: Airbnb style guide per ADR-0010
- Usage: ESLint configuration preset

**eslint-plugin-import** (^2.28.1)
- Manifest: `src/package.json` devDependencies
- Reason: Required peer dependency for eslint-config-airbnb-base
- Usage: Import/export linting rules

**nodemon** (^3.0.1)
- Manifest: `src/package.json` devDependencies
- Reason: Development convenience for auto-restart on file changes
- Usage: Development server (npm run dev)

**No other dependencies**: The locked stack prohibits databases, frontend frameworks, and framework JS components. All functionality is implemented with vanilla JavaScript and Node.js built-in modules (fs, path, crypto for UUID).

## Verification Commands

**Working directory**: `src/`

**Install dependencies**:
```bash
npm install
```

**Start the application**:
```bash
npm start
```

**Expected output**: 
- Server logs "Server running on port 3000" (or configured PORT)
- Navigate to `http://localhost:3000` in browser
- Application UI loads with empty book list

**Verification notes**: 
- No tests were generated per human selection of build-now mode
- Manual verification required: test all CRUD operations through UI
- Check browser console for JavaScript errors
- Verify data persists across server restarts
- Test filter functionality (All, Read, Unread)
- Verify form validation (required fields, length limits)

## Concerns

**1. UUID Generation Without External Library**

The approved architecture specifies UUID v4 for book IDs (ADR-0005), but does not include a UUID library in dependencies. Node.js built-in `crypto.randomUUID()` is available in Node 14.17+ and 16+, which satisfies the package.json engines requirement of `>=14.0.0`. However, for Node 14.0-14.16, this function is not available.

**Options**:
- Use `crypto.randomUUID()` and document minimum Node 14.17 requirement
- Implement simple UUID v4 generator using `crypto.randomBytes()`
- Add `uuid` npm package (contradicts "no other dependencies" unless approved)

**Recommendation**: Implement UUID v4 using `crypto.randomBytes()` to maintain zero external dependencies for core functionality and support Node 14.0+.

**2. Bootstrap CSS Version and CDN**

The architecture plan states "Bootstrap CSS framework" but doesn't specify version. Bootstrap 5.x removed jQuery dependency, making it fully compatible with the "no framework JS" constraint. Bootstrap 4.x included some JS dependencies.

**Recommendation**: Use Bootstrap 5.3 CSS-only CDN link in index.html to ensure no accidental JS inclusion.

**3. Atomic File Write on Windows**

ADR-0004 specifies atomic writes using temp file + rename, noting it's "atomic operation on POSIX systems." On Windows, `fs.rename()` is not atomic if the target file exists. This creates a small risk of data loss if the process crashes during rename.

**Options**:
- Accept the limitation and document it (Windows users have slightly higher corruption risk)
- Implement Windows-specific atomic write using `fs.copyFile()` + `fs.unlink()` sequence
- Use a library (contradicts stack constraints)

**Recommendation**: Accept the limitation, document it in README, and rely on the backup mechanism (corrupted file detection) as the safety net. The risk is minimal for single-user local use.

**4. CORS Configuration**

The architecture plan mentions "CORS configured to allow localhost only" but doesn't specify implementation. For a local-only app, CORS is not strictly necessary since the frontend is served from the same origin as the API.

**Recommendation**: Omit CORS middleware entirely since Express serves both API and static files from the same origin. If needed later, it's a simple addition.

**5. Error Response Format**

The architecture doesn't specify a standard error response format for the API. Consistency improves frontend error handling.

**Recommendation**: Use format `{ error: { message: string, code?: string } }` for all error responses. Document in code comments.

---

**Reply 'approve' to build this, or 'revise <your changes>'.**