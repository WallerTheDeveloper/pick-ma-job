# Task 12 — Move Admin Role to Database

**Size:** S  
**Status:** todo  
**Priority:** MEDIUM

## Goal

Replace the `ADMIN_EMAIL` env-var single-admin check with an `is_admin` boolean column on the `users` table. Adds a second admin currently requires a redeploy.

## Problem

`api/deps.py → get_admin_user` checks `user.email == settings.admin_email`. Only one admin possible; changing it requires env var rotation and restart.

## Changes

**`db/migrations/`** — new migration
```sql
ALTER TABLE users ADD COLUMN IF NOT EXISTS is_admin BOOLEAN NOT NULL DEFAULT FALSE;
```

**Backfill on startup** in `main.py` lifespan (one-time):
```python
await pool.execute(
    "UPDATE users SET is_admin = TRUE WHERE email = $1",
    settings.admin_email,
)
```

**`repositories/user_repo.py`**
- `get_by_session_token` returns row including `is_admin`
- Add `set_admin(user_id, is_admin)` method

**`api/deps.py → get_admin_user`**
- Replace `user.email == settings.admin_email` with `user.is_admin is True`

**`ADMIN_EMAIL`** env var
- Keep for the one-time backfill; document as "used only on first boot to seed the admin row"

## Success Criteria

- Promoting a second user to admin via `UPDATE users SET is_admin=TRUE WHERE email='...'` works without restart
- `GET /api/admin/*` returns 403 for non-admin users
- `GET /api/admin/*` returns 200 for users with `is_admin=TRUE` regardless of `ADMIN_EMAIL`
