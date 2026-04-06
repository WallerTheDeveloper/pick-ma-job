"""pick-ma-job — FastAPI application entry point.

Startup sequence:
1. Validate required environment variables (fail fast if any are missing).
2. Create the asyncpg connection pool and run the DB schema (idempotent).
3. Register all API routers.

The React SPA is served by nginx in production. In development, Vite's dev
server proxies API calls to this backend.
"""

import logging
import os
from contextlib import asynccontextmanager

import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routes.api_admin import router as api_admin_router
from api.routes.api_dashboard import router as api_dashboard_router
from api.routes.api_pipeline import router as api_pipeline_router
from api.routes.api_profile import router as api_profile_router
from api.routes.api_results import router as api_results_router
from api.routes.api_search_config import router as api_search_config_router
from api.routes.auth import router as auth_router
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
    app.state.run_manager = RunManager(
        anthropic_api_key=os.environ["ANTHROPIC_API_KEY"],
        pool=app.state.db_pool,
    )
    logger.info("Application started")

    yield

    await close_pool(app.state.db_pool)
    logger.info("Application stopped")


def create_app() -> FastAPI:
    app = FastAPI(
        title="pick-ma-job",
        version="0.3.0",
        lifespan=lifespan,
    )

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
    app.include_router(api_admin_router)

    return app


app = create_app()


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
