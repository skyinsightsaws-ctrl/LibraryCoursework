CREATE TABLE IF NOT EXISTS readers (
    reader_id INTEGER PRIMARY KEY AUTOINCREMENT,
    full_name TEXT NOT NULL,
    email TEXT NOT NULL UNIQUE,
    phone TEXT NOT NULL,
    membership_date TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS books (
    book_id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    author TEXT NOT NULL,
    category TEXT NOT NULL,
    publication_year INTEGER NOT NULL,
    isbn TEXT NOT NULL UNIQUE,
    total_copies INTEGER NOT NULL CHECK (total_copies > 0),
    available_copies INTEGER NOT NULL CHECK (
        available_copies >= 0 AND available_copies <= total_copies
    )
);

CREATE TABLE IF NOT EXISTS loans (
    loan_id INTEGER PRIMARY KEY AUTOINCREMENT,
    reader_id INTEGER NOT NULL,
    book_id INTEGER NOT NULL,
    issue_date TEXT NOT NULL,
    due_date TEXT NOT NULL,
    return_date TEXT,
    status TEXT NOT NULL CHECK (status IN ('ACTIVE', 'RETURNED')),
    FOREIGN KEY (reader_id) REFERENCES readers (reader_id) ON DELETE RESTRICT,
    FOREIGN KEY (book_id) REFERENCES books (book_id) ON DELETE RESTRICT
);
