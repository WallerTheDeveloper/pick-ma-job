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

import asyncio
import json
import logging
import os
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path

import uvicorn
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from dotenv import load_dotenv
from fastapi import FastAPI, Header, HTTPException

from core.dedup import DedupStore
from core.evaluator import Evaluator
from core.notifier import Notifier
from core.sheets import SheetsClient
from scrapers.registry import get_scraper

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s — %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(fastapi_app: FastAPI):
    await startup()
    yield
    await shutdown()


app = FastAPI(title="pick-ma-job", version="0.1.0", lifespan=lifespan)

# ---------------------------------------------------------------------------
# Shared state — populated during startup
# ---------------------------------------------------------------------------

_scheduler: AsyncIOScheduler | None = None
_evaluator: Evaluator | None = None
_dedup: DedupStore | None = None
_sheets: SheetsClient | None = None
_notifier: Notifier | None = None
_settings: dict = {}
_platform_configs: dict[str, dict] = {}   # platform slug → loaded platform config
_prompt_contexts: dict[str, dict] = {}    # platform slug → loaded prompt context
_last_run: dict[str, str] = {}            # platform slug → ISO timestamp


# ---------------------------------------------------------------------------
# Startup / shutdown
# ---------------------------------------------------------------------------


async def startup() -> None:
    """Load configs, initialise shared clients, and start the scheduler."""
    global _scheduler, _evaluator, _dedup, _sheets, _notifier, _settings

    _settings = load_config("configs/settings.json")
    base_profile = load_config("configs/prompts/base_profile.json")

    # Load all platform configs and their matching prompt contexts
    for path in Path("configs/platforms").glob("*.json"):
        if path.stem.startswith("_"):
            continue
        cfg = load_config(str(path))
        if not cfg.get("enabled", False):
            logger.info("Platform '%s' is disabled — skipping", path.stem)
            continue
        platform = cfg["platform"]
        _platform_configs[platform] = cfg

        context_path = f"configs/prompts/{platform}_context.json"
        if not Path(context_path).exists():
            raise FileNotFoundError(f"Missing prompt context for platform '{platform}': {context_path}")
        _prompt_contexts[platform] = load_config(context_path)
        logger.info("Loaded platform config: %s", platform)

    # Initialise shared clients
    _evaluator = Evaluator(base_profile, _settings, api_key=os.environ["ANTHROPIC_API_KEY"])
    _dedup = DedupStore(_settings["dedup_db_path"])

    _sheets = SheetsClient(
        spreadsheet_id=_settings["sheets"]["spreadsheet_id"],
        service_account_path=os.environ["GOOGLE_SERVICE_ACCOUNT_JSON_PATH"],
    )

    _notifier = Notifier(
        bot_token=os.environ["TELEGRAM_BOT_TOKEN"],
        chat_id=os.environ["TELEGRAM_CHAT_ID"],
        alert_threshold=_settings["alert_threshold"],
    )

    # Register APScheduler cron jobs
    _scheduler = AsyncIOScheduler()
    for platform, cfg in _platform_configs.items():
        cron_expr = cfg["schedule"]["cron"]
        cron_fields = _parse_cron(cron_expr)
        _scheduler.add_job(
            run_platform,
            trigger="cron",
            kwargs={"platform_name": platform},
            id=f"job_{platform}",
            **cron_fields,
        )
        logger.info("Scheduled %s with cron '%s'", platform, cron_expr)

    _scheduler.start()
    logger.info("Scheduler started with %d platform(s)", len(_platform_configs))


async def shutdown() -> None:
    """Gracefully stop the scheduler and close the dedup DB connection."""
    if _scheduler and _scheduler.running:
        _scheduler.shutdown(wait=False)
        logger.info("Scheduler stopped")
    if _dedup:
        _dedup.close()
        logger.info("DedupStore closed")


# ---------------------------------------------------------------------------
# API routes
# ---------------------------------------------------------------------------


@app.post("/run")
async def run(
    platform: str | None = None,
    x_api_key: str | None = Header(default=None),
) -> dict:
    """Manually trigger a pipeline run for one or all enabled platforms.

    Args:
        platform: Platform slug to run (e.g. ``upwork``). If omitted, runs all.

    Returns:
        A dict with ``{"status": "ok", "platforms": [...]}`` on success.

    Raises:
        HTTPException 401: Missing or invalid ``X-API-Key``.
        HTTPException 404: Unknown platform slug.
    """
    _require_api_key(x_api_key)

    if platform is not None:
        if platform not in _platform_configs:
            raise HTTPException(status_code=404, detail=f"Unknown platform: {platform!r}")
        platforms_to_run = [platform]
    else:
        platforms_to_run = list(_platform_configs.keys())

    summaries = await asyncio.gather(
        *[run_platform(p) for p in platforms_to_run],
        return_exceptions=True,
    )

    results = []
    for p, summary in zip(platforms_to_run, summaries):
        if isinstance(summary, Exception):
            logger.error("Platform '%s' run failed: %s", p, summary)
            results.append({"platform": p, "error": str(summary)})
        else:
            results.append(summary)

    return {"status": "ok", "platforms": results}


