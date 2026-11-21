"""Assemble a student profile from saved records.

Owner: both teammates. This combines topic and project data and calculates
the generated skill labels shown on the profile page.
"""

from backend.database import Database
from backend.models import ProfileSummary, StudentProfile
from backend.project_analytics import completed_project_frame
from backend.project_repository import ProjectRepository
from backend.repository import StudentRepository
from backend.skill_analytics import generate_skills
from backend.topic_analytics import completed_topic_frame
from backend.topic_repository import TopicRepository


def get_profile(database: Database, student_id: int) -> StudentProfile:
    """Return current saved records and labels calculated from them."""
    student_repository = StudentRepository(database)
    student = student_repository.get(student_id)
    students = student_repository.list_all()
    topics = TopicRepository(database).list_for_student(student_id)
    projects = ProjectRepository(database).list_for_student(student_id)
    skills = generate_skills(student_id, topics, projects, students)

    return StudentProfile(
        student=student,
        topics=topics,
        projects=projects,
        skills=skills,
        summary=ProfileSummary(
            completed_topics=len(completed_topic_frame(topics)),
            completed_projects=len(completed_project_frame(projects)),
            learned_skills=len(skills),
        ),
    )
