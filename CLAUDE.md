# CLAUDE.md

## Project Overview

A multi-user SaaS product that scrapes job postings from multiple platforms (Upwork, LinkedIn, and future sources), evaluates each posting against the user's profile using the Claude API, and presents results in a web UI.

The SaaS MVP is complete (see [docs/saas-mvp-plan.md](docs/saas-mvp-plan.md) for historical decisions). The frontend has been migrated from Jinja2/HTMX to React/TypeScript (see [docs/frontend-migration-plan.md](docs/frontend-migration-plan.md)).

The pipeline replaces a previous Make.com automation. The goal is lower cost, full control, and extensibility.

## Architecture

```
scrapers/                       # One adapter per platform
├── base.py                     # Abstract base class — NormalizedJob + BaseScraper
├── upwork.py                   # Apify Upwork actor → NormalizedJob
├── linkedin.py                 # Apify LinkedIn actor → NormalizedJob
└── registry.py                 # Platform name → scraper class lookup

core/
└── evaluator.py                # Prompt assembly, AsyncAnthropic API call, JSON parsing

services/                       # Business logic — no direct DB or HTTP access
├── pipeline.py                 # PipelineService — orchestrates scrape → evaluate → store
├── auth.py                     # AuthService — magic links, sessions
├── profile.py                  # ProfileService — user profile CRUD
├── search_config.py            # SearchConfigService
└── run_manager.py              # Background task dispatch + status tracking

repositories/                   # All PostgreSQL access lives here
├── user.py                     # UserRepository
├── profile.py                  # ProfileRepository
├── job_result.py               # JobResultRepository (dedup via unique constraint)
├── job_list.py                 # JobListRepository — named lists + list items
├── search_config.py            # SearchConfigRepository
├── session.py                  # SessionRepository
├── magic_link.py               # MagicLinkRepository
└── pipeline_run.py             # PipelineRunRepository

api/
├── routes/
│   ├── auth.py                 # GET /auth/me, POST /auth/magic-link, GET /auth/verify, POST /auth/logout
│   ├── api_dashboard.py        # GET /api/dashboard
│   ├── api_pipeline.py         # POST /api/run {platforms?}, GET /api/run/{id}/status
│   ├── api_platforms.py        # GET /api/platforms — registry-driven platform list with has_config flag
│   ├── api_version.py          # GET /api/version — no auth required
│   ├── api_profile.py          # GET/POST /api/profile
│   ├── api_results.py          # GET /api/results, PATCH /api/results/{id}
│   ├── api_search_config.py    # GET/POST/DELETE /api/search-configs
│   ├── api_lists.py            # GET/POST/PATCH/DELETE /api/lists, GET/POST/DELETE /api/lists/{id}/jobs
│   └── api_admin.py            # GET /api/admin/users
├── deps.py                     # FastAPI Depends() — get_current_user, get_pipeline_service
├── schemas.py                  # Pydantic response models for all API endpoints
├── csrf.py                     # CSRF token validation (hmac-based)
└── limiter.py                  # Shared slowapi rate limiter instance

configs/prompts/                # Platform evaluation context and message templates
├── upwork_context.json
└── linkedin_context.json

frontend/                       # React SPA (built with Vite, served by nginx)
├── src/
│   ├── api/                    # API client modules
│   │   ├── client.ts           # Base fetch wrapper
│   │   ├── auth.ts, dashboard.ts, pipeline.ts, profile.ts
│   │   ├── results.ts, search-config.ts, lists.ts, admin.ts
│   │   ├── platforms.ts        # GET /api/platforms
│   │   └── version.ts          # GET /api/version
│   ├── components/             # Reusable UI components (shadcn/ui based)
│   │   ├── run-pipeline-dialog.tsx  # Platform selection dialog before starting a run
│   │   └── version-footer.tsx       # Displays app version on all authenticated pages
│   ├── hooks/                  # TanStack Query + utility hooks
│   │   ├── use-auth.ts, use-results.ts, use-profile.ts, use-run.ts
│   │   ├── use-search-config.ts, use-lists.ts, use-theme.ts
│   │   ├── use-platforms.ts    # Fetches /api/platforms
│   │   └── use-version.ts      # Fetches /api/version (stale-time Infinity)
│   ├── pages/                  # Route pages
│   │   ├── landing.tsx, login.tsx, check-email.tsx
│   │   ├── dashboard.tsx, results.tsx, profile.tsx
│   │   ├── search-config.tsx, admin.tsx
│   └── types/                  # Zod schemas and TypeScript types
└── dist/                       # Production build output (served by nginx)

nginx/                          # nginx config for production
deploy.sh                       # Deployment script

main.py                         # FastAPI app factory — mounts routers, registers lifespan
.env                            # Secrets (never committed)
.env.example                    # Required env var template
```

