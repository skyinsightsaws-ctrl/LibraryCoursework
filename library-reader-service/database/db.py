from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
import sqlite3
from typing import Generator, Optional

from models.book import Book
from models.loan import Loan
from models.reader import Reader


class DatabaseManager:
    def __init__(self, database_path: str) -> None:
        self.database_path = Path(database_path)

    def get_connection(self) -> sqlite3.Connection:
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(self.database_path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    @contextmanager
    def transaction(self) -> Generator[sqlite3.Connection, None, None]:
        connection = self.get_connection()
        try:
            with connection:
                yield connection
        finally:
            connection.close()

    def initialize_database(self, seed_sample_books: bool = False) -> None:
        schema_path = Path(__file__).with_name("schema.sql")

        with self.get_connection() as connection:
            connection.executescript(schema_path.read_text(encoding="utf-8"))

        if seed_sample_books and self._books_table_is_empty():
            self.seed_sample_books()

    def _books_table_is_empty(self) -> bool:
        with self.get_connection() as connection:
            book_count = connection.execute("SELECT COUNT(*) FROM books").fetchone()[0]

        return book_count == 0

    def seed_sample_books(self) -> None:
        with self.get_connection() as connection:
            connection.executemany(
                """
                INSERT INTO books (
                    title, author, category, publication_year, isbn, total_copies, available_copies
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        "Clean Code",
                        "Robert C. Martin",
                        "Programming",
                        2008,
                        "9780132350884",
                        4,
                        4,
                    ),
                    (
                        "The Pragmatic Programmer",
                        "Andrew Hunt",
                        "Programming",
                        1999,
                        "9780201616224",
                        3,
                        3,
                    ),
                    (
                        "Design Patterns",
                        "Erich Gamma",
                        "Software Engineering",
                        1994,
                        "9780201633610",
                        2,
                        2,
                    ),
                    (
                        "Database System Concepts",
                        "Abraham Silberschatz",
                        "Databases",
                        2019,
                        "9781260084504",
                        2,
                        2,
                    ),
                    (
                        "Introduction to Algorithms",
                        "Thomas H. Cormen",
                        "Algorithms",
                        2009,
                        "9780262033848",
                        3,
                        3,
                    ),
                ],
            )


class BaseRepository:
    def __init__(self, db_manager: DatabaseManager) -> None:
        self.db_manager = db_manager

    @contextmanager
    def use_connection(
        self, connection: Optional[sqlite3.Connection] = None, commit: bool = False
    ) -> Generator[sqlite3.Connection, None, None]:
        if connection is not None:
            yield connection
            return

        owned_connection = self.db_manager.get_connection()
        try:
            yield owned_connection
            if commit:
                owned_connection.commit()
        finally:
            owned_connection.close()


class ReaderRepository(BaseRepository):
    def get_all(self, search_query: str = "") -> list[Reader]:
        search_term = f"%{search_query.strip()}%"

        with self.use_connection() as connection:
            rows = connection.execute(
                """
                SELECT reader_id, full_name, email, phone, membership_date
                FROM readers
                WHERE ? = ''
                   OR full_name LIKE ?
                   OR email LIKE ?
                ORDER BY full_name
                """,
                (search_query.strip(), search_term, search_term),
            ).fetchall()

        return [Reader.from_row(row) for row in rows]

    def get_by_id(
        self, reader_id: int, connection: Optional[sqlite3.Connection] = None
    ) -> Optional[Reader]:
        with self.use_connection(connection) as active_connection:
            row = active_connection.execute(
                """
                SELECT reader_id, full_name, email, phone, membership_date
                FROM readers
                WHERE reader_id = ?
                """,
                (reader_id,),
            ).fetchone()

        return Reader.from_row(row)

    def add(self, reader: Reader, connection: Optional[sqlite3.Connection] = None) -> int:
        with self.use_connection(connection, commit=True) as active_connection:
            cursor = active_connection.execute(
                """
                INSERT INTO readers (full_name, email, phone, membership_date)
                VALUES (?, ?, ?, ?)
                """,
                (reader.full_name, reader.email, reader.phone, reader.membership_date),
            )

        return int(cursor.lastrowid)

    def update(self, reader: Reader, connection: Optional[sqlite3.Connection] = None) -> None:
        with self.use_connection(connection, commit=True) as active_connection:
            active_connection.execute(
                """
                UPDATE readers
                SET full_name = ?, email = ?, phone = ?, membership_date = ?
                WHERE reader_id = ?
                """,
                (
                    reader.full_name,
                    reader.email,
                    reader.phone,
                    reader.membership_date,
                    reader.reader_id,
                ),
            )

    def delete(self, reader_id: int, connection: Optional[sqlite3.Connection] = None) -> None:
        with self.use_connection(connection, commit=True) as active_connection:
            active_connection.execute("DELETE FROM readers WHERE reader_id = ?", (reader_id,))

    def count_readers(self) -> int:
        with self.use_connection() as connection:
            return int(connection.execute("SELECT COUNT(*) FROM readers").fetchone()[0])


class BookRepository(BaseRepository):
    def get_all(self, search_query: str = "") -> list[Book]:
        search_term = f"%{search_query.strip()}%"

        with self.use_connection() as connection:
            rows = connection.execute(
                """
                SELECT book_id, title, author, category, publication_year, isbn, total_copies, available_copies
                FROM books
                WHERE ? = ''
                   OR title LIKE ?
                   OR author LIKE ?
                   OR category LIKE ?
                ORDER BY title
                """,
                (search_query.strip(), search_term, search_term, search_term),
            ).fetchall()

        return [Book.from_row(row) for row in rows]

    def get_available_books(self) -> list[Book]:
        with self.use_connection() as connection:
            rows = connection.execute(
                """
                SELECT book_id, title, author, category, publication_year, isbn, total_copies, available_copies
                FROM books
                WHERE available_copies > 0
                ORDER BY title
                """
            ).fetchall()

        return [Book.from_row(row) for row in rows]

    def get_by_id(
        self, book_id: int, connection: Optional[sqlite3.Connection] = None
    ) -> Optional[Book]:
        with self.use_connection(connection) as active_connection:
            row = active_connection.execute(
                """
                SELECT book_id, title, author, category, publication_year, isbn, total_copies, available_copies
                FROM books
                WHERE book_id = ?
                """,
                (book_id,),
            ).fetchone()

        return Book.from_row(row)

    def add(self, book: Book, connection: Optional[sqlite3.Connection] = None) -> int:
        with self.use_connection(connection, commit=True) as active_connection:
            cursor = active_connection.execute(
                """
                INSERT INTO books (
                    title, author, category, publication_year, isbn, total_copies, available_copies
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    book.title,
                    book.author,
                    book.category,
                    book.publication_year,
                    book.isbn,
                    book.total_copies,
                    book.available_copies,
                ),
            )

        return int(cursor.lastrowid)

    def update(self, book: Book, connection: Optional[sqlite3.Connection] = None) -> None:
        with self.use_connection(connection, commit=True) as active_connection:
            active_connection.execute(
                """
                UPDATE books
                SET title = ?, author = ?, category = ?, publication_year = ?, isbn = ?,
                    total_copies = ?, available_copies = ?
                WHERE book_id = ?
                """,
                (
                    book.title,
                    book.author,
                    book.category,
                    book.publication_year,
                    book.isbn,
                    book.total_copies,
                    book.available_copies,
                    book.book_id,
                ),
            )

    def update_available_copies(
        self,
        book_id: int | None,
        available_copies: int,
        connection: Optional[sqlite3.Connection] = None,
    ) -> None:
        with self.use_connection(connection, commit=True) as active_connection:
            active_connection.execute(
                "UPDATE books SET available_copies = ? WHERE book_id = ?",
                (available_copies, book_id),
            )

    def delete(self, book_id: int, connection: Optional[sqlite3.Connection] = None) -> None:
        with self.use_connection(connection, commit=True) as active_connection:
            active_connection.execute("DELETE FROM books WHERE book_id = ?", (book_id,))

    def count_books(self) -> int:
        with self.use_connection() as connection:
            return int(connection.execute("SELECT COUNT(*) FROM books").fetchone()[0])

    def sum_available_copies(self) -> int:
        with self.use_connection() as connection:
            result = connection.execute("SELECT COALESCE(SUM(available_copies), 0) FROM books").fetchone()
        return int(result[0])


class LoanRepository(BaseRepository):
    JOIN_FIELDS = """
        SELECT
            l.loan_id,
            l.reader_id,
            l.book_id,
            l.issue_date,
            l.due_date,
            l.return_date,
            l.status,
            r.full_name AS reader_name,
            b.title AS book_title
        FROM loans l
        JOIN readers r ON r.reader_id = l.reader_id
        JOIN books b ON b.book_id = l.book_id
    """

    def get_by_id(
        self, loan_id: int, connection: Optional[sqlite3.Connection] = None
    ) -> Optional[Loan]:
        with self.use_connection(connection) as active_connection:
            row = active_connection.execute(
                f"""
                {self.JOIN_FIELDS}
                WHERE l.loan_id = ?
                """,
                (loan_id,),
            ).fetchone()

        return Loan.from_row(row)

    def add(self, loan: Loan, connection: Optional[sqlite3.Connection] = None) -> int:
        with self.use_connection(connection, commit=True) as active_connection:
            cursor = active_connection.execute(
                """
                INSERT INTO loans (reader_id, book_id, issue_date, due_date, return_date, status)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    loan.reader_id,
                    loan.book_id,
                    loan.issue_date,
                    loan.due_date,
                    loan.return_date,
                    loan.status,
                ),
            )

        return int(cursor.lastrowid)

    def mark_as_returned(
        self, loan_id: int, return_date: str, connection: Optional[sqlite3.Connection] = None
    ) -> None:
        with self.use_connection(connection, commit=True) as active_connection:
            active_connection.execute(
                """
                UPDATE loans
                SET return_date = ?, status = 'RETURNED'
                WHERE loan_id = ?
                """,
                (return_date, loan_id),
            )

    def get_active_loans(self) -> list[Loan]:
        with self.use_connection() as connection:
            rows = connection.execute(
                f"""
                {self.JOIN_FIELDS}
                WHERE l.return_date IS NULL AND l.status = 'ACTIVE'
                ORDER BY l.due_date
                """
            ).fetchall()

        return [Loan.from_row(row) for row in rows]

    def get_returned_loans(self) -> list[Loan]:
        with self.use_connection() as connection:
            rows = connection.execute(
                f"""
                {self.JOIN_FIELDS}
                WHERE l.return_date IS NOT NULL AND l.status = 'RETURNED'
                ORDER BY l.return_date DESC
                """
            ).fetchall()

        return [Loan.from_row(row) for row in rows]

    def get_overdue_loans(self, reference_date: str) -> list[Loan]:
        with self.use_connection() as connection:
            rows = connection.execute(
                f"""
                {self.JOIN_FIELDS}
                WHERE l.return_date IS NULL
                  AND l.status = 'ACTIVE'
                  AND l.due_date < ?
                ORDER BY l.due_date
                """,
                (reference_date,),
            ).fetchall()

        return [Loan.from_row(row) for row in rows]

    def count_active_loans(self) -> int:
        with self.use_connection() as connection:
            return int(
                connection.execute(
                    "SELECT COUNT(*) FROM loans WHERE return_date IS NULL AND status = 'ACTIVE'"
                ).fetchone()[0]
            )

    def count_overdue_loans(self, reference_date: str) -> int:
        with self.use_connection() as connection:
            return int(
                connection.execute(
                    """
                    SELECT COUNT(*)
                    FROM loans
                    WHERE return_date IS NULL
                      AND status = 'ACTIVE'
                      AND due_date < ?
                    """,
                    (reference_date,),
                ).fetchone()[0]
            )
