"""Business logic that does not belong to the web or the database."""

import numpy as np

from backend.config.business_rules import StudentStatus
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


def list_students(database, status=None, search=None, sort=None):
    """Convenience wrapper used outside the API routes.

    StudentQuery applies the same stripping and blank-search rules as the
    HTTP route, so calling this helper cannot bypass validation.
    """
    from backend.models import StudentQuery
    from backend.repository import StudentRepository

    query = StudentQuery(status=status, search=search, sort=sort)
    return StudentRepository(database).list_all(query)


def get_student(database, student_id: int):
    """Load one student through the same repository the routes use."""
    from backend.repository import StudentRepository

    return StudentRepository(database).get(student_id)
