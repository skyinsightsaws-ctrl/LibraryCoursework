from __future__ import annotations

from dataclasses import dataclass
from typing import Optional
import sqlite3


@dataclass(slots=True)
class Book:
    book_id: Optional[int]
    title: str
    author: str
    category: str
    publication_year: int
    isbn: str
    total_copies: int
    available_copies: int

    def is_available(self) -> bool:
        return self.available_copies > 0

    @classmethod
    def from_row(cls, row: sqlite3.Row | None) -> Optional["Book"]:
        if row is None:
            return None

        return cls(
            book_id=row["book_id"],
            title=row["title"],
            author=row["author"],
            category=row["category"],
            publication_year=row["publication_year"],
            isbn=row["isbn"],
            total_copies=row["total_copies"],
            available_copies=row["available_copies"],
        )
