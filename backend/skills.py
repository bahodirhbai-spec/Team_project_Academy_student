"""Skill rules: which skills a student has. Owners: both.

Skills are never saved in the database. They are worked out again on
every request from topics and projects, so a status change shows up
on the profile straight away and can never get out of date.
"""

import numpy as np
import pandas as pd

from backend.config.business_rules import SkillLabel
from backend.models import (
    Profile,
    Project,
    Skill,
    SkillCount,
    SkillOverview,
    Student,
    StudentProgress,
    TopicRecord,
)
from backend.project_analytics import (
    completed_projects,
    progress_summary,
    skills_per_student,
    students_per_skill,
)
from backend.topic_analytics import (
    build_skill_matrix,
    completed_topics,
    student_skill_pairs,
)

SKILL_KEY = ["student_id", "skill"]  # one skill of one student
SKILL_COLUMNS = [*SKILL_KEY, "label", "topics", "projects"]
PROJECT_EVIDENCE_COLUMNS = ["name", "link", "contribution"]

SkillKey = tuple[int, str]


def generate_skills(
    records: pd.DataFrame, projects: pd.DataFrame, links: pd.DataFrame
) -> pd.DataFrame:
    """Every student's skills, one row per (student_id, skill).

    1. Each Completed topic gives its skill the label "Learned".
    2. Topics that teach the same skill are merged into one row.
    3. Completed projects linked to those topics are collected.
    4. If there is at least one, the label is "Applied in a project".

    Columns: student_id, skill, label, topics (list of topic names)
    and projects (list of {name, link, contribution}).
    """
    finished_topics = completed_topics(records)
    skills = student_skill_pairs(finished_topics).sort_values(
        SKILL_KEY, ignore_index=True
    )
    keys: list[SkillKey] = list(zip(skills["student_id"], skills["skill"]))
    topics_by_skill = _topic_names_by_skill(finished_topics)
    projects_by_skill = _projects_by_skill(finished_topics, projects, links)
    skills["topics"] = _object_column(
        [topics_by_skill[key] for key in keys], skills.index
    )
    skills["projects"] = _object_column(
        [projects_by_skill.get(key, []) for key in keys], skills.index
    )
    skills["label"] = np.where(
        skills["projects"].map(len) > 0,
        SkillLabel.APPLIED.value,
        SkillLabel.LEARNED.value,
    )
    return skills[SKILL_COLUMNS]


def build_profile(
    student: Student,
    topics: list[TopicRecord],
    projects: list[Project],
    skills: pd.DataFrame,
) -> Profile:
    """Put together everything the profile page shows."""
    return Profile(
        student=student,
        topics=topics,
        projects=projects,
        skills=_skills_of_student(skills, student.id),
    )


def build_skill_overview(
    students: list[Student],
    records: pd.DataFrame,
    projects: pd.DataFrame,
    links: pd.DataFrame,
) -> SkillOverview:
    """The 0/1 matrix and the totals for the main page."""
    skills = generate_skills(records, projects, links)
    student_ids = [student.id for student in students]
    skill_names = sorted(skills["skill"].unique())
    matrix = build_skill_matrix(
        student_ids, skill_names, student_skill_pairs(skills)
    )
    progress = progress_summary(
        _students_frame(students),
        completed_topics(records),
        completed_projects(projects),
    )
    progress["skill_count"] = skills_per_student(matrix)
    return SkillOverview(
        skills=skill_names,
        students=[
            StudentProgress.model_validate(row)
            for row in progress.to_dict("records")
        ],
        matrix=matrix.tolist(),
        skill_counts=[
            SkillCount(skill=name, student_count=int(count))
            for name, count in zip(skill_names, students_per_skill(matrix))
        ],
    )


def _skills_of_student(skills: pd.DataFrame, student_id: int) -> list[Skill]:
    """Turn one student's rows of the skills table into Skill models."""
    own_rows = skills[skills["student_id"] == student_id]
    return [
        Skill(
            name=row["skill"],
            label=row["label"],
            topics=row["topics"],
            projects=row["projects"],
        )
        for row in own_rows.to_dict("records")
    ]


def _topic_names_by_skill(
    finished_topics: pd.DataFrame,
) -> dict[SkillKey, list[str]]:
    """The completed topic names behind each student's skill."""
    return {
        key: sorted(group["topic_name"])
        for key, group in finished_topics.groupby(SKILL_KEY)
    }


def _projects_by_skill(
    finished_topics: pd.DataFrame,
    projects: pd.DataFrame,
    links: pd.DataFrame,
) -> dict[SkillKey, list[dict]]:
    """The completed projects linked to each student's skill.

    A project linked to two topics of the same skill is listed once.
    """
    finished_projects = completed_projects(projects)[
        ["project_id", *PROJECT_EVIDENCE_COLUMNS]
    ]
    evidence = (
        links[["project_id", "topic_record_id"]]
        .merge(finished_projects, on="project_id")
        .merge(
            finished_topics[["record_id", *SKILL_KEY]],
            left_on="topic_record_id",
            right_on="record_id",
        )
        .drop_duplicates([*SKILL_KEY, "project_id"])
        .sort_values("project_id")
    )
    # SQL NULL can arrive as NaN; the API must send null instead.
    evidence = evidence.astype({"link": object})
    evidence["link"] = evidence["link"].where(evidence["link"].notna(), None)
    return {
        key: group[PROJECT_EVIDENCE_COLUMNS].to_dict("records")
        for key, group in evidence.groupby(SKILL_KEY)
    }


def _object_column(values: list, index: pd.Index) -> pd.Series:
    """A column whose cells are lists (pandas would try to unpack them)."""
    return pd.Series(values, index=index, dtype=object)


def _students_frame(students: list[Student]) -> pd.DataFrame:
    """Students as a table with the columns progress_summary needs."""
    return pd.DataFrame({
        "student_id": [student.id for student in students],
        "name": [student.name for student in students],
    }).astype({"student_id": "int64"})
