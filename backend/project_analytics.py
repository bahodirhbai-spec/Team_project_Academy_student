"""Project analytics: numbers about progress, with pandas and NumPy.

Owner: Hasan. This module has no SQL and no web code: it only takes
tables (pandas DataFrames) or matrices (NumPy arrays) and calculates.
That makes every function easy to test with small hand-made inputs.
"""

import numpy as np
import pandas as pd

from backend.config.business_rules import ProjectStatus

STUDENTS_AXIS = 1  # summing across a row adds up one student's skills
SKILLS_AXIS = 0  # summing down a column adds up one skill's students
MATRIX_DIMENSIONS = 2


def completed_projects(projects: pd.DataFrame) -> pd.DataFrame:
    """Keep only the rows whose status is Completed."""
    is_completed = projects["status"] == ProjectStatus.COMPLETED.value
    return projects[is_completed]


def progress_summary(
    students: pd.DataFrame,
    completed_topics: pd.DataFrame,
    finished_projects: pd.DataFrame,
) -> pd.DataFrame:
    """How many topics and projects each student has completed.

    students needs columns student_id and name; the other two tables
    need a student_id column. Students with nothing completed are kept
    and get 0, so nobody disappears from the summary.
    """
    topic_counts = _count_per_student(completed_topics, "completed_topics")
    project_counts = _count_per_student(
        finished_projects, "completed_projects"
    )
    summary = (
        students[["student_id", "name"]]
        .merge(topic_counts, on="student_id", how="left")
        .merge(project_counts, on="student_id", how="left")
    )
    count_columns = ["completed_topics", "completed_projects"]
    summary[count_columns] = summary[count_columns].fillna(0).astype(int)
    return summary


def skills_per_student(matrix: np.ndarray) -> np.ndarray:
    """Number of skills each student has (one number per row)."""
    _check_is_matrix(matrix)
    return matrix.sum(axis=STUDENTS_AXIS)


def students_per_skill(matrix: np.ndarray) -> np.ndarray:
    """Number of students that have each skill (one per column)."""
    _check_is_matrix(matrix)
    return matrix.sum(axis=SKILLS_AXIS)


def _count_per_student(rows: pd.DataFrame, column: str) -> pd.DataFrame:
    """Count rows per student_id into a table with the given column."""
    return (
        rows.groupby("student_id")
        .size()
        .reset_index(name=column)
    )


def _check_is_matrix(matrix: np.ndarray) -> None:
    """The skill matrix must be 2-D: rows = students, columns = skills."""
    if matrix.ndim != MATRIX_DIMENSIONS:
        raise ValueError(
            f"expected a 2-D matrix, got {matrix.ndim} dimension(s)"
        )
