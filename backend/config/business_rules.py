"""Business rules: the rules of the problem itself.

This is the innermost layer (entities in Clean Architecture). It must
import nothing from the project and nothing about files, .env or
frameworks, so every other layer can depend on it safely.

Change a rule by editing this file. Rules are NOT read from .env,
because the database CHECK rules are built from them when the tables are
created: an existing students.db keeps the old rules, so delete it
after changing a rule here.
"""

from dataclasses import dataclass
from enum import Enum

MIN_SCORE = 0
MAX_SCORE = 100

MIN_TEXT_LENGTH = 1  # 1 = name and topic cannot be blank
MAX_TEXT_LENGTH = 100
MAX_DESCRIPTION_LENGTH = 500
MAX_URL_LENGTH = 500


class StudentStatus(str, Enum):
    """The existing student statuses (unchanged)."""

    ACTIVE = "Active"
    PAUSED = "Paused"
    COMPLETED = "Completed"


class TopicStatus(str, Enum):
    """Status of one learning record on a student's profile."""

    LEARNING = "Learning"
    COMPLETED = "Completed"


class ProjectStatus(str, Enum):
    """Status of one project record on a student's profile."""

    IN_PROGRESS = "In progress"
    COMPLETED = "Completed"


@dataclass(frozen=True)
class TopicDefinition:
    """One catalogue entry and the skill a completed topic generates."""

    key: str
    name: str
    skill: str


# The shared catalogue. Keys are stable identifiers: renaming a name or a
# skill does not break saved learning records. Several topics may map to
# the same skill; analytics merges them into one generated skill.
TOPIC_CATALOGUE: tuple[TopicDefinition, ...] = (
    TopicDefinition(
        "python-functions-collections",
        "Python functions and collections",
        "Python basics",
    ),
    TopicDefinition(
        "git-branches-prs",
        "Git branches and pull requests",
        "Git collaboration",
    ),
    TopicDefinition(
        "numpy-arrays-operations",
        "NumPy arrays and operations",
        "NumPy basics",
    ),
    TopicDefinition(
        "pandas-filtering-grouping",
        "pandas filtering and grouping",
        "Data manipulation with pandas",
    ),
    TopicDefinition(
        "fastapi-endpoints-validation",
        "FastAPI endpoints and validation",
        "REST API basics",
    ),
    # Intentionally mapped to skills above: proves duplicate skills are
    # merged instead of shown twice.
    TopicDefinition(
        "python-lists-dictionaries",
        "Python lists and dictionaries",
        "Python basics",
    ),
    TopicDefinition(
        "git-commits-remotes",
        "Git commits and remote repositories",
        "Git collaboration",
    ),
)

TOPIC_BY_KEY: dict[str, TopicDefinition] = {
    topic.key: topic for topic in TOPIC_CATALOGUE
}

# Fixed catalogue order keeps the NumPy matrix columns stable.
ALL_SKILLS: tuple[str, ...] = tuple(
    dict.fromkeys(topic.skill for topic in TOPIC_CATALOGUE)
)
