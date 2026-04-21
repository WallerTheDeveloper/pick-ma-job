# Task 4 — Store Session and Magic Link Tokens as SHA-256 Hashes

**Size:** M  
**Status:** todo  
**Severity:** MEDIUM

## Goal

Prevent session hijacking from a database leak by storing only the SHA-256 hash of tokens; the raw token is only ever held in memory and sent to the client.

## Changes

**New helper** (e.g. in `db/token_utils.py`):
```python
import hashlib

def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()
```

**`repositories/session.py`**
- `create`: store `hash_token(token)` in the `token` column instead of the raw token.
- `find_by_token`: query `WHERE token = $1` using `hash_token(token)` as the argument.

**`repositories/magic_link.py`**
- `create`: store `hash_token(token)`.
- `find_by_token` / `claim`: pass `hash_token(token)` into the query.

**DB migration** (`db/migrations/NNN_hash_existing_tokens.sql`):
```sql
-- Existing rows have plain-text tokens; they are short-lived so truncating
-- is acceptable. Invalidate all current sessions and magic links on deploy.
TRUNCATE sessions;
TRUNCATE magic_links;
```

## Notes

- The raw token is generated with `secrets.token_urlsafe(32)` (256-bit entropy) so SHA-256 does not reduce security — it just removes the stored plaintext.
- Existing sessions are invalidated by the migration; users will need to re-authenticate once after deployment. Document this in the release notes.
- The atomic `UPDATE ... WHERE used = FALSE` pattern in `claim()` continues to work correctly with hashes.

## Success Criteria

- `sessions.token` column contains 64-char hex strings (SHA-256) after login.
- `magic_links.token` column contains 64-char hex strings after link generation.
- Login flow, session validation, and magic link claim all work end-to-end.
- Old plaintext tokens are invalidated on deploy.
