"""API tests for a student's projects (owner: Hasan)."""

import sqlite3
from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from backend.config.settings import Settings
from backend.database import Database
from backend.main import create_app
from backend.project_repository import ProjectRepository

STUDENT = {"name": "Hasan", "topic": "Python", "status": "Active"}
PROJECT = {
    "name": "Academy tracker",
    "description": "Tracks academy students and their progress",
    "contribution": "Wrote the project endpoints",
    "link": "https://github.com/example/tracker",
}
MISSING_ID = 999


@pytest.fixture
def client(tmp_path: Path) -> Iterator[TestClient]:
    """A test client whose app uses a temporary SQLite file."""
    settings = Settings(database_path=tmp_path / "test.db")
    with TestClient(create_app(settings)) as test_client:
        yield test_client


def add_student(client: TestClient) -> int:
    """Add a student through the API and return its ID."""
    return client.post("/api/students", json=STUDENT).json()["id"]


def add_topic_record(client: TestClient, student_id: int, name: str) -> int:
    """Give a student a topic, straight in SQL.

    Bahodirjon's topic endpoints are on another branch, so the test
    writes the rows itself.
    """
    with client.app.state.database.connect() as connection:
        connection.execute(
            "INSERT OR IGNORE INTO topic_catalogue (name, skill) "
            "VALUES (?, ?)",
            (name, f"{name} skill"),
        )
        topic_id = connection.execute(
            "SELECT id FROM topic_catalogue WHERE name = ?", (name,)
        ).fetchone()["id"]
        cursor = connection.execute(
            "INSERT INTO student_topics (student_id, topic_id, status) "
            "VALUES (?, ?, 'Completed')",
            (student_id, topic_id),
        )
    return cursor.lastrowid


def projects_url(student_id: int) -> str:
    """Address of one student's projects."""
    return f"/api/students/{student_id}/projects"


# ----- Adding and listing -----

def test_add_project_returns_it_with_id_and_defaults(client: TestClient):
    student_id = add_student(client)
    response = client.post(projects_url(student_id), json=PROJECT)
    assert response.status_code == 201
    assert response.json() == {
        "id": 1,
        "student_id": student_id,
        **PROJECT,
        "status": "In progress",
        "topic_record_ids": [],
    }


def test_add_project_links_own_topics_once(client: TestClient):
    student_id = add_student(client)
    git = add_topic_record(client, student_id, "Git")
    sql = add_topic_record(client, student_id, "SQL")
    body = {**PROJECT, "topic_record_ids": [sql, git, git]}
    saved = client.post(projects_url(student_id), json=body).json()
    assert saved["topic_record_ids"] == [git, sql]


def test_list_projects_shows_only_that_students_projects(client: TestClient):
    hasan = add_student(client)
    other = add_student(client)
    client.post(projects_url(hasan), json=PROJECT)
    client.post(projects_url(other), json={**PROJECT, "name": "Other"})
    names = [p["name"] for p in client.get(projects_url(hasan)).json()]
    assert names == ["Academy tracker"]


def test_description_and_contribution_are_saved_separately(
    client: TestClient,
):
    student_id = add_student(client)
    client.post(projects_url(student_id), json=PROJECT)
    saved = client.get(projects_url(student_id)).json()[0]
    assert saved["description"] == PROJECT["description"]
    assert saved["contribution"] == PROJECT["contribution"]


def test_project_without_description_is_rejected(client: TestClient):
    student_id = add_student(client)
    without_description = {
        key: value for key, value in PROJECT.items() if key != "description"
    }
    response = client.post(projects_url(student_id), json=without_description)
    assert response.status_code == 422


def test_projects_of_missing_student_is_404(client: TestClient):
    assert client.get(projects_url(MISSING_ID)).status_code == 404
    response = client.post(projects_url(MISSING_ID), json=PROJECT)
    assert response.status_code == 404


# ----- Validation -----

@pytest.mark.parametrize(
    "bad_field",
    [
        {"name": "   "},
        {"description": ""},
        {"contribution": ""},
        {"status": "Sleeping"},
        {"link": "github.com/example"},
        {"link": "ftp://example.com"},
    ],
)
def test_invalid_project_is_rejected(client: TestClient, bad_field: dict):
    student_id = add_student(client)
    response = client.post(projects_url(student_id), json={
        **PROJECT, **bad_field,
    })
    assert response.status_code == 422


def test_linking_another_students_topic_is_rejected(client: TestClient):
    hasan = add_student(client)
    other = add_student(client)
    others_topic = add_topic_record(client, other, "Git")
    body = {**PROJECT, "topic_record_ids": [others_topic]}
    response = client.post(projects_url(hasan), json=body)
    assert response.status_code == 422
    assert "do not belong" in response.json()["detail"]
    assert client.get(projects_url(hasan)).json() == []  # nothing saved


# ----- Updating -----

