"""Topic repository: the only place that writes SQL for topics.

Owner: Bahodirjon. Covers the shared topic catalogue and each
student's topics (table student_topics).
"""

import sqlite3

import pandas as pd

from backend.database import Database
from backend.errors import ConflictError, InvalidReferenceError, NotFoundError
from backend.models import (
    CatalogueTopic,
    TopicRecord,
    TopicRecordCreate,
    TopicRecordUpdate,
)
from backend.repository import ensure_student_exists

# Each student topic joined with its catalogue row, so the answer
# already has the topic's name and skill.
SELECT_RECORDS_SQL = """
    SELECT st.id, st.student_id, st.topic_id,
           tc.name AS topic_name, tc.skill, st.status
    FROM student_topics AS st
    JOIN topic_catalogue AS tc ON tc.id = st.topic_id
"""

RECORDS_FRAME_SQL = """
    SELECT st.id AS record_id, st.student_id,
           tc.name AS topic_name, tc.skill, st.status
    FROM student_topics AS st
    JOIN topic_catalogue AS tc ON tc.id = st.topic_id
"""

# Fixed column types: an EMPTY table would otherwise get "object"
# columns, and pandas refuses to join an object column to an int one.
RECORDS_FRAME_TYPES = {"record_id": "int64", "student_id": "int64"}


class TopicRecordNotFoundError(NotFoundError):
    """Raised when the student has no topic record with this ID."""

    def __init__(self, student_id: int, record_id: int) -> None:
        super().__init__(
            f"Topic record {record_id} not found for student {student_id}"
        )


class TopicRepository:
    """Saves and loads the catalogue and the students' topics."""

    def __init__(self, database: Database) -> None:
        self._database = database

    def list_catalogue(self) -> list[CatalogueTopic]:
        """Return every topic a student can choose, A to Z."""
        with self._database.connect() as connection:
            rows = connection.execute(
                "SELECT id, name, skill FROM topic_catalogue ORDER BY name"
            )
            return [CatalogueTopic.model_validate(dict(row)) for row in rows]

    def list_for_student(self, student_id: int) -> list[TopicRecord]:
        """Return one student's topics, oldest first."""
        with self._database.connect() as connection:
            ensure_student_exists(connection, student_id)
            return _load_records(connection, student_id)

    def add(
        self, student_id: int, new_record: TopicRecordCreate
    ) -> TopicRecord:
        """Give a student a topic: 409 if it is already there,
        422 if the topic is not in the catalogue."""
        with self._database.connect() as connection:
            ensure_student_exists(connection, student_id)
            _ensure_topic_in_catalogue(connection, new_record.topic_id)
            _ensure_not_added_yet(connection, student_id, new_record.topic_id)
            cursor = connection.execute(
                "INSERT INTO student_topics (student_id, topic_id, status) "
                "VALUES (?, ?, ?)",
                (student_id, new_record.topic_id, new_record.status.value),
            )
            return _load_record(connection, student_id, cursor.lastrowid)

    def update_status(
        self, student_id: int, record_id: int, changes: TopicRecordUpdate
    ) -> TopicRecord:
        """Switch a topic between Learning and Completed."""
        with self._database.connect() as connection:
            cursor = connection.execute(
                "UPDATE student_topics SET status = ? "
                "WHERE id = ? AND student_id = ?",
                (changes.status.value, record_id, student_id),
            )
            if cursor.rowcount == 0:
                raise TopicRecordNotFoundError(student_id, record_id)
            return _load_record(connection, student_id, record_id)

    def records_frame(self) -> pd.DataFrame:
        """All students' topics as a pandas table, for the analytics."""
        with self._database.connect() as connection:
            return pd.read_sql_query(
                RECORDS_FRAME_SQL, connection, dtype=RECORDS_FRAME_TYPES
            )


# ----- Helpers: each one does one small job inside an open connection -----

def _ensure_topic_in_catalogue(
    connection: sqlite3.Connection, topic_id: int
) -> None:
    """Raise InvalidReferenceError (422) for an unknown topic ID."""
    row = connection.execute(
        "SELECT 1 FROM topic_catalogue WHERE id = ?", (topic_id,)
    ).fetchone()
    if row is None:
        raise InvalidReferenceError(
            f"Topic {topic_id} is not in the catalogue"
        )


def _ensure_not_added_yet(
    connection: sqlite3.Connection, student_id: int, topic_id: int
) -> None:
    """Raise ConflictError (409) if the student already has the topic."""
    row = connection.execute(
        "SELECT 1 FROM student_topics WHERE student_id = ? AND topic_id = ?",
        (student_id, topic_id),
    ).fetchone()
    if row is not None:
        raise ConflictError(
            f"Student {student_id} already has topic {topic_id}"
        )


def _load_record(
    connection: sqlite3.Connection, student_id: int, record_id: int
) -> TopicRecord:
    """Return one topic record, or raise TopicRecordNotFoundError."""
    records = _load_records(connection, student_id, record_id)
    if not records:
        raise TopicRecordNotFoundError(student_id, record_id)
    return records[0]


def _load_records(
    connection: sqlite3.Connection,
    student_id: int,
    record_id: int | None = None,
) -> list[TopicRecord]:
    """Read a student's topic records (or just one of them)."""
    sql = f"{SELECT_RECORDS_SQL} WHERE st.student_id = :student_id"
    values: dict[str, int] = {"student_id": student_id}
    if record_id is not None:
        sql += " AND st.id = :record_id"
        values["record_id"] = record_id
    rows = connection.execute(f"{sql} ORDER BY st.id", values)
    return [TopicRecord.model_validate(dict(row)) for row in rows]
