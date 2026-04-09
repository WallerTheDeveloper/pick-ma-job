# SaaS MVP Plan

> **Status: Completed.** All 6 phases are implemented and running. This document is kept as a historical record of decisions made during the SaaS migration. For current active work, see [frontend-migration-plan.md](frontend-migration-plan.md).

## Vision

Convert the personal job pipeline into a multi-user SaaS product. Users configure their own profile and search, manually trigger runs, and view results in a web UI. Operator (Danylo) manages access and hosts everything on DigitalOcean.

## Key Decisions

- **Monetization:** Subscription-based. Operator pays for Apify/Claude API costs.
- **Apify:** Shared account across all users. Revisit when user count grows.
- **Auth:** Magic link (email only, no password). Open registration for now.
- **Scheduling:** Disabled for MVP. Manual runs only. Add later.
- **Notifications:** Telegram and Google Sheets dropped for MVP. Results live in web UI only.
- **Frontend:** React 19 + TypeScript + Vite + Tailwind CSS v4 + shadcn/ui (migrated from HTMX + Jinja — see [frontend-migration-plan.md](frontend-migration-plan.md)).
- **Database:** PostgreSQL (replaces SQLite, handles concurrent multi-user writes).
- **Email provider:** Resend or SendGrid (for magic links).

## Tech Stack

| Layer | Choice |
|-------|--------|
| Backend | Python/FastAPI (existing) |
| Frontend | React 19 + TypeScript + Vite + Tailwind + shadcn/ui |
| Database | PostgreSQL |
| Auth | Custom magic link |
| Email | Resend or SendGrid |
| Hosting | DigitalOcean |

## Database Schema (planned)

- `users` — id, email, created_at, last_login
- `sessions` — id, user_id, token, expires_at
- `magic_links` — id, user_id, token, used, expires_at
- `profiles` — id, user_id, skills, experience, rate, rubric (JSON), updated_at
- `search_configs` — id, user_id, platform, query, filters (JSON), updated_at
- `job_results` — id, user_id, platform, job_id, title, url, score, evaluation (JSON), created_at, status (new/applied/dismissed)

## Implementation Phases

### Phase 1 — Auth & Database (~3 days)
- PostgreSQL setup with schema above
- Magic link flow: signup → email sent → click link → session cookie created
- Login/signup pages (HTMX)

### Phase 2 — User Profile (~2 days)
- Profile form: skills, experience level, rate, "not a good fit for" section
- Replaces static `configs/prompts/base_profile.json`
- Saved per user in `profiles` table

### Phase 3 — Search Configuration (~2 days)
- Per-user search config: platform selection, search query, filters
- Replaces static `configs/platforms/*.json`
- Saved per user in `search_configs` table

### Phase 4 — Pipeline Integration (~3 days)
- Evaluator reads profile from DB instead of JSON files
- Results stored in `job_results` table instead of Google Sheets
- Manual "Run" button triggers scrape + evaluate for authenticated user

### Phase 5 — Results Dashboard (~2 days)
- Table of job results: score, title, recommendation, URL
- Filter by score, sort, mark as applied/dismissed

### Phase 6 — Admin Panel (~1 day)
- User list: email, registration date, last run, job count

**Total estimate: ~13 days**

## What Carries Over from Current Codebase

- Scraper adapters (`scrapers/upwork.py`, `scrapers/linkedin.py`)
- Evaluator logic (`core/evaluator.py`)
- Claude API integration
- Apify integration
- Deduplication concept (moves to PostgreSQL)

## What Gets Dropped for MVP

- Google Sheets output (`core/sheets.py`)
- Telegram notifications (`core/notifier.py`)
- APScheduler / scheduling
- Static JSON configs as source of truth (become DB records)

## Future Roadmap (post-MVP)

- Telegram notification opt-in per user
- Google Sheets export
- Scheduling (per-user cron)
- Billing / subscription management
- LinkedIn scraper (finish implementation)
- Per-user Apify accounts (when scale requires)
