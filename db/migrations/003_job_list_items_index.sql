-- Migration 003: Add index on job_list_items(job_result_id)
--
-- The composite PK (list_id, job_result_id) only indexes on list_id as the
-- leading column. Queries filtering by job_result_id alone (cascade deletes,
-- get_list_ids_for_job) trigger a sequential scan without this index.

CREATE INDEX IF NOT EXISTS idx_job_list_items_job_result_id ON job_list_items(job_result_id);
