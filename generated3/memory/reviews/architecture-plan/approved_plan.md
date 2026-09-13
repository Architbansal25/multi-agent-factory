# Requirements and Architecture Plan

## Locked Stack

| Component  | Value                          | Brief Source |
|------------|--------------------------------|--------------|
| Language   | Node.js                        | "Runtime: Node.js" |
| Framework  | Express.js                     | "Web framework: **Must use Express.js**" |
| Database   | JSON file on disk              | "Data store: JSON file on disk (e.g. `data/books.json`) — no external DB" |
| Infrastructure | Local filesystem          | Implied by JSON file storage requirement |

## Decisions Needed From You

1. **CSS Framework Choice**: The brief permits "Bootstrap or Materialize **CSS only**". Which would you prefer?
   - **Options**: Bootstrap CSS, Materialize CSS, or plain CSS/Sass/Less without a framework
   - **Recommendation**: Bootstrap CSS (more widely known, better documentation)
   - **Impact**: Affects class names in HTML templates and which CDN link or local file we include

2. **Frontend Architecture**: The brief says "simple server-rendered or static HTML/CSS/vanilla-JS frontend"
   - **Options**: 
     - Server-rendered: Express serves HTML templates (EJS/Pug/Handlebars) with data injected server-side
     - Static SPA: Express serves static HTML/CSS/JS files; frontend fetches data via API calls
   - **Recommendation**: Static SPA approach - cleaner separation, easier to test API independently, aligns with "consuming the API" language in brief
   - **Impact**: Determines whether we need a template engine dependency and how data flows to the UI

3. **Book Data Model**: The brief mentions "add books" and "mark as read or unread" but doesn't specify what fields a book has
   - **Options**: Minimal (title, author, status) vs. Extended (+ ISBN, publication year, cover image URL, notes)
   - **Recommendation**: Extended model (id, title, author, isbn, publicationYear, status, dateAdded) - more realistic library app
   - **Impact**: Affects API payload structure and UI form fields

4. **Port Configuration**: No port specified for the server
   - **Options**: Hardcoded (3000), environment variable with default, fully configurable
   - **Recommendation**: Environment variable PORT with default 3000
   - **Impact**: Deployment flexibility and README instructions

5. **Filter Behavior**: "filter the list by status" - should this be client-side only or also support server-side filtering?
   - **Options**: Client-side only (fetch all, filter in browser), Server-side query parameter (?status=read)
   - **Recommendation**: Both - server-side optional query param for scalability demonstration, client-side for UX
   - **Impact**: API endpoint design and frontend implementation

## Global Constraints Carried Forward

- A Node.js + Express backend exposing a REST API
- A JSON file acting as the data store (no database)
- A simple server-rendered or static HTML/CSS/vanilla-JS frontend consuming the API
- **Must use Express.js** as web framework
- JSON file on disk (e.g. `data/books.json`) — no external DB
- Vanilla JavaScript only for frontend JS
- Bootstrap or Materialize **CSS only** — their bundled JS/JS components are **not allowed**
- Plain CSS, Sass, or Less all permitted for styling
- A `README.md` describing the app and local run steps is **required**
- Must not substitute a database (Mongo/Postgres/SQLite/etc.), a frontend framework (React/Vue/Angular), or Bootstrap/Materialize's JS widgets

## Product Scope

**User Goals:**
- Maintain a personal collection of books with metadata
- Track reading progress (read vs. unread status)
- Quickly find books by their reading status
- View and update individual book details

**In Scope:**
- Create new book entries with title, author, and optional metadata
- List all books in the library
- Filter displayed books by read/unread status
- View detailed information for a single book
- Edit book information (including marking as read/unread)
- Delete books from the library
- Persist all changes to disk automatically
- Serve a responsive web UI accessible via browser

**Out of Scope:**
- User authentication or multi-user support
- Book cover image uploads (URLs only)
- Search by title/author (only status filtering)
- Sorting options (display order is chronological by date added)
- Book recommendations or ratings
- Import/export functionality
- Mobile native apps
- Real-time sync across devices

