# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Multi-user SaaS that scrapes job postings from Upwork and LinkedIn, evaluates each posting against the user's profile using the Claude API, and presents results in a React web UI.

## Commands

```bash
# Backend
pip install -r requirements.txt
python db/migrate.py          # Apply pending DB migrations (run before starting)
python main.py                # FastAPI on :8000 (reload mode)

# Frontend (development)
cd frontend && npm install
npm run dev                   # Vite dev server on :5173, proxies /api/* to :8000

# Frontend (production build)
cd frontend && npm run build  # Outputs to frontend/dist/

# Tests
pytest                        # All tests
pytest tests/test_evaluator.py  # Single test file
pytest -k "test_name"           # Single test by name
pytest --cov=. --cov-report=term-missing  # With coverage

# Deployment
python db/migrate.py          # Always run migrations before restarting
bash deploy.sh                # Pull, build frontend, restart systemd service
```

## Architecture

### Request lifecycle

```
HTTP request
→ api/routes/<route>.py       # FastAPI router — validates input, calls service
→ services/<service>.py       # Business logic — no direct DB or HTTP
→ repositories/<repo>.py      # All asyncpg queries live here
→ PostgreSQL (asyncpg pool)
```

All shared state lives on `app.state` (pool, `RunManager`). Every dependency is injected via `api/deps.py` using FastAPI `Depends()` — no module-level globals.

### Pipeline (background task)

`POST /api/run` returns a `run_id` immediately. The actual work runs in a background `asyncio.create_task` managed by `RunManager`:

```
services/run_manager.py       # Dispatches background tasks, tracks status
services/pipeline.py          # PipelineService: scrape → dedup → blacklist-filter
                              #   → keyword-filter → evaluate → store → auto-list
scrapers/<platform>.py        # Apify actor call → list[NormalizedJob]
core/evaluator.py             # Two-pass Claude evaluation (see below)
```

### Two-pass evaluation (`core/evaluator.py`)

Every job goes through two Claude API calls:

1. **Pass 1 — score only:** Lightweight prompt returns a single integer 1–10. Uses `max_tokens=16`.
2. **Pass 2 — full eval:** Only runs if `score >= SCORE_THRESHOLD` (default 5, set in `configs/settings.json`). Returns the full JSON object with `scratchpad`, `evaluation`, `recommendation`, `flags`, `summary`.

Jobs below the threshold are stored with their score and `null` evaluation fields. This avoids billing for irrelevant jobs.

### Adding a platform

1. Create `scrapers/<platform>.py` subclassing `BaseScraper`, implement `fetch_jobs` → `list[NormalizedJob]`.
2. Add `configs/platforms/<platform>.json` (actor ID, field mappings).
3. Add `configs/prompts/<platform>_context.json` (evaluation notes, available fields, `user_message_template`).
4. The platform is auto-discovered by `scrapers/registry.py` and surfaced via `GET /api/platforms`.

### Database migrations

Migrations live in `db/migrations/` as numbered `.sql` files. `db/migrate.py` tracks applied migrations in a `schema_migrations` table and applies unapplied ones in order. Always run `python db/migrate.py` before starting the backend after a pull.

## Key Files

| File | Purpose |
|------|---------|
| `main.py` | App factory, lifespan (pool creation, cleanup loop), router registration |
| `api/deps.py` | All FastAPI `Depends()` functions — pool, auth, repos, services |
| `api/schemas.py` | Pydantic response models for all endpoints |
| `api/csrf.py` | HMAC-based CSRF validation |
| `core/evaluator.py` | Two-pass Claude evaluation; `EvaluationResult` frozen dataclass |
| `core/prompt_adapter.py` | Loads platform context JSON; converts DB profile row to prompt dict |
| `scrapers/base.py` | `NormalizedJob` frozen dataclass; `BaseScraper` ABC |
| `scrapers/registry.py` | Platform slug → scraper class mapping |
| `services/pipeline.py` | `PipelineService.run_pipeline()` — full orchestration |
| `services/run_manager.py` | Background task dispatch and status tracking |
| `services/cv_service.py` | CV customization — generates tailored CV text for a job |
| `services/company_blacklist.py` | Company blacklist CRUD |
| `configs/settings.json` | Model, temperature, `alert_threshold`, `pre_filters.exclude_title_keywords` |
| `db/pool.py` | asyncpg pool creation; JSON/JSONB codec registration |
| `db/migrate.py` | Migration runner |
| `VERSION` | Single-line version string, read at startup |


## Auth Flow

Magic link only (no passwords):
1. `POST /auth/magic-link` — creates token, sends email via Resend
2. `GET /auth/verify?token=...` — validates token, sets `session_token` cookie, redirects to frontend
3. All protected routes read the cookie via `get_current_user` in `api/deps.py`
4. Admin routes additionally check `ADMIN_EMAIL` via `get_admin_user`

## Claude API Response Format

`core/evaluator.py` expects a raw JSON object from Claude (no markdown fences). Fallback strips backtick fences and retries once. The full eval response shape:

```json
{
  "scratchpad": "...",
  "evaluation": "...",
  "relevancy_score": 7,
  "recommendation": "...",
  "flags": "...",
  "summary": "..."
}
```

`configs/settings.json` controls which model is used and the score threshold that gates Pass 2.

## Code Conventions

- `async/await` for all I/O — use `anthropic.AsyncAnthropic`, never the sync client
- `hmac.compare_digest()` for any token/secret comparison
- `NormalizedJob` and `EvaluationResult` must remain `frozen=True` dataclasses
- Type hints on all function signatures
- Logging via `logging` stdlib — no `print()` statements
- All queries are user-scoped — every repository method accepts `user_id`
