"""pick-ma-job — FastAPI application entry point.

Startup sequence:
1. Validate required environment variables (fail fast if any are missing).
2. Create the asyncpg connection pool and run the DB schema (idempotent).
3. Mount the Jinja2 template engine on app.state.
4. Register all API routers.

The old single-user pipeline routes (/run, /status) are removed in this version.
They will be re-implemented as authenticated, per-user background tasks in Phase 4.
"""

import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path

import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from api.routes.auth import router as auth_router
from api.routes.dashboard import router as dashboard_router
from api.routes.pipeline import router as pipeline_router
from api.routes.profile import router as profile_router
from api.routes.results import router as results_router
from api.routes.search_config import router as search_config_router
from db.pool import close_pool, create_pool
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


@asynccontextmanager
async def lifespan(app: FastAPI):
    validate_env()

    app.state.db_pool = await create_pool(os.environ["DATABASE_URL"])
    app.state.templates = Jinja2Templates(
        directory=str(Path(__file__).parent / "templates")
    )
    app.state.run_manager = RunManager(anthropic_api_key=os.environ["ANTHROPIC_API_KEY"])
    logger.info("Application started")

    yield

    await close_pool(app.state.db_pool)
    logger.info("Application stopped")


def create_app() -> FastAPI:
    app = FastAPI(
        title="pick-ma-job",
        version="0.2.0",
        lifespan=lifespan,
    )

    app.include_router(dashboard_router)
    app.include_router(auth_router)
    app.include_router(profile_router)
    app.include_router(search_config_router)
    app.include_router(pipeline_router)
    app.include_router(results_router)

    static_dir = Path(__file__).parent / "static"
    if static_dir.exists():
        app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

    return app


app = create_app()


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
