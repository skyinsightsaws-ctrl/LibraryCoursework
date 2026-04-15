from __future__ import annotations

from datetime import date
import re
import sqlite3
from typing import Any, Mapping

from database.db import BookRepository, DatabaseManager, LoanRepository, ReaderRepository
from models.book import Book
from models.loan import Loan
from models.reader import Reader


EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class ValidationError(Exception):
    """Raised when user input or a business rule is invalid."""


class NotFoundError(Exception):
    """Raised when an entity does not exist."""


class LibraryService:
    def __init__(self, db_manager: DatabaseManager) -> None:
        self.db_manager = db_manager
        self.reader_repository = ReaderRepository(db_manager)
        self.book_repository = BookRepository(db_manager)
        self.loan_repository = LoanRepository(db_manager)

    def get_dashboard_stats(self) -> dict[str, int]:
        return {
            "total_books": self.book_repository.count_books(),
            "total_readers": self.reader_repository.count_readers(),
            "active_loans": self.loan_repository.count_active_loans(),
            "overdue_loans": self.loan_repository.count_overdue_loans(date.today().isoformat()),
            "available_books": self.book_repository.sum_available_copies(),
        }

    def list_readers(self, search_query: str = "") -> list[Reader]:
        return self.reader_repository.get_all(search_query)

    def get_reader(self, reader_id: int) -> Reader:
        reader = self.reader_repository.get_by_id(reader_id)
        if reader is None:
            raise NotFoundError("Reader not found.")
        return reader

    def create_reader(self, data: Mapping[str, Any]) -> Reader:
        reader = Reader(
            reader_id=None,
            full_name=self._require_text(data, "full_name", "Full name"),
            email=self._validate_email(data.get("email", "")),
            phone=self._require_text(data, "phone", "Phone"),
            membership_date=self._validate_date(data.get("membership_date", ""), "Membership date"),
        )

        try:
            reader.reader_id = self.reader_repository.add(reader)
        except sqlite3.IntegrityError as error:
            raise ValidationError("Reader email must be unique.") from error

        return reader

    def update_reader(self, reader_id: int, data: Mapping[str, Any]) -> Reader:
        self.get_reader(reader_id)

        reader = Reader(
            reader_id=reader_id,
            full_name=self._require_text(data, "full_name", "Full name"),
            email=self._validate_email(data.get("email", "")),
            phone=self._require_text(data, "phone", "Phone"),
            membership_date=self._validate_date(data.get("membership_date", ""), "Membership date"),
        )

        try:
            self.reader_repository.update(reader)
        except sqlite3.IntegrityError as error:
            raise ValidationError("Reader email must be unique.") from error

        return reader

    def delete_reader(self, reader_id: int) -> None:
        self.get_reader(reader_id)

        try:
            self.reader_repository.delete(reader_id)
        except sqlite3.IntegrityError as error:
            raise ValidationError(
                "Reader cannot be deleted because there are related loan records."
            ) from error

    def list_books(self, search_query: str = "") -> list[Book]:
        return self.book_repository.get_all(search_query)

    def list_available_books(self) -> list[Book]:
        return self.book_repository.get_available_books()

    def get_book(self, book_id: int) -> Book:
        book = self.book_repository.get_by_id(book_id)
        if book is None:
            raise NotFoundError("Book not found.")
        return book

    def create_book(self, data: Mapping[str, Any]) -> Book:
        total_copies = self._parse_positive_integer(data.get("total_copies", ""), "Total copies")
        available_copies = self._parse_non_negative_integer(
            data.get("available_copies", ""), "Available copies"
        )

        if available_copies > total_copies:
            raise ValidationError("Available copies cannot exceed total copies.")

        book = Book(
            book_id=None,
            title=self._require_text(data, "title", "Title"),
            author=self._require_text(data, "author", "Author"),
            category=self._require_text(data, "category", "Category"),
            publication_year=self._parse_positive_integer(
                data.get("publication_year", ""), "Publication year"
            ),
            isbn=self._require_text(data, "isbn", "ISBN"),
            total_copies=total_copies,
            available_copies=available_copies,
        )

        try:
            book.book_id = self.book_repository.add(book)
        except sqlite3.IntegrityError as error:
            raise ValidationError("Book ISBN must be unique.") from error

        return book

    def update_book(self, book_id: int, data: Mapping[str, Any]) -> Book:
        self.get_book(book_id)

        total_copies = self._parse_positive_integer(data.get("total_copies", ""), "Total copies")
        available_copies = self._parse_non_negative_integer(
            data.get("available_copies", ""), "Available copies"
        )

        if available_copies > total_copies:
            raise ValidationError("Available copies cannot exceed total copies.")

        book = Book(
            book_id=book_id,
            title=self._require_text(data, "title", "Title"),
            author=self._require_text(data, "author", "Author"),
            category=self._require_text(data, "category", "Category"),
            publication_year=self._parse_positive_integer(
                data.get("publication_year", ""), "Publication year"
            ),
            isbn=self._require_text(data, "isbn", "ISBN"),
            total_copies=total_copies,
            available_copies=available_copies,
        )

        try:
            self.book_repository.update(book)
        except sqlite3.IntegrityError as error:
            raise ValidationError("Book ISBN must be unique.") from error

        return book

    def delete_book(self, book_id: int) -> None:
        self.get_book(book_id)

        try:
            self.book_repository.delete(book_id)
        except sqlite3.IntegrityError as error:
            raise ValidationError(
                "Book cannot be deleted because there are related loan records."
            ) from error

    def list_active_loans(self) -> list[Loan]:
        return self.loan_repository.get_active_loans()

    def list_returned_loans(self) -> list[Loan]:
        return self.loan_repository.get_returned_loans()

    def list_overdue_loans(self) -> list[Loan]:
        return self.loan_repository.get_overdue_loans(date.today().isoformat())

    def get_loan(self, loan_id: int) -> Loan:
        loan = self.loan_repository.get_by_id(loan_id)
        if loan is None:
            raise NotFoundError("Loan not found.")
        return loan

    def issue_book(self, data: Mapping[str, Any]) -> Loan:
        reader_id = self._parse_positive_integer(data.get("reader_id", ""), "Reader")
        book_id = self._parse_positive_integer(data.get("book_id", ""), "Book")
        issue_date = self._validate_date(data.get("issue_date", ""), "Issue date")
        due_date = self._validate_date(data.get("due_date", ""), "Due date")

        if due_date < issue_date:
            raise ValidationError("Due date must be on or after the issue date.")

        with self.db_manager.transaction() as connection:
            reader = self.reader_repository.get_by_id(reader_id, connection)
            if reader is None:
                raise NotFoundError("Reader not found.")

            book = self.book_repository.get_by_id(book_id, connection)
            if book is None:
                raise NotFoundError("Book not found.")

            if not book.is_available():
                raise ValidationError("Cannot issue a book with no available copies.")

            loan = Loan(
                loan_id=None,
                reader_id=reader_id,
                book_id=book_id,
                issue_date=issue_date,
                due_date=due_date,
                return_date=None,
                status="ACTIVE",
                reader_name=reader.full_name,
                book_title=book.title,
            )
            loan.loan_id = self.loan_repository.add(loan, connection)
            self.book_repository.update_available_copies(
                book_id, book.available_copies - 1, connection
            )

        return loan

    def return_book(self, loan_id: int, return_date_value: str) -> Loan:
        return_date = self._validate_date(return_date_value, "Return date")

        with self.db_manager.transaction() as connection:
            loan = self.loan_repository.get_by_id(loan_id, connection)
            if loan is None:
                raise NotFoundError("Loan not found.")

            if loan.return_date is not None or loan.status == "RETURNED":
                raise ValidationError("This loan has already been returned.")

            if return_date < loan.issue_date:
                raise ValidationError("Return date cannot be earlier than issue date.")

            book = self.book_repository.get_by_id(loan.book_id, connection)
            if book is None:
                raise NotFoundError("Book not found.")

            if book.available_copies >= book.total_copies:
                raise ValidationError("Book inventory is already at the maximum copy count.")

            self.loan_repository.mark_as_returned(loan_id, return_date, connection)
            self.book_repository.update_available_copies(
                book.book_id, book.available_copies + 1, connection
            )

            loan.return_date = return_date
            loan.status = "RETURNED"

        return loan

    def _require_text(self, data: Mapping[str, Any], field_name: str, label: str) -> str:
        value = str(data.get(field_name, "")).strip()
        if not value:
            raise ValidationError(f"{label} is required.")
        return value

    def _validate_email(self, email: Any) -> str:
        value = str(email).strip()
        if not value:
            raise ValidationError("Email is required.")
        if not EMAIL_PATTERN.match(value):
            raise ValidationError("Email format is invalid.")
        return value

    def _validate_date(self, value: Any, label: str) -> str:
        text = str(value).strip()
        if not text:
            raise ValidationError(f"{label} is required.")

        try:
            date.fromisoformat(text)
        except ValueError as error:
            raise ValidationError(f"{label} must use the YYYY-MM-DD format.") from error

        return text

    def _parse_positive_integer(self, value: Any, label: str) -> int:
        text = str(value).strip()
        if not text:
            raise ValidationError(f"{label} is required.")

        try:
            number = int(text)
        except ValueError as error:
            raise ValidationError(f"{label} must be a whole number.") from error

        if number <= 0:
            raise ValidationError(f"{label} must be a positive integer.")

        return number

    def _parse_non_negative_integer(self, value: Any, label: str) -> int:
        text = str(value).strip()
        if not text:
            raise ValidationError(f"{label} is required.")

        try:
            number = int(text)
        except ValueError as error:
            raise ValidationError(f"{label} must be a whole number.") from error

        if number < 0:
            raise ValidationError(f"{label} cannot be negative.")

        return number
