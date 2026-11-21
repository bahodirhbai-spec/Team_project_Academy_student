"""Application logic for projects and their topic links (Hasan)."""

from backend.database import Database
from backend.models import (
    ProjectCreate,
    ProjectSummary,
    ProjectUpdate,
    StudentProject,
)
from backend.project_analytics import (
    completed_project_frame,
    project_counts_frame,
    students_per_applied_skill,
    supporting_projects_by_skill,
)
from backend.project_repository import (
    InvalidTopicLinksError,
    ProjectNotFoundError,
    ProjectRepository,
)
from backend.repository import StudentNotFoundError, StudentRepository


def add_project(
    database: Database, student_id: int, new_project: ProjectCreate
) -> StudentProject:
    """Validate the student, then save the project and its links."""
    StudentRepository(database).get(student_id)  # 404 in the route layer
    return ProjectRepository(database).add(student_id, new_project)


def list_projects(database: Database, student_id: int) -> list[StudentProject]:
    """List one student's projects."""
    StudentRepository(database).get(student_id)
    return ProjectRepository(database).list_for_student(student_id)


def update_project(
    database: Database,
    student_id: int,
    project_id: int,
    changes: ProjectUpdate,
) -> StudentProject:
    """Patch a project including the set of related learning records."""
    StudentRepository(database).get(student_id)
    return ProjectRepository(database).update(
        student_id, project_id, changes
    )


def build_project_summary(database: Database) -> ProjectSummary:
    """Combine student, topic and project records into displayed counts."""
    students = StudentRepository(database).list_all()
    repository = ProjectRepository(database)
    projects = repository.list_all()
    topics = repository.list_topic_records()

    counts = project_counts_frame(students, projects)
    evidence = supporting_projects_by_skill(projects, topics)
    applied_counts = students_per_applied_skill(students, topics, evidence)
    completed_count = len(completed_project_frame(projects))

    return ProjectSummary(
        total_projects=len(projects),
        completed_projects=completed_count,
        in_progress_projects=len(projects) - completed_count,
        per_student=[
            {
                "student_id": int(row.student_id),
                "name": row.name,
                "total_projects": int(row.total_projects),
                "completed_projects": int(row.completed_projects),
            }
            for row in counts.itertuples(index=False)
        ],
        applied_skills=[
            {"skill": skill, "student_id": student_id, "projects": items}
            for (student_id, skill), items in sorted(evidence.items())
        ],
        students_per_applied_skill=[
            {"skill": skill, "count": count}
            for skill, count in applied_counts.items()
        ],
    )
