import json
import os
from pathlib import Path
from fastapi import FastAPI, HTTPException, Query
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Optional

app = FastAPI()

DATA_DIR = Path("data")
BOOKS_FILE = DATA_DIR / "books.json"
PUBLIC_DIR = Path("public")

class Book(BaseModel):
    title: str
    author: str
    year: int
    read: bool

def ensure_data_dir():
    DATA_DIR.mkdir(exist_ok=True)

def load_books():
    ensure_data_dir()
    if BOOKS_FILE.exists():
        with open(BOOKS_FILE, 'r') as f:
            return json.load(f)
    else:
        initial_data = {"books": [], "nextId": 1}
        save_books(initial_data)
        return initial_data

def save_books(data):
    ensure_data_dir()
    with open(BOOKS_FILE, 'w') as f:
        json.dump(data, f, indent=2)

books_data = load_books()

@app.get("/api/books")
def get_books(read: Optional[bool] = Query(None)):
    global books_data
    books_data = load_books()
    books = books_data.get("books", [])
    
    if read is not None:
        books = [b for b in books if b["read"] == read]
    
    return books

@app.post("/api/books", status_code=201)
def create_book(book: Book):
    global books_data
    books_data = load_books()
    
    new_book = {
        "id": books_data["nextId"],
        "title": book.title,
        "author": book.author,
        "year": book.year,
        "read": book.read
    }
    
    books_data["books"].append(new_book)
    books_data["nextId"] += 1
    save_books(books_data)
    
    return new_book

@app.get("/api/books/{book_id}")
def get_book(book_id: int):
    global books_data
    books_data = load_books()
    
    for book in books_data.get("books", []):
        if book["id"] == book_id:
            return book
    
    raise HTTPException(status_code=404, detail="Book not found")

@app.put("/api/books/{book_id}")
def update_book(book_id: int, book: Book):
    global books_data
    books_data = load_books()
    
    for i, b in enumerate(books_data.get("books", [])):
        if b["id"] == book_id:
            books_data["books"][i].update(book.dict(exclude_unset=True))
            save_books(books_data)
            return books_data["books"][i]
    
    raise HTTPException(status_code=404, detail="Book not found")

@app.delete("/api/books/{book_id}")
def delete_book(book_id: int):
    global books_data
    books_data = load_books()
    
    initial_length = len(books_data.get("books", []))
    books_data["books"] = [b for b in books_data.get("books", []) if b["id"] != book_id]
    
    if len(books_data["books"]) == initial_length:
        raise HTTPException(status_code=404, detail="Book not found")
    
    save_books(books_data)
    return {"success": True}

@app.get("/")
def serve_root():
    html_file = PUBLIC_DIR / "index.html"
    if html_file.exists():
        return FileResponse(html_file)
    return {"message": "Book Library API"}

PUBLIC_DIR.mkdir(exist_ok=True)

