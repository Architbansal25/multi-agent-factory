let currentFilter = null;
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

document.addEventListener('DOMContentLoaded', loadAndRender);