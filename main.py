"""pick-ma-job — FastAPI application entry point.

Startup sequence:
1. Validate required environment variables (fail fast if any are missing).
2. Create the asyncpg connection pool and run the DB schema (idempotent).
3. Register all API routers.

The React SPA is served by nginx in production. In development, Vite's dev
server proxies API calls to this backend.
"""

import asyncio
import logging
import os
from contextlib import asynccontextmanager

import anthropic
import resend
import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from api.limiter import limiter
from core.llm_client import LLMClient
from api.routes.api_admin import router as api_admin_router
from api.routes.api_company_blacklist import router as api_company_blacklist_router
from api.routes.api_cv import router as api_cv_router
from api.routes.api_platforms import router as api_platforms_router
from api.routes.api_version import router as api_version_router
from api.routes.api_lists import router as api_lists_router
from api.routes.api_dashboard import router as api_dashboard_router
from api.routes.api_pipeline import router as api_pipeline_router
from api.routes.api_profile import router as api_profile_router
from api.routes.api_results import router as api_results_router
from api.routes.api_search_config import router as api_search_config_router
from api.routes.auth import router as auth_router
from db.pool import close_pool, create_pool
from repositories.magic_link import MagicLinkRepository
from repositories.session import SessionRepository
from services.run_manager import RunManager

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s — %(message)s",
)
logger = logging.getLogger(__name__)

_REQUIRED_ENV_VARS = [
    "DATABASE_URL",
    "MAGIC_LINK_SECRET",
    "RESEND_API_KEY",
    "EMAIL_FROM",
    "ANTHROPIC_API_KEY",
    "APIFY_API_TOKEN",
]


def validate_env() -> None:
    """Raise RuntimeError immediately if any required env vars are missing."""
    missing = [v for v in _REQUIRED_ENV_VARS if not os.environ.get(v)]
    if missing:
        raise RuntimeError(
            f"Missing required environment variables: {', '.join(missing)}\n"
            f"Copy .env.example to .env and fill in the values."
        )


async def _cleanup_loop(session_repo: SessionRepository, magic_link_repo: MagicLinkRepository) -> None:
    """Periodically delete expired sessions and magic links."""
    while True:
        await asyncio.sleep(3600)
        try:
            sessions_deleted = await session_repo.delete_expired()
            links_deleted = await magic_link_repo.delete_expired()
            logger.info("Cleanup: deleted %d sessions, %d magic links", sessions_deleted, links_deleted)
        except Exception:
            logger.exception("Cleanup task failed")


def _read_version() -> str:
    """Read version from VERSION file at repo root. Fail fast if missing."""
    version_path = os.path.join(os.path.dirname(__file__), "VERSION")
    try:
        with open(version_path) as f:
            return f.read().strip()
    except FileNotFoundError:
        raise RuntimeError(
            f"VERSION file not found at {version_path}. "
            "Ensure the VERSION file exists at the repo root."
        )


@asynccontextmanager
async def lifespan(app: FastAPI):
    validate_env()

    if os.environ.get("SKIP_EMAIL", "").lower() in ("1", "true", "yes"):
        logger.warning("SKIP_EMAIL is enabled — magic link emails will NOT be sent. Never use in production.")

    logger.info("Application version: %s", app.state.version)

    resend.api_key = os.environ["RESEND_API_KEY"]

    app.state.db_pool = await create_pool(os.environ["DATABASE_URL"])

    app.state.anthropic_client = anthropic.AsyncAnthropic(
        api_key=os.environ["ANTHROPIC_API_KEY"],
    )
    app.state.llm_client = LLMClient(
        client=app.state.anthropic_client,
        default_model="claude-haiku-4-5-20251001",
    )

    app.state.run_manager = RunManager(
        llm_client=app.state.llm_client,
        pool=app.state.db_pool,
    )
    await app.state.run_manager.reconcile_stale_runs()

    cleanup_task = asyncio.create_task(
        _cleanup_loop(
            SessionRepository(app.state.db_pool),
            MagicLinkRepository(app.state.db_pool),
        )
    )
    logger.info("Application started")

    yield

    cleanup_task.cancel()
    await close_pool(app.state.db_pool)
    logger.info("Application stopped")


def create_app() -> FastAPI:
    version = _read_version()
    app = FastAPI(
        title="pick-ma-job",
        version=version,
        lifespan=lifespan,
    )
    app.state.version = version

    # IP rate limiting
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    app.add_middleware(SlowAPIMiddleware)

    # CORS — allow the Vite dev server and production domain
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:5173",
            "https://pickmajob.cc",
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ── Auth routes (/auth/*) ────────────────────────────────────────────
    app.include_router(auth_router)

    # ── JSON API routes (/api/*) ─────────────────────────────────────────
    app.include_router(api_dashboard_router)
    app.include_router(api_results_router)
    app.include_router(api_profile_router)
    app.include_router(api_search_config_router)
    app.include_router(api_pipeline_router)
    app.include_router(api_lists_router)
    app.include_router(api_admin_router)
    app.include_router(api_company_blacklist_router)
    app.include_router(api_cv_router)
    app.include_router(api_platforms_router)
    app.include_router(api_version_router)

    return app


app = create_app()


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
