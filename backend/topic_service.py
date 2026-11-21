"""Application logic for topics.

Owner: Bahodirjon. This layer checks business rules and combines data;
the route layer only turns its exceptions into HTTP status codes.
"""

from backend.config.business_rules import TOPIC_BY_KEY, TOPIC_CATALOGUE
from backend.database import Database
from backend.models import (
    StudentTopic,
    TopicCatalogueItem,
    TopicCreate,
    TopicStatusUpdate,
)
from backend.repository import StudentNotFoundError, StudentRepository
from backend.topic_repository import (
    DuplicateTopicError,
    TopicNotFoundError,
    TopicRepository,
)


class UnknownTopicKeyError(Exception):
    """A topic name was not selected from the shared catalogue."""

    def __init__(self, topic_key: str) -> None:
        super().__init__(f"Unknown topic key '{topic_key}'")
        self.topic_key = topic_key


def list_catalogue() -> list[TopicCatalogueItem]:
    """Expose the predefined catalogue in a stable, read-only order."""
    return [
        TopicCatalogueItem(key=topic.key, name=topic.name, skill=topic.skill)
        for topic in TOPIC_CATALOGUE
    ]


def add_topic(
    database: Database, student_id: int, new_topic: TopicCreate
) -> StudentTopic:
    """Validate the student and catalogue key, then save the record."""
    StudentRepository(database).get(student_id)  # raises 404 in the route
    if new_topic.topic_key not in TOPIC_BY_KEY:
        raise UnknownTopicKeyError(new_topic.topic_key)
    return TopicRepository(database).add(student_id, new_topic)


def list_topics(database: Database, student_id: int) -> list[StudentTopic]:
    """List one student's records; unknown students still return 404."""
    StudentRepository(database).get(student_id)
    return TopicRepository(database).list_for_student(student_id)


def update_topic_status(
    database: Database,
    student_id: int,
    topic_id: int,
    changes: TopicStatusUpdate,
) -> StudentTopic:
    """Change Learning <-> Completed and let analytics recalculate skills."""
    StudentRepository(database).get(student_id)
    return TopicRepository(database).update_status(
        student_id, topic_id, changes.status
    )
