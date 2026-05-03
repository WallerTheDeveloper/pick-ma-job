"""Unified domain error hierarchy with built-in HTTP status codes.

All business-logic exceptions should inherit from ``DomainError``.
The global handler in ``main.py`` converts them to JSON responses automatically.
"""


class DomainError(Exception):
    """Base class for all domain/business-logic errors.

    Args:
        message: Human-readable error detail.
        http_status: HTTP status code to return (default 400).
    """

    def __init__(self, message: str, http_status: int = 400):
        super().__init__(message)
        self.http_status = http_status


class NotFoundError(DomainError):
    """Resource not found (HTTP 404)."""

    def __init__(self, message: str = "Not found"):
        super().__init__(message, http_status=404)


class ConflictError(DomainError):
    """Conflict with current state (HTTP 409)."""

    def __init__(self, message: str = "Conflict"):
        super().__init__(message, http_status=409)
