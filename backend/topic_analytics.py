"""pandas topic processing and the NumPy student–skill matrix.

Owner: Bahodirjon. Nothing here talks to HTTP or SQL: callers pass in the
models loaded by the repositories, which keeps the calculations testable.
"""

import numpy as np
import pandas as pd

from backend.config.business_rules import ALL_SKILLS, TopicStatus
from backend.models import Student, StudentTopic

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


def deduplicated_skills(topics: list[StudentTopic]) -> pd.DataFrame:
    """One row per (student, skill), even if several topics map to it."""
    frame = completed_topic_frame(topics)
    columns = ["student_id", "skill"]
    if frame.empty:
        return pd.DataFrame(columns=columns)
    return frame.drop_duplicates(subset=columns)[columns].reset_index(
        drop=True
    )


def completed_topic_counts(topics: list[StudentTopic]) -> pd.DataFrame:
    """pandas groupby summary of completed topics per student."""
    frame = completed_topic_frame(topics)
    if frame.empty:
        return pd.DataFrame(columns=["student_id", "completed_topics"])
    return (
        frame.groupby("student_id", as_index=False)
        .size()
        .rename(columns={"size": "completed_topics"})
    )


def build_skill_matrix(
    students: list[Student], topics: list[StudentTopic]
) -> tuple[list[str], np.ndarray]:
    """Create the 0/1 student–skill matrix from completed topics.

    Row order follows `students`, column order follows the fixed catalogue
    skill list. A skill with no completions is still a column of zeros.
    """
    skills = list(ALL_SKILLS)
    matrix = np.zeros((len(students), len(skills)), dtype=np.int8)
    if not students or not skills:
        return skills, matrix

    frame = deduplicated_skills(topics)
    if frame.empty:
        return skills, matrix

    student_positions = {
        student.id: index for index, student in enumerate(students)
    }
    skill_positions = {skill: index for index, skill in enumerate(skills)}
    rows = frame["student_id"].map(student_positions)
    columns = frame["skill"].map(skill_positions)
    valid = rows.notna() & columns.notna()
    # NumPy advanced indexing sets all qualifying cells to 1 at once.
    matrix[
        rows.loc[valid].to_numpy(dtype=int),
        columns.loc[valid].to_numpy(dtype=int),
    ] = 1
    return skills, matrix


def matrix_counts(matrix: np.ndarray) -> tuple[list[int], list[int]]:
    """Return row sums and column sums as plain Python integers."""
    return (
        matrix.sum(axis=1).astype(int).tolist(),
        matrix.sum(axis=0).astype(int).tolist(),
    )
