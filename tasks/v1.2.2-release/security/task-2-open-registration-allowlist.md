# Task 2 — Restrict Registration via Email Allow-list

**Size:** S  
**Status:** todo  
**Severity:** HIGH

## Goal

Prevent arbitrary self-registration that consumes Anthropic/Apify/Resend quota. Gate magic link requests to an explicit allow-list or allowed domain.

## Changes

**`services/auth.py`** — add at module level and call before user creation:
```python
import os

_ALLOWED_EMAILS = {
    e.strip().lower()
    for e in os.environ.get("ALLOWED_EMAILS", "").split(",")
    if e.strip()
}
_ALLOWED_DOMAIN = os.environ.get("ALLOWED_EMAIL_DOMAIN", "").strip().lower()

def _is_email_allowed(email: str) -> bool:
    if _ALLOWED_EMAILS and email.lower() in _ALLOWED_EMAILS:
        return True
    if _ALLOWED_DOMAIN and email.lower().endswith(f"@{_ALLOWED_DOMAIN}"):
        return True
    # Open if neither env var is configured
    return not _ALLOWED_EMAILS and not _ALLOWED_DOMAIN

# In request_magic_link, before get_or_create_user:
if not _is_email_allowed(email):
    raise AuthValidationError("Email address not permitted.")
```

**`.env.example`** — document the new variables:
```
ALLOWED_EMAILS=admin@example.com,other@example.com   # comma-separated whitelist
ALLOWED_EMAIL_DOMAIN=example.com                      # or allow entire domain
```

## Notes

- If neither var is set, behaviour is unchanged (open registration). This avoids breaking existing deployments on upgrade.
- The check runs before `create_user`, so no DB row or Resend email is produced for rejected addresses.

## Success Criteria

- With `ALLOWED_EMAILS=a@b.com`, a request for `other@b.com` returns an auth error.
- With `ALLOWED_EMAIL_DOMAIN=b.com`, any `*@b.com` address succeeds.
- With neither var set, all emails are accepted (backward-compatible).
