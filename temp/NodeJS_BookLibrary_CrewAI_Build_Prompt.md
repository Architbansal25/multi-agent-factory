# Node.js Book Library Application — Multi-Agent Build Prompt

**Target consumer:** CrewAI-based multi-agent factory app
**Purpose:** Autonomous build spec — feed this whole file to the factory app as the task/crew input so agents can plan, implement, test, and document the application without further clarification.

---

## 1. Project Overview

Build a **Book Library web application** where users can add books, mark them as **read** or **unread**, filter the list by status, and view/manage individual book details.

The system consists of:
- A **Node.js + Express** backend exposing a REST API
- A **JSON file** acting as the data store (no database)
- A simple **server-rendered or static HTML/CSS/vanilla-JS** frontend consuming the API

---

## 2. Mandatory Tech Stack & Constraints

| Constraint | Rule |
|---|---|
| Runtime | Node.js |
| Web framework | **Must use Express.js** |
| Data store | JSON file on disk (e.g. `data/books.json`) — no external DB |
| Frontend JS | Vanilla JavaScript only |
| CSS frameworks | Bootstrap or Materialize **CSS only** — their bundled JS/JS components are **not allowed** |
| Styling | Plain CSS, Sass, or Less all permitted |
| Documentation | A `README.md` describing the app and local run steps is **required** |

Agents must not substitute a database (Mongo/Postgres/SQLite/etc.), a frontend framework (React/Vue/Angular), or Bootstrap/Materialize's JS widgets (modals, dropdowns, carousels via their JS bundle) — reimplement any needed interactivity in vanilla JS.

---

## 3. Data Model

Each **Book** record must have exactly these fields:

```json
{
  "id": "string (unique identifier, e.g. uuid)",
  "title": "string",
  "author": "string",
  "status": "Read | Unread",
  "description": "string",
  "date": "ISO date string — date the book was added"
}
```

`date` is set by the server at creation time, not supplied by the client.

---

## 4. API Endpoints (must all be implemented)

| # | Method | Path | Purpose | Success | Notes |
|---|--------|------|---------|---------|-------|
| 1 | POST | `/api/books` | Create a book | 201 + created book | Validate required fields |
| 2 | GET | `/api/books` | Get all books | 200 + array | Must support `?status=read` / `?status=unread` query filter |
| 3 | GET | `/api/books/:id` | Get a single book | 200 + book | 404 if not found |
| 4 | PATCH or PUT | `/api/books/:id` | Update a book's read/unread status | 200 + updated book | 404 if not found; 400 if invalid status value |
| 5 | DELETE | `/api/books/:id` | Delete a book | 200/204 | 404 if not found |

Path prefix (`/api/...` vs `/books/...`) may vary — path equivalency is acceptable as long as all 5 operations exist and are documented in the README.

---

## 5. Functional Requirements

### 5.1 Filtering
- A dedicated way (query parameter, e.g. `GET /api/books?status=read`) to retrieve **only** read or **only** unread books.
- The UI must expose a filter control (e.g. tabs/dropdown/buttons) that calls this filtered endpoint — not a client-side-only filter of an already-fetched full list.

### 5.2 Book Details View
- Users can click into / view a single book's full details (title, author, status, description, date).

### 5.3 Mark Read/Unread
- Users can toggle a book's status from the UI, which calls the update endpoint.

### 5.4 Error Handling
Minimum required cases:
- Missing/invalid required fields on create → `400` with a clear JSON error message
- Requesting/updating/deleting a non-existent id → `404` with a clear JSON error message
- Invalid `status` value (anything other than `Read`/`Unread`) → `400`
- Malformed JSON body → `400` (not an uncaught server crash)
- All errors return a consistent JSON shape, e.g. `{ "error": "message" }`

---

## 6. UI Requirements

- Add-book form (title, author, description, status)
- Book list view showing title, author, status at a glance
- Filter control for Read / Unread / All
- Book detail view (click-through or expandable)
- Controls to mark a book read/unread and to delete a book
- Styled with CSS/Sass/Less and optionally Bootstrap/Materialize CSS classes only

---

## 7. Deliverables

1. Complete, runnable Node.js/Express project source
2. `data/books.json` (or equivalent) as the JSON data store, created/seeded at startup if missing
3. Frontend (HTML/CSS/vanilla JS) served by the same Express app or as static files
4. `README.md` including:
   - App description
   - Setup & install steps (`npm install`)
   - How to run locally (`npm start` / `node server.js`, port used)
   - API endpoint list with example requests
5. Clean project structure (suggested):
   ```
   /
   ├── server.js
   ├── routes/books.js
   ├── data/books.json
   ├── public/ (index.html, styles, client.js)
   ├── package.json
   └── README.md
   ```

---

## 8. Suggested CrewAI Agent/Task Breakdown

For the factory app's crew, this task decomposes cleanly into:

1. **Architect Agent** — designs folder structure, data schema, and endpoint contracts from this spec
2. **Backend Developer Agent** — implements Express server, routes, JSON persistence layer, validation, error handling
3. **Frontend Developer Agent** — builds the HTML/CSS/vanilla-JS UI (list, filter, detail, add/edit/delete controls) against the API contract
4. **QA/Reviewer Agent** — verifies against the Acceptance Criteria in Section 9 below, checks for forbidden dependencies (DB, frontend framework, Bootstrap/Materialize JS)
5. **Documentation Agent** — writes/finalizes `README.md`

Agents should treat Sections 2–7 above as immutable constraints, not suggestions.

---

## 9. Acceptance Criteria

The build is considered **complete and passing** only if all of the following are true:

**Setup & Stack**
- [ ] Project runs with `npm install && npm start` (or documented equivalent) with no manual steps beyond that
- [ ] Server is built with Express.js
- [ ] No external database is used; data persists to a JSON file on disk
- [ ] No frontend JS framework (React/Vue/Angular/etc.) is used
- [ ] If Bootstrap/Materialize is used, only their CSS is included — no bundled JS

**Data Model**
- [ ] Every book record has `title`, `author`, `status`, `description`, `date`
- [ ] `status` is restricted to `Read`/`Unread` (case-consistent) at the API layer
- [ ] `date` is server-assigned at creation and not client-overridable

**Endpoints**
- [ ] `POST` creates a book and returns it with a generated `id` and `date`
- [ ] `GET` all books returns the full list
- [ ] `GET` all books supports filtering to read-only or unread-only via a query parameter
- [ ] `GET` single book by id returns that book, or `404` if missing
- [ ] Update endpoint changes a book's status and returns the updated record
- [ ] `DELETE` removes a book and it no longer appears in subsequent `GET` calls

**Error Handling**
- [ ] Creating a book with missing required fields returns `400` with an error message, not a crash
- [ ] Fetching/updating/deleting an unknown id returns `404` with an error message
- [ ] Sending an invalid `status` value on update returns `400`
- [ ] Sending malformed JSON does not crash the server and returns a `4xx` response

**UI**
- [ ] User can add a book via a form
- [ ] User can see the list of books with title/author/status visible
- [ ] User can filter the visible list to Read-only or Unread-only via a control that hits the filtered endpoint
- [ ] User can open a book to see its full details (including description and date)
- [ ] User can toggle a book's read/unread status from the UI
- [ ] User can delete a book from the UI

**Documentation**
- [ ] `README.md` exists and explains what the app does
- [ ] `README.md` includes exact steps to install and run the app locally
- [ ] `README.md` lists the available API endpoints

**Definition of Done:** All checkboxes above pass on a clean clone + `npm install` + run, using only the JSON file as storage, with no console errors on any of the 5 core operations (create, list, filter, detail, update-status, delete).