## Tech Stack

- **Language:** Python 3.12+ (backend), TypeScript (frontend)
- **LLM:** Claude Haiku 4.5 (`claude-haiku-4-5-20251001`) via `anthropic.AsyncAnthropic`, temperature 0
- **Scraping:** Apify (`apify-client`) — actors differ per platform
- **Frontend:** React 19, TypeScript, Vite, Tailwind CSS v4, shadcn/ui, TanStack Query v5, React Router v7, Zod
- **Backend:** FastAPI (JSON API only — all routes return JSON except `/auth/verify` which redirects)
- **Database:** PostgreSQL
- **Auth:** Custom magic link (email only, no passwords)
- **Email:** Resend or SendGrid
- **Background tasks:** `asyncio.create_task` via `RunManager` for pipeline runs
- **Deployment:** DigitalOcean droplet (Ubuntu 24.04), nginx + systemd service

## Key Design Principles

1. **Plugin architecture for platforms.** Adding a new platform = 1 scraper adapter file + DB row in `search_configs`. Zero changes to core logic.
2. **NormalizedJob is the universal internal format.** Every scraper outputs `NormalizedJob` objects. The evaluator doesn't know or care which platform a job came from.
3. **No module-level globals.** All shared state (DB connections, API clients) injected via FastAPI `Depends()`. Request-scoped dependencies prevent cross-user data leakage.
4. **Service layer owns business logic.** `PipelineService`, `AuthService`, `ProfileService` — no direct DB queries or HTTP logic inside services. Repositories handle DB; routes handle HTTP.
5. **Pipeline runs are background tasks.** A `POST /run` request returns a `run_id` immediately. The actual scrape + evaluate loop runs in the background. Frontend polls for status.
6. **Secrets live in `.env`, never in code or configs.** All API keys, tokens, and credentials referenced as environment variables resolved at startup.
7. **User isolation at the DB layer.** All queries scoped by `user_id`. The `job_results` table has a unique constraint on `(user_id, platform, job_id)` — this replaces the SQLite dedup store.

## Data Flow (Per User, Per Run — SaaS)

```
POST /run (authenticated user)
→ Return run_id immediately
→ Background task:
    Load user's search_config from DB
    → Run scraper adapter (user's query + filters)
    → Normalize to NormalizedJob[]
    → Skip jobs already in job_results for this user (dedup via DB unique constraint)
    → Keyword pre-filter (excluded keywords from user's profile/settings)
    → For each remaining job:
        → Load user's profile from DB
        → Assemble prompt (profile + platform_context + job fields)
        → Call Claude Haiku 4.5 async (temperature 0)
        → Parse JSON response into EvaluationResult (frozen dataclass)
        → Insert row into job_results table
    → Update run status to completed
```

## Scraper Adapter Contract

Every scraper must inherit from `BaseScraper` and implement `fetch_jobs`. This contract does not change for SaaS — scrapers remain platform-specific and stateless.

```python
from dataclasses import dataclass, field
from abc import ABC, abstractmethod

@dataclass(frozen=True)
class NormalizedJob:
    id: str
    platform: str
    title: str
    description: str
    url: str
    skills: list[str] | None = None
    budget: str | None = None
    job_type: str | None = None
    experience_level: str | None = None
    extras: dict = field(default_factory=dict)  # platform-specific fields

class BaseScraper(ABC):
    platform: str

    @abstractmethod
    async def fetch_jobs(self, config: dict) -> list[NormalizedJob]:
        ...
```

