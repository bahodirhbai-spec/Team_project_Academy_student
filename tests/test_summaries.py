"""API tests for the restored skills and projects summary endpoints."""

from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from backend.config.settings import Settings
from backend.main import create_app

STUDENT = {"name": "Hasan", "topic": "Python", "status": "Active"}
GIT_TOPIC = "Git branches and pull requests"
GIT_SKILL = "Git collaboration"
TRACKER_LINK = "https://github.com/team/tracker"


@pytest.fixture
def client(tmp_path: Path) -> Iterator[TestClient]:
    """A test client whose app uses a temporary SQLite file."""
    settings = Settings(database_path=tmp_path / "test.db")
    with TestClient(create_app(settings)) as test_client:
        yield test_client


def add_student(client: TestClient, name: str = "Hasan") -> int:
    body = {**STUDENT, "name": name}
    response = client.post("/api/students", json=body)
    assert response.status_code == 201
    return response.json()["id"]


def add_topic(client: TestClient, student_id: int) -> int:
    topic_id = next(
        topic["id"]
        for topic in client.get("/api/topics").json()
        if topic["name"] == GIT_TOPIC
    )
    response = client.post(
        f"/api/students/{student_id}/topics", json={"topic_id": topic_id}
    )
    assert response.status_code == 201
    return response.json()["id"]


def complete_topic(
    client: TestClient, student_id: int, record_id: int
) -> None:
    response = client.patch(
        f"/api/students/{student_id}/topics/{record_id}",
        json={"status": "Completed"},
    )
    assert response.status_code == 200


def add_project(
    client: TestClient,
    student_id: int,
    record_id: int,
    status: str,
) -> None:
    response = client.post(f"/api/students/{student_id}/projects", json={
        "name": "Tracker",
        "description": "Tracks students",
        "contribution": "Pull requests",
        "link": TRACKER_LINK,
        "status": status,
        "topic_record_ids": [record_id],
    })
    assert response.status_code == 201


def test_summaries_are_empty_on_a_fresh_database(client: TestClient):
    skills = client.get("/api/skills/summary")
    projects = client.get("/api/projects/summary")
    assert skills.status_code == 200
    assert projects.status_code == 200
    assert skills.json()["progress_per_student"] == []
    assert skills.json()["students_per_skill"] == []
    assert projects.json()["total_projects"] == 0
    assert projects.json()["completed_projects"] == 0
    assert projects.json()["students_per_applied_skill"] == []


def test_completed_topic_counts_as_a_learned_skill(client: TestClient):
    student_id = add_student(client)
    record_id = add_topic(client, student_id)
    complete_topic(client, student_id, record_id)

    summary = client.get("/api/skills/summary").json()
    assert summary["progress_per_student"] == [{
        "student_id": student_id,
        "name": "Hasan",
        "completed_topics": 1,
        "completed_projects": 0,
        "skill_count": 1,
    }]
    assert summary["students_per_skill"] == [
        {"skill": GIT_SKILL, "student_count": 1}
    ]
    projects = client.get("/api/projects/summary").json()
    assert projects["students_per_applied_skill"] == [
        {"skill": GIT_SKILL, "student_count": 0}
    ]


def test_completed_project_marks_the_skill_as_applied(client: TestClient):
    student_id = add_student(client)
    record_id = add_topic(client, student_id)
    complete_topic(client, student_id, record_id)
    add_project(client, student_id, record_id, "Completed")

    projects = client.get("/api/projects/summary").json()
    assert projects["total_projects"] == 1
    assert projects["completed_projects"] == 1
    assert projects["in_progress_projects"] == 0
    assert projects["students_per_applied_skill"] == [
        {"skill": GIT_SKILL, "student_count": 1}
    ]


def test_in_progress_project_does_not_count_as_applied(client: TestClient):
    student_id = add_student(client)
    record_id = add_topic(client, student_id)
    complete_topic(client, student_id, record_id)
    add_project(client, student_id, record_id, "In progress")

    projects = client.get("/api/projects/summary").json()
    assert projects["completed_projects"] == 0
    assert projects["in_progress_projects"] == 1
    assert projects["students_per_applied_skill"] == [
        {"skill": GIT_SKILL, "student_count": 0}
    ]
