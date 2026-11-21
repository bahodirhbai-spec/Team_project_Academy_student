"""Generated skill labels calculated from current saved records.

Owner: both teammates. pandas combines student, topic and project rows;
labels are computed on every read and never stored in SQLite.
"""

import pandas as pd

from backend.config.business_rules import TopicStatus
from backend.models import (
    GeneratedSkill,
    SkillLabel,
    Student,
    StudentProject,
    StudentTopic,
    SupportingProject,
    SupportingTopic,
)
from backend.project_analytics import completed_project_skill_frame
from backend.topic_analytics import completed_topic_frame


def skill_evidence_frame(
    students: list[Student],
    topics: list[StudentTopic],
    projects: list[StudentProject],
) -> pd.DataFrame:
    """Join students, completed topics and completed project evidence."""
    student_rows = [
        {"student_id": student.id, "student_name": student.name}
        for student in students
    ]
    students_frame = pd.DataFrame(
        student_rows, columns=["student_id", "student_name"]
    )
    topic_frame = completed_topic_frame(topics)[
        ["student_id", "topic_id", "topic_name", "status", "skill"]
    ]
    project_frame = completed_project_skill_frame(projects, topics)
    combined = students_frame.merge(topic_frame, on="student_id", how="inner")
    return combined.merge(
        project_frame, on=["student_id", "skill"], how="left"
    )


def generate_skills(
    student_id: int,
    topics: list[StudentTopic],
    projects: list[StudentProject],
    students: list[Student],
) -> list[GeneratedSkill]:
    """Build one entry per skill, with its supporting topics and projects."""
    frame = skill_evidence_frame(students, topics, projects)
    frame = frame.loc[frame["student_id"] == student_id]
    if frame.empty:
        return []

    generated: list[GeneratedSkill] = []
    for skill, group in frame.groupby("skill", sort=True):
        topic_rows = group.drop_duplicates(subset=["topic_id"])
        supporting_topics = [
            SupportingTopic(
                id=int(row.topic_id),
                name=row.topic_name,
                status=TopicStatus(row.status),
            )
            for row in topic_rows.itertuples(index=False)
        ]
        project_rows = group.dropna(subset=["project_id"]).drop_duplicates(
            subset=["project_id"]
        )
        supporting_projects = [
            SupportingProject(
                id=int(row.project_id),
                title=row.title,
                contribution=row.contribution,
                repository_link=row.repository_link,
            )
            for row in project_rows.itertuples(index=False)
        ]
        generated.append(
            GeneratedSkill(
                name=str(skill),
                label=(
                    SkillLabel.APPLIED
                    if supporting_projects
                    else SkillLabel.LEARNED
                ),
                topics=supporting_topics,
                projects=supporting_projects,
            )
        )
    return generated
