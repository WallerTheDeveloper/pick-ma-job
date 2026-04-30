"""Structured JSON logging with automatic run_id / user_id propagation.

Call ``configure_logging()`` once at startup to replace the root logger's
handler with a JSON formatter and the context-aware filter.
"""

import json
import logging
import sys
from datetime import datetime, timezone

from core.context import run_id_var, user_id_var


class ContextFilter(logging.Filter):
    """Injects ``run_id`` and ``user_id`` from ``contextvars`` into every LogRecord."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.run_id = run_id_var.get()  # type: ignore[attr-defined]
        record.user_id = user_id_var.get()  # type: ignore[attr-defined]
        return True


class JSONFormatter(logging.Formatter):
    """Emit each log record as a single-line JSON object."""

    def format(self, record: logging.LogRecord) -> str:
        log_entry: dict = {
            "time": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "run_id": getattr(record, "run_id", "-"),
            "user_id": getattr(record, "user_id", "-"),
            "msg": record.getMessage(),
        }

        if record.exc_info and record.exc_info[1] is not None:
            log_entry["exc_info"] = self.formatException(record.exc_info)

        return json.dumps(log_entry, default=str)


def configure_logging(level: int = logging.INFO) -> None:
    """Replace the root logger's handler with structured JSON output."""
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JSONFormatter())
    handler.addFilter(ContextFilter())

    root = logging.getLogger()
    root.setLevel(level)
    root.handlers.clear()
    root.addHandler(handler)