index_html = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Book Library</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <link rel="stylesheet" href="style.css">
</head>
<body>
    <div class="container mt-5">
        <h1 class="text-center mb-4">Book Library</h1>
        
        <div class="card mb-4">
            <div class="card-body">
                <h5 class="card-title">Add New Book</h5>
                <form id="add-book-form">
                    <div class="row mb-3">
                        <div class="col-md-6">
                            <input type="text" id="title" class="form-control" placeholder="Book Title" required>
                        </div>
                        <div class="col-md-6">
                            <input type="text" id="author" class="form-control" placeholder="Author Name" required>
                        </div>
                    </div>
                    <div class="row mb-3">
                        <div class="col-md-6">
                            <input type="number" id="year" class="form-control" placeholder="Publication Year" required>
                        </div>
                        <div class="col-md-6">
                            <div class="form-check mt-2">
                                <input type="checkbox" id="read" class="form-check-input">
                                <label class="form-check-label" for="read">I have read this book</label>
                            </div>
                        </div>
                    </div>
                    <button type="submit" class="btn btn-primary">Add Book</button>
                </form>
            </div>
        </div>

        <div class="mb-3 text-center">
            <button id="filter-all" class="btn btn-outline-secondary active">All Books</button>
            <button id="filter-read" class="btn btn-outline-success">Read</button>
            <button id="filter-unread" class="btn btn-outline-warning">Unread</button>
        </div>

        <div id="books-list" class="row"></div>
    </div>

    <div class="modal fade" id="editModal" tabindex="-1">
        <div class="modal-dialog">
            <div class="modal-content">
                <div class="modal-header">
                    <h5 class="modal-title">Edit Book</h5>
                    <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                </div>
                <div class="modal-body">
                    <form id="edit-book-form">
                        <div class="mb-3">
                            <label for="edit-title" class="form-label">Title</label>
                            <input type="text" id="edit-title" class="form-control" required>
                        </div>
                        <div class="mb-3">
                            <label for="edit-author" class="form-label">Author</label>
                            <input type="text" id="edit-author" class="form-control" required>
                        </div>
                        <div class="mb-3">
                            <label for="edit-year" class="form-label">Year</label>
                            <input type="number" id="edit-year" class="form-control" required>
                        </div>
                        <div class="form-check">
                            <input type="checkbox" id="edit-read" class="form-check-input">
                            <label class="form-check-label" for="edit-read">I have read this book</label>
                        </div>
                    </form>
                </div>
                <div class="modal-footer">
                    <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cancel</button>
                    <button type="button" id="save-edit" class="btn btn-primary">Save</button>
                </div>
            </div>
        </div>
    </div>

    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
    <script src="app.js"></script>
</body>
</html>"""

app_js = """let currentFilter = null;
let currentEditId = null;
const editModal = new bootstrap.Modal(document.getElementById('editModal'));

async function fetchBooks(filter = null) {
    let url = '/api/books';
    if (filter !== null) {
        url += '?read=' + (filter === 'read' ? 'true' : 'false');
    }
    const response = await fetch(url);
    return await response.json();
}

function renderBooks(books) {
    const booksList = document.getElementById('books-list');
    booksList.innerHTML = '';
    
    if (books.length === 0) {
        booksList.innerHTML = '<div class="col-12"><p class="text-center text-muted">No books found.</p></div>';
        return;
    }
    
    books.forEach(book => {
        const col = document.createElement('div');
        col.className = 'col-md-6 col-lg-4 mb-3';
        
        const statusBadge = book.read ? '<span class="badge bg-success">Read</span>' : '<span class="badge bg-warning">Unread</span>';
        const toggleText = book.read ? 'Mark as Unread' : 'Mark as Read';
        
        col.innerHTML = `
            <div class="card h-100">
                <div class="card-body">
                    <h5 class="card-title">${book.title}</h5>
                    <p class="card-text"><strong>Author:</strong> ${book.author}</p>
                    <p class="card-text"><strong>Year:</strong> ${book.year}</p>
                    <p class="card-text">${statusBadge}</p>
                </div>
                <div class="card-footer bg-light">
                    <button class="btn btn-sm btn-info" onclick="openEditModal(${book.id}, '${book.title}', '${book.author}', ${book.year}, ${book.read})">Edit</button>
                    <button class="btn btn-sm btn-primary" onclick="toggleReadStatus(${book.id}, ${book.read})">${toggleText}</button>
                    <button class="btn btn-sm btn-danger" onclick="deleteBook(${book.id})">Delete</button>
                </div>
            </div>
        `;
        booksList.appendChild(col);
    });
}

async function addBook(event) {
    event.preventDefault();
    
    const title = document.getElementById('title').value;
    const author = document.getElementById('author').value;
    const year = parseInt(document.getElementById('year').value);
    const read = document.getElementById('read').checked;
    
    if (!title || !author || !year) {
        alert('Please fill in all fields');
        return;
    }
    
    const response = await fetch('/api/books', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ title, author, year, read })
    });
    
    if (response.ok) {
        document.getElementById('add-book-form').reset();
        loadAndRender();
    } else {
        alert('Error adding book');
    }
}

