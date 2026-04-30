"""Context variables for structured logging across async tasks.

Each pipeline background task sets ``run_id_var`` and ``user_id_var``
so that every log line emitted during that run is automatically tagged.
"""

import contextvars

run_id_var: contextvars.ContextVar[str] = contextvars.ContextVar("run_id", default="-")
user_id_var: contextvars.ContextVar[str] = contextvars.ContextVar("user_id", default="-")
