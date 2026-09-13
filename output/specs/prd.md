# PRD: Book Library Web Application

## Overview
A self-contained personal book library management web application with a Node.js + Express backend and vanilla JavaScript frontend. Data persists in a JSON file with no external dependencies.

---

# SERVICE 1: BACKEND API (Node.js + Express)

## Build Step 1.1: Project Initialization
**Objective**: Set up Node.js project with Express dependency.

**Concrete Actions**:
1. Create project directory: `mkdir book-library && cd book-library`
2. Initialize npm: `npm init -y`
3. Install Express: `npm install express`
4. Create `server.js` file in project root

**Acceptance Criteria**:
- [ ] `package.json` exists with `express` listed in dependencies
- [ ] `node_modules/` directory created
- [ ] `server.js` file exists and is empty/ready for code

---

## Build Step 1.2: Implement Express Server with Static File Serving
**Objective**: Create Express server that listens on port 3000 and serves static HTML/CSS/JS files.

**Concrete Actions**:
1. In `server.js`, import Express
2. Create Express app instance
3. Configure middleware: `app.use(express.json())` and `app.use(express.static('public'))`
4. Add root GET route (`/`) that serves `public/index.html`
5. Start server on port 3000 with console log: `"Server running on http://localhost:3000"`

**Acceptance Criteria**:
- [ ] Server starts without errors: `node server.js`
- [ ] Console outputs: `"Server running on http://localhost:3000"`
- [ ] Visiting `http://localhost:3000` in browser returns HTML (will be empty until Step 2.1)
- [ ] Server can be stopped with Ctrl+C

---

## Build Step 1.3: Implement Data Persistence Layer (JSON File)
**Objective**: Create functions to read/write book data from/to `data/books.json`.

**Concrete Actions**:
1. Create `data/` directory in project root
2. In `server.js`, add function `loadBooks()` that:
   - Reads `data/books.json` if it exists
   - Returns parsed JSON object with `books` array and `nextId` counter
   - If file doesn't exist, creates it with initial structure: `{ "books": [], "nextId": 1 }`
3. Add function `saveBooks(data)` that writes data object to `data/books.json`
4. Call `loadBooks()` on server startup to initialize data in memory

**Acceptance Criteria**:
- [ ] `data/` directory exists
- [ ] `data/books.json` is created automatically on first server run
- [ ] `data/books.json` contains valid JSON: `{ "books": [], "nextId": 1 }`
- [ ] `loadBooks()` returns correct structure when called
- [ ] `saveBooks()` writes changes to file and persists across server restarts

---

## Build Step 1.4: Implement GET /api/books Endpoint (List All Books)
**Objective**: Return all books from JSON file, with optional read status filter.

**Concrete Actions**:
1. Add GET route `/api/books` in `server.js`
2. Extract query parameter `read` (if present: `req.query.read`)
3. Load books from memory (populated in Step 1.3)
4. If `read` query param exists:
   - If `read=true`, filter to books where `read === true`
   - If `read=false`, filter to books where `read === false`
5. Return filtered/unfiltered array as JSON

**Acceptance Criteria**:
- [ ] `curl http://localhost:3000/api/books` returns `[]` (empty array initially)
- [ ] `curl http://localhost:3000/api/books?read=true` returns `[]`
- [ ] `curl http://localhost:3000/api/books?read=false` returns `[]`
- [ ] After adding books (Step 1.5), filtering works correctly

---

## Build Step 1.5: Implement POST /api/books Endpoint (Add New Book)
**Objective**: Accept new book data, assign ID, save to JSON file, return created book.

**Concrete Actions**:
1. Add POST route `/api/books` in `server.js`
2. Extract request body: `title`, `author`, `year`, `read`
3. Validate all fields are present (return 400 if any missing)
4. Create new book object with:
   - `id`: current `nextId` value
   - `title`, `author`, `year`, `read`: from request body
5. Add book to `books` array in memory
6. Increment `nextId` counter
7. Call `saveBooks()` to persist to JSON file
8. Return created book object with 201 status code

