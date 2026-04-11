-- Migration 006: composite index on pipeline_runs(user_id, started_at DESC)
--
-- find_by_user and find_latest_by_user filter by user_id and sort by started_at DESC.
-- The existing single-column user_id index covers the WHERE clause but requires a
-- separate sort step. The composite index eliminates that sort for both queries.
-- The single-column index is subsumed by the composite (leftmost-prefix rule).

DROP INDEX IF EXISTS idx_pipeline_runs_user_id;

CREATE INDEX IF NOT EXISTS idx_pipeline_runs_user_started
    ON pipeline_runs(user_id, started_at DESC);