**Testable Acceptance Criteria:**
1. Starting the server with `npm start` serves the application on the configured port
2. Navigating to `http://localhost:<PORT>` displays the book library interface
3. The UI uses the chosen CSS framework and is visually centered and readable
4. Users can add a new book via a form, and it appears in the list immediately
5. Users can click a book to view its full details
6. Users can edit any book field including its read/unread status
7. Users can delete a book, and it is removed from the list
8. Filtering by "All", "Read", or "Unread" updates the visible book list
9. Closing and restarting the server preserves all book data
10. The README contains clear instructions to install dependencies and run the app

## Functional Requirements Outline

**FR-1: Book Management**
- FR-1.1: Create new book with required and optional fields
- FR-1.2: Retrieve list of all books
- FR-1.3: Retrieve single book by ID
- FR-1.4: Update existing book fields
- FR-1.5: Delete book by ID

**FR-2: Status Tracking**
- FR-2.1: Mark book as read
- FR-2.2: Mark book as unread
- FR-2.3: Filter book list by status (all/read/unread)

**FR-3: Data Persistence**
- FR-3.1: Load books from JSON file on server start
- FR-3.2: Save books to JSON file after each modification
- FR-3.3: Handle missing or corrupted data file gracefully

**FR-4: User Interface**
- FR-4.1: Display book list with key information (title, author, status)
- FR-4.2: Provide form to add new books
- FR-4.3: Provide detail view for individual books
- FR-4.4: Provide edit interface for book fields
- FR-4.5: Provide delete confirmation mechanism
- FR-4.6: Provide status filter controls

**FR-5: API Endpoints**
- FR-5.1: GET /api/books - list all books (with optional ?status= query)
- FR-5.2: GET /api/books/:id - retrieve single book
- FR-5.3: POST /api/books - create new book
- FR-5.4: PUT /api/books/:id - update book
- FR-5.5: DELETE /api/books/:id - delete book

## Non-Functional Targets

**Performance:**
- API response time < 100ms for all endpoints under normal load (< 1000 books)
- Page load time < 2 seconds on standard broadband
- UI interactions (filter, add, edit) feel instant (< 200ms perceived delay)
- *Justification*: Single-user local app with file-based storage; these targets ensure smooth UX without over-engineering

**Scalability:**
- Support up to 10,000 books without degradation
- JSON file size limit: 10MB (approximately 5,000-10,000 books depending on metadata)
- *Justification*: Personal library use case; file-based storage has natural limits; beyond this scale a real database is appropriate

**Reliability:**
- Data consistency: atomic file writes prevent corruption
- Graceful degradation: if data file is corrupted, start with empty library and log error
- Error handling: all API endpoints return appropriate HTTP status codes and error messages
- *Justification*: Single point of failure (file system) requires defensive coding; user should never lose data due to app error

**Security:**
- Input validation: sanitize all user inputs to prevent injection attacks
- File path validation: prevent directory traversal attacks
- No sensitive data: application stores only book metadata (no passwords, payment info)
- *Justification*: Local-only app reduces attack surface; still must prevent malicious input from corrupting data or accessing filesystem

**Maintainability:**
- Code coverage: aim for 80%+ test coverage on business logic
- Modular architecture: clear separation between API routes, business logic, and data access
- Documentation: inline comments for complex logic, README for setup/usage
- Linting: ESLint with standard configuration
- *Justification*: Enables future enhancements and debugging; demonstrates professional development practices

**Usability:**
- Responsive design: works on desktop and tablet viewports (mobile optional)
- Accessible: semantic HTML, keyboard navigation support
- Error feedback: clear messages when operations fail
- *Justification*: Modern web standards; improves user experience without significant cost

## Architecture

### Components and Responsibilities

