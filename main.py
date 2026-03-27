"""Entry point — FastAPI app, APScheduler cron jobs, and pipeline orchestration.

Startup sequence:
1. Load all configs from ``configs/`` and secrets from ``.env``.
2. Initialize shared clients: Evaluator, DedupStore, SheetsClient, Notifier.
3. Register APScheduler jobs for each enabled platform (cron from platform config).
4. Start the FastAPI app via uvicorn.

Endpoints:
- ``POST /run?platform=<name>`` — trigger a single platform run immediately.
- ``POST /run`` — trigger all enabled platforms.
- ``GET  /status`` — return scheduler status and last run times.

All endpoints require the ``X-API-Key`` header matching the ``API_KEY`` env var.
"""

import logging

import uvicorn
from fastapi import FastAPI

logger = logging.getLogger(__name__)

app = FastAPI(title="pick-ma-job", version="0.1.0")


# ---------------------------------------------------------------------------
# Startup / shutdown
# ---------------------------------------------------------------------------


@app.on_event("startup")
async def startup() -> None:
    """Load configs, initialise shared clients, and start the scheduler."""
    ...


@app.on_event("shutdown")
async def shutdown() -> None:
    """Gracefully stop the scheduler and close the dedup DB connection."""
    ...


# ---------------------------------------------------------------------------
# API routes
# ---------------------------------------------------------------------------


@app.post("/run")
async def run(platform: str | None = None) -> dict:
    """Manually trigger a pipeline run for one or all enabled platforms.

    Args:
        platform: Platform slug to run (e.g. ``upwork``). If omitted, runs all.

    Returns:
        A dict with ``{"status": "ok", "platforms": [...]}`` on success.

    Raises:
        HTTPException 401: Missing or invalid ``X-API-Key``.
        HTTPException 404: Unknown platform slug.
    """
    ...


@app.get("/status")
async def status() -> dict:
    """Return scheduler health and last run times per platform.

    Returns:
        A dict with ``{"scheduler": "running"|"stopped", "platforms": {...}}``.
    """
    ...


# ---------------------------------------------------------------------------
# Core orchestration
# ---------------------------------------------------------------------------


async def run_platform(platform_name: str) -> dict:
    """Execute the full pipeline for a single platform.

    Data flow:
    1. Load platform config + prompt context.
    2. Fetch jobs via the platform scraper.
    3. Deduplicate against SQLite store (skip seen IDs).
    4. Apply keyword pre-filter (exclude_title_keywords from settings.json).
    5. For each remaining job: evaluate → append to Sheets → notify if threshold met.
    6. Return a run summary dict.

    Args:
        platform_name: The platform slug (e.g. ``"upwork"``).

    Returns:
        A summary dict: ``{"platform": str, "fetched": int, "evaluated": int,
        "skipped_dedup": int, "skipped_filter": int, "alerted": int}``.
    """
    ...


def load_config(path: str) -> dict:
    """Load and return a JSON config file, resolving ``$ENV_VAR`` references.

    Recursively walks the config dict and replaces any string values matching
    ``$VAR_NAME`` with the corresponding environment variable value.

    Args:
        path: Path to the JSON file.

    Returns:
        The parsed config dict with env vars resolved.

    Raises:
        FileNotFoundError: If the config file does not exist.
        KeyError: If a referenced env var is not set.
    """
    ...


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=False)
