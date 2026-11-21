"""Errors the business code raises when a request cannot be done.

They say WHAT went wrong, never which HTTP status to send: that is
the web layer's job (see main.py). This keeps the inner layers free
of any FastAPI or HTTP knowledge (Clean Architecture).
"""


class AppError(Exception):
    """Base class, so main.py can recognise all of our own errors."""


class NotFoundError(AppError):
    """The requested ID does not exist (sent as 404)."""


class ConflictError(AppError):
    """The thing already exists, e.g. a topic added twice (sent as 409)."""


class InvalidReferenceError(AppError):
    """An ID points at something not allowed, e.g. another student's
    topic (sent as 422)."""