The `extras` dict carries platform-specific fields (e.g., `client_rating`, `proposals` for Upwork; `company_name`, `company_size` for LinkedIn) interpolated into the platform's message template.

## Claude API Response Format

The evaluator expects Claude to return a raw JSON object (no markdown, no backticks). `EvaluationResult` must be a `frozen=True` dataclass or Pydantic model for clean DB serialization.

```json
{
  "scratchpad": "Internal step-by-step analysis",
  "evaluation": "Detailed explanation of relevance",
  "relevancy_score": 7,
  "recommendation": "Yes apply / Consider applying / Do not apply — with justification",
  "flags": "Comma-separated red/green flags",
  "summary": "One sentence summary of job fit"
}
```

`relevancy_score` is a number 1-10. All other fields are strings. Retry logic: strip markdown fences as fallback, then retry once.

## Database Schema

```sql
users         — id, email, created_at, last_login
sessions      — id, user_id, token, expires_at
magic_links   — id, user_id, token, used, expires_at
profiles      — id, user_id, role, experience, rate,
                primary_skills TEXT[], secondary_skills TEXT[], tertiary_skills TEXT[],
                not_a_good_fit TEXT[], background TEXT[],
                notable_projects JSONB, languages TEXT[],
                rubric JSONB, updated_at
search_configs — id, user_id, platform, query, filters (JSON), updated_at
job_results   — id, user_id, platform, job_id, title, url, score,
                evaluation (JSON), created_at, status (new/applied/dismissed)
                UNIQUE (user_id, platform, job_id)  -- dedup constraint
job_lists     — id, user_id, name, created_at
job_list_items — list_id, job_result_id, added_at
                 PRIMARY KEY (list_id, job_result_id)
```

## Apify Input Notes

Each Apify actor has a completely different input schema. The `scraper.input` in `search_configs.filters` stores the exact Apify payload per user. Example for Upwork:

```json
{
  "query": "unity developer",
  "experienceLevel": ["entry", "intermediate"],
  "jobType": ["fixed", "hourly"],
  "paymentVerified": true,
  "perPage": 50,
  "sort": "newest",
  "maxJobAge": { "value": 24, "unit": "hours" }
}
```

The Apify Upwork actor handles authentication internally — no user cookies needed. All API tokens come from environment variables, never from user-supplied config.

---

## Developer Profile (Single-User Reference)

This is the profile for the initial user (Danylo Golosov). In SaaS, this data lives in the `profiles` table per user.

### Identity

- **Name:** Danylo Golosov
- **Role:** Unity Developer
- **Experience:** 4 years professional (mid-level)
- **Location:** Berlin, Germany
- **Work preference:** Remote only
- **Rate:** €10–30/hour (Upwork freelance), €50,000/year gross (full-time)

### Professional Background

- 2 years as AR & Web Developer at ZAUBAR (Berlin) — AR SDK development, cross-platform mobile app shipping, CI/CD pipelines, VR haptics integration
- 2 years as Backend Developer at Intelligent Project (Kyiv) — server-side architecture, database integration, WordPress backend
- BSc Computer Science from Lublin University of Technology (thesis: 4X strategy game in Unity)

### Primary Strengths (score heavily)

