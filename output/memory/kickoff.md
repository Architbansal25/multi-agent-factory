# Build Instruction for Software Architect

## Project: Book Library Web Application

---

## What Must Be Built

A single full-stack web application that allows users to manage a personal book library. The application consists of:

1. **Backend**: A Node.js + Express REST API that handles all book operations
2. **Frontend**: A server-rendered or static HTML page with vanilla JavaScript that consumes the API
3. **Data Store**: A JSON file (`data/books.json`) persisted on disk

---

## Why This Matters

Users need a simple, lightweight way to track their books and reading progress without complexity or external dependencies. This application demonstrates a complete, self-contained web service that can run locally with zero external infrastructure.

---

## Core Features to Implement

### Backend API (Express.js)
- **GET `/api/books`** – Retrieve all books (with optional query parameter for filtering by read status)
- **POST `/api/books`** – Add a new book (title, author, publication year, read status)
- **GET `/api/books/:id`** – Retrieve a single book's details
- **PUT `/api/books/:id`** – Update a book (mark as read/unread, edit details)
- **DELETE `/api/books/:id`** – Remove a book from the library
- **Serve static frontend** – Serve the HTML/CSS/JS files from the Express app

### Frontend (Vanilla JS + Bootstrap/Materialize CSS only)
- Display a list of all books with title, author, year, and read status
- Add new book form (inputs for title, author, year, read checkbox)
- Filter controls to show all books, read books, or unread books only
- Mark individual books as read/unread via UI interaction
- View/edit individual book details
- Delete books from the library
- Clean, centered, readable layout using Bootstrap or Materialize CSS framework (CSS only—no JS components)

---

## Hard Constraints (Non-Negotiable)

| Constraint | Rule |
|---|---|
| **Runtime** | Node.js only |
| **Web Framework** | Express.js (required) |
| **Data Store** | JSON file at `data/books.json`—no external database (Mongo, Postgres, SQLite, etc.) |
| **Frontend Framework** | Vanilla JavaScript only—no React, Vue, Angular, or similar |
| **CSS Framework** | Bootstrap or Materialize CSS only—their bundled JS and JS components (modals, dropdowns, carousels) are **forbidden**. Reimplement any interactive UI in vanilla JS. |
| **Styling** | Plain CSS, Sass, or Less permitted |
| **Documentation** | A `README.md` file is **required**, describing the app and providing complete local run instructions |

---

## Acceptance Criteria

✅ The application launches and serves a page in the browser  
✅ The page prominently displays the book library interface  
✅ The UI is clean, readable, and aesthetically styled with centered content  
✅ All CRUD operations (add, read, update, delete) work via the REST API  
✅ Filtering by read status works correctly  
✅ Data persists in the JSON file across restarts  
✅ `README.md` includes clear setup and run instructions  

---

## Your Task

Please confirm acceptance of this build instruction and proceed with implementation. Once complete, explicitly confirm that the application is ready for delivery, including verification that all features work and the `README.md` is complete.