from __future__ import annotations

from datetime import date
from pathlib import Path
from uuid import uuid4

import pytest

from app import create_app
from models.loan import Loan
from services.library_service import ValidationError


@pytest.fixture()
def app():
    temp_dir = Path(__file__).resolve().parent / ".tmp"
    temp_dir.mkdir(exist_ok=True)
    database_path = temp_dir / f"test_library_{uuid4().hex}.db"
    app = create_app(
        {
            "TESTING": True,
            "DATABASE": str(database_path),
            "SEED_SAMPLE_BOOKS": False,
        }
    )
    yield app

    if database_path.exists():
        try:
            database_path.unlink()
        except PermissionError:
            pass


@pytest.fixture()
def client(app):
    return app.test_client()


@pytest.fixture()
def service(app):
    return app.extensions["library_service"]


def test_add_reader(client):
    response = client.post(
        "/readers/new",
        data={
            "full_name": "Test Reader",
            "email": "reader@test.com",
            "phone": "+1-555-1111",
            "membership_date": "2026-04-10",
        },
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert b"Reader added successfully." in response.data
    assert b"Test Reader" in response.data


def test_add_book(client):
    response = client.post(
        "/books/new",
        data={
            "title": "Test Driven Development",
            "author": "Kent Beck",
            "category": "Programming",
            "publication_year": "2002",
            "isbn": "9780321146533",
            "total_copies": "3",
            "available_copies": "3",
        },
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert b"Book added successfully." in response.data
    assert b"Test Driven Development" in response.data


def test_issue_book(service):
    reader = service.create_reader(
        {
            "full_name": "Issue Reader",
            "email": "issue.reader@test.com",
            "phone": "555-1010",
            "membership_date": "2026-04-01",
        }
    )
    book = service.create_book(
        {
            "title": "Refactoring",
            "author": "Martin Fowler",
            "category": "Programming",
            "publication_year": "2018",
            "isbn": "9780134757599",
            "total_copies": "2",
            "available_copies": "2",
        }
    )

    loan = service.issue_book(
        {
            "reader_id": str(reader.reader_id),
            "book_id": str(book.book_id),
            "issue_date": "2026-04-01",
            "due_date": "2026-04-15",
        }
    )

    refreshed_book = service.get_book(book.book_id)

    assert loan.loan_id is not None
    assert refreshed_book.available_copies == 1
    assert service.list_active_loans()[0].book_title == "Refactoring"


def test_return_book(service):
    reader = service.create_reader(
        {
            "full_name": "Return Reader",
            "email": "return.reader@test.com",
            "phone": "555-2020",
            "membership_date": "2026-04-01",
        }
    )
    book = service.create_book(
        {
            "title": "Domain-Driven Design",
            "author": "Eric Evans",
            "category": "Software Engineering",
            "publication_year": "2003",
            "isbn": "9780321125217",
            "total_copies": "1",
            "available_copies": "1",
        }
    )
    loan = service.issue_book(
        {
            "reader_id": str(reader.reader_id),
            "book_id": str(book.book_id),
            "issue_date": "2026-04-01",
            "due_date": "2026-04-12",
        }
    )

    returned_loan = service.return_book(loan.loan_id, "2026-04-05")
    refreshed_book = service.get_book(book.book_id)

    assert returned_loan.status == "RETURNED"
    assert refreshed_book.available_copies == 1
    assert service.list_active_loans() == []


def test_prevent_issue_when_no_copies_available(service):
    reader = service.create_reader(
        {
            "full_name": "Busy Reader",
            "email": "busy.reader@test.com",
            "phone": "555-3030",
            "membership_date": "2026-04-01",
        }
    )
    book = service.create_book(
        {
            "title": "Patterns of Enterprise Application Architecture",
            "author": "Martin Fowler",
            "category": "Software Engineering",
            "publication_year": "2002",
            "isbn": "9780321127426",
            "total_copies": "1",
            "available_copies": "0",
        }
    )

    with pytest.raises(ValidationError) as error:
        service.issue_book(
            {
                "reader_id": str(reader.reader_id),
                "book_id": str(book.book_id),
                "issue_date": "2026-04-01",
                "due_date": "2026-04-10",
            }
        )

    assert "no available copies" in str(error.value).lower()


def test_overdue_loan_logic():
    loan = Loan(
        loan_id=1,
        reader_id=1,
        book_id=1,
        issue_date="2026-03-01",
        due_date="2026-03-10",
        return_date=None,
        status="ACTIVE",
    )

    assert loan.is_overdue(date(2026, 3, 15)) is True
    assert loan.days_overdue(date(2026, 3, 15)) == 5
