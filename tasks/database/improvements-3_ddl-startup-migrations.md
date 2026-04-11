# DB-10: DDL Runs on Every Startup — Numbered Migrations Never Applied

- **Phase:** improvements
- **Priority:** P3 (Medium)
- **Status:** DONE
- **Depends on:** None

## Problem

`init_db` in `db/pool.py:31–48` runs the full `schema.sql` on every app restart. The numbered migrations in `db/migrations/` (`001_expand_profiles.sql`, `002_multi_config_per_platform.sql`) are never applied automatically. DDL at startup acquires locks on system catalogs, can block under concurrent load, and couples migration logic to the connection pool lifecycle. The numbered migrations are effectively dead code.

## Approach

1. Create a simple ordered migration runner `db/migrate.py`:
   - Maintains a `schema_migrations` table: `CREATE TABLE IF NOT EXISTS schema_migrations (filename TEXT PRIMARY KEY, applied_at TIMESTAMPTZ DEFAULT now())`.
   - Reads `db/migrations/*.sql` in sorted order.
   - Applies only unapplied migrations within a transaction.
2. Move base schema into `db/migrations/000_initial_schema.sql` so all DDL flows through the migration system.
3. Remove or guard `init_db` behind `RUN_MIGRATIONS=true` env var.
4. Update `deploy.sh` to run migrations before restarting the service.

## Files

- `db/pool.py:31–48` — remove or guard `init_db` call from `create_pool`
- `db/migrate.py` — new migration runner
- `db/migrations/000_initial_schema.sql` — new file: move base schema from `schema.sql`
- `deploy.sh` — add migration step before service restart

## Implementation Notes

- Keep `schema.sql` as a reference/documentation file.
- The migration runner can be < 50 lines — no ORM or rollback support needed for MVP.
- Alternatively, adopt `yoyo-migrations` or `alembic` if a mature tool is preferred.
