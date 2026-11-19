"""Repository: the only place that writes SQL for students.

Other code asks the repository for students and never talks to SQLite
directly. If we ever change databases, only this file changes.
"""

import sqlite3

from backend.database import Database
from backend.errors import NotFoundError
from backend.models import (
    Student,
    StudentCreate,
    StudentQuery,
    StudentSort,
    StudentUpdate,
)

SELECT_STUDENTS_SQL = "SELECT id, name, topic, status, score FROM students"

ALL_STUDENTS = StudentQuery()

# Fixed SQL pieces picked by the enum value, never built from user text.
ORDER_BY_SQL = {
    None: "id",
    StudentSort.NAME_ASC: "name COLLATE NOCASE ASC, id",
    StudentSort.NAME_DESC: "name COLLATE NOCASE DESC, id",
}

# instr() looks for plain text in the name, so "%" and "_" are not wildcards
# (with LIKE they would mean "any characters").
SEARCH_SQL = "instr(lower(name), :search) > 0"


class StudentNotFoundError(NotFoundError):
    """Raised when no student has the requested ID."""

    def __init__(self, student_id: int) -> None:
        super().__init__(f"Student {student_id} not found")
        self.student_id = student_id


class StudentRepository:
    """Saves and loads students in the SQLite database."""

    def __init__(self, database: Database) -> None:
        self._database = database

    def add(self, new_student: StudentCreate) -> Student:
        """Insert a student and return it with its generated ID."""
        data = new_student.model_dump(mode="json")
        with self._database.connect() as connection:
            cursor = connection.execute(
                "INSERT INTO students (name, topic, status, score) "
                "VALUES (:name, :topic, :status, :score)",
                data,
            )
        return Student(id=cursor.lastrowid, **data)

    def list_all(self, query: StudentQuery = ALL_STUDENTS) -> list[Student]:
        """Return the students that match the query, in its order."""
        conditions: list[str] = []
        values: dict[str, str] = {}
        if query.status is not None:
            conditions.append("status = :status")
            values["status"] = query.status.value
        if query.search is not None:
            conditions.append(SEARCH_SQL)
            values["search"] = query.search.lower()
        where = f" WHERE {' AND '.join(conditions)}" if conditions else ""
        order_by = ORDER_BY_SQL[query.sort]
        sql = f"{SELECT_STUDENTS_SQL}{where} ORDER BY {order_by}"
        with self._database.connect() as connection:
            rows = connection.execute(sql, values)
            return [_row_to_student(row) for row in rows]

    def get(self, student_id: int) -> Student:
        """Return one student, or raise StudentNotFoundError."""
        with self._database.connect() as connection:
            row = connection.execute(
                f"{SELECT_STUDENTS_SQL} WHERE id = ?", (student_id,)
            ).fetchone()
        if row is None:
            raise StudentNotFoundError(student_id)
        return _row_to_student(row)

    def update(self, student_id: int, changes: StudentUpdate) -> Student:
        """Change only the fields that were sent, then return the student."""
        # exclude_unset: keep only the fields the client actually sent.
        # The keys are Pydantic field names (a fixed, safe list), so it is
        # safe to put them into the SQL text. Values still use "?".
        data = changes.model_dump(mode="json", exclude_unset=True)
        set_clause = ", ".join(f"{column} = ?" for column in data)
        with self._database.connect() as connection:
            cursor = connection.execute(
                f"UPDATE students SET {set_clause} WHERE id = ?",
                (*data.values(), student_id),
            )
        if cursor.rowcount == 0:
            raise StudentNotFoundError(student_id)
        return self.get(student_id)


def _row_to_student(row: sqlite3.Row) -> Student:
    """Convert one database row into a Student model."""
    return Student.model_validate(dict(row))


def ensure_student_exists(
    connection: sqlite3.Connection, student_id: int
) -> None:
    """Raise StudentNotFoundError (404) if the student is missing.

    Used by the topic and project repositories inside their own
    connection, so the check and the change are one transaction.
    """
    row = connection.execute(
        "SELECT 1 FROM students WHERE id = ?", (student_id,)
    ).fetchone()
    if row is None:
        raise StudentNotFoundError(student_id)
