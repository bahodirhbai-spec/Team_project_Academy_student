"""Application entry point: builds the FastAPI app.

Run from the project root with:
    uvicorn backend.main:app --reload
"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from backend.config.settings import Settings, get_settings
from backend.database import Database
from backend.profile_routes import router as profile_router
from backend.project_routes import router as project_router
from backend.routes import router
from backend.topic_routes import router as topic_router


def create_app(settings: Settings | None = None) -> FastAPI:
    """Build the app. Tests pass their own Settings (temporary DB)."""
    settings = settings or get_settings()
    database = Database(settings.database_path)

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        database.create_tables()  # runs once when the server starts
        yield

    app = FastAPI(title=settings.app_title, lifespan=lifespan)
    app.state.settings = settings
    app.state.database = database
    app.include_router(router)
    app.include_router(topic_router)
    app.include_router(project_router)
    app.include_router(profile_router)
    # Serve index.html, index.css and app.js at "/".
    # Mounted last, so the /api routes above take priority.
    app.mount(
        "/",
        StaticFiles(directory=settings.frontend_directory, html=True),
        name="frontend",
    )
    return app


app = create_app()
