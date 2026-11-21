"""pandas processing of project records.

Owner: Hasan. The project rows come from the repository; no SQL or HTTP
lives here, so the calculations can be tested directly.
"""

import pandas as pd

from backend.config.business_rules import ProjectStatus, TopicStatus
from backend.models import StudentProject, StudentTopic

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
