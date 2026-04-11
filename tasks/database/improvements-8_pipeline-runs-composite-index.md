# DB-15: Missing Composite Index on pipeline_runs(user_id, started_at DESC)

- **Phase:** improvements
- **Priority:** P4 (Low)
- **Status:** DONE
- **Depends on:** None

## Problem

`find_by_user` and `find_latest_by_user` filter by `user_id` and sort by `started_at DESC`. The existing single-column index `idx_pipeline_runs_user_id` covers the WHERE clause but requires a separate sort step for every query.

## Approach

1. Create a new migration file.
2. Add the composite index:
   ```sql
   CREATE INDEX IF NOT EXISTS idx_pipeline_runs_user_started ON pipeline_runs(user_id, started_at DESC);
   ```
3. Add to `db/schema.sql:112` for new installs.
4. Consider dropping the now-redundant `idx_pipeline_runs_user_id`.

## Files

- `db/schema.sql:112` — add alongside or replace existing index
- `db/migrations/` — new migration file

## Implementation Notes

- The composite index covers both `find_by_user` (sorted list) and `find_latest_by_user` (LIMIT 1) efficiently.
- The single-column `user_id` index is redundant once this composite index exists — dropping it saves write overhead and storage.
