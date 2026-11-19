"""Pydantic models: the shape and validation rules of our data.

These models are the "data format agreement" between the frontend and
the backend (see docs/data-contract.md). FastAPI uses them to validate
incoming JSON and to build the JSON responses.
"""

from enum import Enum
from typing import Any
from urllib.parse import urlparse

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)

from backend.config.business_rules import (
    MAX_DESCRIPTION_LENGTH,
    MAX_SCORE,
    MAX_TEXT_LENGTH,
    MAX_URL_LENGTH,
    MIN_SCORE,
    MIN_TEXT_LENGTH,
    ProjectStatus,
    StudentStatus,
    TopicStatus,
)


class StudentSort(str, Enum):
    """Allowed values of ?sort= when listing students."""

    NAME_ASC = "name_asc"
    NAME_DESC = "name_desc"


class SkillLabel(str, Enum):
    """How strongly a student has demonstrated a generated skill."""

    LEARNED = "Learned"
    APPLIED = "Applied in a project"


class StudentQuery(BaseModel):
    """Optional filters for GET /api/students."""

    model_config = ConfigDict(str_strip_whitespace=True, frozen=True)

    status: StudentStatus | None = None
    search: str | None = Field(default=None, max_length=MAX_TEXT_LENGTH)
    sort: StudentSort | None = None

    @field_validator("search")
    @classmethod
    def blank_search_means_no_search(cls, value: str | None) -> str | None:
        """An empty search box shows every student, not none."""
        return value or None


class StudentCreate(BaseModel):
    """Data the frontend sends when adding a new student."""

    # Strip spaces first, so "   " becomes "" and fails min_length.
    model_config = ConfigDict(str_strip_whitespace=True)

    name: str = Field(
        min_length=MIN_TEXT_LENGTH, max_length=MAX_TEXT_LENGTH
    )
    topic: str = Field(
        min_length=MIN_TEXT_LENGTH, max_length=MAX_TEXT_LENGTH
    )
    status: StudentStatus
    score: int | None = Field(default=None, ge=MIN_SCORE, le=MAX_SCORE)


class StudentUpdate(BaseModel):
    """Data the frontend sends when updating a student (PATCH).

    Every field is optional: only the fields that are sent get changed.
    """

    model_config = ConfigDict(str_strip_whitespace=True)

    topic: str | None = Field(
        default=None,
        min_length=MIN_TEXT_LENGTH,
        max_length=MAX_TEXT_LENGTH,
    )
    status: StudentStatus | None = None
    score: int | None = Field(default=None, ge=MIN_SCORE, le=MAX_SCORE)

    @field_validator("topic", "status", mode="before")
    @classmethod
    def reject_explicit_null(cls, value: Any) -> Any:
        """Topic and status may be left out, but never set to null."""
        if value is None:
            raise ValueError("cannot be empty")
        return value

    @model_validator(mode="after")
    def require_at_least_one_field(self) -> "StudentUpdate":
        """An update with no fields would do nothing, so reject it."""
        if not self.model_fields_set:
            raise ValueError("send at least one of: topic, status, score")
        return self


class Student(StudentCreate):
    """A student as stored in the database (it now has an ID)."""

    id: int


class Summary(BaseModel):
    """Numbers shown in the summary boxes on the webpage."""

    total_students: int
    active_students: int
    average_score: float | None  # None means "No scores yet."


# ----- Topic catalogue and learning records (Bahodirjon) -----


class TopicCatalogueItem(BaseModel):
    """One read-only entry from the shared catalogue."""

    model_config = ConfigDict(frozen=True)

    key: str
    name: str
    skill: str


class TopicCreate(BaseModel):
    """Add a catalogue topic to a student's learning records."""

    model_config = ConfigDict(str_strip_whitespace=True)

    topic_key: str = Field(
        min_length=MIN_TEXT_LENGTH, max_length=MAX_TEXT_LENGTH
    )
    status: TopicStatus


class TopicStatusUpdate(BaseModel):
    """Change only the status of an existing learning record."""

    model_config = ConfigDict(str_strip_whitespace=True)

    status: TopicStatus


class StudentTopic(BaseModel):
    """A learning record as returned by the API."""

    id: int
    student_id: int
    topic_key: str
    topic_name: str
    skill: str
    status: TopicStatus


# ----- Projects and topic links (Hasan) -----


def validate_repository_link(value: str) -> str:
    """Accept only http(s) URLs, so links are safe to put in <a href>."""
    parsed = urlparse(value)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError("must be an http:// or https:// URL")
    return value


