"""HTTP endpoints for topics and the skill matrix (Bahodirjon)."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status

from backend.database import Database
from backend.models import (
    SkillSummary,
    StudentTopic,
    TopicCatalogueItem,
    TopicCreate,
    TopicStatusUpdate,
)
from backend.profile_service import build_combined_skill_summary
from backend.repository import StudentNotFoundError
from backend.topic_repository import DuplicateTopicError, TopicNotFoundError
from backend.topic_service import UnknownTopicKeyError
from backend.topic_service import add_topic as service_add_topic
from backend.topic_service import list_catalogue, list_topics
from backend.topic_service import update_topic_status as service_update_status

router = APIRouter(prefix="/api")


def get_database(request: Request) -> Database:
    """Use the same database the rest of the app was built with."""
    return request.app.state.database


DatabaseDep = Annotated[Database, Depends(get_database)]


@router.get("/topics/catalogue", response_model=list[TopicCatalogueItem])
def get_catalogue() -> list[TopicCatalogueItem]:
    """Return the predefined topics and their mapped skills."""
    return list_catalogue()


@router.post(
    "/students/{student_id}/topics",
    response_model=StudentTopic,
    status_code=status.HTTP_201_CREATED,
)
def create_topic(
    student_id: int, new_topic: TopicCreate, database: DatabaseDep
) -> StudentTopic:
    """Add a catalogue topic to one student's learning records."""
    try:
        return service_add_topic(database, student_id, new_topic)
    except StudentNotFoundError as error:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(error)) from error
    except UnknownTopicKeyError as error:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT, str(error)
        ) from error
    except DuplicateTopicError as error:
        raise HTTPException(status.HTTP_409_CONFLICT, str(error)) from error


@router.get("/students/{student_id}/topics", response_model=list[StudentTopic])
def get_topics(student_id: int, database: DatabaseDep) -> list[StudentTopic]:
    """List one student's learning records."""
    try:
        return list_topics(database, student_id)
    except StudentNotFoundError as error:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(error)) from error


@router.patch(
    "/students/{student_id}/topics/{topic_id}", response_model=StudentTopic
)
def patch_topic_status(
    student_id: int,
    topic_id: int,
    changes: TopicStatusUpdate,
    database: DatabaseDep,
) -> StudentTopic:
    """Change a learning record's status from Learning to Completed or back."""
    try:
        return service_update_status(database, student_id, topic_id, changes)
    except (StudentNotFoundError, TopicNotFoundError) as error:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(error)) from error


@router.get("/skills/summary", response_model=SkillSummary)
def get_skill_summary(database: DatabaseDep) -> SkillSummary:
    """Return the NumPy matrix, its counts and the pandas progress summary."""
    return build_combined_skill_summary(database)
