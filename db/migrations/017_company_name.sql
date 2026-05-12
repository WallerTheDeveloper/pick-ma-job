-- Add company_name column to job_results table
ALTER TABLE job_results ADD COLUMN IF NOT EXISTS company_name TEXT;