# Task 1 — Create company_blacklist DB migration

**Size:** S  
**Status:** done

## Goal

Create the SQL migration that introduces the `company_blacklist` table.

## Migration

File: `migrations/NNN_company_blacklist.sql`

```sql
CREATE TABLE company_blacklist (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    name_lower TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (user_id, name_lower)
);
CREATE INDEX idx_company_blacklist_user ON company_blacklist(user_id);
```

## Notes

- `name_lower` stores `name.strip().lower()` — enables case-insensitive uniqueness via a simple constraint (no expression index needed).
- `ON DELETE CASCADE` clears entries when the user is deleted.
- `UNIQUE(user_id, name_lower)` is the dedup constraint; the repo uses `ON CONFLICT DO NOTHING`.

## Success Criteria

- Migration runs without error on a clean DB.
- `UNIQUE(user_id, name_lower)` prevents duplicate entries for the same user.
- Deleting a user cascades to their blacklist rows.
