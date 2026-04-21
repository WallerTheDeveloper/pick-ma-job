# Task 3 — Enforce Email Validation at the Pydantic Layer

**Size:** XS  
**Status:** todo  
**Severity:** HIGH

## Goal

Replace `email: str` with `email: EmailStr` in `MagicLinkRequest` so malformed emails are rejected at request-parsing time, before reaching the service layer.

## Changes

**`requirements.txt`** — add:
```
email-validator>=2.0.0
```

**`api/schemas.py`**:
```python
from pydantic import EmailStr

class MagicLinkRequest(BaseModel):
    email: EmailStr
```

## Notes

- `EmailStr` normalises the value (lowercases domain), so the service-layer `_EMAIL_RE` check becomes redundant but harmless to keep as defence-in-depth.
- The `email-validator` package is a standard Pydantic extra and has no conflicting dependencies.

## Success Criteria

- `POST /auth/magic-link` with `{"email": "not-an-email"}` returns `422`.
- Valid email addresses continue to work.
