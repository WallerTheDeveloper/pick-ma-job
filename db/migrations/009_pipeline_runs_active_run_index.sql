-- Migration 009: index on pipeline_runs(user_id, status) for active-run check
--
-- RunManager._has_active_run now queries the DB instead of an in-memory dict.
-- This index makes the WHERE user_id = $1 AND status IN ('pending', 'running')
-- lookup fast without a sequential scan.

CREATE INDEX IF NOT EXISTS idx_pipeline_runs_user_status
    ON pipeline_runs(user_id, status);