**Acceptance Criteria**:
- [ ] `curl -X POST http://localhost:3000/api/books -H "Content-Type: application/json" -d '{"title":"1984","author":"Orwell","year":1949,"read":true}'` returns `{"id":1,"title":"1984","author":"Orwell","year":1949,"read":true}`
- [ ] Response status code is 201
- [ ] Book is saved to `data/books.json` and persists after server restart
- [ ] Second POST request returns `id: 2` (nextId incremented)
- [ ] Missing fields return 400 error with descriptive message

---

## Build Step 1.6: Implement GET /api/books/:id Endpoint (Get Single Book)
**Objective**: Return a single book by ID.

**Concrete Actions**:
1. Add GET route `/api/books/:id` in `server.js`
2. Extract `id` from URL parameter: `req.params.id`
3. Search `books` array for book with matching `id`
4. If found, return book object with 200 status
5. If not found, return 404 error with message: `"Book not found"`

**Acceptance Criteria**:
- [ ] `curl http://localhost:3000/api/books/1` returns the book with `id: 1`
- [ ] `curl http://localhost:3000/api/books/999` returns 404 with `"Book not found"`
- [ ] Response includes all book fields: `id`, `title`, `author`, `year`, `read`

---

## Build Step 1.7: Implement PUT /api/books/:id Endpoint (Update Book)
**Objective**: Update one or more fields of an existing book.

**Concrete Actions**:
1. Add PUT route `/api/books/:id` in `server.js`
2. Extract `id` from URL parameter
3. Search `books` array for book with matching `id`
4. If not found, return 404 error
5. If found, update fields from request body (only fields present in body):
   - Accept partial updates: `title`, `author`, `year`, `read` (any combination)
6. Save updated data to JSON file via `saveBooks()`
7. Return updated book object with 200 status

**Acceptance Criteria**:
- [ ] `curl -X PUT http://localhost:3000/api/books/1 -H "Content-Type: application/json" -d '{"read":false}'` updates only the `read` field
- [ ] `curl -X PUT http://localhost:3000/api/books/1 -H "Content-Type: application/json" -d '{"title":"New Title","year":2020}'` updates multiple fields
- [ ] Unmodified fields remain unchanged
- [ ] Changes persist in `data/books.json` after server restart
- [ ] `curl -X PUT http://localhost:3000/api/books/999 ...` returns 404

---

## Build Step 1.8: Implement DELETE /api/books/:id Endpoint (Delete Book)
**Objective**: Remove a book by ID.

**Concrete Actions**:
1. Add DELETE route `/api/books/:id` in `server.js`
2. Extract `id` from URL parameter
3. Search `books` array for book with matching `id`
4. If not found, return 404 error
5. If found, remove book from array using `filter()` or `splice()`
6. Save updated data to JSON file via `saveBooks()`
7. Return JSON response: `{"success": true}` with 200 status

**Acceptance Criteria**:
- [ ] `curl -X DELETE http://localhost:3000/api/books/1` returns `{"success": true}`
- [ ] Book is removed from `data/books.json` and does not appear in subsequent GET requests
- [ ] `curl -X DELETE http://localhost:3000/api/books/999` returns 404
- [ ] Deletion persists after server restart

---

## Build Step 1.9: Test All Backend Endpoints
**Objective**: Verify all API endpoints work correctly in isolation.

**Concrete Actions**:
1. Start server: `node server.js`
2. Execute curl commands in order:
   - POST 3 books with different `read` values
   - GET all books (verify count = 3)
   - GET with `?read=true` filter
   - GET with `?read=false` filter
   - GET single book by ID
   - PUT to update a book field
   - DELETE a book
   - GET all books again (verify count = 2)
3. Restart server and verify data persists

**Acceptance Criteria**:
- [ ] All curl commands execute without error
- [ ] Responses match expected structure and values
- [ ] Filtering returns correct subset of books
- [ ] Data persists across server restart
- [ ] No console errors during execution

---

# SERVICE 2: FRONTEND UI (Vanilla JavaScript + Bootstrap 5)

## Build Step 2.1: Create HTML Structure with Bootstrap Styling
**Objective**: Build responsive HTML page with form and book list container.

