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

from backend.config.settings import Settings
from backend.models import (
    Student,
    StudentCreate,
    StudentQuery,
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
StudentFilters = Annotated[StudentQuery, Query()]


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
    repository: Repository, filters: StudentFilters
) -> list[Student]:
    """List students; ?status=, ?search= and ?sort= are optional."""
    return repository.list_all(filters)


@router.get("/students/{student_id}", response_model=Student)
def get_student(student_id: int, repository: Repository) -> Student:
    """Return one student, or 404 if the ID does not exist."""
    try:
        return repository.get(student_id)
    except StudentNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(error)
        ) from error


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
