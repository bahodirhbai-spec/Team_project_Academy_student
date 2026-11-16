"""API endpoints. They connect HTTP requests to the repository."""

from typing import Annotated

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
    Request,
    status,
)

from backend.config.business_rules import StudentStatus
from backend.config.settings import Settings
from backend.models import (
    Student,
    StudentCreate,
    StudentUpdate,
    Summary,
)
from backend.repository import StudentNotFoundError, StudentRepository
from backend.services import calculate_summary

router = APIRouter(prefix="/api")


def get_repository(request: Request) -> StudentRepository:
    """Give each endpoint a repository that uses the app's database."""
    return StudentRepository(request.app.state.database)


def get_app_settings(request: Request) -> Settings:
    """Give each endpoint the settings the app was created with."""
    return request.app.state.settings


Repository = Annotated[StudentRepository, Depends(get_repository)]
AppSettings = Annotated[Settings, Depends(get_app_settings)]
# The URL uses "?status=", but "status" is already the name of the
# imported fastapi.status module, so the Python variable gets another name.
StatusFilter = Annotated[StudentStatus | None, Query(alias="status")]


@router.post(
    "/students",
    response_model=Student,
    status_code=status.HTTP_201_CREATED,
)
def add_student(new_student: StudentCreate, repository: Repository) -> Student:
    """Validate and save a new student, then return it with its ID."""
    return repository.add(new_student)


@router.get("/students", response_model=list[Student])
def list_students(
    repository: Repository, status_filter: StatusFilter = None
) -> list[Student]:
    """List all students; ?status=Active returns only active ones."""
    return repository.list_all(status_filter)


@router.patch("/students/{student_id}", response_model=Student)
def update_student(
    student_id: int, changes: StudentUpdate, repository: Repository
) -> Student:
    """Update a student's topic, status, or score."""
    try:
        return repository.update(student_id, changes)
    except StudentNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(error)
        ) from error


@router.get("/summary", response_model=Summary)
def get_summary(repository: Repository, settings: AppSettings) -> Summary:
    """Return total students, active students, and average score."""
    return calculate_summary(
        repository.list_all(), decimals=settings.average_decimals
    )
