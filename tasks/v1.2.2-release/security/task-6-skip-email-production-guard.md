# Task 6 — Hard-fail if `SKIP_EMAIL` is Set in Production

**Size:** XS  
**Status:** todo  
**Severity:** MEDIUM

## Goal

`SKIP_EMAIL=true` causes magic link tokens to be logged at DEBUG level. A startup `RuntimeError` prevents accidental production deployment with this flag set.

## Changes

**`main.py`** — replace the existing `logger.warning` with a hard guard:
```python
skip_email = os.environ.get("SKIP_EMAIL", "").lower() in ("1", "true", "yes")
base_url = os.environ.get("BASE_URL", "")
is_local = base_url.startswith("http://localhost") or base_url.startswith("http://127.")

if skip_email:
    if not is_local:
        raise RuntimeError(
            "SKIP_EMAIL must never be enabled in production. "
            "Unset the variable before starting the server."
        )
    logger.warning("SKIP_EMAIL is enabled — magic link emails will NOT be sent.")
```

## Success Criteria

- Server refuses to start with `SKIP_EMAIL=true` and a non-localhost `BASE_URL`.
- Server starts normally with `SKIP_EMAIL=true` and `BASE_URL=http://localhost:8000`.
- Server starts normally with `SKIP_EMAIL` unset in any environment.