**Concrete Actions**:
1. Create `public/` directory in project root
2. Create `public/index.html` with:
   - Bootstrap 5 CDN link in `<head>` (CSS only, no JS)
   - Title: "Book Library"
   - Container div with Bootstrap classes for centering and responsive layout
   - Form section with fields:
     - Text input: `title` (placeholder: "Book Title")
     - Text input: `author` (placeholder: "Author Name")
     - Number input: `year` (placeholder: "Publication Year")
     - Checkbox: `read` (label: "I have read this book")
     - Submit button: "Add Book"
   - Filter buttons section:
     - Button: "All Books" (id: `filter-all`)
     - Button: "Read" (id: `filter-read`)
     - Button: "Unread" (id: `filter-unread`)
   - Empty div with id `books-list` for rendering books
   - Script tag linking to `public/app.js`

**Acceptance Criteria**:
- [ ] `public/index.html` file exists and is valid HTML5
- [ ] Page loads in browser at `http://localhost:3000` without errors
- [ ] Bootstrap styling is applied (page is centered, responsive)
- [ ] Form fields are visible and properly labeled
- [ ] Filter buttons are visible
- [ ] `books-list` div is empty and ready for content

---

## Build Step 2.2: Create Vanilla JavaScript App Logic
**Objective**: Implement client-side logic to fetch, display, and manage books.

**Concrete Actions**:
1. Create `public/app.js` with:
   - `fetchBooks(filter = null)` function:
     - Calls GET `/api/books` (with `?read=true` or `?read=false` if filter provided)
     - Returns parsed JSON array
   - `renderBooks(books)` function:
     - Clears `books-list` div
     - For each book, create HTML row with:
       - Book title, author, year
       - "Mark as Read" or "Mark as Unread" button (based on `read` status)
       - "Edit" button (id: `edit-{id}`)
       - "Delete" button (id: `delete-{id}`)
     - Append row to `books-list`
   - `addBook(event)` function (form submit handler):
     - Prevent default form submission
     - Extract form values
     - POST to `/api/books`
     - Clear form fields
     - Call `fetchBooks()` and `renderBooks()` to refresh UI
   - `toggleReadStatus(id, currentStatus)` function:
     - PUT to `/api/books/{id}` with `read: !currentStatus`
     - Refresh book list
   - `deleteBook(id)` function:
     - DELETE `/api/books/{id}`
     - Refresh book list
   - `filterBooks(status)` function:
     - Call `fetchBooks(status)` and `renderBooks()`
   - Event listeners:
     - Form submit → `addBook()`
     - Filter buttons → `filterBooks()`
     - Dynamic event delegation for Edit/Delete/Toggle buttons

**Acceptance Criteria**:
- [ ] `public/app.js` file exists and has no syntax errors
- [ ] Console shows no JavaScript errors when page loads
- [ ] `fetchBooks()` successfully retrieves books from API
- [ ] `renderBooks()` displays books in `books-list` div
- [ ] Form submission triggers `addBook()` without page reload
- [ ] New books appear in list immediately after submission
- [ ] Filter buttons change displayed books without page reload
- [ ] Edit/Delete/Toggle buttons are clickable (functionality in next steps)

---

## Build Step 2.3: Implement Toggle Read Status Feature
**Objective**: Allow users to mark books as read/unread from the UI.

**Concrete Actions**:
1. In `public/app.js`, update `renderBooks()` to:
   - For each book, create button with text "Mark as Read" or "Mark as Unread" (based on `read` value)
   - Add click event listener that calls `toggleReadStatus(id, currentStatus)`
2. Implement `toggleReadStatus(id, currentStatus)` function:
   - Send PUT request to `/api/books/{id}` with `{"read": !currentStatus}`
   - On success, call `fetchBooks()` and `renderBooks()` to update UI
   - On error, show alert with error message

**Acceptance Criteria**:
- [ ] Each book row displays "Mark as Read" or "Mark as Unread" button
- [ ] Clicking button sends PUT request to correct endpoint
- [ ] Button text updates immediately after click
- [ ] Change persists in `data/books.json`
- [ ] Filtering still works correctly after toggling read status

---

## Build Step 2.4: Implement Delete Book Feature
**Objective**: Allow users to delete books from the UI.

**Concrete Actions**:
1. In `public/app.js`, update `renderBooks()` to:
   - For each book, create "Delete" button
   - Add click event listener that calls `deleteBook(id)`
2. Implement `deleteBook(id)` function:
   - Show confirmation dialog: `confirm("Are you sure you want to delete this book?")`
   - If user confirms, send DELETE request to `/api/books/{id}`
   - On success, call `fetchBooks()` and `renderBooks()` to update UI
   - On error, show alert with error message