def test_update_changes_only_sent_fields(client: TestClient):
    student_id = add_student(client)
    client.post(projects_url(student_id), json=PROJECT)
    response = client.patch(
        f"{projects_url(student_id)}/1", json={"status": "Completed"}
    )
    assert response.status_code == 200
    assert response.json()["status"] == "Completed"
    assert response.json()["name"] == PROJECT["name"]


def test_update_changes_description(client: TestClient):
    student_id = add_student(client)
    client.post(projects_url(student_id), json=PROJECT)
    response = client.patch(
        f"{projects_url(student_id)}/1",
        json={"description": "A new description"},
    )
    assert response.status_code == 200
    assert response.json()["description"] == "A new description"
    assert response.json()["contribution"] == PROJECT["contribution"]


def test_update_replaces_linked_topics(client: TestClient):
    student_id = add_student(client)
    git = add_topic_record(client, student_id, "Git")
    sql = add_topic_record(client, student_id, "SQL")
    client.post(
        projects_url(student_id),
        json={**PROJECT, "topic_record_ids": [git]},
    )
    response = client.patch(
        f"{projects_url(student_id)}/1", json={"topic_record_ids": [sql]}
    )
    assert response.json()["topic_record_ids"] == [sql]


def test_update_can_remove_link_with_null(client: TestClient):
    student_id = add_student(client)
    client.post(projects_url(student_id), json=PROJECT)
    response = client.patch(
        f"{projects_url(student_id)}/1", json={"link": None}
    )
    assert response.json()["link"] is None


@pytest.mark.parametrize(
    "bad_changes",
    [{}, {"name": None}, {"description": None}, {"status": "Done"}],
)
def test_invalid_update_is_rejected(client: TestClient, bad_changes: dict):
    student_id = add_student(client)
    client.post(projects_url(student_id), json=PROJECT)
    response = client.patch(
        f"{projects_url(student_id)}/1", json=bad_changes
    )
    assert response.status_code == 422


def test_update_another_students_project_is_404(client: TestClient):
    hasan = add_student(client)
    other = add_student(client)
    client.post(projects_url(hasan), json=PROJECT)
    response = client.patch(
        f"{projects_url(other)}/1", json={"status": "Completed"}
    )
    assert response.status_code == 404


# ----- Saving to the database -----

def test_description_and_contribution_survive_app_restart(tmp_path: Path):
    settings = Settings(database_path=tmp_path / "restart.db")
    with TestClient(create_app(settings)) as first_run:
        student_id = add_student(first_run)
        first_run.post(projects_url(student_id), json=PROJECT)
    with TestClient(create_app(settings)) as second_run:
        saved = second_run.get(projects_url(student_id)).json()[0]
    assert saved["description"] == PROJECT["description"]
    assert saved["contribution"] == PROJECT["contribution"]


def test_old_database_gets_description_column(tmp_path: Path):
    """A students.db made before this change has no description column."""
    path = tmp_path / "old.db"
    with sqlite3.connect(path) as connection:
        connection.execute(
            "CREATE TABLE projects (id INTEGER PRIMARY KEY, "
            "student_id INTEGER, name TEXT, contribution TEXT, "
            "link TEXT, status TEXT, UNIQUE (student_id, id))"
        )
        connection.execute(
            "INSERT INTO projects (student_id, name, contribution, status) "
            "VALUES (1, 'Old project', 'My part', 'Completed')"
        )
    connection.close()
    Database(path).create_tables()
    with Database(path).connect() as connection:
        row = connection.execute(
            "SELECT name, description FROM projects"
        ).fetchone()
    assert dict(row) == {"name": "Old project", "description": ""}


# ----- Database safety net -----

def test_database_itself_refuses_cross_student_link(client: TestClient):
    """Even SQL that skips the repository cannot break the rule."""
    hasan = add_student(client)
    other = add_student(client)
    others_topic = add_topic_record(client, other, "Git")
    client.post(projects_url(hasan), json=PROJECT)
    with pytest.raises(Exception, match="FOREIGN KEY"):
        with client.app.state.database.connect() as connection:
            connection.execute(
                "INSERT INTO project_topics "
                "(project_id, topic_record_id, student_id) "
                "VALUES (1, ?, ?)",
                (others_topic, hasan),
            )


# ----- pandas tables for the analytics code -----

def test_frames_return_projects_and_links_as_tables(client: TestClient):
    student_id = add_student(client)
    git = add_topic_record(client, student_id, "Git")
    client.post(
        projects_url(student_id),
        json={**PROJECT, "topic_record_ids": [git]},
    )
    repository = ProjectRepository(client.app.state.database)
    projects = repository.projects_frame()
    links = repository.links_frame()
    # contribution and link are shown as evidence under each skill.
    assert projects.columns.tolist() == [
        "project_id", "student_id", "name", "contribution", "link",
        "status",
    ]
    assert links.to_dict("records") == [
        {"project_id": 1, "topic_record_id": git, "student_id": student_id},
    ]