async function toggleReadStatus(id, currentStatus) {
    const response = await fetch(`/api/books/${id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ read: !currentStatus })
    });
    
    if (response.ok) {
        loadAndRender();
    } else {
        alert('Error updating book');
    }
}

async function deleteBook(id) {
    if (!confirm('Are you sure you want to delete this book?')) return;
    
    const response = await fetch(`/api/books/${id}`, {
        method: 'DELETE'
    });
    
    if (response.ok) {
        loadAndRender();
    } else {
        alert('Error deleting book');
    }
}

function openEditModal(id, title, author, year, read) {
    currentEditId = id;
    document.getElementById('edit-title').value = title;
    document.getElementById('edit-author').value = author;
    document.getElementById('edit-year').value = year;
    document.getElementById('edit-read').checked = read;
    editModal.show();
}

async function saveEdit() {
    const title = document.getElementById('edit-title').value;
    const author = document.getElementById('edit-author').value;
    const year = parseInt(document.getElementById('edit-year').value);
    const read = document.getElementById('edit-read').checked;
    
    if (!title || !author || !year) {
        alert('Please fill in all fields');
        return;
    }
    
    const response = await fetch(`/api/books/${currentEditId}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ title, author, year, read })
    });
    
    if (response.ok) {
        editModal.hide();
        loadAndRender();
    } else {
        alert('Error updating book');
    }
}

async function loadAndRender() {
    const books = await fetchBooks(currentFilter);
    renderBooks(books);
}

async function filterBooks(filter) {
    currentFilter = filter;
    document.querySelectorAll('[id^="filter-"]').forEach(btn => btn.classList.remove('active'));
    document.getElementById(`filter-${filter || 'all'}`).classList.add('active');
    loadAndRender();
}

document.getElementById('add-book-form').addEventListener('submit', addBook);
document.getElementById('filter-all').addEventListener('click', () => filterBooks(null));
document.getElementById('filter-read').addEventListener('click', () => filterBooks('read'));
document.getElementById('filter-unread').addEventListener('click', () => filterBooks('unread'));
document.getElementById('save-edit').addEventListener('click', saveEdit);

document.addEventListener('DOMContentLoaded', loadAndRender);"""

style_css = """body {
    background-color: #f8f9fa;
    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
}

.container {
    background-color: white;
    border-radius: 8px;
    padding: 30px;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
    max-width: 1000px;
}

h1 {
    color: #2c3e50;
    font-weight: 700;
}

.card {
    border: none;
    box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
    transition: transform 0.2s, box-shadow 0.2s;
}

.card:hover {
    transform: translateY(-2px);
    box-shadow: 0 4px 8px rgba(0, 0, 0, 0.15);
}

.card-title {
    color: #2c3e50;
    font-weight: 600;
}

.btn {
    border-radius: 4px;
    font-weight: 500;
    transition: all 0.2s;
}

.btn-primary:hover {
    transform: translateY(-1px);
}

.btn-outline-secondary.active {
    background-color: #6c757d;
    border-color: #6c757d;
    color: white;
}

.form-control {
    border-radius: 4px;
    border: 1px solid #ddd;
}

.form-control:focus {
    border-color: #007bff;
    box-shadow: 0 0 0 0.2rem rgba(0, 123, 255, 0.25);
}

.badge {
    font-size: 0.85rem;
    padding: 0.4rem 0.6rem;
}

.card-footer {
    display: flex;
    gap: 5px;
    flex-wrap: wrap;
}

.card-footer .btn {
    flex: 1;
    min-width: 80px;
    font-size: 0.85rem;
    padding: 0.4rem 0.6rem;
}

@media (max-width: 768px) {
    .container {
        padding: 15px;
    }
    
    h1 {
        font-size: 1.75rem;
    }
    
    .card-footer {
        flex-direction: column;
    }
    
    .card-footer .btn {
        width: 100%;
    }
}"""

if not (PUBLIC_DIR / "index.html").exists():
    with open(PUBLIC_DIR / "index.html", "w") as f:
        f.write(index_html)

if not (PUBLIC_DIR / "app.js").exists():
    with open(PUBLIC_DIR / "app.js", "w") as f:
        f.write(app_js)

if not (PUBLIC_DIR / "style.css").exists():
    with open(PUBLIC_DIR / "style.css", "w") as f:
        f.write(style_css)

app.mount("/", StaticFiles(directory="public", html=True), name="static")

if __name__ == "__main__":
    import uvicorn
    print("Server running on http://localhost:8000")
    uvicorn.run(app, host="0.0.0.0", port=8000)