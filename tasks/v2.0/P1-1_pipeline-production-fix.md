# P1-1: Fix Pipeline on Production

- **Phase:** 1 — Critical Bugs
- **Priority:** P0 — Blocking
- **Status:** DONE
- **Depends on:** None (server access required)

## Problem

Pipeline doesn't work on production server. Users can trigger a run but it never completes successfully.

## Root Cause Investigation

Check in order:

1. **Environment variables** — Verify `.env` on production has all required keys:
   - `ANTHROPIC_API_KEY`
   - `APIFY_API_TOKEN`
   - `DATABASE_URL`
2. **Server logs** — `journalctl -u pick-ma-job -n 200 --no-pager`
3. **Apify actor call** — Is the token valid? Is the actor reachable from the server?
4. **asyncio background task** — Does `RunManager` propagate exceptions or silently swallow them? Check if the task crashes without updating run status.
5. **Database connection pool** — Is the pool exhausted under systemd? Check `DATABASE_URL` pool size and concurrent connections.

## Files

- `services/run_manager.py` — background task dispatch
- `services/pipeline.py` — pipeline orchestration
- `main.py` — app factory, lifespan
- `.env` on production server
- `deploy.sh` — deployment script

## Acceptance Criteria

- [ ] `POST /api/run` triggers a pipeline run on production
- [ ] Run status transitions from pending → running → completed
- [ ] Job results appear in the database after a successful run
- [ ] Errors are logged, not silently swallowed