class ProjectCreate(BaseModel):
    """Add a project and link it to the student's own learning records."""

    model_config = ConfigDict(str_strip_whitespace=True)

    title: str = Field(
        min_length=MIN_TEXT_LENGTH, max_length=MAX_TEXT_LENGTH
    )
    description: str = Field(
        min_length=MIN_TEXT_LENGTH, max_length=MAX_DESCRIPTION_LENGTH
    )
    contribution: str = Field(
        min_length=MIN_TEXT_LENGTH, max_length=MAX_DESCRIPTION_LENGTH
    )
    repository_link: str = Field(
        min_length=MIN_TEXT_LENGTH, max_length=MAX_URL_LENGTH
    )
    status: ProjectStatus
    topic_ids: list[int] = Field(default_factory=list)

    @field_validator("repository_link")
    @classmethod
    def check_link(cls, value: str) -> str:
        return validate_repository_link(value)


class ProjectUpdate(BaseModel):
    """Patch any project field; omitted fields are left unchanged."""

    model_config = ConfigDict(str_strip_whitespace=True)

    title: str | None = Field(
        default=None,
        min_length=MIN_TEXT_LENGTH,
        max_length=MAX_TEXT_LENGTH,
    )
    description: str | None = Field(
        default=None,
        min_length=MIN_TEXT_LENGTH,
        max_length=MAX_DESCRIPTION_LENGTH,
    )
    contribution: str | None = Field(
        default=None,
        min_length=MIN_TEXT_LENGTH,
        max_length=MAX_DESCRIPTION_LENGTH,
    )
    repository_link: str | None = Field(
        default=None,
        min_length=MIN_TEXT_LENGTH,
        max_length=MAX_URL_LENGTH,
    )
    status: ProjectStatus | None = None
    topic_ids: list[int] | None = None

    @field_validator(
        "title",
        "description",
        "contribution",
        "repository_link",
        "status",
        "topic_ids",
        mode="before",
    )
    @classmethod
    def reject_explicit_null(cls, value: Any) -> Any:
        """Fields may be left out, but not explicitly set to null."""
        if value is None:
            raise ValueError("cannot be empty")
        return value

    @field_validator("repository_link")
    @classmethod
    def check_link(cls, value: str | None) -> str | None:
        return validate_repository_link(value) if value is not None else None

    @model_validator(mode="after")
    def require_at_least_one_field(self) -> "ProjectUpdate":
        if not self.model_fields_set:
            raise ValueError("send at least one project field to change")
        return self


class StudentProject(BaseModel):
    """A project as returned by the API, with its own topic links."""

    id: int
    student_id: int
    title: str
    description: str
    contribution: str
    repository_link: str
    status: ProjectStatus
    topic_ids: list[int]


# ----- Generated profile and analytics views (together) -----


class SupportingTopic(BaseModel):
    """A completed topic that supports one generated skill."""

    id: int
    name: str
    status: TopicStatus


class SupportingProject(BaseModel):
    """A completed project that proves a generated skill was applied."""

    id: int
    title: str
    contribution: str
    repository_link: str


class GeneratedSkill(BaseModel):
    """A skill calculated from current saved records."""

    name: str
    label: SkillLabel
    topics: list[SupportingTopic]
    projects: list[SupportingProject]


class ProfileSummary(BaseModel):
    """Counts shown at the top of a student profile."""

    completed_topics: int
    completed_projects: int
    learned_skills: int


class StudentProfile(BaseModel):
    """Everything shown by the View Profile page."""

    student: Student
    topics: list[StudentTopic]
    projects: list[StudentProject]
    skills: list[GeneratedSkill]
    summary: ProfileSummary


class SkillStudent(BaseModel):
    """One row label of the NumPy student–skill matrix."""

    student_id: int
    name: str


class LearnedSkillsCount(BaseModel):
    """Number of 1s in one matrix row."""

    student_id: int
    name: str
    count: int


class StudentsPerSkill(BaseModel):
    """Number of 1s in one matrix column."""

    skill: str
    count: int


# ----- Project summaries (Hasan) -----


class StudentProjectCount(BaseModel):
    """pandas project summary for one student."""

    student_id: int
    name: str
    total_projects: int
    completed_projects: int


class AppliedSkillEvidence(BaseModel):
    """Completed projects that prove a student applied one skill."""

    skill: str
    student_id: int
    projects: list[SupportingProject]


class ProjectSummary(BaseModel):
    """Global project counts and skill evidence."""

    total_projects: int
    completed_projects: int
    in_progress_projects: int
    per_student: list[StudentProjectCount]
    applied_skills: list[AppliedSkillEvidence]
    students_per_applied_skill: list[StudentsPerSkill]


class StudentProgress(BaseModel):
    """pandas summary of completed topics and projects per student."""

    student_id: int
    name: str
    completed_topics: int
    completed_projects: int
    learned_skills: int


class SkillSummary(BaseModel):
    """The two summaries displayed on the website."""

    students: list[SkillStudent]
    skills: list[str]
    matrix: list[list[int]]
    learned_skills_per_student: list[LearnedSkillsCount]
    students_per_skill: list[StudentsPerSkill]
    progress_per_student: list[StudentProgress]