**Acceptance Criteria**:
- [ ] Each book row displays "Delete" button
- [ ] Clicking Delete shows confirmation dialog
- [ ] Confirming sends DELETE request to correct endpoint
- [ ] Book is removed from UI immediately
- [ ] Book is removed from `data/books.json`
- [ ] Subsequent page refresh does not show deleted book

---

## Build Step 2.5: Implement Edit Book Feature (Modal Form)
**Objective**: Allow users to edit book details via a modal dialog.

**Concrete Actions**:
1. In `public/index.html`, add hidden modal div with:
   - Modal title: "Edit Book"
   - Form fields for: `title`, `author`, `year`, `read` (pre-populated)
   - "Save" button (id: `save-edit`)
   - "Cancel" button (closes modal)
2. In `public/app.js`, update `renderBooks()` to:
   - For each book, create "Edit" button
   - Add click event listener that:
     - Populates modal form with current book data
     - Shows modal (using Bootstrap modal or simple CSS display)
3. Implement `editBook(id)` function:
   - Extract updated values from modal form
   - Send PUT request to `/api/books/{id}` with updated fields
   - Close modal
   - Call `fetchBooks()` and `renderBooks()` to update UI
   - On error, show alert with error message

**Acceptance Criteria**:
- [ ] Each book row displays "Edit" button
- [ ] Clicking Edit opens modal with book data pre-filled
- [ ] Modal form fields are editable
- [ ] Clicking "Save" sends PUT request with updated data
- [ ] Modal closes after successful save
- [ ] Book list updates with new values
- [ ] Changes persist in `data/books.json`
- [ ] Clicking "Cancel" closes modal without saving

---

## Build Step 2.6: Create Custom CSS Styling
**Objective**: Style the application for a clean, professional appearance.

**Concrete Actions**:
1. Create `public/style.css` with:
   - Body: centered layout, light background color, readable font
   - Container: max-width 900px, centered with margin auto, padding
   - Form section: styled input fields, button with hover effects
   - Filter buttons: grouped, with active state styling
   - Book list: table or card layout, alternating row colors
   - Book row: clear spacing, buttons aligned right
   - Modal: overlay, centered, with shadow
   - Responsive design: media queries for mobile (stack layout vertically)
2. Link stylesheet in `public/index.html`: `<link rel="stylesheet" href="style.css">`

**Acceptance Criteria**:
- [ ] `public/style.css` file exists
- [ ] Stylesheet is linked in HTML and loads without 404 errors
- [ ] Page layout is clean, centered, and readable
- [ ] Form and buttons have visible styling and hover effects
- [ ] Book list is well-organized and easy to scan
- [ ] Modal is visually distinct and centered
- [ ] Page is responsive on mobile devices (tested at 375px width)
- [ ] No layout breaks or overlapping elements

---

## Build Step 2.7: Initialize App on Page Load
**Objective**: Load and display books when page first loads.

**Concrete Actions**:
1. In `public/app.js`, add initialization code at bottom:
   - Call `fetchBooks()` on page load
   - Call `renderBooks()` with fetched data
   - Attach form submit event listener to form element
   - Attach click event listeners to filter buttons
2. Wrap initialization in `document.addEventListener('DOMContentLoaded', () => { ... })`

**Acceptance Criteria**:
- [ ] Page loads and displays all books from `data/books.json` automatically
- [ ] Books appear without manual refresh or button click
- [ ] Form and filter buttons are functional immediately
- [ ] No console errors on page load
- [ ] Works on page refresh (data loads from backend)

---

## Build Step 2.8: Test Frontend UI End-to-End
**Objective**: Verify all UI features work correctly with backend.

**Concrete Actions**:
1. Start server: `node server.js`
2. Open browser to `http://localhost:3000`
3. Execute test sequence:
   - Verify empty book list displays
   - Add 3 books using form (mix of read/unread)
   - Verify books appear in list immediately
   - Click "Read" filter, verify only read books show
   - Click "Unread" filter, verify only unread books show
   - Click "All Books" filter, verify all books show
   - Click "Mark as Unread" on a read book, verify status changes
   - Click "Edit" on a book, modify title, save, verify change appears
   - Click "Delete" on a book, confirm, verify book disappears
   - Refresh page, verify all changes persisted
