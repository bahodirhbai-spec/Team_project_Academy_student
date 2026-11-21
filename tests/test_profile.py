"""Cross-feature tests for generated skills and profiles (both owners).

Two tests are explicit cross-reviews: each owner runs the teammate's
feature and adds a test that proves the integration still works.
"""

from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from backend.config.settings import Settings
from backend.main import create_app

STUDENT = {"name": "Hasan", "topic": "Python", "status": "Active", "score": 80}


@pytest.fixture
def profile_client(tmp_path: Path) -> Iterator[TestClient]:
    settings = Settings(database_path=tmp_path / "profile.db")
    with TestClient(create_app(settings)) as client:
        yield client


def add_student(client: TestClient, name="Hasan") -> dict:
    response = client.post("/api/students", json={**STUDENT, "name": name})
    assert response.status_code == 201
    return response.json()


def add_topic(
    client: TestClient, student_id: int, key: str, status="Completed"
) -> dict:
    response = client.post(
        f"/api/students/{student_id}/topics",
        json={"topic_key": key, "status": status},
    )
    assert response.status_code == 201
    return response.json()


def add_project(
    client: TestClient, student_id: int, topic_id: int, status="Completed"
) -> dict:
    response = client.post(
        f"/api/students/{student_id}/projects",
        json={
            "title": "Team portfolio",
            "description": "A shared site built by the cohort.",
            "contribution": "I implemented the pull request workflow.",
            "repository_link": "https://github.com/example/portfolio",
            "status": status,
            "topic_ids": [topic_id],
        },
    )
    assert response.status_code == 201
    return response.json()


def profile(client: TestClient, student_id: int) -> dict:
    response = client.get(f"/api/students/{student_id}/profile")
    assert response.status_code == 200
    return response.json()


def test_empty_profile_has_no_records_or_skills(profile_client: TestClient):
    student = add_student(profile_client)
    result = profile(profile_client, student["id"])
    assert result["student"] == student
    assert result["topics"] == []
    assert result["projects"] == []
    assert result["skills"] == []
    assert result["summary"] == {
        "completed_topics": 0,
        "completed_projects": 0,
        "learned_skills": 0,
    }


def test_completed_topic_gives_learned_label(profile_client: TestClient):
    student = add_student(profile_client)
    topic = add_topic(profile_client, student["id"], "git-branches-prs")
    result = profile(profile_client, student["id"])
    assert result["skills"] == [
        {
            "name": "Git collaboration",
            "label": "Learned",
            "topics": [
                {
                    "id": topic["id"],
                    "name": "Git branches and pull requests",
                    "status": "Completed",
                }
            ],
            "projects": [],
        }
    ]


def test_completed_linked_project_gives_applied_label(
    profile_client: TestClient,
):
    student = add_student(profile_client)
    topic = add_topic(profile_client, student["id"], "git-branches-prs")
    project = add_project(profile_client, student["id"], topic["id"])

    skill = profile(profile_client, student["id"])["skills"][0]
    assert skill["name"] == "Git collaboration"
    assert skill["label"] == "Applied in a project"
    assert skill["projects"] == [
        {
            "id": project["id"],
            "title": "Team portfolio",
            "contribution": "I implemented the pull request workflow.",
            "repository_link": "https://github.com/example/portfolio",
        }
    ]


def test_learning_topic_never_generates_a_skill(profile_client: TestClient):
    student = add_student(profile_client)
    topic = add_topic(
        profile_client, student["id"], "numpy-arrays-operations", "Learning"
    )
    add_project(profile_client, student["id"], topic["id"])
    result = profile(profile_client, student["id"])
    assert result["skills"] == []
    assert result["summary"]["learned_skills"] == 0


def test_project_linked_to_learning_topic_does_not_upgrade_other_skill(
    profile_client: TestClient,
):
    student = add_student(profile_client)
    completed = add_topic(profile_client, student["id"], "git-branches-prs")
    learning = add_topic(
        profile_client, student["id"], "numpy-arrays-operations", "Learning"
    )
    response = profile_client.post(
        f"/api/students/{student['id']}/projects",
        json={
            "title": "Mixed links",
            "description": "Two links, only one qualifying topic.",
            "contribution": "I built the API endpoints.",
            "repository_link": "https://github.com/example/mixed",
            "status": "Completed",
            "topic_ids": [completed["id"], learning["id"]],
        },
    )
    assert response.status_code == 201
    skills = profile(profile_client, student["id"])["skills"]
    assert [skill["name"] for skill in skills] == ["Git collaboration"]
    assert skills[0]["label"] == "Applied in a project"


