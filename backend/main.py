"""Application entry point: builds the FastAPI app.

Run from the project root with:
    uvicorn backend.main:app --reload
"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from backend.database import DEFAULT_DATABASE_PATH, PROJECT_ROOT, Database
from backend.routes import router

FRONTEND_DIRECTORY = PROJECT_ROOT / "frontend"


def create_app(database_path: Path = DEFAULT_DATABASE_PATH) -> FastAPI:
    """Build the app. Tests pass a different path for a temporary DB."""
    database = Database(database_path)

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        database.create_tables()  # runs once when the server starts
        yield

    app = FastAPI(title="Academy Students", lifespan=lifespan)
    app.state.database = database
    app.include_router(router)
    # Serve index.html, index.css and app.js at "/".
    # Mounted last, so the /api routes above take priority.
    app.mount(
        "/",
        StaticFiles(directory=FRONTEND_DIRECTORY, html=True),
        name="frontend",
    )
    return app


app = create_app()
