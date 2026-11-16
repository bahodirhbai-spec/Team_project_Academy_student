"""Database setup: where the SQLite file lives and how to connect."""

import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DATABASE_PATH = PROJECT_ROOT / "students.db"

CREATE_STUDENTS_TABLE = """
    CREATE TABLE IF NOT EXISTS students (
        id     INTEGER PRIMARY KEY AUTOINCREMENT,
        name   TEXT    NOT NULL,
        topic  TEXT    NOT NULL,
        status TEXT    NOT NULL
               CHECK (status IN ('Active', 'Paused', 'Completed')),
        score  INTEGER CHECK (score BETWEEN 0 AND 100)
    )
"""


class Database:
    """Knows where the SQLite file is and how to open it."""

    def __init__(self, path: Path = DEFAULT_DATABASE_PATH) -> None:
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