def test_several_topics_for_one_skill_are_merged(profile_client: TestClient):
    student = add_student(profile_client)
    first = add_topic(
        profile_client, student["id"], "python-functions-collections"
    )
    second = add_topic(
        profile_client, student["id"], "python-lists-dictionaries"
    )
    add_project(profile_client, student["id"], first["id"])
    add_project(profile_client, student["id"], second["id"])

    skills = profile(profile_client, student["id"])["skills"]
    assert len(skills) == 1
    assert skills[0]["name"] == "Python basics"
    assert skills[0]["label"] == "Applied in a project"
    assert sorted(topic["id"] for topic in skills[0]["topics"]) == [
        first["id"],
        second["id"],
    ]
    assert len(skills[0]["projects"]) == 2


def test_hasans_review_topic_status_changes_update_profile(
    profile_client: TestClient,
):
    """Hasan runs Bahodirjon's topic feature and tests its recalculation."""
    student = add_student(profile_client, "Bahodirjon")
    topic = add_topic(
        profile_client,
        student["id"],
        "fastapi-endpoints-validation",
        status="Learning",
    )
    assert profile(profile_client, student["id"])["skills"] == []

    response = profile_client.patch(
        f"/api/students/{student['id']}/topics/{topic['id']}",
        json={"status": "Completed"},
    )
    assert response.status_code == 200
    assert profile(profile_client, student["id"])["skills"][0]["label"] == (
        "Learned"
    )

    profile_client.patch(
        f"/api/students/{student['id']}/topics/{topic['id']}",
        json={"status": "Learning"},
    )
    assert profile(profile_client, student["id"])["skills"] == []


def test_bahodirjons_review_project_status_changes_update_skill_label(
    profile_client: TestClient,
):
    """Bahodirjon runs Hasan's project feature and tests recalculation."""
    student = add_student(profile_client)
    topic = add_topic(profile_client, student["id"], "git-branches-prs")
    project = add_project(
        profile_client, student["id"], topic["id"], status="In progress"
    )
    assert profile(profile_client, student["id"])["skills"][0]["label"] == (
        "Learned"
    )

    response = profile_client.patch(
        f"/api/students/{student['id']}/projects/{project['id']}",
        json={"status": "Completed"},
    )
    assert response.status_code == 200
    assert profile(profile_client, student["id"])["skills"][0]["label"] == (
        "Applied in a project"
    )

    profile_client.patch(
        f"/api/students/{student['id']}/projects/{project['id']}",
        json={"status": "In progress"},
    )
    assert profile(profile_client, student["id"])["skills"][0]["label"] == (
        "Learned"
    )


def test_unknown_profile_and_foreign_topic_link(profile_client: TestClient):
    assert profile_client.get("/api/students/999/profile").status_code == 404
    hasan = add_student(profile_client, "Hasan")
    other = add_student(profile_client, "Ali")
    foreign_topic = add_topic(profile_client, other["id"], "git-branches-prs")
    response = profile_client.post(
        f"/api/students/{hasan['id']}/projects",
        json={
            "title": "Wrong link",
            "description": "This topic belongs to somebody else.",
            "contribution": "Should be rejected.",
            "repository_link": "https://github.com/example/wrong",
            "status": "Completed",
            "topic_ids": [foreign_topic["id"]],
        },
    )
    assert response.status_code == 422
    assert profile(profile_client, hasan["id"])["projects"] == []


def test_profile_survives_restart(tmp_path: Path):
    settings = Settings(database_path=tmp_path / "profile-persist.db")
    with TestClient(create_app(settings)) as first:
        student = add_student(first)
        topic = add_topic(first, student["id"], "git-branches-prs")
        add_project(first, student["id"], topic["id"])
        expected = profile(first, student["id"])

    with TestClient(create_app(settings)) as second:
        assert profile(second, student["id"]) == expected
