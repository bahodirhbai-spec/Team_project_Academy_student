"""Application entry point: builds the FastAPI app.

Run from the project root with:
    uvicorn backend.main:app --reload
"""

from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from backend.config.settings import Settings, get_settings
from backend.database import Database
from backend.errors import (
    AppError,
    ConflictError,
    InvalidReferenceError,
    NotFoundError,
)
from backend.profile_routes import router as profile_router
from backend.project_routes import router as project_router
from backend.routes import router
from backend.topic_routes import router as topic_router

ErrorHandler = Callable[[Request, Exception], Awaitable[JSONResponse]]

# Which HTTP status each of our own errors becomes. The inner layers
# only know the error names; this is the one place that knows HTTP.
ERROR_STATUS_CODES: dict[type[AppError], int] = {
    NotFoundError: status.HTTP_404_NOT_FOUND,
    ConflictError: status.HTTP_409_CONFLICT,
    InvalidReferenceError: status.HTTP_422_UNPROCESSABLE_CONTENT,
}


def create_app(settings: Settings | None = None) -> FastAPI:
    """Build the app. Tests pass their own Settings (temporary DB)."""
    settings = settings or get_settings()
    database = Database(settings.database_path)

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        database.create_tables()  # runs once when the server starts
        database.fill_catalogue()  # copy TOPIC_CATALOGUE into the table
        yield

    app = FastAPI(title=settings.app_title, lifespan=lifespan)
    app.state.settings = settings
    app.state.database = database
    app.include_router(router)
    app.include_router(topic_router)
    app.include_router(project_router)
    app.include_router(profile_router)
    _register_error_handlers(app)
    # Serve index.html, index.css and app.js at "/".
    # Mounted last, so the /api routes above take priority.
    app.mount(
        "/",
        StaticFiles(directory=settings.frontend_directory, html=True),
        name="frontend",
    )
    return app


def _register_error_handlers(app: FastAPI) -> None:
    """Tell FastAPI how to answer when one of our errors is raised."""
    for error_type, status_code in ERROR_STATUS_CODES.items():
        app.add_exception_handler(error_type, _error_handler(status_code))


def _error_handler(status_code: int) -> ErrorHandler:
    """Build a handler that sends {"detail": message} with this status.

    {"detail": ...} is the same shape FastAPI uses for its own errors,
    so the frontend can show every error the same way.
    """
    async def handle(request: Request, error: Exception) -> JSONResponse:
        return JSONResponse(
            status_code=status_code, content={"detail": str(error)}
        )

    return handle


app = create_app()
