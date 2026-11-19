"""SQL for projects and their links to learning records (Hasan)."""

import sqlite3

from backend.config.business_rules import TOPIC_BY_KEY, ProjectStatus
from backend.database import Database
from backend.models import (
    ProjectCreate,
    ProjectUpdate,
    StudentProject,
    StudentTopic,
    TopicStatus,
)

SELECT_PROJECTS_SQL = (
    "SELECT id, student_id, title, description, contribution, "
    "repository_link, status FROM projects"
)
SELECT_TOPICS_SQL = (
    "SELECT id, student_id, topic_key, status FROM student_topics"
)


class ProjectNotFoundError(Exception):
    """No project with this ID exists for this student."""

    def __init__(self, project_id: int) -> None:
        super().__init__(f"Project {project_id} not found")
        self.project_id = project_id


class InvalidTopicLinksError(Exception):
    """Links must point to existing topics owned by the same student."""

    def __init__(
        self, missing: list[int], other_student: list[int]
    ) -> None:
        parts = []
        if missing:
            parts.append(f"unknown topic ids: {missing}")
        if other_student:
            parts.append(f"topic ids from another student: {other_student}")
        super().__init__("; ".join(parts))
        self.missing = missing
        self.other_student = other_student


class ProjectRepository:
    """Saves and loads projects; the only project SQL in the app."""

    def __init__(self, database: Database) -> None:
        self._database = database

    def add(
        self, student_id: int, new_project: ProjectCreate
    ) -> StudentProject:
        """Insert a project and its links in one transaction."""
        data = new_project.model_dump(mode="json")
        topic_ids = _unique_ids(data.pop("topic_ids"))
        with self._database.connect() as connection:
            _validate_links(connection, student_id, topic_ids)
            cursor = connection.execute(
                "INSERT INTO projects "
                "(student_id, title, description, contribution, "
                "repository_link, status) "
                "VALUES (:student_id, :title, :description, :contribution, "
                ":repository_link, :status)",
                {"student_id": student_id, **data},
            )
            project_id = cursor.lastrowid
            _insert_links(connection, project_id, topic_ids)
            row = _get_project_row(connection, project_id)
            linked_ids = _linked_topic_ids(connection, project_id)
        return _row_to_project(row, linked_ids)

    def list_for_student(self, student_id: int) -> list[StudentProject]:
        """Return one student's projects with their own topic links."""
        with self._database.connect() as connection:
            rows = connection.execute(
                f"{SELECT_PROJECTS_SQL} WHERE student_id = ? ORDER BY id",
                (student_id,),
            ).fetchall()
            return [
                _row_to_project(
                    row, _linked_topic_ids(connection, row["id"])
                )
                for row in rows
            ]

    def list_all(self) -> list[StudentProject]:
        """Return every project for the global pandas summary."""
        with self._database.connect() as connection:
            rows = connection.execute(
                f"{SELECT_PROJECTS_SQL} ORDER BY student_id, id"
            ).fetchall()
            return [
                _row_to_project(
                    row, _linked_topic_ids(connection, row["id"])
                )
                for row in rows
            ]

    def list_topic_records(self) -> list[StudentTopic]:
        """Read learning records to match completed projects to skills."""
        with self._database.connect() as connection:
            rows = connection.execute(
                f"{SELECT_TOPICS_SQL} ORDER BY id"
            ).fetchall()
        return [_row_to_topic(row) for row in rows]

    def get(self, student_id: int, project_id: int) -> StudentProject | None:
        """Return a project only when it belongs to this student."""
        with self._database.connect() as connection:
            row = connection.execute(
                f"{SELECT_PROJECTS_SQL} WHERE id = ? AND student_id = ?",
                (project_id, student_id),
            ).fetchone()
            if row is None:
                return None
            return _row_to_project(
                row, _linked_topic_ids(connection, project_id)
            )

    def update(
        self, student_id: int, project_id: int, changes: ProjectUpdate
    ) -> StudentProject:
        """Patch sent fields and optionally replace all topic links."""
        if self.get(student_id, project_id) is None:
            raise ProjectNotFoundError(project_id)

        data = changes.model_dump(mode="json", exclude_unset=True)
        topic_ids_changed = "topic_ids" in data
        topic_ids = _unique_ids(data.pop("topic_ids", []))
        set_clause = ", ".join(f"{column} = ?" for column in data)
        with self._database.connect() as connection:
            if topic_ids_changed:
                _validate_links(connection, student_id, topic_ids)
            if set_clause:
                connection.execute(
                    f"UPDATE projects SET {set_clause} WHERE id = ?",
                    (*data.values(), project_id),
                )
            if topic_ids_changed:
                connection.execute(
                    "DELETE FROM project_topics WHERE project_id = ?",
                    (project_id,),
                )
                _insert_links(connection, project_id, topic_ids)
            row = _get_project_row(connection, project_id)
            linked_ids = _linked_topic_ids(connection, project_id)
        return _row_to_project(row, linked_ids)