4. Test on mobile viewport (375px width) for responsiveness

**Acceptance Criteria**:
- [ ] All CRUD operations work from UI
- [ ] Form submission adds books without page reload
- [ ] Filtering works correctly
- [ ] Toggle read status works
- [ ] Edit modal opens, saves, and updates list
- [ ] Delete removes book with confirmation
- [ ] Page refresh loads persisted data
- [ ] No console errors during any operation
- [ ] Layout is responsive and readable on mobile

---

# SERVICE 3: DOCUMENTATION

## Build Step 3.1: Create README.md
**Objective**: Document setup, installation, and usage instructions.

**Concrete Actions**:
1. Create `README.md` in project root with sections:
   - **Project Title**: "Book Library Web Application"
   - **Overview**: 1-2 sentence description
   - **Features**: Bulleted list of CRUD operations and filtering
   - **Tech Stack**: Table with technology choices and rationale
   - **Installation**:
     - Prerequisites: Node.js 16+
     - Step-by-step: clone, npm install, run
   - **Running the Application**:
     - Command: `node server.js`
     - URL: `http://localhost:3000`
   - **API Endpoints**: Table with method, path, description, example curl commands
   - **Data Persistence**: Explanation of JSON file location and structure
   - **Project Structure**: Directory tree showing all files
   - **Troubleshooting**: Common issues and solutions

**Acceptance Criteria**:
- [ ] `README.md` file exists in project root
- [ ] All sections are complete and clearly written
- [ ] Installation steps are accurate and can be followed by a new developer
- [ ] API endpoint examples include working curl commands
- [ ] File structure matches actual project layout
- [ ] No typos or broken formatting

---

## Build Step 3.2: Create Project Structure Documentation
**Objective**: Verify final project structure matches specification.

**Concrete Actions**:
1. Verify directory structure:
   ```
   book-library/
   ├── server.js
   ├── package.json
   ├── package-lock.json
   ├── README.md
   ├── data/
   │   └── books.json
   └── public/
       ├── index.html
       ├── app.js
       └── style.css
   ```
2. Verify all files exist and contain code (no empty files except data/books.json on first run)

**Acceptance Criteria**:
- [ ] All required files exist in correct locations
- [ ] No extra files or directories
- [ ] `server.js` is single entry point for backend
- [ ] `public/` contains only frontend files
- [ ] `data/` directory is created and contains `books.json`

---

# FINAL ACCEPTANCE CRITERIA (All Services)

## Functional Requirements
- [ ] Application starts with `node server.js` and listens on port 3000
- [ ] Visiting `http://localhost:3000` displays book library UI
- [ ] All 5 CRUD operations work (Create, Read, Update, Delete via API and UI)
- [ ] Filtering by read status works (query parameter and UI buttons)
- [ ] Data persists in `data/books.json` across server restarts
- [ ] Form submission adds books without page reload
- [ ] Edit modal allows partial updates to book fields
- [ ] Delete requires user confirmation before removing book
- [ ] Toggle read status updates immediately in UI and backend

## Technical Requirements
- [ ] Backend: Single `server.js` file with Express.js
- [ ] Frontend: Vanilla JavaScript (no frameworks), Bootstrap 5 CSS only
- [ ] Data: JSON file (`data/books.json`), no external database
- [ ] Dependencies: Only `express` npm package
- [ ] No third-party integrations or external APIs
- [ ] All endpoints return proper HTTP status codes (200, 201, 400, 404)
- [ ] All endpoints return valid JSON responses

## Code Quality
- [ ] No console errors or warnings
- [ ] No unhandled promise rejections
- [ ] Responsive design works on mobile (375px+) and desktop
- [ ] Form validation prevents empty submissions
- [ ] Error messages are user-friendly
- [ ] Code is readable with clear variable/function names

## Documentation
- [ ] `README.md` includes complete setup and run instructions
- [ ] API endpoints documented with examples
- [ ] Project structure clearly explained
- [ ] All files are present and in correct locations

---

**Architect Sign-Off**: This PRD is complete and ready for Developer implementation. All build steps are concrete, independently checkable, and include explicit acceptance criteria. Upon Developer confirmation of completion, I will verify against these criteria and sign off on delivery to Manager.