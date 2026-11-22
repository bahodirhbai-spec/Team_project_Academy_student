"""API endpoints for topics. Owner: Bahodirjon.

No try/except here: the repository raises our own errors (errors.py)
and main.py turns them into 404 / 409 / 422 responses.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, Request, status

from backend.models import (
    CatalogueTopic,
    TopicRecord,
    TopicRecordCreate,
    TopicRecordUpdate,
)
from backend.topic_repository import TopicRepository

router = APIRouter(prefix="/api", tags=["topics"])


def get_topic_repository(request: Request) -> TopicRepository:
    """Give each endpoint a repository that uses the app's database."""
    return TopicRepository(request.app.state.database)


Topics = Annotated[TopicRepository, Depends(get_topic_repository)]


@router.get("/topics", response_model=list[CatalogueTopic])
def list_catalogue(repository: Topics) -> list[CatalogueTopic]:
    """Every topic a student can choose, with the skill it teaches."""
    return repository.list_catalogue()


@router.get(
    "/students/{student_id}/topics", response_model=list[TopicRecord]
)
def list_student_topics(
    student_id: int, repository: Topics
) -> list[TopicRecord]:
    """One student's topics and their status."""
    return repository.list_for_student(student_id)


@router.post(
    "/students/{student_id}/topics",
    response_model=TopicRecord,
    status_code=status.HTTP_201_CREATED,
)
def add_student_topic(
    student_id: int, new_record: TopicRecordCreate, repository: Topics
) -> TopicRecord:
    """Give a student a topic from the catalogue."""
    return repository.add(student_id, new_record)


@router.patch(
    "/students/{student_id}/topics/{record_id}", response_model=TopicRecord
)
def update_student_topic(
    student_id: int,
    record_id: int,
    changes: TopicRecordUpdate,
    repository: Topics,
) -> TopicRecord:
    """Switch a topic between Learning and Completed."""
    return repository.update_status(student_id, record_id, changes)
