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
    MAX_SCORE,
    MAX_TEXT_LENGTH,
    MIN_SCORE,
    MIN_TEXT_LENGTH,
    StudentStatus,
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
