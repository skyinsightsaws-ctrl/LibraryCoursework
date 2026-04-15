from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path
from typing import Any, Dict

import click
from flask import Flask, current_app, flash, redirect, render_template, request, url_for

from database.db import DatabaseManager
from services.library_service import LibraryService, NotFoundError, ValidationError


def create_app(test_config: Dict[str, Any] | None = None) -> Flask:
    base_dir = Path(__file__).resolve().parent

    app = Flask(__name__)
    app.config.from_mapping(
        SECRET_KEY="library-reader-service-secret",
        DATABASE=str(base_dir / "library_service.db"),
        SEED_SAMPLE_BOOKS=True,
        TESTING=False,
    )

    if test_config:
        app.config.update(test_config)

    database_path = Path(app.config["DATABASE"])
    database_exists = database_path.exists()
    db_manager = DatabaseManager(app.config["DATABASE"])
    db_manager.initialize_database(
        seed_sample_books=app.config["SEED_SAMPLE_BOOKS"] and not database_exists
    )

    app.extensions["db_manager"] = db_manager
    app.extensions["library_service"] = LibraryService(db_manager)

    register_cli_commands(app)
    register_routes(app)

    @app.context_processor
    def inject_globals() -> Dict[str, str]:
        return {"today": date.today().isoformat()}

    return app


def register_cli_commands(app: Flask) -> None:
    @app.cli.command("init-db")
    def init_db_command() -> None:
        db_manager: DatabaseManager = app.extensions["db_manager"]
        db_manager.initialize_database(seed_sample_books=True)
        click.echo("Database initialized successfully.")


def get_service() -> LibraryService:
    return current_app.extensions["library_service"]


def build_reader_form_data(source: Any | None = None) -> Dict[str, str]:
    if not source:
        return {
            "full_name": "",
            "email": "",
            "phone": "",
            "membership_date": date.today().isoformat(),
        }

    if hasattr(source, "get"):
        return {
            "full_name": source.get("full_name", ""),
            "email": source.get("email", ""),
            "phone": source.get("phone", ""),
            "membership_date": source.get("membership_date", date.today().isoformat()),
        }

    return {
        "full_name": getattr(source, "full_name", ""),
        "email": getattr(source, "email", ""),
        "phone": getattr(source, "phone", ""),
        "membership_date": getattr(source, "membership_date", date.today().isoformat()),
    }


def build_book_form_data(source: Any | None = None) -> Dict[str, str]:
    if not source:
        return {
            "title": "",
            "author": "",
            "category": "",
            "publication_year": "",
            "isbn": "",
            "total_copies": "1",
            "available_copies": "1",
        }

    if hasattr(source, "get"):
        return {
            "title": source.get("title", ""),
            "author": source.get("author", ""),
            "category": source.get("category", ""),
            "publication_year": str(source.get("publication_year", "")),
            "isbn": source.get("isbn", ""),
            "total_copies": str(source.get("total_copies", "1")),
            "available_copies": str(source.get("available_copies", "1")),
        }

    return {
        "title": getattr(source, "title", ""),
        "author": getattr(source, "author", ""),
        "category": getattr(source, "category", ""),
        "publication_year": str(getattr(source, "publication_year", "")),
        "isbn": getattr(source, "isbn", ""),
        "total_copies": str(getattr(source, "total_copies", "1")),
        "available_copies": str(getattr(source, "available_copies", "1")),
    }


