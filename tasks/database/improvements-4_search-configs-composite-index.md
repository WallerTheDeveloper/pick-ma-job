# DB-11: Missing Composite Index on search_configs(user_id, platform)

- **Phase:** improvements
- **Priority:** P3 (Medium)
- **Status:** DONE
- **Depends on:** None

## Problem

`find_by_user_and_platform` filters on both `user_id` AND `platform`, but only a single-column `user_id` index exists (`idx_search_configs_user_id`). PostgreSQL must scan all configs for a user and then filter by platform in memory.

## Approach

1. Create a new migration file.
2. Add the composite index:
   ```sql
   CREATE INDEX IF NOT EXISTS idx_search_configs_user_platform ON search_configs(user_id, platform);
   ```
3. Add to `db/schema.sql:77` for new installs.
4. Consider dropping the now-redundant `idx_search_configs_user_id` since the composite index covers `user_id`-only queries as well (leftmost prefix rule).

## Files

- `db/schema.sql:77` — replace or add alongside existing index
- `db/migrations/` — new migration file

## Implementation Notes

- The composite index subsumes the single-column `user_id` index for all queries that filter on `user_id`.
- This is a small table (few rows per user), so the performance impact is minimal today — the index matters more as user count grows.
