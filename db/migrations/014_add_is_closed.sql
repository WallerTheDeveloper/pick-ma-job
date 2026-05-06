-- Migration 014: add is_closed column to job_results
-- Indicates whether a job was flagged as no longer accepting applications
-- at the time it was scraped.

ALTER TABLE job_results
  ADD COLUMN IF NOT EXISTS is_closed BOOLEAN DEFAULT FALSE;
