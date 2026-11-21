"""pandas topic processing.

Owner: Bahodirjon. Nothing here talks to HTTP or SQL: callers pass in the
models loaded by the repositories, which keeps the calculations testable.
"""

import pandas as pd

from backend.config.business_rules import TopicStatus
from backend.models import StudentTopic

TOPIC_FRAME_COLUMNS = (
    "student_id",
    "topic_id",
    "topic_key",
    "topic_name",
    "skill",
    "status",
)


def completed_topic_frame(topics: list[StudentTopic]) -> pd.DataFrame:
    """Build a topic frame and keep only Completed learning records."""
    rows = [
        {
            "student_id": topic.student_id,
            "topic_id": topic.id,
            "topic_key": topic.topic_key,
            "topic_name": topic.topic_name,
            "skill": topic.skill,
            "status": topic.status.value,
        }
        for topic in topics
    ]
    frame = pd.DataFrame(rows, columns=list(TOPIC_FRAME_COLUMNS))
    # pandas boolean filter: a Learning row never reaches the skill logic.
    completed = frame.loc[
        frame["status"] == TopicStatus.COMPLETED.value
    ]
    return completed.reset_index(drop=True)
