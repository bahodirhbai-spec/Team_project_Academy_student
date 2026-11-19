"""Assemble a student profile and merge both analytics summaries.

Owner: both teammates. This is the integration point where Bahodirjon's
topic/matrix data and Hasan's project data are shown together.
"""

from backend.database import Database
from backend.models import ProfileSummary, SkillSummary, StudentProfile
from backend.project_analytics import completed_project_frame
from backend.project_repository import ProjectRepository
from backend.project_service import build_project_summary
from backend.repository import StudentRepository
from backend.skill_analytics import generate_skills
from backend.topic_analytics import completed_topic_frame
from backend.topic_repository import TopicRepository
from backend.topic_service import build_skill_summary as build_topic_summary


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


def build_combined_skill_summary(database) -> SkillSummary:
    """Add Hasan's completed-project counts to Bahodirjon's matrix summary."""
    summary = build_topic_summary(database)
    project_summary = build_project_summary(database)
    completed_by_student = {
        row.student_id: row.completed_projects
        for row in project_summary.per_student
    }
    summary.progress_per_student = [
        row.model_copy(
            update={
                "completed_projects": completed_by_student.get(
                    row.student_id, 0
                )
            }
        )
        for row in summary.progress_per_student
    ]
    return summary
