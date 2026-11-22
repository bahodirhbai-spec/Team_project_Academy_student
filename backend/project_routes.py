"""API endpoints for a student's projects. Owner: Hasan.

There is no try/except here on purpose: the repository raises our own
errors (errors.py) and main.py turns them into 404 / 422 responses.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, Request, status

from backend.models import Project, ProjectCreate, ProjectUpdate
from backend.project_repository import ProjectRepository

router = APIRouter(
    prefix="/api/students/{student_id}/projects", tags=["projects"]
)


def get_project_repository(request: Request) -> ProjectRepository:
    """Give each endpoint a repository that uses the app's database."""
    return ProjectRepository(request.app.state.database)


Projects = Annotated[ProjectRepository, Depends(get_project_repository)]


@router.get("", response_model=list[Project])
def list_projects(student_id: int, repository: Projects) -> list[Project]:
    """List one student's projects, or 404 if the student is missing."""
    return repository.list_for_student(student_id)


@router.post(
    "", response_model=Project, status_code=status.HTTP_201_CREATED
)
def add_project(
    student_id: int, new_project: ProjectCreate, repository: Projects
) -> Project:
    """Validate and save a project, then return it with its ID."""
    return repository.add(student_id, new_project)


@router.patch("/{project_id}", response_model=Project)
def update_project(
    student_id: int,
    project_id: int,
    changes: ProjectUpdate,
    repository: Projects,
) -> Project:
    """Change a project's fields and/or its linked topics."""
    return repository.update(student_id, project_id, changes)
