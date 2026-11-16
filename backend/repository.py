"""Repository: the only place that writes SQL for students.

Other code asks the repository for students and never talks to SQLite
directly. If we ever change databases, only this file changes.
"""

import sqlite3

from backend.config.business_rules import StudentStatus
from backend.database import Database
from backend.models import Student, StudentCreate, StudentUpdate

SELECT_STUDENTS_SQL = "SELECT id, name, topic, status, score FROM students"


class StudentNotFoundError(Exception):
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

    def list_all(self, status: StudentStatus | None = None) -> list[Student]:
        """Return all students, or only those with the given status."""
        with self._database.connect() as connection:
            if status is None:
                rows = connection.execute(f"{SELECT_STUDENTS_SQL} ORDER BY id")
            else:
                rows = connection.execute(
                    f"{SELECT_STUDENTS_SQL} WHERE status = ? ORDER BY id",
                    (status.value,),
                )
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
