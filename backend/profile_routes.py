"""HTTP endpoint for the View Profile page and the combined summary."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status

from backend.database import Database
from backend.models import StudentProfile
from backend.profile_service import get_profile
from backend.repository import StudentNotFoundError

router = APIRouter(prefix="/api")


def get_database(request: Request) -> Database:
    """Use the database the app was built with."""
    return request.app.state.database


DatabaseDep = Annotated[Database, Depends(get_database)]


@router.get("/students/{student_id}/profile", response_model=StudentProfile)
def get_student_profile(
    student_id: int, database: DatabaseDep
) -> StudentProfile:
    """Return the student's info, topics, projects and generated skills."""
    try:
        return get_profile(database, student_id)
    except StudentNotFoundError as error:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(error)) from error
