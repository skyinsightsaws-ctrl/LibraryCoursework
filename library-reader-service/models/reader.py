from __future__ import annotations

from dataclasses import dataclass
from typing import Optional
import sqlite3


@dataclass(slots=True)
class Reader:
    reader_id: Optional[int]
    full_name: str
    email: str
    phone: str
    membership_date: str

    @classmethod
    def from_row(cls, row: sqlite3.Row | None) -> Optional["Reader"]:
        if row is None:
            return None

        return cls(
            reader_id=row["reader_id"],
            full_name=row["full_name"],
            email=row["email"],
            phone=row["phone"],
            membership_date=row["membership_date"],
        )
