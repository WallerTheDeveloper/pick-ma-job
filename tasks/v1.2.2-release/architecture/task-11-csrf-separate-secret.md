# Task 11 — Separate CSRF_SECRET from MAGIC_LINK_SECRET

**Size:** XS  
**Status:** done  
**Priority:** MEDIUM

## Goal

Give CSRF token derivation its own secret so rotating the magic-link secret doesn't silently invalidate all active sessions (and vice versa).

## Problem

`api/csrf.py` uses `MAGIC_LINK_SECRET` for CSRF token derivation — a secret intended for a different purpose. Rotating one forces rotation of the other.

## Changes

**`.env.example`**
```
CSRF_SECRET=<generate with: python -c "import secrets; print(secrets.token_hex(32))">
```

**`api/csrf.py`**
```python
import os
_CSRF_SECRET = os.environ.get("CSRF_SECRET") or os.environ["MAGIC_LINK_SECRET"]
```
- Use `_CSRF_SECRET` in `derive_csrf_token` and `validate_csrf_token`
- Falls back to `MAGIC_LINK_SECRET` for zero-downtime migration (no redeploy needed by existing installs without `CSRF_SECRET`)

**`core/settings.py`** (from Task 6)
- Add `csrf_secret: str` field with fallback to `magic_link_secret`

## Success Criteria

- App starts and CSRF validation works with only `CSRF_SECRET` set (no `MAGIC_LINK_SECRET`)
- App starts and CSRF validation works with only `MAGIC_LINK_SECRET` set (backward compat)
- Rotating `MAGIC_LINK_SECRET` while keeping `CSRF_SECRET` unchanged does not invalidate CSRF tokens
