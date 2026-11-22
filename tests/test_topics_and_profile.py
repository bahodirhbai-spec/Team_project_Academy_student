"""API tests: topics (Bahodirjon), profile and skills overview (both)."""

from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from backend.config.business_rules import TOPIC_CATALOGUE
from backend.config.settings import Settings
from backend.database import Database
from backend.main import create_app

STUDENT = {"name": "Hasan", "topic": "Python", "status": "Active"}
GIT_TOPIC = "Git branches and pull requests"
# Two catalogue topics that teach the same skill: "REST API basics".
API_TOPICS = ("FastAPI endpoints and validation", "Pydantic models")
TRACKER_LINK = "https://github.com/team/tracker"
MISSING_ID = 999


@pytest.fixture
def client(tmp_path: Path) -> Iterator[TestClient]:
    """A test client whose app uses a temporary SQLite file."""
    settings = Settings(database_path=tmp_path / "test.db")
    with TestClient(create_app(settings)) as test_client:
        yield test_client


def add_student(client: TestClient, name: str = "Hasan") -> int:
    """Add a student through the API and return its ID."""
    body = {**STUDENT, "name": name}
    return client.post("/api/students", json=body).json()["id"]


def catalogue_id(client: TestClient, topic_name: str) -> int:
    """Find a catalogue topic's ID by its name."""
    topics = client.get("/api/topics").json()
    return next(t["id"] for t in topics if t["name"] == topic_name)


def add_topic(client: TestClient, student_id: int, topic_name: str) -> int:
    """Give a student a topic through the API; return the record ID."""
    response = client.post(
        f"/api/students/{student_id}/topics",
        json={"topic_id": catalogue_id(client, topic_name)},
    )
    assert response.status_code == 201
    return response.json()["id"]


def set_topic_status(
    client: TestClient, student_id: int, record_id: int, status: str
) -> None:
    """Change one of the student's topics to Learning or Completed."""
    response = client.patch(
        f"/api/students/{student_id}/topics/{record_id}",
        json={"status": status},
    )
    assert response.status_code == 200


def complete_topic(client: TestClient, student_id: int, record_id: int):
    """Mark one of the student's topics as Completed."""
    set_topic_status(client, student_id, record_id, "Completed")


def add_project(
    client: TestClient,
    student_id: int,
    topic_record_ids: list[int],
    status: str,
    contribution: str = "Pull requests",
) -> int:
    """Add a project linked to the given topic records; return its ID."""
    response = client.post(f"/api/students/{student_id}/projects", json={
        "name": "Tracker",
        "description": "Tracks students",
        "contribution": contribution,
        "link": TRACKER_LINK,
        "status": status,
        "topic_record_ids": topic_record_ids,
    })
    assert response.status_code == 201
    return response.json()["id"]


def profile_skills(client: TestClient, student_id: int) -> list[dict]:
    """The skills shown on a student's profile."""
    return client.get(f"/api/students/{student_id}/profile").json()["skills"]


# ----- Topics -----

def test_catalogue_is_filled_from_business_rules(client: TestClient):
    topics = client.get("/api/topics").json()
    assert {t["name"]: t["skill"] for t in topics} == TOPIC_CATALOGUE


def test_add_topic_starts_as_learning_with_name_and_skill(client):
    student_id = add_student(client)
    record_id = add_topic(client, student_id, GIT_TOPIC)
    records = client.get(f"/api/students/{student_id}/topics").json()
    assert records == [{
        "id": record_id,
        "student_id": student_id,
        "topic_id": catalogue_id(client, GIT_TOPIC),
        "topic_name": GIT_TOPIC,
        "skill": "Git collaboration",
        "status": "Learning",
    }]


def test_same_topic_twice_is_409(client: TestClient):
    student_id = add_student(client)
    add_topic(client, student_id, GIT_TOPIC)
    response = client.post(
        f"/api/students/{student_id}/topics",
        json={"topic_id": catalogue_id(client, GIT_TOPIC)},
    )
    assert response.status_code == 409


def test_unknown_topic_is_422(client: TestClient):
    student_id = add_student(client)
    response = client.post(
        f"/api/students/{student_id}/topics", json={"topic_id": MISSING_ID}
    )
    assert response.status_code == 422


def test_topics_of_missing_student_is_404(client: TestClient):
    response = client.get(f"/api/students/{MISSING_ID}/topics")
    assert response.status_code == 404


def test_update_another_students_topic_is_404(client: TestClient):
    hasan = add_student(client)
    other = add_student(client, "Bahodirjon")
    record_id = add_topic(client, hasan, GIT_TOPIC)
    response = client.patch(
        f"/api/students/{other}/topics/{record_id}",
        json={"status": "Completed"},
    )
    assert response.status_code == 404


# ----- Profile and skills -----

def test_profile_of_missing_student_is_404(client: TestClient):
    response = client.get(f"/api/students/{MISSING_ID}/profile")
    assert response.status_code == 404


def test_learning_topic_gives_no_skill(client: TestClient):
    student_id = add_student(client)
    add_topic(client, student_id, GIT_TOPIC)
    assert profile_skills(client, student_id) == []


def test_completed_topic_gives_learned_skill(client: TestClient):
    student_id = add_student(client)
    record_id = add_topic(client, student_id, GIT_TOPIC)
    complete_topic(client, student_id, record_id)
    assert profile_skills(client, student_id) == [{
        "name": "Git collaboration",
        "label": "Learned",
        "topics": [GIT_TOPIC],
        "projects": [],
    }]