@app.get("/status")
async def status() -> dict:
    """Return scheduler health and last run times per platform.

    Returns:
        A dict with ``{"scheduler": "running"|"stopped", "platforms": {...}}``.
    """
    scheduler_status = "running" if (_scheduler and _scheduler.running) else "stopped"
    platforms_status = {
        p: {"last_run": _last_run.get(p, "never"), "enabled": True}
        for p in _platform_configs
    }
    return {"scheduler": scheduler_status, "platforms": platforms_status}


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
    logger.info("Starting pipeline run for platform='%s'", platform_name)

    platform_config = _platform_configs[platform_name]
    platform_context = _prompt_contexts[platform_name]
    exclude_keywords: list[str] = [
        kw.lower()
        for kw in _settings.get("pre_filters", {}).get("exclude_title_keywords", [])
    ]

    scraper = get_scraper(platform_name)
    jobs = await scraper.fetch_jobs(platform_config)

    fetched = len(jobs)
    skipped_dedup = 0
    skipped_filter = 0
    evaluated = 0
    alerted = 0

    for job in jobs:
        # Deduplication
        if _dedup.is_seen(job.id, platform_name):
            skipped_dedup += 1
            continue

        # Keyword pre-filter
        title_lower = job.title.lower()
        if any(kw in title_lower for kw in exclude_keywords):
            logger.debug("Filtered out job '%s' (title keyword match)", job.title)
            skipped_filter += 1
            _dedup.mark_seen(job.id, platform_name)
            continue

        # Evaluate
        try:
            result = await _evaluator.evaluate(job, platform_context)
        except Exception:
            logger.exception("Evaluation failed for job %s — skipping", job.id)
            continue

        # Persist to Sheets
        try:
            _sheets.append_row(job, result, platform_config)
        except Exception:
            logger.exception("Failed to append row for job %s to Sheets", job.id)

        # Telegram alert
        try:
            _notifier.notify(job, result)
            if result.relevancy_score >= _settings["alert_threshold"]:
                alerted += 1
        except Exception:
            logger.exception("Failed to send Telegram alert for job %s", job.id)

        _dedup.mark_seen(job.id, platform_name)
        evaluated += 1

    _last_run[platform_name] = datetime.now(timezone.utc).isoformat()

    summary = {
        "platform": platform_name,
        "fetched": fetched,
        "evaluated": evaluated,
        "skipped_dedup": skipped_dedup,
        "skipped_filter": skipped_filter,
        "alerted": alerted,
    }
    logger.info("Run complete: %s", summary)
    return summary


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
    with open(path) as f:
        raw = json.load(f)
    return _resolve_env_vars(raw)


def _resolve_env_vars(obj: object) -> object:
    """Recursively replace ``$VAR_NAME`` strings with environment variable values."""
    if isinstance(obj, dict):
        return {k: _resolve_env_vars(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_resolve_env_vars(item) for item in obj]
    if isinstance(obj, str) and obj.startswith("$"):
        var_name = obj[1:]
        value = os.environ.get(var_name)
        if value is None:
            raise KeyError(f"Environment variable '{var_name}' is not set (referenced in config as '{obj}')")
        return value
    return obj


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _require_api_key(provided: str | None) -> None:
    """Raise HTTP 401 if the provided API key doesn't match the configured one."""
    expected = os.environ.get("API_KEY")
    if not expected or provided != expected:
        raise HTTPException(status_code=401, detail="Missing or invalid X-API-Key")


def _parse_cron(expr: str) -> dict:
    """Parse a 5-field cron expression into APScheduler keyword arguments.

    Args:
        expr: A standard cron string e.g. ``"0 */6 * * *"``.

    Returns:
        Dict with keys ``minute``, ``hour``, ``day``, ``month``, ``day_of_week``.

    Raises:
        ValueError: If the expression does not have exactly 5 fields.
    """
    fields = expr.split()
    if len(fields) != 5:
        raise ValueError(f"Expected 5-field cron expression, got: {expr!r}")
    minute, hour, day, month, day_of_week = fields
    return {
        "minute": minute,
        "hour": hour,
        "day": day,
        "month": month,
        "day_of_week": day_of_week,
    }


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=False)
