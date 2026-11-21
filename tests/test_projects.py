"""Tests for project records and topic links.

Owner: Hasan. Learning records are seeded through the repository layer in
this branch because the topic API is developed in parallel.
"""

from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from backend.config.settings import Settings
from backend.main import create_app

STUDENT = {"name": "Hasan", "topic": "Python", "status": "Active", "score": 80}


@pytest.fixture
def project_client(tmp_path: Path) -> Iterator[TestClient]:
    settings = Settings(database_path=tmp_path / "projects.db")
    with TestClient(create_app(settings)) as client:
        yield client


def add_student(client: TestClient, name="Hasan") -> dict:
    response = client.post("/api/students", json={**STUDENT, "name": name})
    assert response.status_code == 201
    return response.json()


def seed_topic(
    client: TestClient,
    student_id: int,
    topic_key: str,
    status: str = "Completed",
) -> int:
    """Insert a learning record directly; parallel branch owns its API."""
    with client.app.state.database.connect() as connection:
        cursor = connection.execute(
            "INSERT INTO student_topics (student_id, topic_key, status) "
            "VALUES (?, ?, ?)",
            (student_id, topic_key, status),
        )
        return cursor.lastrowid


def project_payload(topic_ids: list[int], **changes) -> dict:
    return {
        "title": "Student portfolio",
        "description": "A shared portfolio site for the academy cohort.",
        "contribution": "I implemented Git branches and the PR review flow.",
        "repository_link": "https://github.com/example/portfolio",
        "status": "In progress",
        "topic_ids": topic_ids,
        **changes,
    }


def add_project(client: TestClient, student_id: int, payload: dict) -> dict:
    response = client.post(
        f"/api/students/{student_id}/projects", json=payload
    )
    assert response.status_code == 201
    return response.json()


def test_add_project_with_its_own_topic_links(project_client: TestClient):
    student = add_student(project_client)
    topic_id = seed_topic(project_client, student["id"], "git-branches-prs")
    saved = add_project(
        project_client, student["id"], project_payload([topic_id])
    )
    assert saved["student_id"] == student["id"]
    assert saved["topic_ids"] == [topic_id]
    assert "Git" in saved["contribution"]
    listed = project_client.get(
        f"/api/students/{student['id']}/projects"
    ).json()
    assert [project["id"] for project in listed] == [saved["id"]]


def test_two_students_can_describe_the_same_team_project(
    project_client: TestClient,
):
    hasan = add_student(project_client, "Hasan")
    bahodir = add_student(project_client, "Bahodirjon")
    hasan_topic = seed_topic(project_client, hasan["id"], "git-branches-prs")
    bahodir_topic = seed_topic(
        project_client, bahodir["id"], "git-branches-prs"
    )
    payload = project_payload([hasan_topic], status="Completed")
    add_project(project_client, hasan["id"], payload)
    add_project(
        project_client,
        bahodir["id"],
        {
            **payload,
            "topic_ids": [bahodir_topic],
            "contribution": "I set up the pull request review checklist.",
        },
    )
    hasan_projects = project_client.get(
        f"/api/students/{hasan['id']}/projects"
    ).json()
    bahodir_projects = project_client.get(
        f"/api/students/{bahodir['id']}/projects"
    ).json()
    assert len(hasan_projects) == len(bahodir_projects) == 1
    contributions = {
        hasan_projects[0]["contribution"],
        bahodir_projects[0]["contribution"],
    }
    assert len(contributions) == 2


def test_unknown_and_foreign_topic_links_are_rejected(
    project_client: TestClient,
):
    hasan = add_student(project_client, "Hasan")
    bahodir = add_student(project_client, "Bahodirjon")
    foreign_topic = seed_topic(
        project_client, bahodir["id"], "git-branches-prs"
    )

    unknown = project_client.post(
        f"/api/students/{hasan['id']}/projects",
        json=project_payload([999]),
    )
    assert unknown.status_code == 422
    assert "unknown topic ids" in unknown.json()["detail"]

    foreign = project_client.post(
        f"/api/students/{hasan['id']}/projects",
        json=project_payload([foreign_topic]),
    )
    assert foreign.status_code == 422
    assert "another student" in foreign.json()["detail"]
    assert (
        project_client.get(f"/api/students/{hasan['id']}/projects").json()
        == []
    )


def test_project_status_and_topic_links_can_be_updated(
    project_client: TestClient,
):
    student = add_student(project_client)
    first_topic = seed_topic(project_client, student["id"], "git-branches-prs")
    second_topic = seed_topic(
        project_client, student["id"], "numpy-arrays-operations"
    )
    saved = add_project(
        project_client, student["id"], project_payload([first_topic])
    )
    response = project_client.patch(
        f"/api/students/{student['id']}/projects/{saved['id']}",
        json={"status": "Completed", "topic_ids": [second_topic]},
    )
    assert response.status_code == 200
    assert response.json()["status"] == "Completed"
    assert response.json()["topic_ids"] == [second_topic]


def test_invalid_project_updates_and_unknown_ids(project_client: TestClient):
    student = add_student(project_client)
    topic_id = seed_topic(project_client, student["id"], "git-branches-prs")
    saved = add_project(
        project_client, student["id"], project_payload([topic_id])
    )
    assert (
        project_client.patch(
            f"/api/students/{student['id']}/projects/{saved['id']}", json={}
        ).status_code
        == 422
    )
    assert (
        project_client.post(
            f"/api/students/{student['id']}/projects",
            json=project_payload([], repository_link="not-a-url"),
        ).status_code
        == 422
    )
    assert (
        project_client.patch(
            f"/api/students/{student['id']}/projects/999",
            json={"status": "Completed"},
        ).status_code
        == 404
    )
    assert (
        project_client.patch(
            f"/api/students/999/projects/{saved['id']}",
            json={"status": "Completed"},
        ).status_code
        == 404
    )


def test_projects_survive_restart(tmp_path: Path):
    settings = Settings(database_path=tmp_path / "project-persist.db")
    with TestClient(create_app(settings)) as first:
        student = add_student(first)
        topic_id = seed_topic(first, student["id"], "git-branches-prs")
        saved = add_project(
            first,
            student["id"],
            project_payload([topic_id], status="Completed"),
        )

    with TestClient(create_app(settings)) as second:
        records = second.get(f"/api/students/{student['id']}/projects").json()
        assert len(records) == 1
        assert records[0]["id"] == saved["id"]
        assert records[0]["topic_ids"] == [topic_id]
