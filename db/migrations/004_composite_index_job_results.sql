-- Migration 004: covering composite index on job_results(user_id, score DESC, status)
--
-- The primary query pattern — filter by status AND sort by score DESC — cannot be
-- satisfied by the existing single-column indexes alone. This covering index lets
-- PostgreSQL answer filtered/sorted queries with an index-only scan.
--
-- The old indexes are subsumed by the new one (leftmost-prefix rule covers
-- user_id-only queries; status is included in the leaf pages).

DROP INDEX IF EXISTS idx_job_results_user_status;
DROP INDEX IF EXISTS idx_job_results_user_score;

CREATE INDEX IF NOT EXISTS idx_job_results_user_score_status
    ON job_results(user_id, score DESC NULLS LAST, status)
    INCLUDE (title, url, platform, created_at);
