"""Unit tests for project_analytics.py: small hand-made tables only."""

import numpy as np
import pandas as pd
import pytest

from backend.project_analytics import (
    completed_projects,
    progress_summary,
    skills_per_student,
    students_per_skill,
)

# Rows = students (Hasan, Bahodirjon), columns = skills (Git, SQL, API).
SKILL_MATRIX = np.array([[1, 1, 0], [1, 0, 0]])


def test_completed_projects_keeps_only_completed():
    projects = pd.DataFrame({
        "project_id": [1, 2],
        "status": ["Completed", "In progress"],
    })
    assert completed_projects(projects)["project_id"].tolist() == [1]


def test_progress_summary_counts_and_keeps_students_with_zero():
    students = pd.DataFrame({
        "student_id": [1, 2],
        "name": ["Hasan", "Bahodirjon"],
    })
    topics = pd.DataFrame({"student_id": [1, 1]})
    projects = pd.DataFrame({"student_id": [1]})
    summary = progress_summary(students, topics, projects)
    assert summary.to_dict("records") == [
        {"student_id": 1, "name": "Hasan",
         "completed_topics": 2, "completed_projects": 1},
        {"student_id": 2, "name": "Bahodirjon",
         "completed_topics": 0, "completed_projects": 0},
    ]


def test_skills_per_student_sums_each_row():
    assert skills_per_student(SKILL_MATRIX).tolist() == [2, 1]


def test_students_per_skill_sums_each_column():
    assert students_per_skill(SKILL_MATRIX).tolist() == [2, 1, 0]


def test_matrix_functions_reject_a_flat_list():
    with pytest.raises(ValueError, match="2-D"):
        skills_per_student(np.array([1, 0, 1]))
