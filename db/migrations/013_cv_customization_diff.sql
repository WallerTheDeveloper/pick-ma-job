-- Add customized_diff JSONB column for diff-style CV customization output.

ALTER TABLE cv_customizations
    ADD COLUMN IF NOT EXISTS customized_diff JSONB;

-- Add updated_at column if it doesn't exist (for cache invalidation)
ALTER TABLE cv_customizations
    ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ NOT NULL DEFAULT now();
