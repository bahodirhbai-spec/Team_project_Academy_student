"""Business logic that does not belong to the web or the database."""

import numpy as np

from backend.config import StudentStatus
from backend.models import Student, Summary


def calculate_summary(students: list[Student], decimals: int) -> Summary:
    """Count students and compute the average quiz score with NumPy."""
    active_count = sum(
        1 for student in students if student.status == StudentStatus.ACTIVE
    )
    scores = [
        student.score for student in students if student.score is not None
    ]
    return Summary(
        total_students=len(students),
        active_students=active_count,
        average_score=_average(scores, decimals),
    )


def _average(scores: list[int], decimals: int) -> float | None:
    """Return the rounded mean, or None when there are no scores."""
    # np.mean([]) would return NaN with a warning, so check first.
    if not scores:
        return None
    return round(float(np.mean(scores)), decimals)
