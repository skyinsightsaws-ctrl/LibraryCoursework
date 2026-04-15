# Development of a Library Reader Service System

## Project Description

This project is a simple web application for a university Object-Oriented Programming / Software Engineering course project. It manages readers, books, loans, returns, availability, and overdue records using a clear object-oriented design that is easy to explain in UML and technical documentation.

## Technologies Used

- Python
- Flask
- SQLite
- HTML/CSS
- Pytest

## Main Features

- Reader management: add, edit, delete, view, and search readers
- Book management: add, edit, delete, view, search books, and track availability
- Loan management: issue books, return books, view active and returned loans
- Overdue tracking for unreturned loans whose due date has passed
- Dashboard with summary statistics
- Basic validation and flash messages
- Sample books for the catalog demonstration

## Folder Structure

```text
library-reader-service/
  app.py
  models/
    __init__.py
    reader.py
    book.py
    loan.py
  services/
    __init__.py
    library_service.py
  database/
    __init__.py
    db.py
    schema.sql
  templates/
    base.html
    index.html
    readers.html
    reader_form.html
    books.html
    book_form.html
    loans.html
    loan_form.html
    overdue_loans.html
  static/
    style.css
  tests/
    test_basic.py
  README.md
  requirements.txt
```

## Setup Instructions

Start in the project folder:

```powershell
cd library-reader-service
```

### 1. Create a virtual environment

Windows PowerShell:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

Linux / macOS:

```bash
python -m venv .venv
source .venv/bin/activate
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Initialize the database

```bash
flask --app app.py init-db
```

The application creates the database automatically on first run. New databases are preloaded with sample books only, while readers and loans remain empty so you can manage them yourself.

### 4. Run the application

```bash
flask --app app.py run
```

You can also run it with:

```bash
python app.py
```

Then open `http://127.0.0.1:5000/` in your browser.

## Running Tests

```bash
pytest
```

## Example Functional Areas

- Register new readers with contact information and membership dates
- Maintain a book catalog with categories, ISBN, and copy counts
- Issue books only when copies are available
- Return books and automatically restore available copies
- Detect overdue loans and display them on a separate page

## Design Notes

The codebase is intentionally simple and layered so it is easy to explain in a report:

- `models/` contains entity classes such as `Reader`, `Book`, and `Loan`
- `services/` contains business logic in `LibraryService`
- `database/` contains SQLite setup and repository classes
- `templates/` provides the user interface
- `app.py` contains Flask application setup and routes

This structure supports later documentation such as:

- business use case diagram
- system use case diagram
- sequence diagrams
- initial and evolved class diagrams
- component diagram
- deployment diagram
- software quality discussion using CK metrics

## Report Support Notes

### Main Actors

- Librarian
- Reader

### Main Use Cases

- Manage readers
- Manage books
- Issue book
- Return book
- Search records
- Monitor overdue loans

### Main Classes

- `Reader`
- `Book`
- `Loan`
- `LibraryService`
- `DatabaseManager`
- `ReaderRepository`
- `BookRepository`
- `LoanRepository`

### Main Components

- Flask routes and controllers
- Service layer
- Repository/database layer
- SQLite database
- HTML templates and CSS UI

### Iteration Summary

- Iteration 1: reader management, book management, SQLite database, dashboard
- Iteration 2: loan issue/return, availability logic, active and returned loans
- Iteration 3: overdue tracking, search/filtering, stronger validation, tests, cleaner UI
