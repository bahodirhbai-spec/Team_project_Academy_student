"""Database setup: how to connect to SQLite and create the tables."""

import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from enum import Enum
from pathlib import Path

from backend.config.business_rules import (
    MAX_SCORE,
    MIN_SCORE,
    TOPIC_CATALOGUE,
    ProjectStatus,
    StudentStatus,
    TopicStatus,
)


def _sql_value_list(statuses: type[Enum]) -> str:
    """Turn an Enum into "'A', 'B'" for a CHECK (... IN (...)) rule.

    The values are our own constants, not user input, so putting them
    into the SQL text is safe. Each rule is written in exactly one
    place: config/business_rules.py.
    """
    return ", ".join(f"'{status.value}'" for status in statuses)


CREATE_STUDENTS_TABLE = f"""
    CREATE TABLE IF NOT EXISTS students (
        id     INTEGER PRIMARY KEY AUTOINCREMENT,
        name   TEXT    NOT NULL,
        topic  TEXT    NOT NULL,
        status TEXT    NOT NULL
               CHECK (status IN ({_sql_value_list(StudentStatus)})),
        score  INTEGER CHECK (score BETWEEN {MIN_SCORE} AND {MAX_SCORE})
    )
"""

# ----- Topics (owner: Bahodirjon) -----
# UNIQUE (student_id, topic_id): a topic is added to a student once.

CREATE_TOPIC_CATALOGUE_TABLE = """
    CREATE TABLE IF NOT EXISTS topic_catalogue (
        id    INTEGER PRIMARY KEY AUTOINCREMENT,
        name  TEXT    NOT NULL UNIQUE,
        skill TEXT    NOT NULL
    )
"""

CREATE_STUDENT_TOPICS_TABLE = f"""
    CREATE TABLE IF NOT EXISTS student_topics (
        id         INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id INTEGER NOT NULL REFERENCES students (id),
        topic_id   INTEGER NOT NULL REFERENCES topic_catalogue (id),
        status     TEXT    NOT NULL
                   CHECK (status IN ({_sql_value_list(TopicStatus)})),
        UNIQUE (student_id, topic_id),
        UNIQUE (student_id, id)
    )
"""

# ----- Projects (owner: Hasan) -----
# UNIQUE (student_id, id) looks redundant (id is already unique), but
# SQLite needs it so project_topics can point at the PAIR of columns.

CREATE_PROJECTS_TABLE = f"""
    CREATE TABLE IF NOT EXISTS projects (
        id           INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id   INTEGER NOT NULL REFERENCES students (id),
        name         TEXT    NOT NULL,
        contribution TEXT    NOT NULL,
        link         TEXT,
        status       TEXT    NOT NULL
                     CHECK (status IN ({_sql_value_list(ProjectStatus)})),
        UNIQUE (student_id, id)
    )
"""

# Both foreign keys share the same student_id column. So a project can
# only be linked to a topic record of the SAME student: the database
# itself refuses a link to another student's topic.
CREATE_PROJECT_TOPICS_TABLE = """
    CREATE TABLE IF NOT EXISTS project_topics (
        project_id      INTEGER NOT NULL,
        topic_record_id INTEGER NOT NULL,
        student_id      INTEGER NOT NULL,
        PRIMARY KEY (project_id, topic_record_id),
        FOREIGN KEY (student_id, project_id)
            REFERENCES projects (student_id, id) ON DELETE CASCADE,
        FOREIGN KEY (student_id, topic_record_id)
            REFERENCES student_topics (student_id, id) ON DELETE CASCADE
    )
"""

# Adds new topics and updates the skill of existing ones, so editing
# TOPIC_CATALOGUE is enough: no need to delete students.db.
UPSERT_CATALOGUE_TOPIC = """
    INSERT INTO topic_catalogue (name, skill) VALUES (?, ?)
    ON CONFLICT (name) DO UPDATE SET skill = excluded.skill
"""

# A topic removed from TOPIC_CATALOGUE disappears from the list, but
# only if no student has it: deleting a used topic would lose data.
# The "?" placeholders are filled with the current topic names.
DELETE_UNUSED_OLD_TOPICS = """
    DELETE FROM topic_catalogue
    WHERE name NOT IN ({placeholders})
      AND id NOT IN (SELECT topic_id FROM student_topics)
"""

# Order matters: a table must exist before another table points at it.
CREATE_TABLE_STATEMENTS = (
    CREATE_STUDENTS_TABLE,
    CREATE_TOPIC_CATALOGUE_TABLE,
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
        # SQLite's lower()/NOCASE only fold ASCII letters. Python's str.lower()
        # also handles Cyrillic and other Unicode text, so searching and
        # sorting work for every student name.
        connection.create_function(
            "py_lower", 1, str.lower, deterministic=True
        )
        # SQLite ignores FOREIGN KEY rules unless this is switched on,
        # and it must be switched on again for every new connection.
        connection.execute("PRAGMA foreign_keys = ON")
        try:
            with connection:  # commits, or rolls back on an error
                yield connection
        finally:
            connection.close()

    def create_tables(self) -> None:
        """Create every table that does not exist yet."""
        with self.connect() as connection:
            for statement in CREATE_TABLE_STATEMENTS:
                connection.execute(statement)

    def fill_catalogue(self) -> None:
        """Make the topic_catalogue table match TOPIC_CATALOGUE."""
        topic_names = list(TOPIC_CATALOGUE)
        placeholders = ", ".join("?" for _ in topic_names)
        with self.connect() as connection:
            connection.executemany(
                UPSERT_CATALOGUE_TOPIC, TOPIC_CATALOGUE.items()
            )
            connection.execute(
                DELETE_UNUSED_OLD_TOPICS.format(placeholders=placeholders),
                topic_names,
            )
