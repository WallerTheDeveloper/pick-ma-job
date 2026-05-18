# Pick Ma Job

> **AI-powered job discovery and evaluation platform** — find the right freelance gigs, not all of them.

<p align="center">
  <img src="https://img.shields.io/badge/version-1.4.0-blue?style=for-the-badge" alt="Version 1.4.0">
  <img src="https://img.shields.io/badge/python-3.11+-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python 3.11+">
  <img src="https://img.shields.io/badge/react-19-61DAFB?style=for-the-badge&logo=react&logoColor=black" alt="React 19">
  <img src="https://img.shields.io/badge/fastapi-0.115+-009688?style=for-the-badge&logo=fastapi&logoColor=white" alt="FastAPI">
  <img src="https://img.shields.io/badge/postgresql-14+-4169E1?style=for-the-badge&logo=postgresql&logoColor=white" alt="PostgreSQL 14+">
  <img src="https://img.shields.io/badge/license-MIT-green?style=for-the-badge" alt="MIT License">
  <img src="https://img.shields.io/badge/status-active-success?style=for-the-badge" alt="Active">
</p>

---

**Pick Ma Job** is a multi-user SaaS platform that scrapes job postings from Upwork and LinkedIn, evaluates every posting against **your** profile using Anthropic's Claude API, and presents only the most relevant opportunities in a clean, modern React UI. Stop sifting through noise — let AI surface the jobs worth your time.

---

## ✨ Features

| Category | Highlights |
|----------|-----------|
| 🔍 **Multi-platform scraping** | Scrapes Upwork and LinkedIn job postings via Apify actors. Extensible to new platforms in minutes. |
| 🧠 **Two-pass AI evaluation** | Cost-efficient Claude evaluation: a lightweight Pass 1 scores every job (1–10), then only high-scoring jobs undergo detailed Pass 2 analysis. Configurable score threshold. |
| 📋 **Smart filtering** | Company blacklist, configurable keyword exclusions in titles, automatic deduplication — clean before you see it. |
| 📊 **Rich results dashboard** | Cursor-paginated job browser with filters by platform, status, and score. Bulk dismiss, delete, or re-evaluate. |
| 👤 **Profile-aware matching** | Upload your CV as PDF, describe your skills and preferences — every job is evaluated against your actual profile. |
| ✍️ **Custom CV generation** | One-click generation of a tailored CV for any job, with section-by-section diff highlighting what changed. |
| 💬 **Upwork proposal generation** | Generate compelling Upwork proposals tuned to the job and your profile. |
| 📝 **Custom job lists** | Create named lists, auto-add matching jobs, organize with drag-and-drop. |
| 🔐 **Passwordless auth** | Magic-link authentication via email (Resend). No passwords to manage or leak. |
| 🛡️ **Security-first** | CSRF protection (double-submit cookie with HMAC-SHA256), rate limiting, hashed tokens, HttpOnly/Secure session cookies, strict security headers, user-scoped database queries. |
| 🏠 **Self-hosted** | Full control. Single `setup.sh` for Ubuntu 24.04. Deploy with `deploy.sh` in seconds. |
| 👑 **Admin panel** | User management with stats. Registration allowlist by email or domain. |

---

## 🧰 Tech Stack

### Backend
| Component | Technology |
|-----------|-----------|
| Framework | **FastAPI** + Uvicorn (ASGI) |
| Language | **Python 3.11+** (full type hints, `async`/`await`) |
| Database | **PostgreSQL 14+** via `asyncpg` (async connection pool) |
| AI / LLM | **Anthropic Claude** (default: `claude-haiku-4-5-20251001`) |
| Scraping | **Apify** actors (Upwork + LinkedIn) |
| Email | **Resend** (magic link delivery) |
| Rate limiting | **SlowAPI** |
| PDF parsing | **pypdf** |

### Frontend
| Component | Technology |
|-----------|-----------|
| Framework | **React 19** + TypeScript (strict) |
| Build tool | **Vite 6** |
| Styling | **Tailwind CSS 4** + `shadcn/ui` + Base UI |
| Icons | **Lucide React** |
| State / data | **TanStack Query** (server state), React Router v7 |
| Drag-and-drop | **@dnd-kit** |
| Validation | **Zod** |
| Toasts | **Sonner** |
| Testing | **Vitest** + React Testing Library + MSW (mocked API) |

---

## 🏗️ Architecture