def test_completed_project_turns_skill_into_applied(client: TestClient):
    """The example from the assignment, step by step."""
    student_id = add_student(client)
    record_id = add_topic(client, student_id, GIT_TOPIC)
    complete_topic(client, student_id, record_id)
    add_project(client, student_id, [record_id], "Completed")
    assert profile_skills(client, student_id) == [{
        "name": "Git collaboration",
        "label": "Applied in a project",
        "topics": [GIT_TOPIC],
        "projects": [{
            "name": "Tracker",
            "link": TRACKER_LINK,
            "contribution": "Pull requests",
        }],
    }]


def test_empty_profile_has_no_topics_projects_or_skills(client):
    student_id = add_student(client)
    profile = client.get(f"/api/students/{student_id}/profile").json()
    assert profile["topics"] == []
    assert profile["projects"] == []
    assert profile["skills"] == []


def test_two_topics_with_same_skill_give_one_skill(client: TestClient):
    student_id = add_student(client)
    for topic in API_TOPICS:
        record_id = add_topic(client, student_id, topic)
        complete_topic(client, student_id, record_id)
    skills = profile_skills(client, student_id)
    assert [skill["name"] for skill in skills] == ["REST API basics"]
    assert skills[0]["topics"] == sorted(API_TOPICS)


def test_topic_back_to_learning_removes_the_skill(client: TestClient):
    student_id = add_student(client)
    record_id = add_topic(client, student_id, GIT_TOPIC)
    complete_topic(client, student_id, record_id)
    set_topic_status(client, student_id, record_id, "Learning")
    assert profile_skills(client, student_id) == []


def test_project_back_in_progress_makes_skill_learned_again(client):
    student_id = add_student(client)
    record_id = add_topic(client, student_id, GIT_TOPIC)
    complete_topic(client, student_id, record_id)
    project_id = add_project(client, student_id, [record_id], "Completed")
    client.patch(
        f"/api/students/{student_id}/projects/{project_id}",
        json={"status": "In progress"},
    )
    [skill] = profile_skills(client, student_id)
    assert skill["label"] == "Learned"
    assert skill["projects"] == []


def test_completed_project_with_learning_topic_gives_no_skill(client):
    student_id = add_student(client)
    record_id = add_topic(client, student_id, GIT_TOPIC)
    add_project(client, student_id, [record_id], "Completed")
    assert profile_skills(client, student_id) == []


def test_each_student_shows_own_contribution_to_team_project(client):
    """Two students describe the same team project differently."""
    contributions = {"Hasan": "Project API", "Bahodirjon": "Topic API"}
    for name, contribution in contributions.items():
        student_id = add_student(client, name)
        record_id = add_topic(client, student_id, GIT_TOPIC)
        complete_topic(client, student_id, record_id)
        add_project(
            client, student_id, [record_id], "Completed", contribution
        )
        [skill] = profile_skills(client, student_id)
        assert skill["projects"][0]["contribution"] == contribution


def test_topics_and_skills_survive_app_restart(tmp_path: Path):
    settings = Settings(database_path=tmp_path / "restart.db")
    with TestClient(create_app(settings)) as first_run:
        student_id = add_student(first_run)
        complete_topic(
            first_run, student_id, add_topic(first_run, student_id, GIT_TOPIC)
        )
    with TestClient(create_app(settings)) as second_run:
        [skill] = profile_skills(second_run, student_id)
        assert skill["name"] == "Git collaboration"
        assert len(second_run.get("/api/topics").json()) == len(
            TOPIC_CATALOGUE
        )


def test_profile_contains_student_topics_and_projects(client):
    student_id = add_student(client)
    add_topic(client, student_id, GIT_TOPIC)
    profile = client.get(f"/api/students/{student_id}/profile").json()
    assert profile["student"]["name"] == "Hasan"
    assert len(profile["topics"]) == 1
    assert profile["projects"] == []


# ----- Overview -----

def test_overview_of_empty_database(client: TestClient):
    assert client.get("/api/skills/overview").json() == {
        "skills": [], "students": [], "matrix": [], "skill_counts": [],
    }


def test_overview_matrix_and_counts(client: TestClient):
    hasan = add_student(client)
    other = add_student(client, "Bahodirjon")
    for topic in (GIT_TOPIC, "SQL and SQLite"):
        complete_topic(client, hasan, add_topic(client, hasan, topic))
    add_topic(client, other, GIT_TOPIC)  # still Learning: no skill
    overview = client.get("/api/skills/overview").json()
    assert overview["skills"] == ["Databases", "Git collaboration"]
    assert overview["matrix"] == [[1, 1], [0, 0]]
    assert [s["skill_count"] for s in overview["students"]] == [2, 0]
    assert [s["completed_topics"] for s in overview["students"]] == [2, 0]
    assert [c["student_count"] for c in overview["skill_counts"]] == [1, 1]


def test_old_topic_leaves_catalogue_unless_a_student_has_it(tmp_path):
    database = Database(tmp_path / "old.db")
    database.create_tables()
    with database.connect() as connection:
        connection.executemany(
            "INSERT INTO topic_catalogue (name, skill) VALUES (?, ?)",
            [("Old unused topic", "Old"), ("Old used topic", "Old")],
        )
        connection.execute(
            "INSERT INTO students (name, topic, status) "
            "VALUES ('Hasan', 'Python', 'Active')"
        )
        connection.execute(
            "INSERT INTO student_topics (student_id, topic_id, status) "
            "SELECT 1, id, 'Learning' FROM topic_catalogue "
            "WHERE name = 'Old used topic'"
        )
    database.fill_catalogue()
    with database.connect() as connection:
        names = {
            row["name"]
            for row in connection.execute("SELECT name FROM topic_catalogue")
        }
    assert names == set(TOPIC_CATALOGUE) | {"Old used topic"}