def _unique_ids(topic_ids: list[int]) -> list[int]:
    """Ignore repeated IDs; a project links to each topic only once."""
    return list(dict.fromkeys(topic_ids))


def _validate_links(
    connection: sqlite3.Connection, student_id: int, topic_ids: list[int]
) -> None:
    """Reject unknown IDs and IDs owned by a different student."""
    if not topic_ids:
        return
    placeholders = ", ".join("?" for _ in topic_ids)
    rows = connection.execute(
        f"SELECT id, student_id FROM student_topics "
        f"WHERE id IN ({placeholders})",
        tuple(topic_ids),
    ).fetchall()
    owners = {row["id"]: row["student_id"] for row in rows}
    missing = [topic_id for topic_id in topic_ids if topic_id not in owners]
    other_student = [
        topic_id
        for topic_id in topic_ids
        if topic_id in owners and owners[topic_id] != student_id
    ]
    if missing or other_student:
        raise InvalidTopicLinksError(missing, other_student)


def _insert_links(
    connection: sqlite3.Connection, project_id: int, topic_ids: list[int]
) -> None:
    """Insert validated links; the table's PK stops accidental duplicates."""
    connection.executemany(
        "INSERT INTO project_topics (project_id, topic_id) VALUES (?, ?)",
        [(project_id, topic_id) for topic_id in topic_ids],
    )


def _get_project_row(
    connection: sqlite3.Connection, project_id: int
) -> sqlite3.Row:
    """Fetch a project row inside an open transaction."""
    row = connection.execute(
        f"{SELECT_PROJECTS_SQL} WHERE id = ?", (project_id,)
    ).fetchone()
    if row is None:
        raise ProjectNotFoundError(project_id)
    return row


def _linked_topic_ids(
    connection: sqlite3.Connection, project_id: int
) -> list[int]:
    """Return the project's own topic IDs in a stable order."""
    rows = connection.execute(
        "SELECT topic_id FROM project_topics WHERE project_id = ? "
        "ORDER BY topic_id",
        (project_id,),
    ).fetchall()
    return [row["topic_id"] for row in rows]


def _row_to_project(
    row: sqlite3.Row, topic_ids: list[int]
) -> StudentProject:
    """Convert one project row plus its links into the API model."""
    return StudentProject(
        id=row["id"],
        student_id=row["student_id"],
        title=row["title"],
        description=row["description"],
        contribution=row["contribution"],
        repository_link=row["repository_link"],
        status=ProjectStatus(row["status"]),
        topic_ids=topic_ids,
    )


def _row_to_topic(row: sqlite3.Row) -> StudentTopic:
    """Attach catalogue name and skill to a stored learning record."""
    definition = TOPIC_BY_KEY[row["topic_key"]]
    return StudentTopic(
        id=row["id"],
        student_id=row["student_id"],
        topic_key=definition.key,
        topic_name=definition.name,
        skill=definition.skill,
        status=TopicStatus(row["status"]),
    )