```
                         ┌──────────────┐
                         │   Browser    │
                         │  (React SPA) │
                         └──────┬───────┘
                                │ HTTPS
                         ┌──────▼───────┐
                         │    nginx      │
                         │  (reverse     │
                         │   proxy +     │
                         │   static)     │
                         └──────┬───────┘
                                │ /api/*
                         ┌──────▼───────┐
                         │   FastAPI     │
                         │  (Uvicorn)    │
                         │               │
                         │  ┌─────────┐  │
                         │  │ Routes  │  │
                         │  │ (14)    │  │  ← validation, auth, serialization
                         │  └────┬────┘  │
                         │       │       │
                         │  ┌────▼────┐  │
                         │  │Services │  │  ← business logic (no raw DB)
                         │  │ (10)    │  │
                         │  └────┬────┘  │
                         │       │       │
                         │  ┌────▼────┐  │
                         │  │  Repos  │  │  ← SQL (asyncpg), user-scoped
                         │  │  (14)   │  │
                         │  └────┬────┘  │
                         └───────┼───────┘
                                 │
                         ┌───────▼───────┐     ┌──────────────┐
                         │  PostgreSQL   │     │ Claude API   │
                         │    14+        │     │ (Anthropic)  │
                         └───────────────┘     └──────────────┘
                                                       │
                         ┌──────────────┐              │
                         │ Apify (jobs) │◄─────────────┘
                         └──────────────┘
```

### Request Lifecycle

```
HTTP request
  → api/routes/<route>.py    FastAPI router — validates input, calls service
    → services/<service>.py   Business logic — no direct DB or HTTP calls
      → repositories/<repo>.py  All asyncpg queries live here
        → PostgreSQL
```

All shared state lives on `app.state` (connection pool, `RunManager`). Every dependency is injected via FastAPI `Depends()` — **no module-level globals**. Every repository method accepts `user_id` — **all queries are user-scoped**.

### Pipeline (Background Job Processing)

```
POST /api/run  ──►  run_id returned immediately
                       │
                       ▼  (background asyncio task)
              ┌─────────────────────┐
              │  1. Scrape          │  Apify actors fetch jobs
              │  2. Deduplicate     │  Remove duplicates across runs
              │  3. Blacklist       │  Filter out blocked companies
              │  4. Keyword filter  │  Exclude titles with banned keywords
              │  5. Evaluate        │  Two-pass Claude evaluation
              │  6. Store           │  Persist results to PostgreSQL
              │  7. Auto-list       │  Add matching jobs to custom lists
              └─────────────────────┘
```

### Two-Pass Evaluation

```
Pass 1: Score only                    Pass 2: Full evaluation
┌──────────────────────┐              ┌──────────────────────────────┐
│  Lightweight prompt   │              │  Detailed analysis            │
│  max_tokens = 16      │  score ≥ 5  │  Returns:                     │
│  Returns: integer 1-10├──────────────►  • scratchpad                │
│                       │  (default    │  • evaluation                 │
│  Jobs below threshold │   threshold) │  • relevancy_score (1–10)    │
│  stored with score    │              │  • recommendation            │
│  only (no cost for    │              │  • flags                     │
│  irrelevant jobs)     │              │  • summary                   │
└──────────────────────┘              └──────────────────────────────┘
```

The score threshold is configurable in `configs/settings.json` (`alert_threshold`, default 7). The evaluation model and concurrency (default 3) are also configurable.

---

## 🚀 Quick Start

### Prerequisites

- **Python 3.11+** with `pip`
- **Node.js 20+** with `npm`
- **PostgreSQL 14+** running locally
- An **Anthropic API key** (for Claude evaluation)
- An **Apify API token** (for job scraping)
- A **Resend API key** (for magic link emails — can skip with `SKIP_EMAIL=true`)

### 1. Clone & Install

```bash
git clone https://github.com/your-org/pick-ma-job.git
cd pick-ma-job

# Backend
python -m venv .venv
.venv/bin/pip install -r requirements.txt   # Windows: .venv\Scripts\pip install -r requirements.txt

# Frontend
cd frontend
npm install
cd ..
```

### 2. Configure Environment

```bash
cp .env.example .env
# Edit .env with your real values — at minimum:
#   DATABASE_URL, MAGIC_LINK_SECRET, ANTHROPIC_API_KEY, APIFY_API_TOKEN
```

Set `SKIP_EMAIL=true` for local development if you don't have a Resend account (magic links will be logged to the console). **This is refused in production.**

### 3. Initialize the Database

```bash
# Create the PostgreSQL database
createdb pickmajob

# Run migrations
python db/migrate.py
```

### 4. Start the Backend

```bash
python main.py
# FastAPI running at http://localhost:8000
```

### 5. Start the Frontend

```bash
cd frontend
npm run dev
# Vite dev server at http://localhost:5173 (proxies /api/* to :8000)
```

### 6. Log In

Navigate to `http://localhost:5173/login`, enter your email, and click the magic link logged to the console (or received via email).

