"""HTTP endpoints for projects and their topic links (Hasan)."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status

from backend.database import Database
from backend.models import (
    ProjectCreate,
    ProjectUpdate,
    StudentProject,
)
from backend.project_repository import (
    InvalidTopicLinksError,
    ProjectNotFoundError,
)
from backend.project_service import add_project as service_add_project
from backend.project_service import list_projects, update_project
from backend.repository import StudentNotFoundError

router = APIRouter(prefix="/api")


def get_database(request: Request) -> Database:
    """Use the database the app was built with."""
    return request.app.state.database


DatabaseDep = Annotated[Database, Depends(get_database)]


@router.post(
    "/students/{student_id}/projects",
    response_model=StudentProject,
    status_code=status.HTTP_201_CREATED,
)
def create_project(
    student_id: int, new_project: ProjectCreate, database: DatabaseDep
) -> StudentProject:
    """Save one student's own version of a project."""
    try:
        return service_add_project(database, student_id, new_project)
    except StudentNotFoundError as error:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(error)) from error
    except InvalidTopicLinksError as error:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT, str(error)
        ) from error


@router.get(
    "/students/{student_id}/projects", response_model=list[StudentProject]
)
def get_projects(
    student_id: int, database: DatabaseDep
) -> list[StudentProject]:
    """List one student's projects with their own topic links."""
    try:
        return list_projects(database, student_id)
    except StudentNotFoundError as error:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(error)) from error


@router.patch(
    "/students/{student_id}/projects/{project_id}",
    response_model=StudentProject,
)
def patch_project(
    student_id: int,
    project_id: int,
    changes: ProjectUpdate,
    database: DatabaseDep,
) -> StudentProject:
    """Change status, text or topic links; nothing is stored in the label."""
    try:
        return update_project(database, student_id, project_id, changes)
    except (StudentNotFoundError, ProjectNotFoundError) as error:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(error)) from error
    except InvalidTopicLinksError as error:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT, str(error)
        ) from error
