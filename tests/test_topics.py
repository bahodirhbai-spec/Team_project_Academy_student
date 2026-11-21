"""Tests for the topic catalogue, learning records and skill matrix.

Owner: Bahodirjon. These exercise the API the same way the page does.
"""

from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from backend.config.settings import Settings
from backend.main import create_app

STUDENT = {"name": "Hasan", "topic": "Python", "status": "Active", "score": 80}


@pytest.fixture
def topic_client(tmp_path: Path) -> Iterator[TestClient]:
    settings = Settings(database_path=tmp_path / "topics.db")
    with TestClient(create_app(settings)) as client:
        yield client


def add_student(client: TestClient) -> dict:
    response = client.post("/api/students", json=STUDENT)
    assert response.status_code == 201
    return response.json()


def add_topic(
    client: TestClient, student_id: int, topic_key: str, status="Completed"
) -> dict:
    response = client.post(
        f"/api/students/{student_id}/topics",
        json={"topic_key": topic_key, "status": status},
    )
    assert response.status_code == 201
    return response.json()


def summary(client: TestClient) -> dict:
    response = client.get("/api/skills/summary")
    assert response.status_code == 200
    return response.json()


def test_catalogue_exposes_predefined_skill_mappings(topic_client: TestClient):
    catalogue = topic_client.get("/api/topics/catalogue").json()
    by_key = {item["key"]: item for item in catalogue}
    assert by_key["git-branches-prs"] == {
        "key": "git-branches-prs",
        "name": "Git branches and pull requests",
        "skill": "Git collaboration",
    }
    # Two catalogue topics deliberately produce the same skill.
    assert by_key["python-lists-dictionaries"]["skill"] == "Python basics"


def test_add_and_list_learning_records(topic_client: TestClient):
    student = add_student(topic_client)
    saved = add_topic(
        topic_client, student["id"], "python-functions-collections"
    )
    assert saved["topic_name"] == "Python functions and collections"
    assert saved["skill"] == "Python basics"
    listed = topic_client.get(f"/api/students/{student['id']}/topics").json()
    assert [topic["id"] for topic in listed] == [saved["id"]]


def test_duplicate_topic_is_rejected(topic_client: TestClient):
    student = add_student(topic_client)
    add_topic(topic_client, student["id"], "git-branches-prs")
    response = topic_client.post(
        f"/api/students/{student['id']}/topics",
        json={"topic_key": "git-branches-prs", "status": "Learning"},
    )
    assert response.status_code == 409
    records = topic_client.get(f"/api/students/{student['id']}/topics").json()
    assert len(records) == 1


def test_unknown_student_and_unknown_topic_key(topic_client: TestClient):
    unknown_student = topic_client.post(
        "/api/students/999/topics",
        json={"topic_key": "git-branches-prs", "status": "Completed"},
    )
    assert unknown_student.status_code == 404

    student = add_student(topic_client)
    unknown_key = topic_client.post(
        f"/api/students/{student['id']}/topics",
        json={"topic_key": "made-up-topic", "status": "Completed"},
    )
    assert unknown_key.status_code == 422


def test_topic_status_change_recalculates_matrix(topic_client: TestClient):
    student = add_student(topic_client)
    topic = add_topic(topic_client, student["id"], "git-branches-prs")

    result = summary(topic_client)
    assert result["matrix"] == [[0, 1, 0, 0, 0]]
    assert result["students_per_skill"][1] == {
        "skill": "Git collaboration",
        "count": 1,
    }

    response = topic_client.patch(
        f"/api/students/{student['id']}/topics/{topic['id']}",
        json={"status": "Learning"},
    )
    assert response.status_code == 200
    assert summary(topic_client)["matrix"] == [[0, 0, 0, 0, 0]]


def test_learning_topic_does_not_generate_a_skill(topic_client: TestClient):
    student = add_student(topic_client)
    add_topic(
        topic_client,
        student["id"],
        "fastapi-endpoints-validation",
        status="Learning",
    )
    result = summary(topic_client)
    assert result["matrix"] == [[0, 0, 0, 0, 0]]
    assert result["progress_per_student"][0]["learned_skills"] == 0


def test_multiple_topics_for_one_skill_are_not_counted_twice(
    topic_client: TestClient,
):
    student = add_student(topic_client)
    add_topic(topic_client, student["id"], "python-functions-collections")
    add_topic(topic_client, student["id"], "python-lists-dictionaries")

    result = summary(topic_client)
    assert result["matrix"][0][0] == 1  # Python basics column
    assert result["students_per_skill"][0]["count"] == 1
    assert result["progress_per_student"][0] == {
        "student_id": student["id"],
        "name": "Hasan",
        "completed_topics": 2,
        "completed_projects": 0,
        "learned_skills": 1,
    }


def test_empty_database_has_no_matrix_rows(topic_client: TestClient):
    result = summary(topic_client)
    assert result["students"] == []
    assert result["matrix"] == []
    assert result["learned_skills_per_student"] == []
    assert result["progress_per_student"] == []
    assert len(result["skills"]) == 5
    assert all(item["count"] == 0 for item in result["students_per_skill"])


def test_patch_unknown_topic_returns_404(topic_client: TestClient):
    student = add_student(topic_client)
    response = topic_client.patch(
        f"/api/students/{student['id']}/topics/999",
        json={"status": "Completed"},
    )
    assert response.status_code == 404


def test_topic_records_survive_restart(tmp_path: Path):
    settings = Settings(database_path=tmp_path / "topic-persist.db")
    with TestClient(create_app(settings)) as first:
        student = add_student(first)
        add_topic(first, student["id"], "numpy-arrays-operations")

    with TestClient(create_app(settings)) as second:
        topics = second.get(f"/api/students/{student['id']}/topics").json()
        assert len(topics) == 1
        assert summary(second)["matrix"][0][2] == 1
