"""API tests. Each test gets a fresh, empty, temporary database."""

from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from backend.config import Settings
from backend.main import create_app

HASAN = {"name": "Hasan", "topic": "Python", "status": "Active", "score": 80}
BAHODIR = {
    "name": "Bahodirjon",
    "topic": "FastAPI",
    "status": "Paused",
    "score": 70,
}


@pytest.fixture
def client(tmp_path: Path) -> Iterator[TestClient]:
    """A test client whose app uses a temporary SQLite file."""
    settings = Settings(database_path=tmp_path / "test.db")
    with TestClient(create_app(settings)) as test_client:
        yield test_client


def add_student(client: TestClient, student: dict) -> dict:
    """Add a student through the API and return the saved JSON."""
    response = client.post("/api/students", json=student)
    assert response.status_code == 201
    return response.json()


# ----- Adding and listing -----

def test_add_student_returns_it_with_generated_id(client: TestClient):
    saved = add_student(client, HASAN)
    assert saved == {"id": 1, **HASAN}


def test_list_students_returns_saved_students(client: TestClient):
    add_student(client, HASAN)
    add_student(client, BAHODIR)
    names = [s["name"] for s in client.get("/api/students").json()]
    assert names == ["Hasan", "Bahodirjon"]


def test_empty_database_lists_no_students(client: TestClient):
    assert client.get("/api/students").json() == []


@pytest.mark.parametrize(
    "bad_field",
    [
        {"name": "   "},
        {"status": "Sleeping"},
        {"score": 101},
        {"score": -1},
    ],
)
def test_invalid_student_is_rejected(client: TestClient, bad_field: dict):
    response = client.post("/api/students", json={**HASAN, **bad_field})
    assert response.status_code == 422


def test_data_survives_app_restart(tmp_path: Path):
    settings = Settings(database_path=tmp_path / "persist.db")
    with TestClient(create_app(settings)) as first_run:
        add_student(first_run, HASAN)
    with TestClient(create_app(settings)) as second_run:
        assert len(second_run.get("/api/students").json()) == 1


# ----- Filtering -----

def test_filter_by_status(client: TestClient):
    add_student(client, HASAN)
    add_student(client, BAHODIR)
    response = client.get("/api/students", params={"status": "Paused"})
    assert [s["name"] for s in response.json()] == ["Bahodirjon"]


def test_filter_with_unknown_status_is_rejected(client: TestClient):
    response = client.get("/api/students", params={"status": "Sleeping"})
    assert response.status_code == 422


# ----- Updating -----

def test_update_changes_only_sent_fields(client: TestClient):
    saved = add_student(client, HASAN)
    response = client.patch(
        f"/api/students/{saved['id']}", json={"status": "Completed"}
    )
    assert response.status_code == 200
    assert response.json() == {**saved, "status": "Completed"}


def test_update_unknown_student_returns_404(client: TestClient):
    response = client.patch("/api/students/999", json={"score": 50})
    assert response.status_code == 404


@pytest.mark.parametrize(
    "bad_changes",
    [{}, {"topic": "  "}, {"topic": None}, {"status": "X"}, {"score": 150}],
)
def test_invalid_update_is_rejected(client: TestClient, bad_changes: dict):
    saved = add_student(client, HASAN)
    response = client.patch(f"/api/students/{saved['id']}", json=bad_changes)
    assert response.status_code == 422


# ----- Summary -----

def test_summary_with_no_students(client: TestClient):
    assert client.get("/api/summary").json() == {
        "total_students": 0,
        "active_students": 0,
        "average_score": None,
    }


def test_summary_counts_and_average(client: TestClient):
    add_student(client, HASAN)  # Active, 80
    add_student(client, BAHODIR)  # Paused, 70
    add_student(client, {**HASAN, "name": "Ali", "score": None})
    assert client.get("/api/summary").json() == {
        "total_students": 3,
        "active_students": 2,
        "average_score": 75.0,  # (80 + 70) / 2, the missing score is skipped
    }


def test_average_decimals_comes_from_settings(tmp_path: Path):
    settings = Settings(
        database_path=tmp_path / "decimals.db", average_decimals=0
    )
    with TestClient(create_app(settings)) as client:
        add_student(client, {**HASAN, "score": 80})
        add_student(client, {**HASAN, "score": 85})
        assert client.get("/api/summary").json()["average_score"] == 82
