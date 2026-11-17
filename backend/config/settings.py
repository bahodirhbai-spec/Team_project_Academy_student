"""Settings: values that depend on WHERE the app runs.

This is the outermost layer ("Main" in Clean Architecture): it reads
the .env file and environment variables. Only the startup code
(main.py, __main__.py) and the web layer should import it, never the
business rules or the models.

Each value has a default below that can be overridden without touching
the code, in this order (highest priority first):
    1. an environment variable, e.g.  ACADEMY_PORT=9000
    2. a line in the .env file in the project root
    3. the default written below
"""

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# settings.py -> config/ -> backend/ -> project root
PROJECT_ROOT = Path(__file__).resolve().parents[2]


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
