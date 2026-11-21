"""API endpoints for the profile and the skills summary. Owners: both.

These only collect data from the three repositories and hand it to
skills.py, which does the actual work.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, Request

from backend.models import Profile, SkillOverview
from backend.project_repository import ProjectRepository
from backend.repository import StudentRepository
from backend.skills import (
    build_profile,
    build_skill_overview,
    generate_skills,
)
from backend.topic_repository import TopicRepository

router = APIRouter(prefix="/api", tags=["profile"])


class Repositories:
    """The three repositories these endpoints read from."""

    def __init__(self, request: Request) -> None:
        database = request.app.state.database
        self.students = StudentRepository(database)
        self.topics = TopicRepository(database)
        self.projects = ProjectRepository(database)


AllRepositories = Annotated[Repositories, Depends(Repositories)]


@router.get("/students/{student_id}/profile", response_model=Profile)
def get_profile(student_id: int, repositories: AllRepositories) -> Profile:
    """A student with topics, projects and skills (404 if missing)."""
    student = repositories.students.get(student_id)
    skills = generate_skills(
        repositories.topics.records_frame(),
        repositories.projects.projects_frame(),
        repositories.projects.links_frame(),
    )
    return build_profile(
        student,
        repositories.topics.list_for_student(student_id),
        repositories.projects.list_for_student(student_id),
        skills,
    )


@router.get("/skills/overview", response_model=SkillOverview)
def get_skill_overview(repositories: AllRepositories) -> SkillOverview:
    """The NumPy skill matrix and totals for the main page."""
    return build_skill_overview(
        repositories.students.list_all(),
        repositories.topics.records_frame(),
        repositories.projects.projects_frame(),
        repositories.projects.links_frame(),
    )
