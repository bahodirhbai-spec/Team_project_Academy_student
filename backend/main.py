"""Application entry point: builds the FastAPI app.

Run from the project root with:
    uvicorn backend.main:app --reload
"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from backend.config import Settings, get_settings
from backend.database import Database
from backend.routes import router


def create_app(settings: Settings | None = None) -> FastAPI:
    """Build the app. Tests pass their own Settings (temporary DB)."""
    settings = settings or get_settings()
    database = Database(settings.database_path)

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
        StaticFiles(directory=settings.frontend_directory, html=True),
        name="frontend",
    )
    return app


app = create_app()
