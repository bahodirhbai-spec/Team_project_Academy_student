"""Unit tests for topic_analytics.py and skills.py (hand-made tables)."""

import pandas as pd

from backend.skills import generate_skills
from backend.topic_analytics import (
    build_skill_matrix,
    completed_topics,
    student_skill_pairs,
)

# Student 1 finished two topics that teach the same skill, and one
# more; student 2 is still learning.
RECORDS = pd.DataFrame({
    "record_id": [1, 2, 3, 4],
    "student_id": [1, 1, 1, 2],
    "topic_name": ["pandas", "NumPy", "SQL", "SQL"],
    "skill": ["Data analysis", "Data analysis", "Databases", "Databases"],
    "status": ["Completed", "Completed", "Completed", "Learning"],
})
NO_PROJECTS = pd.DataFrame({
    "project_id": pd.Series(dtype="int64"),
    "student_id": pd.Series(dtype="int64"),
    "name": pd.Series(dtype="object"),
    "contribution": pd.Series(dtype="object"),
    "link": pd.Series(dtype="object"),
    "status": pd.Series(dtype="object"),
})
NO_LINKS = pd.DataFrame({
    "project_id": pd.Series(dtype="int64"),
    "topic_record_id": pd.Series(dtype="int64"),
})
KEY_COLUMNS = ["student_id", "skill", "label"]


def make_projects(statuses: list[str]) -> pd.DataFrame:
    """Projects 10, 11, ... of student 1 with the given statuses."""
    count = len(statuses)
    return pd.DataFrame({
        "project_id": [10 + number for number in range(count)],
        "student_id": [1] * count,
        "name": [f"Project {number}" for number in range(count)],
        "contribution": ["My part"] * count,
        "link": [None] * count,
        "status": statuses,
    })


def test_completed_topics_keeps_only_completed():
    assert completed_topics(RECORDS)["record_id"].tolist() == [1, 2, 3]


def test_student_skill_pairs_removes_duplicates():
    pairs = student_skill_pairs(completed_topics(RECORDS))
    assert pairs.values.tolist() == [[1, "Data analysis"], [1, "Databases"]]


def test_build_skill_matrix_places_ones():
    pairs = pd.DataFrame({"student_id": [2], "skill": ["Git"]})
    matrix = build_skill_matrix([1, 2], ["Databases", "Git"], pairs)
    assert matrix.tolist() == [[0, 0], [0, 1]]


def test_generate_skills_merges_topics_with_same_skill():
    skills = generate_skills(RECORDS, NO_PROJECTS, NO_LINKS)
    assert skills[KEY_COLUMNS].values.tolist() == [
        [1, "Data analysis", "Learned"],
        [1, "Databases", "Learned"],
    ]
    # Both supporting topics are kept on the one merged skill.
    assert skills["topics"].tolist() == [["NumPy", "pandas"], ["SQL"]]


def test_only_a_completed_project_makes_a_skill_applied():
    projects = make_projects(["Completed", "In progress"])
    links = pd.DataFrame({
        "project_id": [10, 11],
        "topic_record_id": [1, 3],  # 1 = Data analysis, 3 = Databases
    })
    skills = generate_skills(RECORDS, projects, links)
    assert skills["label"].tolist() == ["Applied in a project", "Learned"]
    assert skills["projects"].tolist() == [
        [{"name": "Project 0", "link": None, "contribution": "My part"}],
        [],
    ]


def test_project_linked_to_two_topics_of_one_skill_is_listed_once():
    links = pd.DataFrame({
        "project_id": [10, 10],
        "topic_record_id": [1, 2],  # both teach Data analysis
    })
    skills = generate_skills(RECORDS, make_projects(["Completed"]), links)
    assert len(skills["projects"].iloc[0]) == 1


def test_no_completed_topics_gives_an_empty_table():
    learning_only = RECORDS[RECORDS["status"] == "Learning"]
    skills = generate_skills(learning_only, NO_PROJECTS, NO_LINKS)
    assert skills.empty
