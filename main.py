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

import resend
import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from starlette.types import ASGIApp, Receive, Scope, Send

from api.limiter import limiter
from api.routes import all_routers
from core.exceptions import DomainError
from core.llm_client import LLMClient, MultiModelLLMClient
from core.llm_provider import create_provider
from core.logging import configure_logging
from core.settings import Settings
from db.pool import close_pool, create_pool
from repositories.magic_link import MagicLinkRepository
from repositories.session import SessionRepository
from services.run_manager import RunManager

load_dotenv()

configure_logging()
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


def _build_multi_model_client(settings: Settings) -> MultiModelLLMClient:
    """Build a MultiModelLLMClient from settings and env vars.

    Creates per-pass LLMClient instances with the appropriate provider,
    model, and temperature from ``Settings.cv_models``.  Each pass can
    route to a different provider or model independently.
    """
    # Cache provider instances by name to reuse connections
    _provider_cache: dict[str, object] = {}

    def _get_provider(provider_name: str) -> object:
        if provider_name not in _provider_cache:
            if provider_name == "anthropic":
                api_key = os.environ.get("ANTHROPIC_API_KEY", "")
                if not api_key:
                    raise RuntimeError(
                        f"ANTHROPIC_API_KEY env var required for provider "
                        f"'{provider_name}' referenced in cv_models config."
                    )
                _provider_cache[provider_name] = create_provider(
                    "anthropic", api_key=api_key,
                )
            else:
                raise ValueError(
                    f"Unknown provider '{provider_name}' in cv_models config. "
                    f"Supported providers: anthropic"
                )
        return _provider_cache[provider_name]

    cv = settings.cv_models
    clients: dict[str, LLMClient] = {}

    # Default / evaluate client uses the configured claude_model
    default_provider = _get_provider("anthropic")
    clients["default"] = LLMClient(
        provider=default_provider,
        default_model=settings.claude_model,
        default_temperature=settings.claude_temperature,
    )
    clients["evaluate"] = LLMClient(
        provider=default_provider,
        default_model=settings.claude_model,
        default_temperature=settings.claude_temperature,
    )

    # Per-pass clients from cv_models configuration
    for pass_name, pass_config in [
        ("optimize", cv.optimize),
        ("humanize", cv.humanize),
        ("keyword_audit", cv.keyword_audit),
    ]:
        provider = _get_provider(pass_config.provider)
        clients[pass_name] = LLMClient(
            provider=provider,
            default_model=pass_config.model,
            default_temperature=pass_config.temperature,
        )

    return MultiModelLLMClient(clients=clients)


@asynccontextmanager
async def lifespan(app: FastAPI):
    validate_env()

    skip_email = os.environ.get("SKIP_EMAIL", "").lower() in ("1", "true", "yes")
    base_url = os.environ.get("BASE_URL", "")
    is_local = base_url.startswith("http://localhost") or base_url.startswith("http://127.")

    if skip_email:
        if not is_local:
            raise RuntimeError(
                "SKIP_EMAIL must never be enabled in production. "
                "Unset the variable before starting the server, or set "
                "BASE_URL=http://localhost:8000 for local development."
            )
        logger.warning("SKIP_EMAIL is enabled — magic link emails will NOT be sent.")

    logger.info("Application version: %s", app.state.version)

    # Load and validate settings at startup — fails fast on malformed config
    app.state.settings = Settings.from_json_file()
    settings = app.state.settings
    logger.info(
        "Settings loaded: model=%s score_threshold=%d",
        settings.claude_model,
        settings.score_threshold,
    )
    logger.info(
        "CV models: optimize=%s/%.1f humanize=%s/%.1f keyword_audit=%s/%.1f",
        settings.cv_models.optimize.model, settings.cv_models.optimize.temperature,
        settings.cv_models.humanize.model, settings.cv_models.humanize.temperature,
        settings.cv_models.keyword_audit.model, settings.cv_models.keyword_audit.temperature,
    )

    resend.api_key = os.environ["RESEND_API_KEY"]

    app.state.db_pool = await create_pool(os.environ["DATABASE_URL"])

    # Backfill admin flag from ADMIN_EMAIL env var (one-time, idempotent)
    admin_email = os.environ.get("ADMIN_EMAIL", "").strip()
    if admin_email:
        async with app.state.db_pool.acquire() as conn:
            await conn.execute(
                "UPDATE users SET is_admin = TRUE WHERE email = $1",
                admin_email,
            )
        logger.info("Backfilled is_admin for ADMIN_EMAIL=%s", admin_email)

    # Build multi-model LLM client
    app.state.llm_client = _build_multi_model_client(settings)

    # Default LLMClient for backward compatibility (evaluator, pipeline, etc.)
    default_llm = app.state.llm_client.for_pass("default")

    app.state.run_manager = RunManager(
        llm_client=default_llm,
        pool=app.state.db_pool,
        settings=settings,
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


class SecurityHeadersMiddleware:
    """Attach baseline HTTP security headers to every response (raw ASGI)."""

    _EXTRA_HEADERS = [
        (b"x-content-type-options", b"nosniff"),
        (b"x-frame-options", b"DENY"),
        (b"x-xss-protection", b"0"),
        (b"referrer-policy", b"strict-origin-when-cross-origin"),
        (b"permissions-policy", b"geolocation=(), microphone=(), camera=()"),
    ]

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        async def send_with_headers(message):
            if message["type"] == "http.response.start":
                message.setdefault("headers", []).extend(self._EXTRA_HEADERS)
            await send(message)

        await self.app(scope, receive, send_with_headers)


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

    # Security headers
    app.add_middleware(SecurityHeadersMiddleware)

    # ── Domain error handler ─────────────────────────────────────────────
    @app.exception_handler(DomainError)
    async def domain_error_handler(request, exc: DomainError):
        return JSONResponse(status_code=exc.http_status, content={"detail": str(exc)})

    # ── Register all routers ─────────────────────────────────────────────
    for router in all_routers:
        app.include_router(router)

    return app


app = create_app()


if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)