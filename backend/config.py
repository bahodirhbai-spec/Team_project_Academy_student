"""Configuration: values that change depending on where the app runs.

Each setting has a default, which can be overridden without touching
the code, in this order (highest priority first):
    1. an environment variable, e.g.  ACADEMY_DATABASE_PATH=/tmp/x.db
    2. a line in the .env file in the project root
    3. the default written below

Business rules (score 0-100, allowed statuses) are NOT here: they are
part of the problem itself, so they live in models.py.
"""

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    """All configurable values of the application."""

    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env",
        env_prefix="ACADEMY_",  # ACADEMY_DATABASE_PATH -> database_path
    )

    database_path: Path = PROJECT_ROOT / "students.db"
    frontend_directory: Path = PROJECT_ROOT / "frontend"


@lru_cache
def get_settings() -> Settings:
    """Read the settings once and reuse them (lru_cache remembers)."""
    return Settings()
