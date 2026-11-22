"""Pydantic models: the shape and validation rules of our data.

These models are the "data format agreement" between the frontend and
the backend. FastAPI uses them to validate incoming JSON and to build
the JSON responses.
"""

from enum import Enum
from typing import Any

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)

from backend.config.business_rules import (
    ALLOWED_LINK_PREFIXES,
    MAX_CONTRIBUTION_LENGTH,
    MAX_LINK_LENGTH,
    MAX_SCORE,
    MAX_TEXT_LENGTH,
    MIN_SCORE,
    MIN_TEXT_LENGTH,
    ProjectStatus,
    SkillLabel,
    StudentStatus,
    TopicStatus,
)


class StudentSort(str, Enum):
    """Allowed values of ?sort= when listing students."""

    NAME_ASC = "name_asc"
    NAME_DESC = "name_desc"


class StudentQuery(BaseModel):
    """Optional filters for GET /api/students."""

    # forbid: a typo like ?serch=ali must fail loudly instead of silently
    # returning every student.
    model_config = ConfigDict(
        str_strip_whitespace=True, frozen=True, extra="forbid"
    )

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


# ----- Projects (owner: Hasan) -----

TopicRecordIds = list[int]


def _check_link(link: str | None) -> str | None:
    """Empty means "no link"; otherwise it must be a web address."""
    if not link:
        return None
    if not link.startswith(ALLOWED_LINK_PREFIXES):
        raise ValueError("must start with http:// or https://")
    return link


def _remove_duplicate_ids(ids: TopicRecordIds) -> TopicRecordIds:
    """Linking the same topic twice means the same as linking it once."""
    return sorted(set(ids))


class ProjectCreate(BaseModel):
    """Data the frontend sends when adding a project to a student."""

    model_config = ConfigDict(str_strip_whitespace=True)

    name: str = Field(
        min_length=MIN_TEXT_LENGTH, max_length=MAX_TEXT_LENGTH
    )
    contribution: str = Field(
        min_length=MIN_TEXT_LENGTH,
        max_length=MAX_CONTRIBUTION_LENGTH,
        description="What this student personally did in the project.",
    )
    link: str | None = Field(default=None, max_length=MAX_LINK_LENGTH)
    status: ProjectStatus = ProjectStatus.IN_PROGRESS
    topic_record_ids: TopicRecordIds = Field(
        default_factory=list,
        description="IDs from student_topics that the project used.",
    )

    @field_validator("link")
    @classmethod
    def link_must_be_web_address(cls, value: str | None) -> str | None:
        """Reject links like "github.com/x" that are not clickable."""
        return _check_link(value)

    @field_validator("topic_record_ids")
    @classmethod
    def drop_duplicate_topics(cls, value: TopicRecordIds) -> TopicRecordIds:
        """Store each linked topic only once."""
        return _remove_duplicate_ids(value)


class ProjectUpdate(BaseModel):
    """Data the frontend sends when editing a project (PATCH).

    Every field is optional: only the fields that are sent get changed.
    Sending topic_record_ids replaces the whole list of linked topics.
    """

    model_config = ConfigDict(str_strip_whitespace=True)

    name: str | None = Field(
        default=None,
        min_length=MIN_TEXT_LENGTH,
        max_length=MAX_TEXT_LENGTH,
    )
    contribution: str | None = Field(
        default=None,
        min_length=MIN_TEXT_LENGTH,
        max_length=MAX_CONTRIBUTION_LENGTH,
    )
    link: str | None = Field(default=None, max_length=MAX_LINK_LENGTH)
    status: ProjectStatus | None = None
    topic_record_ids: TopicRecordIds | None = None

    @field_validator(
        "name", "contribution", "status", "topic_record_ids", mode="before"
    )
    @classmethod
    def reject_explicit_null(cls, value: Any) -> Any:
        """These may be left out, but never set to null.

        link is not in this list: null is how a link gets removed.
        """
        if value is None:
            raise ValueError("cannot be empty")
        return value

    @field_validator("link")
    @classmethod
    def link_must_be_web_address(cls, value: str | None) -> str | None:
        """Same link rule as when creating a project."""
        return _check_link(value)

    @field_validator("topic_record_ids")
    @classmethod
    def drop_duplicate_topics(
        cls, value: TopicRecordIds | None
    ) -> TopicRecordIds | None:
        """Same duplicate rule as when creating a project."""
        return None if value is None else _remove_duplicate_ids(value)

    @model_validator(mode="after")
    def require_at_least_one_field(self) -> "ProjectUpdate":
        """An update with no fields would do nothing, so reject it."""
        if not self.model_fields_set:
            raise ValueError(
                "send at least one of: name, contribution, link, "
                "status, topic_record_ids"
            )
        return self


