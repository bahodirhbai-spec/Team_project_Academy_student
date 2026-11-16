"""Start the server with the host and port from config/settings.py.

Run from the project root with:
    python -m backend
"""

import uvicorn

from backend.config.settings import get_settings


def main() -> None:
    """Start uvicorn using the configured settings."""
    settings = get_settings()
    uvicorn.run(
        "backend.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.reload,
    )


if __name__ == "__main__":
    main()