**1. Express Server (`src/server.js`)**
- Initialize Express app
- Configure middleware (JSON parsing, static file serving, CORS if needed)
- Mount API routes
- Start HTTP server on configured port
- Handle graceful shutdown

**2. API Routes (`src/routes/bookRoutes.js`)**
- Define REST endpoints for book operations
- Validate request parameters and body
- Delegate business logic to service layer
- Transform responses to JSON
- Handle HTTP errors

**3. Book Service (`src/services/bookService.js`)**
- Implement business logic for book operations (CRUD)
- Generate unique IDs for new books
- Validate book data model
- Coordinate with data access layer

**4. Data Access Layer (`src/data/bookRepository.js`)**
- Read books from JSON file
- Write books to JSON file (atomic operations)
- Handle file system errors
- Initialize data file if missing
- In-memory caching of book data for performance

**5. Data Models (`src/models/book.js`)**
- Define book schema/interface
- Validation functions for book fields
- Default values

**6. Frontend Static Files**
- `public/index.html` - Main application page structure
- `public/css/styles.css` - Custom styles (plus CSS framework CDN)
- `public/js/app.js` - Main application logic, API client
- `public/js/ui.js` - DOM manipulation, event handlers, rendering

**7. Configuration (`src/config/config.js`)**
- Environment variable loading
- Default configuration values
- Data file path configuration

### Key Flows

**Flow 1: Add New Book (Sequence Diagram)**
```
User -> Browser: Fill form, click "Add Book"
Browser -> app.js: Capture form submit event
app.js -> API (POST /api/books): { title, author, ... }
API -> bookRoutes: Route request
bookRoutes -> bookService: createBook(bookData)
bookService -> bookRepository: save(newBook)
bookRepository -> FileSystem: Write data/books.json
FileSystem -> bookRepository: Success
bookRepository -> bookService: newBook
bookService -> bookRoutes: newBook
bookRoutes -> API: 201 Created, { book }
API -> app.js: Response JSON
app.js -> ui.js: renderBookList(books)
ui.js -> Browser: Update DOM with new book
Browser -> User: Display updated list
```

**Flow 2: Filter Books by Status**
```
User -> Browser: Click "Read" filter button
Browser -> app.js: Capture click event
app.js -> API (GET /api/books?status=read): Request
API -> bookRoutes: Route with query param
bookRoutes -> bookService: getBooks({ status: 'read' })
bookService -> bookRepository: findAll()
bookRepository -> bookService: allBooks[]
bookService -> bookService: Filter by status
bookService -> bookRoutes: filteredBooks[]
bookRoutes -> API: 200 OK, { books }
API -> app.js: Response JSON
app.js -> ui.js: renderBookList(filteredBooks)
ui.js -> Browser: Update DOM
Browser -> User: Display filtered list
```

**Flow 3: Server Startup and Data Loading**
```
Process -> server.js: node src/server.js
server.js -> config: Load configuration
server.js -> bookRepository: initialize()
bookRepository -> FileSystem: Check data/books.json exists
FileSystem -> bookRepository: File status
bookRepository -> FileSystem: Read or create file
FileSystem -> bookRepository: JSON content
bookRepository -> bookRepository: Parse and cache books
bookRepository -> server.js: Ready
server.js -> Express: app.listen(PORT)
Express -> server.js: Server running
server.js -> Console: "Server running on port 3000"
```

### Failure Modes and Handling

**1. Corrupted JSON File**
- Detection: JSON.parse() throws error during startup
- Handling: Log error, backup corrupted file to `data/books.json.backup`, start with empty array
- Recovery: User can manually restore from backup

**2. File System Write Failure**
- Detection: fs.writeFile() returns error
- Handling: Return 500 error to client, log error, keep in-memory state unchanged
- Recovery: Retry on next operation; if persistent, user must check disk space/permissions

**3. Invalid Book Data**
- Detection: Validation in bookService before save
- Handling: Return 400 Bad Request with specific error message
- Recovery: User corrects input and resubmits

