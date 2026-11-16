"""Database setup: how to connect to SQLite and create the table."""

import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from backend.config.business_rules import MAX_SCORE, MIN_SCORE, StudentStatus

# Built from config/business_rules.py, so each rule is written in
# exactly one place. They are our own constants, not user input, so
# putting them into the SQL text is safe.
_ALLOWED_STATUSES = ", ".join(f"'{status.value}'" for status in StudentStatus)

CREATE_STUDENTS_TABLE = f"""
    CREATE TABLE IF NOT EXISTS students (
        id     INTEGER PRIMARY KEY AUTOINCREMENT,
        name   TEXT    NOT NULL,
        topic  TEXT    NOT NULL,
        status TEXT    NOT NULL CHECK (status IN ({_ALLOWED_STATUSES})),
        score  INTEGER CHECK (score BETWEEN {MIN_SCORE} AND {MAX_SCORE})
    )
"""


class Database:
    """Knows where the SQLite file is and how to open it."""

    def __init__(self, path: Path) -> None:
        self.path = path

    @contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]:
        """Open a connection, commit on success, and always close it."""
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row  # rows act like dicts
        try:
            with connection:  # commits, or rolls back on an error
                yield connection
        finally:
            connection.close()

    def create_tables(self) -> None:
        """Create the students table if it does not exist yet."""
        with self.connect() as connection:
            connection.execute(CREATE_STUDENTS_TABLE)