class Project(BaseModel):
    """A project as stored in the database, with its linked topics."""

    id: int
    student_id: int
    name: str
    contribution: str
    link: str | None
    status: ProjectStatus
    topic_record_ids: TopicRecordIds


# ----- Topics (owner: Bahodirjon) -----

class CatalogueTopic(BaseModel):
    """One topic anyone can study, and the skill it teaches."""

    id: int
    name: str
    skill: str


class TopicRecordCreate(BaseModel):
    """Data the frontend sends when a student starts a topic."""

    topic_id: int = Field(description="ID from GET /api/topics.")
    status: TopicStatus = TopicStatus.LEARNING


class TopicRecordUpdate(BaseModel):
    """Data the frontend sends to change a topic's status (PATCH)."""

    status: TopicStatus


class TopicRecord(BaseModel):
    """One topic of one student, with the topic's name and skill."""

    id: int
    student_id: int
    topic_id: int
    topic_name: str
    skill: str
    status: TopicStatus


# ----- Skills and profile (owners: both) -----

class SkillProject(BaseModel):
    """A completed project that proves a skill was applied."""

    name: str
    link: str | None
    contribution: str = Field(
        description="What THIS student did in the project."
    )


class Skill(BaseModel):
    """A skill a student has. Calculated on every request, never saved.

    topics and projects are the evidence: the completed topics that
    teach the skill and the completed projects linked to them.
    """

    name: str
    label: SkillLabel
    topics: list[str] = Field(min_length=1)
    projects: list[SkillProject] = Field(default_factory=list)

    @model_validator(mode="after")
    def label_matches_projects(self) -> "Skill":
        """The label says APPLIED only when a project proves it."""
        is_applied = self.label == SkillLabel.APPLIED
        if is_applied != bool(self.projects):
            raise ValueError(
                "label must be 'Applied in a project' exactly when "
                "there is a supporting project"
            )
        return self


class Profile(BaseModel):
    """Everything the profile page shows, in one response."""

    student: Student
    topics: list[TopicRecord]
    projects: list[Project]
    skills: list[Skill]


class StudentProgress(BaseModel):
    """One row of the overview table (and one row of the matrix)."""

    student_id: int
    name: str
    completed_topics: int = Field(ge=0)
    completed_projects: int = Field(ge=0)
    skill_count: int = Field(ge=0)


class SkillCount(BaseModel):
    """How many students have one skill (one bar of the chart)."""

    skill: str
    student_count: int = Field(ge=0)


class SkillOverview(BaseModel):
    """Data for the "skills summary" section of the main page.

    matrix[row][column] is 1 when students[row] has skills[column].
    """

    skills: list[str]
    students: list[StudentProgress]
    matrix: list[list[int]]
    skill_counts: list[SkillCount]

    @model_validator(mode="after")
    def matrix_matches_rows_and_columns(self) -> "SkillOverview":
        """Catch a bug early: the matrix must fit the two lists."""
        if len(self.matrix) != len(self.students):
            raise ValueError("matrix needs one row per student")
        if any(len(row) != len(self.skills) for row in self.matrix):
            raise ValueError("matrix needs one column per skill")
        return self


class SkillSummary(BaseModel):
    """The extra progress tables under the skills section of the page.

    This is the restored summary view from PR #6, expressed with the
    response shapes the current dev branch already uses.
    """

    skills: list[str]
    matrix: list[list[int]]
    progress_per_student: list[StudentProgress]
    students_per_skill: list[SkillCount]


class ProjectSummary(BaseModel):
    """Project totals and how many students applied each skill."""

    total_projects: int = Field(ge=0)
    completed_projects: int = Field(ge=0)
    in_progress_projects: int = Field(ge=0)
    students_per_applied_skill: list[SkillCount]