- Unity Engine development (C#) — mobile apps, AR/VR, games
- AR/VR SDKs: AR Foundation, ARKit, ARCore, XR Interaction Toolkit, OpenXR
- Shipping cross-platform mobile apps (iOS & Android) from start to release
- CI/CD for mobile builds (Jenkins, Firebase App Distribution)
- Performance profiling and optimization (Unity Profiler, Android Logcat)

### Secondary Strengths (score moderately)

- Rust — multiplayer game server development, networking, authoritative server architecture
- C++ and OpenGL — custom rendering, graphics programming, shader development
- Backend architecture and server-side systems
- Python scripting
- Swift — native iOS plugins

### Tertiary / Supporting Skills (score lightly)

- Vue.js, TypeScript, Tailwind CSS — web component development
- Blender — 3D modeling
- WordPress backend configuration

### Not a Good Fit For

- Pure frontend/web development (unless tied to Unity or AR/VR pipeline)
- Generic mobile development without Unity (native Android/iOS with Kotlin/SwiftUI as primary)
- Data science, machine learning engineering, DevOps-only, database administration
- Roles requiring Unreal Engine, Godot, or other non-Unity game engines as primary tool

### Notable Projects

- **Rust Multiplayer Game (Paper.io 2 clone):** Fully authoritative game server from scratch in Rust, 200+ concurrent players, full client-server pipeline with cheat prevention
- **Solar System Simulation:** C++17 + OpenGL 3.3, custom rendering engine, no game engine dependency
- **VR Tower Defense:** Unity + XR Interaction Toolkit, spatial tower placement, state machine AI architecture

### Languages

English, Ukrainian, German (actively studying), Russian, Polish

---

## Scoring Rubric

The Claude evaluator uses this rubric to score jobs 1–10:

- **9–10:** Excellent match — hits primary strengths, appropriate level and budget, apply immediately
- **7–8:** Good match — primarily relevant with minor gaps, likely worth applying
- **5–6:** Moderate match — touches secondary/tertiary skills or notable mismatches, apply cautiously
- **3–4:** Poor match — only tangential overlap or significant red flags, probably not worth it
- **1–2:** Very poor match — outside domain entirely, do not apply

### Evaluation Factors

1. **Skills Match:** How well required skills align with primary > secondary > tertiary strengths
2. **Experience Level:** Mid-level is ideal. Junior is fine. Senior in AR/VR is acceptable.
3. **Project Type:** Prioritize AR/VR, Unity games, multiplayer servers (Rust), graphics programming (OpenGL/C++), mobile shipping
4. **Budget/Rate:** For Upwork: €10–30/hour or reasonable fixed-price. For full-time: ~€50k/year. Flag lowball budgets.
5. **Project Scope:** Both full project ownership and SDK/feature contribution are fine. Fixed-price and hourly both acceptable.
6. **Client Quality:** Flag vague requirements, unrealistic expectations, no verified payment, spec work. Positive: clear scope, hire history, domain knowledge.
7. **Competition:** AR/VR and Rust game server roles have less competition — factor this in positively.

---

## Code Style & Conventions

- Python 3.12+ features are fine (type hints, match statements, etc.)
- Use `async/await` for all I/O — API calls use `anthropic.AsyncAnthropic`, not the sync client
- Use `hmac.compare_digest()` for any secret/token comparison — never `==` or `!=`
- `NormalizedJob` and `EvaluationResult` must be `frozen=True` dataclasses or Pydantic models
- No module-level mutable state — inject dependencies via FastAPI `Depends()`
- Type hints on all function signatures
- Docstrings on public functions and classes
- Keep modules focused — one responsibility per file
- Error handling: retry with exponential backoff for external API calls, fail gracefully with logging
- Logging via `logging` stdlib, not print statements
- Validate required config/env vars at startup and fail fast with clear error messages

## Environment Variables (.env)

```
# Claude API
ANTHROPIC_API_KEY=

# Apify (shared account across all users for MVP)
APIFY_API_TOKEN=

# PostgreSQL
DATABASE_URL=

# Auth / Email
EMAIL_FROM=
RESEND_API_KEY=
MAGIC_LINK_SECRET=

# FastAPI
API_KEY=
SECRET_KEY=
```

## Commands

```bash
# Backend
pip install -r requirements.txt
python main.py                    # Starts FastAPI on :8000

# Frontend (development)
cd frontend && npm install
npm run dev                       # Vite dev server on :5173, proxies API to :8000

# Frontend (production build)
cd frontend && npm run build      # Outputs to frontend/dist/

# Deployment (on server)
bash deploy.sh                    # Pull, build, restart services

# Health check
curl http://localhost:8000/health
```
