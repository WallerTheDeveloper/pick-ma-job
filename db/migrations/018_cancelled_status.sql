-- Add 'cancelled' as a valid pipeline run status.
ALTER TABLE pipeline_runs DROP CONSTRAINT IF EXISTS pipeline_runs_status_check;
ALTER TABLE pipeline_runs ADD CONSTRAINT pipeline_runs_status_check 
  CHECK (status IN ('pending', 'running', 'completed', 'failed', 'cancelled'));