def register_routes(app: Flask) -> None:
    @app.route("/")
    def dashboard():
        stats = get_service().get_dashboard_stats()
        return render_template("index.html", stats=stats)

    @app.route("/readers")
    def readers():
        query = request.args.get("q", "").strip()
        readers_list = get_service().list_readers(query)
        return render_template("readers.html", readers=readers_list, query=query)

    @app.route("/readers/new", methods=["GET", "POST"])
    def create_reader():
        form_data = build_reader_form_data()

        if request.method == "POST":
            form_data = build_reader_form_data(request.form)
            try:
                get_service().create_reader(request.form)
                flash("Reader added successfully.", "success")
                return redirect(url_for("readers"))
            except ValidationError as error:
                flash(str(error), "error")

        return render_template(
            "reader_form.html",
            form_title="Add Reader",
            submit_label="Create Reader",
            form_action=url_for("create_reader"),
            form_data=form_data,
        )

    @app.route("/readers/<int:reader_id>/edit", methods=["GET", "POST"])
    def edit_reader(reader_id: int):
        service = get_service()

        try:
            reader = service.get_reader(reader_id)
        except NotFoundError as error:
            flash(str(error), "error")
            return redirect(url_for("readers"))

        form_data = build_reader_form_data(reader)

        if request.method == "POST":
            form_data = build_reader_form_data(request.form)
            try:
                service.update_reader(reader_id, request.form)
                flash("Reader updated successfully.", "success")
                return redirect(url_for("readers"))
            except ValidationError as error:
                flash(str(error), "error")

        return render_template(
            "reader_form.html",
            form_title="Edit Reader",
            submit_label="Save Changes",
            form_action=url_for("edit_reader", reader_id=reader_id),
            form_data=form_data,
        )

    @app.route("/readers/<int:reader_id>/delete", methods=["POST"])
    def delete_reader(reader_id: int):
        try:
            get_service().delete_reader(reader_id)
            flash("Reader deleted successfully.", "success")
        except (ValidationError, NotFoundError) as error:
            flash(str(error), "error")

        return redirect(url_for("readers"))

    @app.route("/books")
    def books():
        query = request.args.get("q", "").strip()
        books_list = get_service().list_books(query)
        return render_template("books.html", books=books_list, query=query)

    @app.route("/books/new", methods=["GET", "POST"])
    def create_book():
        form_data = build_book_form_data()

        if request.method == "POST":
            form_data = build_book_form_data(request.form)
            try:
                get_service().create_book(request.form)
                flash("Book added successfully.", "success")
                return redirect(url_for("books"))
            except ValidationError as error:
                flash(str(error), "error")

        return render_template(
            "book_form.html",
            form_title="Add Book",
            submit_label="Create Book",
            form_action=url_for("create_book"),
            form_data=form_data,
        )

    @app.route("/books/<int:book_id>/edit", methods=["GET", "POST"])
    def edit_book(book_id: int):
        service = get_service()

        try:
            book = service.get_book(book_id)
        except NotFoundError as error:
            flash(str(error), "error")
            return redirect(url_for("books"))

        form_data = build_book_form_data(book)

        if request.method == "POST":
            form_data = build_book_form_data(request.form)
            try:
                service.update_book(book_id, request.form)
                flash("Book updated successfully.", "success")
                return redirect(url_for("books"))
            except ValidationError as error:
                flash(str(error), "error")

        return render_template(
            "book_form.html",
            form_title="Edit Book",
            submit_label="Save Changes",
            form_action=url_for("edit_book", book_id=book_id),
            form_data=form_data,
        )

    @app.route("/books/<int:book_id>/delete", methods=["POST"])
    def delete_book(book_id: int):
        try:
            get_service().delete_book(book_id)
            flash("Book deleted successfully.", "success")
        except (ValidationError, NotFoundError) as error:
            flash(str(error), "error")

        return redirect(url_for("books"))

    @app.route("/loans")
    def loans():
        service = get_service()
        return render_template(
            "loans.html",
            active_loans=service.list_active_loans(),
            returned_loans=service.list_returned_loans(),
        )

    @app.route("/loans/new", methods=["GET", "POST"])
    def create_loan():
        service = get_service()
        default_issue_date = date.today()
        default_due_date = default_issue_date + timedelta(days=14)
        form_data = {
            "reader_id": "",
            "book_id": "",
            "issue_date": default_issue_date.isoformat(),
            "due_date": default_due_date.isoformat(),
        }

        if request.method == "POST":
            form_data = {
                "reader_id": request.form.get("reader_id", ""),
                "book_id": request.form.get("book_id", ""),
                "issue_date": request.form.get("issue_date", ""),
                "due_date": request.form.get("due_date", ""),
            }
            try:
                service.issue_book(request.form)
                flash("Book issued successfully.", "success")
                return redirect(url_for("loans"))
            except (ValidationError, NotFoundError) as error:
                flash(str(error), "error")

        return render_template(
            "loan_form.html",
            form_data=form_data,
            readers=service.list_readers(),
            books=service.list_available_books(),
        )

    @app.route("/loans/<int:loan_id>/return", methods=["POST"])
    def return_loan(loan_id: int):
        return_date = request.form.get("return_date", date.today().isoformat())

        try:
            get_service().return_book(loan_id, return_date)
            flash("Book returned successfully.", "success")
        except (ValidationError, NotFoundError) as error:
            flash(str(error), "error")

        return redirect(url_for("loans"))

    @app.route("/loans/overdue")
    def overdue_loans():
        overdue_list = get_service().list_overdue_loans()
        return render_template("overdue_loans.html", overdue_loans=overdue_list)


app = create_app()


if __name__ == "__main__":
    app.run(debug=True)
