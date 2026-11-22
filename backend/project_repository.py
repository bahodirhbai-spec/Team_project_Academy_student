"""Project repository: the only place that writes SQL for projects.

Owner: Hasan. Other code asks this class for projects and never talks
to SQLite directly, the same idea as repository.py for students.
"""

import sqlite3
from collections import defaultdict

import pandas as pd

from backend.database import Database
from backend.errors import InvalidReferenceError, NotFoundError
from backend.models import (
    Project,
    ProjectCreate,
    ProjectUpdate,
    TopicRecordIds,
)
from backend.repository import ensure_student_exists

SELECT_PROJECTS_SQL = (
    "SELECT id, student_id, name, contribution, link, status "
    "FROM projects WHERE student_id = :student_id"
)

# Columns the analytics code needs, already named for joining tables.
PROJECTS_FRAME_SQL = (
    "SELECT id AS project_id, student_id, name, contribution, link, "
    "status FROM projects"
)
LINKS_FRAME_SQL = (
    "SELECT project_id, topic_record_id, student_id FROM project_topics"
)

# Fixed column types: an EMPTY table would otherwise get "object"
# columns, and pandas refuses to join an object column to an int one.
PROJECTS_FRAME_TYPES = {"project_id": "int64", "student_id": "int64"}
LINKS_FRAME_TYPES = {
    "project_id": "int64",
    "topic_record_id": "int64",
    "student_id": "int64",
}


class ProjectNotFoundError(NotFoundError):
    """Raised when the student has no project with the requested ID."""

    def __init__(self, student_id: int, project_id: int) -> None:
        super().__init__(
            f"Project {project_id} not found for student {student_id}"
        )


class ProjectRepository:
    """Saves and loads projects and their linked topics in SQLite."""

    def __init__(self, database: Database) -> None:
        self._database = database

    def list_for_student(self, student_id: int) -> list[Project]:
        """Return all projects of one student, oldest first."""
        with self._database.connect() as connection:
            ensure_student_exists(connection, student_id)
            return _load_projects(connection, student_id)

    def add(self, student_id: int, new_project: ProjectCreate) -> Project:
        """Save a project and its topic links in ONE transaction.

        If anything fails half way, nothing is saved: we never get a
        project without its links, or links without their project.
        """
        data = new_project.model_dump(
            mode="json", exclude={"topic_record_ids"}
        )
        topic_ids = new_project.topic_record_ids
        with self._database.connect() as connection:
            ensure_student_exists(connection, student_id)
            _check_own_topics(connection, student_id, topic_ids)
            cursor = connection.execute(
                "INSERT INTO projects "
                "(student_id, name, contribution, link, status) "
                "VALUES (:student_id, :name, :contribution, :link, :status)",
                {"student_id": student_id, **data},
            )
            project_id = cursor.lastrowid
            _replace_links(connection, student_id, project_id, topic_ids)
            return _load_project(connection, student_id, project_id)

    def update(
        self, student_id: int, project_id: int, changes: ProjectUpdate
    ) -> Project:
        """Change only the fields that were sent, then return the project."""
        # exclude_unset: keep only the fields the client actually sent.
        data = changes.model_dump(mode="json", exclude_unset=True)
        topic_ids = data.pop("topic_record_ids", None)
        with self._database.connect() as connection:
            _load_project(connection, student_id, project_id)  # 404 check
            if data:
                _update_columns(connection, project_id, data)
            if topic_ids is not None:
                _check_own_topics(connection, student_id, topic_ids)
                _replace_links(connection, student_id, project_id, topic_ids)
            return _load_project(connection, student_id, project_id)

    def projects_frame(self) -> pd.DataFrame:
        """All projects as a pandas table, for the analytics code."""
        with self._database.connect() as connection:
            return pd.read_sql_query(
                PROJECTS_FRAME_SQL, connection, dtype=PROJECTS_FRAME_TYPES
            )

    def links_frame(self) -> pd.DataFrame:
        """All project-topic links as a pandas table."""
        with self._database.connect() as connection:
            return pd.read_sql_query(
                LINKS_FRAME_SQL, connection, dtype=LINKS_FRAME_TYPES
            )


