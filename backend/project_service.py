"""Application logic for projects and their topic links (Hasan)."""

from backend.database import Database
from backend.models import (
    ProjectCreate,
    ProjectUpdate,
    StudentProject,
)
from backend.project_repository import (
    InvalidTopicLinksError,
    ProjectNotFoundError,
    ProjectRepository,
)
from backend.repository import StudentNotFoundError, StudentRepository


def add_project(
    database: Database, student_id: int, new_project: ProjectCreate
) -> StudentProject:
    """Validate the student, then save the project and its links."""
    StudentRepository(database).get(student_id)  # 404 in the route layer
    return ProjectRepository(database).add(student_id, new_project)


def list_projects(database: Database, student_id: int) -> list[StudentProject]:
    """List one student's projects."""
    StudentRepository(database).get(student_id)
    return ProjectRepository(database).list_for_student(student_id)


def update_project(
    database: Database,
    student_id: int,
    project_id: int,
    changes: ProjectUpdate,
) -> StudentProject:
    """Patch a project including the set of related learning records."""
    StudentRepository(database).get(student_id)
    return ProjectRepository(database).update(
        student_id, project_id, changes
    )