---

## 🔌 API Reference

### Authentication

| Method | Endpoint | Description | Rate Limit |
|--------|----------|-------------|------------|
| `POST` | `/auth/magic-link` | Request a magic link email | 5 / min |
| `GET` | `/auth/verify?token=...` | Verify token, set session cookie, redirect | — |
| `POST` | `/auth/logout` | Invalidate session, clear cookies | — |
| `GET` | `/auth/me` | Get current user info | — |

### Dashboard

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/dashboard` | User stats, profile status, recent pipeline runs |

### Results

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/results` | List job results (cursor pagination, filters: platform, status, score) |
| `GET` | `/api/results/{id}` | Single result detail |
| `PUT` | `/api/results/{id}/status` | Update status (`new` / `applied` / `dismissed` / `cancelled`) |
| `POST` | `/api/results/bulk-dismiss` | Bulk dismiss by filters |
| `POST` | `/api/results/bulk-delete` | Bulk delete by filters or IDs |
| `POST` | `/api/results/bulk-status` | Bulk status update by IDs |
| `POST` | `/api/results/bulk-evaluate` | Bulk Pass 2 evaluation by filters |

### Pipeline

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/run` | Start pipeline run (optional `platforms` filter in body) |
| `GET` | `/api/run/{run_id}` | Get run status and progress |

### Profile

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/profile` | Get current user's profile |
| `PUT` | `/api/profile` | Create or update profile (skills, preferences, bio, etc.) |

### CV

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/cv/upload` | Upload PDF CV (multipart form) |
| `GET` | `/api/cv` | Get CV metadata (upload date, filename) |
| `POST` | `/api/cv/generate` | Generate a customized CV tailored to a specific job |

### Proposals

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/results/{id}/proposal` | Get existing proposal for a job |
| `POST` | `/api/results/{id}/proposal` | Generate an Upwork proposal for a job |

### Search Configs

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/search-configs` | List user's search configurations |
| `POST` | `/api/search-configs` | Create a search config |
| `PUT` | `/api/search-configs/{id}` | Update a search config |
| `DELETE` | `/api/search-configs/{id}` | Delete a search config |

### Job Lists

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/lists` | List all user's lists |
| `POST` | `/api/lists` | Create a new list |
| `PUT` | `/api/lists/{id}` | Rename a list |
| `DELETE` | `/api/lists/{id}` | Delete a list |
| `POST` | `/api/lists/{id}/jobs` | Add a job to a list |
| `DELETE` | `/api/lists/{id}/jobs/{job_id}` | Remove a job from a list |
| `GET` | `/api/lists/{id}/jobs` | Get jobs in a list |
| `POST` | `/api/lists/{id}/bulk-add` | Bulk add jobs to a list |
| `POST` | `/api/lists/{id}/add-by-filter` | Add jobs matching score/status filter |

### Company Blacklist

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/company-blacklist` | List blacklisted companies |
| `POST` | `/api/company-blacklist` | Add a company to the blacklist |
| `DELETE` | `/api/company-blacklist/{id}` | Remove a company from the blacklist |

### Platforms & Admin

| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| `GET` | `/api/platforms` | List available platforms and config status | User |
| `GET` | `/api/version` | Get application version | — |
| `GET` | `/api/admin/users` | List all users with stats | Admin |


## 🧪 Testing

```bash
# Run all tests
pytest

# Run a single test file
pytest tests/test_evaluator.py

# Run a specific test by name
pytest -k "test_name"

# Run with coverage report
pytest --cov=. --cov-report=term-missing

# Frontend tests
cd frontend && npm test

