"""SQL for the shared catalogue's student learning records (Bahodirjon)."""

import sqlite3

from backend.config.business_rules import TOPIC_BY_KEY, TopicStatus
from backend.database import Database
from backend.models import StudentTopic, TopicCreate

SELECT_TOPICS_SQL = (
    "SELECT id, student_id, topic_key, status FROM student_topics"
)


class DuplicateTopicError(Exception):
    """The student already has this catalogue topic in their records."""

    def __init__(self, student_id: int, topic_key: str) -> None:
        super().__init__(
            f"Student {student_id} already has topic '{topic_key}'"
        )
        self.student_id = student_id
        self.topic_key = topic_key


class TopicNotFoundError(Exception):
    """No learning record with this ID exists for this student."""

    def __init__(self, topic_id: int) -> None:
        super().__init__(f"Topic record {topic_id} not found")
        self.topic_id = topic_id


class TopicRepository:
    """Saves and loads student_topics rows; the only topic SQL in the app."""

    def __init__(self, database: Database) -> None:
        self._database = database

    def add(self, student_id: int, new_topic: TopicCreate) -> StudentTopic:
        """Insert one learning record; the DB unique constraint is final."""
        values = {
            "student_id": student_id,
            "topic_key": new_topic.topic_key,
            "status": new_topic.status.value,
        }
        try:
            with self._database.connect() as connection:
                cursor = connection.execute(
                    "INSERT INTO student_topics "
                    "(student_id, topic_key, status) "
                    "VALUES (:student_id, :topic_key, :status)",
                    values,
                )
                topic_id = cursor.lastrowid
        except sqlite3.IntegrityError as error:
            if "UNIQUE constraint failed" in str(error):
                raise DuplicateTopicError(
                    student_id, new_topic.topic_key
                ) from error
            raise
        return StudentTopic(
            id=topic_id,
            student_id=student_id,
            topic_key=new_topic.topic_key,
            topic_name=TOPIC_BY_KEY[new_topic.topic_key].name,
            skill=TOPIC_BY_KEY[new_topic.topic_key].skill,
            status=new_topic.status,
        )

    def list_for_student(self, student_id: int) -> list[StudentTopic]:
        """Return one student's learning records in insertion order."""
        with self._database.connect() as connection:
            rows = connection.execute(
                f"{SELECT_TOPICS_SQL} WHERE student_id = ? ORDER BY id",
                (student_id,),
            ).fetchall()
        return [_row_to_topic(row) for row in rows]

    def list_all(self) -> list[StudentTopic]:
        """Return every learning record, needed by the global skill matrix."""
        with self._database.connect() as connection:
            rows = connection.execute(
                f"{SELECT_TOPICS_SQL} ORDER BY student_id, id"
            ).fetchall()
        return [_row_to_topic(row) for row in rows]

    def get_many(self, topic_ids: list[int]) -> list[StudentTopic]:
        """Load several records for project-link validation."""
        if not topic_ids:
            return []
        placeholders = ", ".join("?" for _ in topic_ids)
        with self._database.connect() as connection:
            rows = connection.execute(
                f"{SELECT_TOPICS_SQL} WHERE id IN ({placeholders}) "
                "ORDER BY id",
                tuple(topic_ids),
            ).fetchall()
        return [_row_to_topic(row) for row in rows]

    def get(self, student_id: int, topic_id: int) -> StudentTopic | None:
        """Return a record only when it belongs to this student."""
        with self._database.connect() as connection:
            row = connection.execute(
                f"{SELECT_TOPICS_SQL} WHERE id = ? AND student_id = ?",
                (topic_id, student_id),
            ).fetchone()
        return _row_to_topic(row) if row is not None else None

    def update_status(
        self, student_id: int, topic_id: int, status: TopicStatus
    ) -> StudentTopic:
        """Change the status of one record and return the saved row."""
        with self._database.connect() as connection:
            cursor = connection.execute(
                "UPDATE student_topics SET status = ? "
                "WHERE id = ? AND student_id = ?",
                (status.value, topic_id, student_id),
            )
            row = connection.execute(
                f"{SELECT_TOPICS_SQL} WHERE id = ?", (topic_id,)
            ).fetchone()
        if cursor.rowcount == 0 or row is None:
            raise TopicNotFoundError(topic_id)
        return _row_to_topic(row)


def _row_to_topic(row: sqlite3.Row) -> StudentTopic:
    """Attach the catalogue name and skill to a stored learning record."""
    definition = TOPIC_BY_KEY[row["topic_key"]]
    return StudentTopic(
        id=row["id"],
        student_id=row["student_id"],
        topic_key=definition.key,
        topic_name=definition.name,
        skill=definition.skill,
        status=TopicStatus(row["status"]),
    )
