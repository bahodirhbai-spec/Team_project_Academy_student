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
