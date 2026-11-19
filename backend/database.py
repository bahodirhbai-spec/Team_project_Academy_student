"""Database setup: connections, schema creation and table definitions."""

import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from backend.config.business_rules import (
    MAX_SCORE,
    MIN_SCORE,
    ProjectStatus,
    StudentStatus,
    TopicStatus,
)

# Built from config/business_rules.py, so each rule is written in
# exactly one place. They are our own constants, not user input, so
# putting them into the SQL text is safe.
_ALLOWED_STATUSES = ", ".join(f"'{status.value}'" for status in StudentStatus)
_ALLOWED_TOPIC_STATUSES = ", ".join(
    f"'{status.value}'" for status in TopicStatus
)
_ALLOWED_PROJECT_STATUSES = ", ".join(
    f"'{status.value}'" for status in ProjectStatus
)

CREATE_STUDENTS_TABLE = f"""
    CREATE TABLE IF NOT EXISTS students (
        id     INTEGER PRIMARY KEY AUTOINCREMENT,
        name   TEXT    NOT NULL,
        topic  TEXT    NOT NULL,
        status TEXT    NOT NULL CHECK (status IN ({_ALLOWED_STATUSES})),
        score  INTEGER CHECK (score BETWEEN {MIN_SCORE} AND {MAX_SCORE})
    )
"""

CREATE_STUDENT_TOPICS_TABLE = f"""
    CREATE TABLE IF NOT EXISTS student_topics (
        id         INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id INTEGER NOT NULL REFERENCES students(id) ON DELETE CASCADE,
        topic_key  TEXT    NOT NULL,
        status     TEXT    NOT NULL
                   CHECK (status IN ({_ALLOWED_TOPIC_STATUSES})),
        UNIQUE (student_id, topic_key)
    )
"""

CREATE_PROJECTS_TABLE = f"""
    CREATE TABLE IF NOT EXISTS projects (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id      INTEGER NOT NULL REFERENCES students(id) ON DELETE CASCADE,
        title           TEXT    NOT NULL CHECK (length(trim(title)) > 0),
        description     TEXT    NOT NULL CHECK (length(trim(description)) > 0),
        contribution    TEXT    NOT NULL CHECK (length(trim(contribution)) > 0),
        repository_link TEXT    NOT NULL CHECK (length(trim(repository_link)) > 0),
        status          TEXT    NOT NULL
                        CHECK (status IN ({_ALLOWED_PROJECT_STATUSES}))
    )
"""

CREATE_PROJECT_TOPICS_TABLE = """
    CREATE TABLE IF NOT EXISTS project_topics (
        project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
        topic_id   INTEGER NOT NULL REFERENCES student_topics(id) ON DELETE CASCADE,
        PRIMARY KEY (project_id, topic_id)
    )
"""

ALL_TABLE_STATEMENTS = (
    CREATE_STUDENTS_TABLE,
    CREATE_STUDENT_TOPICS_TABLE,
    CREATE_PROJECTS_TABLE,
    CREATE_PROJECT_TOPICS_TABLE,
)


class Database:
    """Knows where the SQLite file is and how to open it."""

    def __init__(self, path: Path) -> None:
        self.path = path

    @contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]:
        """Open a connection, commit on success, and always close it."""
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row  # rows act like dicts
        connection.execute("PRAGMA foreign_keys = ON")
        try:
            with connection:  # commits, or rolls back on an error
                yield connection
        finally:
            connection.close()

    def create_tables(self) -> None:
        """Create every table if it does not exist yet."""
        with self.connect() as connection:
            for statement in ALL_TABLE_STATEMENTS:
                connection.execute(statement)
