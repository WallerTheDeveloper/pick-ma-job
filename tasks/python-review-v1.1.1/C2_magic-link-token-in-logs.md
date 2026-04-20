# C2: Prevent Magic Link Token from Being Logged in Plaintext

- **Phase:** Critical
- **Priority:** P0 — Security / Credential Leak
- **Status:** DONE
- **Depends on:** None

## Problem

`services/auth.py:74` logs the full magic link URL (including the auth token) at `INFO` level when `SKIP_EMAIL=true`:

```python
logger.info("SKIP_EMAIL=true — magic link for %s: %s", email, magic_url)
```

If `SKIP_EMAIL=true` leaks into a production environment (e.g. via a misconfigured CI/CD deploy), a valid authentication token is written to the application log. Application logs are commonly shipped to centralised aggregators accessible by non-operators.

Additionally, there is no startup guard that warns operators when `SKIP_EMAIL` is enabled in a non-development context.

## Solution

1. **`services/auth.py:74`** — downgrade to `DEBUG` and mask the token:
   ```python
   logger.debug("SKIP_EMAIL=true — magic link for %s: %.40s…", email, magic_url)
   ```

2. **`main.py` lifespan or `api/deps.py`** — add a startup warning if `SKIP_EMAIL` is set:
   ```python
   if os.environ.get("SKIP_EMAIL", "").lower() in ("1", "true", "yes"):
       logger.warning("SKIP_EMAIL is enabled — magic link emails will NOT be sent. Never use in production.")
   ```

3. **`.env.example`** — add a comment explicitly stating `SKIP_EMAIL` must never be set in production.

## Files

- `services/auth.py`
- `main.py` or `api/deps.py`
- `.env.example`

## Acceptance Criteria

- [x] Magic link token is no longer emitted at INFO/WARNING/ERROR log levels
- [x] A startup WARNING is logged whenever `SKIP_EMAIL` is set
- [ ] `.env.example` documents that `SKIP_EMAIL` is development-only — **blocked by file permissions, add manually**
- [x] `DEBUG` log still shows enough info to retrieve the link during local development
