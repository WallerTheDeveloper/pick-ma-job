-- Migration 012: add skip_reason and detected_language columns to job_results
-- These columns support the language filtering feature:
--   - skip_reason: why a job was skipped (e.g., 'language')
--   - detected_language: the language detected by the LLM (e.g., 'Dutch', 'French')

ALTER TABLE job_results
  ADD COLUMN IF NOT EXISTS skip_reason TEXT,
  ADD COLUMN IF NOT EXISTS detected_language TEXT;