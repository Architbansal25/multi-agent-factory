# Book Library

A web application for managing your personal book collection. Track books you've read and want to read, with a clean and intuitive interface.

## Features

- Add books with title, author, ISBN, publication year, and reading status
- View all books in your library
- Filter books by read/unread status
- Edit book details
- Delete books from your collection
- Persistent storage using JSON file
- Responsive design that works on desktop and tablet
- Automatic data backup on file corruption

## Prerequisites

- Node.js 14.0 or higher
- npm (comes with Node.js)

## Installation

1. Clone or download this repository
2. Navigate to the `src` directory:
   ```bash
   cd src
   ```
3. Install dependencies:
   ```bash
   npm install
   ```

## Running the Application

### Production Mode

Start the server:
```bash
npm start
```

### Development Mode

Start the server with auto-reload on file changes:
```bash
npm run dev
```

The application will be available at `http://localhost:3000` by default.

## Usage

1. **Open the application**: Navigate to `http://localhost:3000` in your web browser

2. **Add a book**: Fill out the "Add New Book" form with the book details and click "Add Book"
   - Title and Author are required fields
   - ISBN, Publication Year, and Status are optional

3. **Filter books**: Use the filter buttons (All, Read, Unread) to view books by status

4. **View/Edit a book**: Click on any book card to open the detail modal where you can:
   - Edit any book information
   - Change the reading status
   - Delete the book

5. **Save changes**: Click "Save Changes" in the modal to update the book

6. **Delete a book**: Click "Delete Book" in the modal and confirm the deletion

## Configuration

The application can be configured using environment variables:

- `PORT`: Server port (default: 3000)
  ```bash
  PORT=8080 npm start
  ```

- `DATA_FILE_PATH`: Path to the JSON data file (default: `data/books.json`)
  ```bash
  DATA_FILE_PATH=/path/to/books.json npm start
  ```

- `LOG_LEVEL`: Logging level - error, warn, info, debug (default: info)
  ```bash
  LOG_LEVEL=debug npm start
  ```

## Data Persistence

- Books are stored in `data/books.json`
- The file is created automatically on first run
- All changes are saved immediately
- If the data file becomes corrupted, it is automatically backed up to `data/books.json.backup` and a new empty file is created

## Architecture

The application follows a layered architecture:

- **Server Layer** (`server.js`): Express server setup and middleware
- **Routes Layer** (`routes/`): REST API endpoint definitions
- **Service Layer** (`services/`): Business logic and validation
- **Data Layer** (`data/`): File I/O and in-memory caching
- **Model Layer** (`models/`): Data validation and schema
- **Frontend**: Vanilla JavaScript SPA consuming the REST API

## Troubleshooting

### Port already in use

If you see an error that the port is already in use, either:
- Stop the other application using that port
- Use a different port: `PORT=3001 npm start`

### Data file corruption

If your data file becomes corrupted:
1. The application will automatically create a backup at `data/books.json.backup`
2. A new empty data file will be created
3. You can manually restore from the backup if needed

### Books not persisting

Check that:
- The `data` directory exists and is writable
- You have sufficient disk space
- The application has permission to write files

### Browser compatibility issues

The application is tested and works on:
- Chrome 90+
- Firefox 88+
- Safari 14+
- Edge 90+

Older browsers may not support all features.

## Development

### Code Style

The project uses ESLint with Airbnb base configuration. Run the linter:
```bash
npm run lint
```

### File Structure

```
src/
├── server.js              # Application entry point
├── config/
│   └── config.js          # Configuration management
├── models/
│   └── book.js            # Book data model and validation
├── data/
│   ├── bookRepository.js  # Data access layer
│   └── books.json         # JSON data file
├── services/
│   └── bookService.js     # Business logic
├── routes/
│   └── bookRoutes.js      # API route definitions
├── utils/
│   ├── logger.js          # Logging utility
│   └── fileUtils.js       # File system utilities
├── public/
│   ├── index.html         # Main HTML page
│   ├── css/
│   │   └── styles.css     # Custom styles
│   └── js/
│       ├── app.js         # Frontend application logic
│       └── ui.js          # DOM manipulation
├── package.json           # Dependencies and scripts
├── .eslintrc.json         # ESLint configuration
└── README.md              # This file
```

## Technical Notes

- **UUID Generation**: Uses Node.js built-in `crypto.randomBytes()` for UUID v4 generation, compatible with Node 14.0+
- **Atomic Writes**: File writes use a temp file + rename pattern for atomicity on POSIX systems. On Windows, there is a small risk of corruption during crashes.
- **Bootstrap CSS**: Uses Bootstrap 5.3 CSS-only (no JavaScript components) for styling
- **No External Database**: All data is stored in a JSON file for simplicity
- **Single User**: Designed for local, single-user use

## License

This project is provided as-is for educational and personal use.