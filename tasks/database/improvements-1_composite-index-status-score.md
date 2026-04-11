# DB-8: No Composite Index for status + score Combined Queries

- **Phase:** improvements
- **Priority:** P3 (Medium)
- **Status:** DONE
- **Depends on:** None

## Problem

The most common query pattern — filter by status AND sort by score DESC — cannot be satisfied by either existing index alone (`idx_job_results_user_status` or `idx_job_results_user_score`). PostgreSQL must use one index and then re-sort or re-filter the results in memory.

## Approach

1. Create a new migration file.
2. Add a covering composite index:
   ```sql
   CREATE INDEX IF NOT EXISTS idx_job_results_user_score_status
       ON job_results(user_id, score DESC, status)
       INCLUDE (title, url, platform, created_at);
   ```
3. Add to `db/schema.sql` for new installs.
4. After deploying, verify with `EXPLAIN ANALYZE` that the new index is used.

## Files

- `db/schema.sql:96–97` — add index after existing indexes
- `db/migrations/` — new migration file

## Implementation Notes

- The `INCLUDE` clause makes this a covering index — queries can be answered from the index alone (index-only scan), avoiding heap lookups.
- Monitor index size — covering indexes are larger. If storage is a concern, drop the `INCLUDE` clause.
- Consider whether the existing `idx_job_results_user_status` and `idx_job_results_user_score` can be dropped since the new index subsumes them.