# Frontend tests in watch mode
cd frontend && npm run test:watch
```

### What's Tested

| Layer | Tool | What |
|-------|------|------|
| Backend unit | `pytest` | Evaluator logic, services, repositories (with real PostgreSQL test DB) |
| Backend integration | `pytest` | API route handlers, middleware, auth flows |
| Frontend unit | `Vitest` + React Testing Library | Component rendering, hook behavior, state logic |
| Frontend integration | `Vitest` + MSW | Full-page flows with mocked API responses |

---

## 🔒 Security

| Measure | Detail |
|---------|--------|
| **Auth** | Magic link only — no passwords to store, leak, or brute-force |
| **Tokens** | SHA-256 hashed in database; never stored in plaintext |
| **Session cookies** | `HttpOnly`, `Secure` (production), `SameSite=Lax` |
| **CSRF** | Double-submit cookie pattern with HMAC-SHA256 derivation; `SameSite=Strict` CSRF cookie |
| **Rate limiting** | Magic link: 5/min; application-level: 3 per 10 min |
| **Security headers** | `X-Content-Type-Options`, `X-Frame-Options: DENY`, `X-XSS-Protection: 0`, `Referrer-Policy`, `Permissions-Policy` |
| **CORS** | Restricted to `localhost:5173` (dev) and `pickmajob.cc` (prod) |
| **DB isolation** | Every repository method is `user_id`-scoped — no cross-user data leaks |
| **Admin guard** | Admin routes gate-checked by `is_admin` flag + `ADMIN_EMAIL` env var |
| **Registration control** | `ALLOWED_EMAILS` and `ALLOWED_EMAIL_DOMAIN` env vars for allowlisting |
| **Production guard** | `SKIP_EMAIL=true` is refused at startup in production |

---

## ➕ Adding a New Platform

Pick Ma Job is built to be extended. Adding a new job source takes three steps:

1. **Create a scraper** — `scrapers/<platform>.py`, subclass `BaseScraper`, implement `fetch_jobs() → list[NormalizedJob]`.
2. **Add platform config** — `configs/platforms/<platform>.json` with the Apify actor ID and field mappings.
3. **Add prompt config** — `configs/prompts/<platform>_context.json` with evaluation notes, available job fields, and the `user_message_template`.

The platform is **auto-discovered** by `scrapers/registry.py` and surfaced via `GET /api/platforms` — no other code changes needed.

---

## 🤝 Contributing

Contributions are welcome! Here's how to get involved:

1. **Fork** the repository and create a feature branch.
2. **Follow the code conventions**: `async`/`await` everywhere, type hints on all signatures, `hmac.compare_digest()` for token comparisons, no `print()` — use `logging`.
3. **Write tests** for new features. We target 80%+ coverage.
4. **Run the full test suite** before opening a PR: `pytest` and `cd frontend && npm test`.
5. **Run migrations** if your change modifies the schema: add a numbered `.sql` file to `db/migrations/`.
6. **Open a PR** with a clear description of what changed and why.

### Code Conventions

- `async`/`await` for all I/O — use `anthropic.AsyncAnthropic`, never the sync client
- `hmac.compare_digest()` for any token or secret comparison
- `NormalizedJob` and `EvaluationResult` must remain `frozen=True` dataclasses
- Type hints on **all** function signatures
- `logging` stdlib only — no `print()` statements
- All queries are user-scoped — every repository method accepts `user_id`
- Dependency injection via FastAPI `Depends()` — no module-level globals

---

## ⚙️ Configuration Reference

### `configs/settings.json`

```json
{
  "model": "claude-haiku-4-5-20251001",
  "temperature": 0,
  "alert_threshold": 7,
  "evaluation_concurrency": 3,
  "pre_filters": {
    "exclude_title_keywords": [
      "unreal", "godot", "react native", "flutter",
      "devops", "data science", "machine learning",
      "data engineer", "android developer", "ios developer"
    ]
  }
}
```

| Key | Description |
|-----|-------------|
| `model` | Anthropic Claude model used for evaluation |
| `temperature` | LLM temperature (0 = deterministic) |
| `alert_threshold` | Minimum score (1–10) for Pass 2 full evaluation |
| `evaluation_concurrency` | Max concurrent Claude API calls during evaluation |
| `pre_filters.exclude_title_keywords` | Jobs with these phrases in the title are skipped before evaluation |

### Environment Variables

See `.env.example` for the full list with descriptions. Required variables:

| Variable | Purpose |
|----------|---------|
| `DATABASE_URL` | PostgreSQL connection string |
| `MAGIC_LINK_SECRET` | HMAC secret for signing magic link tokens |
| `ANTHROPIC_API_KEY` | Claude API key |
| `APIFY_API_TOKEN` | Apify API token |
| `RESEND_API_KEY` | Resend API key (optional in dev with `SKIP_EMAIL=true`) |
| `BASE_URL` | Public base URL for magic link construction |
| `ADMIN_EMAIL` | Email of the admin user (optional) |
| `ALLOWED_EMAILS` / `ALLOWED_EMAIL_DOMAIN` | Registration allowlist (optional) |

---

## 📄 License

This project is licensed under the **MIT License**. See [`LICENSE`](LICENSE) for details.

---

## 🙏 Acknowledgments

- **[Anthropic](https://anthropic.com)** — Claude API for intelligent job evaluation
- **[Apify](https://apify.com)** — Reliable web scraping infrastructure
- **[Resend](https://resend.com)** — Simple, reliable email delivery
- **[shadcn/ui](https://ui.shadcn.com)** — Beautiful, accessible React components
- **[TanStack](https://tanstack.com)** — Powerful data fetching and routing

---

<p align="center">
  <sub>Built with ❤️ for everyone who value their time.</sub>
</p>
