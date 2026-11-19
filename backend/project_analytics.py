"""pandas project summaries and NumPy counts from the skill matrix.

Owner: Hasan. The project rows come from the repository; no SQL or HTTP
lives here, so the summaries can be tested directly.
"""

import numpy as np
import pandas as pd

from backend.config.business_rules import (
    ALL_SKILLS,
    ProjectStatus,
    TopicStatus,
)
from backend.models import (
    Student,
    StudentProject,
    StudentTopic,
    SupportingProject,
)

PROJECT_COLUMNS = (
    "project_id",
    "student_id",
    "title",
    "description",
    "contribution",
    "repository_link",
    "status",
    "topic_ids",
)

EVIDENCE_COLUMNS = (
    "student_id",
    "skill",
    "project_id",
    "title",
    "contribution",
    "repository_link",
)


def completed_project_frame(projects: list[StudentProject]) -> pd.DataFrame:
    """Build a project frame with pandas and keep Completed rows only."""
    rows = [
        {
            "project_id": project.id,
            "student_id": project.student_id,
            "title": project.title,
            "description": project.description,
            "contribution": project.contribution,
            "repository_link": project.repository_link,
            "status": project.status.value,
            "topic_ids": tuple(project.topic_ids),
        }
        for project in projects
    ]
    frame = pd.DataFrame(rows, columns=list(PROJECT_COLUMNS))
    completed = frame.loc[
        frame["status"] == ProjectStatus.COMPLETED.value
    ]
    return completed.reset_index(drop=True)


def project_counts_frame(
    students: list[Student], projects: list[StudentProject]
) -> pd.DataFrame:
    """Combine student and project rows into counts per student."""
    rows = [
        {
            "project_id": project.id,
            "student_id": project.student_id,
            "status": project.status.value,
        }
        for project in projects
    ]
    frame = pd.DataFrame(rows, columns=["project_id", "student_id", "status"])
    totals = (
        frame.groupby("student_id", as_index=False)["project_id"]
        .count()
        .rename(columns={"project_id": "total_projects"})
    )
    completed = (
        frame.loc[frame["status"] == ProjectStatus.COMPLETED.value]
        .groupby("student_id", as_index=False)["project_id"]
        .count()
        .rename(columns={"project_id": "completed_projects"})
    )
    summary = totals.merge(completed, on="student_id", how="outer").fillna(0)
    student_rows = [
        {"student_id": student.id, "name": student.name}
        for student in students
    ]
    student_frame = pd.DataFrame(
        student_rows, columns=["student_id", "name"]
    )
    combined = student_frame.merge(summary, on="student_id", how="left")
    return combined.fillna(0).astype(
        {"total_projects": int, "completed_projects": int}
    )


def completed_project_skill_frame(
    projects: list[StudentProject], topics: list[StudentTopic]
) -> pd.DataFrame:
    """Join completed projects to completed topics through their links.

    The inner merge deliberately drops links to topics that are still
    Learning: those cannot support a generated skill.
    """
    frame = completed_project_frame(projects)
    if frame.empty:
        return pd.DataFrame(columns=list(EVIDENCE_COLUMNS))

    topic_rows = [
        {
            "topic_id": topic.id,
            "student_id": topic.student_id,
            "skill": topic.skill,
            "status": topic.status.value,
        }
        for topic in topics
    ]
    topic_frame = pd.DataFrame(
        topic_rows, columns=["topic_id", "student_id", "skill", "status"]
    )
    completed_topics = topic_frame.loc[
        topic_frame["status"] == TopicStatus.COMPLETED.value
    ]

    exploded = frame.explode("topic_ids").rename(
        columns={"topic_ids": "topic_id"}
    )
    joined = exploded.merge(
        completed_topics, on=["student_id", "topic_id"], how="inner"
    )
    evidence = joined[
        [
            "student_id",
            "skill",
            "project_id",
            "title",
            "contribution",
            "repository_link",
        ]
    ]
    # A project can link several topics with the same mapped skill.
    return evidence.drop_duplicates(
        subset=["student_id", "skill", "project_id"]
    ).reset_index(drop=True)


def supporting_projects_by_skill(
    projects: list[StudentProject], topics: list[StudentTopic]
) -> dict[tuple[int, str], list[SupportingProject]]:
    """Group the pandas evidence frame by (student, skill)."""
    frame = completed_project_skill_frame(projects, topics)
    evidence: dict[tuple[int, str], list[SupportingProject]] = {}
    for row in frame.itertuples(index=False):
        key = (row.student_id, row.skill)
        evidence.setdefault(key, []).append(
            SupportingProject(
                id=row.project_id,
                title=row.title,
                contribution=row.contribution,
                repository_link=row.repository_link,
            )
        )
    return evidence


def completion_matrix(
    students: list[Student], topics: list[StudentTopic]
) -> tuple[list[str], np.ndarray]:
    """Build a 0/1 matrix from completed topics for NumPy column counts."""
    skills = list(ALL_SKILLS)
    matrix = np.zeros((len(students), len(skills)), dtype=np.int8)
    positions = {student.id: index for index, student in enumerate(students)}
    skill_positions = {skill: index for index, skill in enumerate(skills)}
    for topic in topics:
        if topic.status != TopicStatus.COMPLETED:
            continue
        row = positions.get(topic.student_id)
        column = skill_positions.get(topic.skill)
        if row is not None and column is not None:
            matrix[row, column] = 1
    return skills, matrix


def students_per_applied_skill(
    students: list[Student],
    topics: list[StudentTopic],
    evidence: dict[tuple[int, str], list[SupportingProject]],
) -> dict[str, int]:
    """Count 1s in the matrix columns that have completed project evidence."""
    skills, matrix = completion_matrix(students, topics)
    positions = {student.id: index for index, student in enumerate(students)}
    applied = np.zeros_like(matrix)
    for student_id, skill in evidence:
        row = positions.get(student_id)
        try:
            column = skills.index(skill)
        except ValueError:
            continue
        if row is not None:
            # A completed project only counts when a completed topic also
            # exists, i.e. the matrix cell is already 1.
            applied[row, column] = matrix[row, column]
    counts = applied.sum(axis=0).astype(int)
    return {
        skill: int(counts[index]) for index, skill in enumerate(skills)
    }