**4. Concurrent Modifications**
- Risk: Multiple requests modifying data simultaneously
- Handling: In-memory cache is single-threaded (Node.js event loop); file writes are queued
- Limitation: Multiple server instances would conflict (out of scope)

**5. Missing Book ID**
- Detection: GET/PUT/DELETE with non-existent ID
- Handling: Return 404 Not Found
- Recovery: User refreshes list to see current state

### Security Boundaries

**1. Input Validation Boundary**
- All API inputs validated before processing
- String length limits (title: 200 chars, author: 100 chars)
- Enum validation for status field (read/unread only)
- ID format validation (UUID or numeric)

**2. File System Boundary**
- Data file path is hardcoded in configuration
- No user-supplied file paths accepted
- Directory traversal prevention (validate paths don't contain `..`)

**3. API Boundary**
- No authentication (single-user local app)
- CORS configured to allow localhost only
- Rate limiting not required (local use)

### Data Consistency

**Strategy: Write-Through Cache**
- In-memory array holds current state
- Every modification immediately written to disk
- Atomic writes using temp file + rename pattern
- On startup, file is source of truth

**Consistency Guarantees:**
- Single server instance: strong consistency (in-memory state always matches file after successful write)
- Crash recovery: last successful write is recovered on restart
- No distributed consistency needed (single node)

### Testing Strategy

**Unit Tests:**
- `bookService.js`: All CRUD operations, validation logic
- `bookRepository.js`: File read/write, error handling, initialization
- `book.js`: Model validation functions

**Integration Tests:**
- API endpoints: Request/response for all routes
- End-to-end flows: Create -> Read -> Update -> Delete
- Error scenarios: Invalid input, missing resources

**Manual Testing:**
- Browser UI testing for all user interactions
- Visual regression testing for CSS framework integration
- Cross-browser testing (Chrome, Firefox, Safari)

**Test Data:**
- Mock file system for repository tests
- Fixture books for service and API tests
- Temporary test directory for integration tests

### Deployment

**Local Development:**
1. Clone repository
2. Run `npm install`
3. Run `npm start` (starts server on port 3000)
4. Open `http://localhost:3000` in browser

**Production Considerations (if deployed):**
- Environment variable for PORT
- Environment variable for DATA_FILE_PATH
- Process manager (PM2) for auto-restart
- Reverse proxy (nginx) for static file serving
- Regular backups of data/books.json

**No CI/CD Pipeline Required** (local app, but tests can be run with `npm test`)

## Proposed File Tree

```
src/
  server.js
  config/
    config.js
  models/
    book.js
  data/
    bookRepository.js
  services/
    bookService.js
  routes/
    bookRoutes.js
  utils/
    logger.js
    fileUtils.js
public/
  index.html
  css/
    styles.css
  js/
    app.js
    ui.js
data/
  books.json
  .gitkeep
tests/
  unit/
    models/
      book.test.js
    services/
      bookService.test.js
    data/
      bookRepository.test.js
  integration/
    routes/
      bookRoutes.test.js
  fixtures/
    sampleBooks.json
package.json
.gitignore
.eslintrc.json
README.md
```

## Architecture Decision Records

**ADR-0001: JSON File Storage Over Database**
- Decision: Use JSON file on disk instead of SQLite or other embedded database
- Rationale: Explicit requirement in brief; simplifies deployment; sufficient for single-user use case
- Tradeoffs: Limited scalability, no ACID transactions, manual consistency management

**ADR-0002: Static SPA Frontend Over Server-Side Rendering**
- Decision: Serve static HTML/CSS/JS files; fetch data via REST API
- Rationale: Cleaner separation of concerns, easier to test API independently, aligns with "consuming the API" language
- Tradeoffs: Requires JavaScript enabled in browser; slightly more complex initial load

**ADR-0003: Write-Through Cache for Data Access**
- Decision: Keep books in memory, write to file on every modification
- Rationale: Fast reads (no file I/O), acceptable write performance for expected load, simple consistency model
- Tradeoffs: Memory usage scales with book count; data loss if write fails (mitigated by error handling)

**ADR-0004: Atomic File Writes Using Temp File Pattern**
- Decision: Write to temporary file, then rename to target (atomic operation on POSIX systems)
- Rationale: Prevents corruption if process crashes during write
- Tradeoffs: Requires extra disk I/O; temp file cleanup needed on errors

**ADR-0005: UUID v4 for Book IDs**
- Decision: Generate UUIDs for book identifiers instead of auto-increment integers
- Rationale: No collision risk, no need to track counter in file, easier to reason about in distributed scenarios (future)
- Tradeoffs: Longer IDs (36 chars vs. 1-5 digits), not human-readable

**ADR-0006: Bootstrap CSS Over Materialize**
- Decision: Use Bootstrap CSS framework (pending human confirmation)
- Rationale: More widely adopted, better documentation, larger community
- Tradeoffs: Slightly heavier CSS bundle; specific design aesthetic

**ADR-0007: Express Middleware for Error Handling**
- Decision: Centralized error handling middleware as last route handler
- Rationale: DRY principle, consistent error responses, easier logging
- Tradeoffs: Requires throwing/passing errors correctly in all routes

**ADR-0008: No Authentication Layer**
- Decision: No user login or session management
- Rationale: Single-user local application per brief; authentication adds complexity without value
- Tradeoffs: Cannot be safely exposed to network without adding auth later

**ADR-0009: Mocha + Chai for Testing**
- Decision: Use Mocha test framework with Chai assertion library
- Rationale: Standard Node.js testing stack, good Express integration, readable syntax
- Tradeoffs: Requires learning curve if team unfamiliar; alternative is Jest (more batteries-included)

**ADR-0010: ESLint with Airbnb Style Guide**
- Decision: Enforce code style with ESLint using Airbnb base configuration
- Rationale: Industry-standard style guide, catches common errors, improves maintainability
- Tradeoffs: Initial setup time; some rules may feel restrictive

## Risks

**Risk 1: File Corruption Due to Concurrent Writes**
- **Likelihood**: Low (Node.js single-threaded, writes are queued)
- **Impact**: High (data loss)
- **Mitigation**: Atomic write pattern, backup on corruption detection, comprehensive error handling
- **Contingency**: Document manual recovery process in README

**Risk 2: JSON File Size Growth**
- **Likelihood**: Medium (depends on user behavior)
- **Impact**: Medium (performance degradation)
- **Mitigation**: Document 10,000 book limit in README, test with large datasets
- **Contingency**: Provide migration path to real database in future version

**Risk 3: Browser Compatibility Issues**
- **Likelihood**: Medium (vanilla JS, modern features)
- **Impact**: Low (affects UX but not data)
- **Mitigation**: Use widely-supported ES6 features, test on major browsers, provide graceful degradation
- **Contingency**: Document supported browsers in README

**Risk 4: Ambiguous Requirements Leading to Rework**
- **Likelihood**: Medium (brief leaves some details open)
- **Impact**: Medium (wasted development time)
- **Mitigation**: This plan surfaces all open decisions for human approval before implementation
- **Contingency**: Modular architecture allows swapping components (e.g., changing ID generation strategy)

**Risk 5: CSS Framework JS Accidentally Included**
- **Likelihood**: Low (explicit constraint)
- **Impact**: Low (violates brief but easy to fix)
- **Mitigation**: Use CSS-only CDN links, code review checklist, test without framework JS
- **Contingency**: Remove framework JS, reimplement needed interactions in vanilla JS

**Risk 6: Developer Misinterprets File Tree**
- **Likelihood**: Low (tree is explicit)
- **Impact**: High (wrong structure, rework needed)
- **Mitigation**: File tree above is binding and complete; includes all source files, tests, and configs
- **Contingency**: This plan serves as specification; Developer must match it exactly

---

**Reply 'approve' to lock this plan, or 'revise <your answers or changes>'.**