# ----- Helpers: each one does one small job inside an open connection -----

def _check_own_topics(
    connection: sqlite3.Connection,
    student_id: int,
    topic_record_ids: TopicRecordIds,
) -> None:
    """Every linked topic record must belong to THIS student.

    The database would refuse a wrong link too (see database.py), but
    checking first lets us send a clear message instead of a crash.
    """
    if not topic_record_ids:
        return
    placeholders = ", ".join("?" for _ in topic_record_ids)
    rows = connection.execute(
        f"SELECT id FROM student_topics "
        f"WHERE student_id = ? AND id IN ({placeholders})",
        (student_id, *topic_record_ids),
    ).fetchall()
    found_ids = {row["id"] for row in rows}
    foreign_ids = sorted(set(topic_record_ids) - found_ids)
    if foreign_ids:
        raise InvalidReferenceError(
            f"Topic records {foreign_ids} do not belong to "
            f"student {student_id}"
        )


def _update_columns(
    connection: sqlite3.Connection, project_id: int, data: dict
) -> None:
    """Run UPDATE for the plain columns (name, status, ...)."""
    # The keys are Pydantic field names (a fixed, safe list), so it is
    # safe to put them into the SQL text. Values still use "?".
    set_clause = ", ".join(f"{column} = ?" for column in data)
    connection.execute(
        f"UPDATE projects SET {set_clause} WHERE id = ?",
        (*data.values(), project_id),
    )


def _replace_links(
    connection: sqlite3.Connection,
    student_id: int,
    project_id: int,
    topic_record_ids: TopicRecordIds,
) -> None:
    """Make the project's links exactly the given list.

    Deleting and inserting again is simpler than working out which
    links were added and which were removed.
    """
    connection.execute(
        "DELETE FROM project_topics WHERE project_id = ?", (project_id,)
    )
    connection.executemany(
        "INSERT INTO project_topics "
        "(project_id, topic_record_id, student_id) VALUES (?, ?, ?)",
        [(project_id, topic_id, student_id) for topic_id in topic_record_ids],
    )


def _load_project(
    connection: sqlite3.Connection, student_id: int, project_id: int
) -> Project:
    """Return one project, or raise ProjectNotFoundError (404)."""
    projects = _load_projects(connection, student_id, project_id)
    if not projects:
        raise ProjectNotFoundError(student_id, project_id)
    return projects[0]


def _load_projects(
    connection: sqlite3.Connection,
    student_id: int,
    project_id: int | None = None,
) -> list[Project]:
    """Read projects and attach the list of linked topic IDs to each."""
    sql = SELECT_PROJECTS_SQL
    values: dict[str, int] = {"student_id": student_id}
    if project_id is not None:
        sql += " AND id = :project_id"
        values["project_id"] = project_id
    project_rows = connection.execute(f"{sql} ORDER BY id", values)
    links = _links_by_project(connection, student_id)
    return [
        Project(**dict(row), topic_record_ids=links[row["id"]])
        for row in project_rows
    ]


def _links_by_project(
    connection: sqlite3.Connection, student_id: int
) -> dict[int, TopicRecordIds]:
    """Map project ID -> sorted list of its topic record IDs.

    One query for all of the student's links, instead of one query per
    project. defaultdict gives [] for a project with no links.
    """
    rows = connection.execute(
        "SELECT project_id, topic_record_id FROM project_topics "
        "WHERE student_id = ? ORDER BY topic_record_id",
        (student_id,),
    )
    links: dict[int, TopicRecordIds] = defaultdict(list)
    for row in rows:
        links[row["project_id"]].append(row["topic_record_id"])
    return links
