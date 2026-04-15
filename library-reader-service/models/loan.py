from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Optional
import sqlite3


@dataclass(slots=True)
class Loan:
    loan_id: Optional[int]
    reader_id: int
    book_id: int
    issue_date: str
    due_date: str
    return_date: Optional[str]
    status: str
    reader_name: str = ""
    book_title: str = ""

    def is_active(self) -> bool:
        return self.status == "ACTIVE" and self.return_date is None

    def is_overdue(self, reference_date: Optional[date] = None) -> bool:
        current_date = reference_date or date.today()
        due = date.fromisoformat(self.due_date)
        return self.return_date is None and current_date > due

    def days_overdue(self, reference_date: Optional[date] = None) -> int:
        if not self.is_overdue(reference_date):
            return 0

        current_date = reference_date or date.today()
        due = date.fromisoformat(self.due_date)
        return (current_date - due).days

    @classmethod
    def from_row(cls, row: sqlite3.Row | None) -> Optional["Loan"]:
        if row is None:
            return None

        return cls(
            loan_id=row["loan_id"],
            reader_id=row["reader_id"],
            book_id=row["book_id"],
            issue_date=row["issue_date"],
            due_date=row["due_date"],
            return_date=row["return_date"],
            status=row["status"],
            reader_name=row["reader_name"] if "reader_name" in row.keys() else "",
            book_title=row["book_title"] if "book_title" in row.keys() else "",
        )
