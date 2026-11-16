"""All configuration of the application lives in this one file.

Part 1 - Settings
    Values that depend on WHERE the app runs (port, database file...).
    Each has a default below that can be overridden without touching
    the code, in this order (highest priority first):
        1. an environment variable, e.g.  ACADEMY_PORT=9000
        2. a line in the .env file in the project root
        3. the default written below

Part 2 - Business rules
    Rules of the problem itself (score range, allowed statuses...).
    Change them by editing this file. They are NOT read from .env,
    because the database CHECK rules are built from them when the table
    is created: an existing students.db keeps the old rules, so delete
    it after changing a rule here.
"""

from enum import Enum
from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parent.parent


# ===== Part 1: Settings =====

class Settings(BaseSettings):
    """Values that can change per computer, via .env or environment."""

    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env",
        env_prefix="ACADEMY_",  # ACADEMY_DATABASE_PATH -> database_path
    )

    # Application
    app_title: str = "Academy Students"

    # Server (used by: python -m backend)
    host: str = "127.0.0.1"
    port: int = Field(default=8000, ge=1, le=65535)
    reload: bool = True  # restart automatically when code changes

    # Files
    database_path: Path = PROJECT_ROOT / "students.db"
    frontend_directory: Path = PROJECT_ROOT / "frontend"

    # Display
    average_decimals: int = Field(default=2, ge=0)


@lru_cache
def get_settings() -> Settings:
    """Read the settings once and reuse them (lru_cache remembers)."""
    return Settings()


# ===== Part 2: Business rules =====

MIN_SCORE = 0
MAX_SCORE = 100

MIN_TEXT_LENGTH = 1  # 1 = name and topic cannot be blank
MAX_TEXT_LENGTH = 100


class StudentStatus(str, Enum):
    """The only statuses a student is allowed to have."""

    ACTIVE = "Active"
    PAUSED = "Paused"
    COMPLETED = "Completed"
