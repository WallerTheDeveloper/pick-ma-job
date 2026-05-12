CREATE TABLE proposals (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  job_result_id UUID NOT NULL REFERENCES job_results(id) ON DELETE CASCADE,
  proposal_text TEXT NOT NULL,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE(user_id, job_result_id)
);
CREATE INDEX idx_proposals_user_job ON proposals(user_id, job_result_id);