"""Business rules: the rules of the problem itself.

This is the innermost layer (entities in Clean Architecture). It must
import nothing from the project and nothing about files, .env or
frameworks, so every other layer can depend on it safely.

Change a rule by editing this file. Rules are NOT read from .env,
because the database CHECK rules are built from them when the table is
created: an existing students.db keeps the old rules, so delete it
after changing a rule here.
"""

from enum import Enum

MIN_SCORE = 0
MAX_SCORE = 100

MIN_TEXT_LENGTH = 1  # 1 = name and topic cannot be blank
MAX_TEXT_LENGTH = 100


class StudentStatus(str, Enum):
    """The only statuses a student is allowed to have."""

    ACTIVE = "Active"
    PAUSED = "Paused"
    COMPLETED = "Completed"


# ----- Projects (owner: Hasan) -----

MAX_CONTRIBUTION_LENGTH = 1000  # a few sentences about own work
MAX_LINK_LENGTH = 300
ALLOWED_LINK_SCHEMES = ("http", "https")


class ProjectStatus(str, Enum):
    """The only statuses a project is allowed to have."""

    IN_PROGRESS = "In progress"
    COMPLETED = "Completed"


# ----- Topics (owner: Bahodirjon) -----


class TopicStatus(str, Enum):
    """The only statuses a student's topic is allowed to have."""

    LEARNING = "Learning"
    COMPLETED = "Completed"


# Topic -> the skill it teaches. To add a topic, add one line here:
# the server copies this into the topic_catalogue table on startup.
# The first five lines are the mapping given in the assignment.
# Several topics may teach the same skill (see "REST API basics").
TOPIC_CATALOGUE: dict[str, str] = {
    "Python functions and collections": "Python basics",
    "Git branches and pull requests": "Git collaboration",
    "NumPy arrays and operations": "NumPy basics",
    "pandas filtering and grouping": "Data manipulation with pandas",
    "FastAPI endpoints and validation": "REST API basics",
    "Pydantic models": "REST API basics",
    "SQL and SQLite": "Databases",
    "HTML and CSS": "Web layout",
    "JavaScript fetch": "Frontend development",
    "pytest testing": "Automated testing",
}


# ----- Skills (owners: both) -----


class SkillLabel(str, Enum):
    """How strongly a student has a skill."""

    LEARNED = "Learned"  # finished a topic that teaches it
    APPLIED = "Applied in a project"  # ...and used it in a finished project
