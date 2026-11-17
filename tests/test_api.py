"""API tests. Each test gets a fresh, empty, temporary database."""

from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from backend.config.settings import Settings
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


def add_students_named(client: TestClient, *names: str) -> None:
    """Add one active Python student for each given name."""
    for name in names:
        add_student(client, {**HASAN, "name": name})


def names(response):
    return [student["name"] for student in response.json()]


def test_partial_and_case_insensitive_search(client):
    add_students_named(client, "Ali", "Aliya", "Bob")
    assert sorted(names(client.get("/api/students?search=ali"))) == [
        "Ali", "Aliya"
    ]
    assert sorted(names(client.get("/api/students?search=ALI"))) == [
        "Ali", "Aliya"
    ]


def test_search_ignores_surrounding_spaces(client):
    add_students_named(client, "Ali", "Bob")
    assert names(client.get("/api/students?search=%20%20ali%20")) == ["Ali"]


def test_search_does_not_match_topic(client):
    add_student(client, {**HASAN, "name": "Aziz", "topic": "Ali algebra"})
    add_student(client, {**HASAN, "name": "Ali", "topic": "Python"})
    assert names(client.get("/api/students?search=ali")) == ["Ali"]
    assert client.get("/api/students?search=python").json() == []


def test_search_combined_with_status(client):
    add_student(client, {**HASAN, "name": "Ali", "status": "Active"})
    add_student(client, {**HASAN, "name": "Aliya", "status": "Paused"})
    add_student(client, {**HASAN, "name": "Bob", "status": "Active"})
    response = client.get("/api/students?search=ali&status=Active")
    assert names(response) == ["Ali"]


def test_sort_name_asc(client):
    add_students_named(client, "Charlie", "alice", "Bob")
    assert names(client.get("/api/students?sort=name_asc")) == [
        "alice", "Bob", "Charlie"
    ]


def test_sort_name_desc(client):
    add_students_named(client, "Charlie", "alice", "Bob")
    assert names(client.get("/api/students?sort=name_desc")) == [
        "Charlie", "Bob", "alice"
    ]


def test_search_with_sort(client):
    add_students_named(client, "Aliya", "Ali", "Bob")
    response = client.get("/api/students?search=ali&sort=name_asc")
    assert names(response) == ["Ali", "Aliya"]


def test_no_matching_students_returns_empty_list(client):
    add_students_named(client, "Ali")
    response = client.get("/api/students?search=zzz")
    assert response.status_code == 200
    assert response.json() == []


def test_invalid_sort_is_rejected(client):
    response = client.get("/api/students?sort=score_asc")
    assert response.status_code == 422


def test_percent_sign_is_not_a_wildcard(client):
    add_students_named(client, "Ali")
    assert client.get("/api/students?search=%25").json() == []


def test_get_existing_student(client):
    created = add_student(client, {**HASAN, "name": "Ali"})
    response = client.get(f"/api/students/{created['id']}")
    assert response.status_code == 200
    assert response.json()["name"] == "Ali"


def test_get_nonexistent_student_returns_404(client):
    response = client.get("/api/students/9999")
    assert response.status_code == 404
    assert "9999" in response.json()["detail"]


def test_no_parameters_keeps_existing_behaviour(client):
    add_students_named(client, "Bob", "Ali")
    assert names(client.get("/api/students")) == ["Bob", "Ali"]
