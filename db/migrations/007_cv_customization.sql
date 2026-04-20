-- Add cv_customize_threshold to profiles; create cvs and cv_customizations tables.

ALTER TABLE profiles
    ADD COLUMN IF NOT EXISTS cv_customize_threshold INTEGER NOT NULL DEFAULT 7;

CREATE TABLE IF NOT EXISTS cvs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    filename TEXT NOT NULL,
    raw_text TEXT NOT NULL,
    structured JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (user_id)
);

CREATE TABLE IF NOT EXISTS cv_customizations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    job_result_id UUID NOT NULL REFERENCES job_results(id) ON DELETE CASCADE,
    customized_text TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (user_id, job_result_id)
);
