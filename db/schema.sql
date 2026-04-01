-- pick-ma-job database schema
-- Idempotent: safe to run multiple times (CREATE TABLE IF NOT EXISTS)

CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- ── Users ────────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS users (
    id         UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    email      TEXT        UNIQUE NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    last_login TIMESTAMPTZ
);

-- ── Sessions ─────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS sessions (
    id         UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id    UUID        NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token      TEXT        UNIQUE NOT NULL,
    expires_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_sessions_token ON sessions(token);
CREATE INDEX IF NOT EXISTS idx_sessions_user_id ON sessions(user_id);

-- ── Magic Links ───────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS magic_links (
    id         UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id    UUID        NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token      TEXT        UNIQUE NOT NULL,
    used       BOOLEAN     NOT NULL DEFAULT FALSE,
    expires_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_magic_links_token ON magic_links(token);
CREATE INDEX IF NOT EXISTS idx_magic_links_user_id ON magic_links(user_id);

-- ── Profiles ──────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS profiles (
    id                UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id           UUID        UNIQUE NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    -- Identity
    role              TEXT,
    experience        TEXT,
    rate              TEXT,
    -- Skills (tiered)
    primary_skills    TEXT[]      NOT NULL DEFAULT '{}',
    secondary_skills  TEXT[]      NOT NULL DEFAULT '{}',
    tertiary_skills   TEXT[]      NOT NULL DEFAULT '{}',
    -- Fit criteria
    not_a_good_fit    TEXT[]      NOT NULL DEFAULT '{}',
    -- Background
    background        TEXT[]      NOT NULL DEFAULT '{}',
    notable_projects  JSONB       NOT NULL DEFAULT '[]',
    languages         TEXT[]      NOT NULL DEFAULT '{}',
    -- Evaluator config
    rubric            JSONB       NOT NULL DEFAULT '{}',
    updated_at        TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ── Search Configs ────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS search_configs (
    id         UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id    UUID        NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    platform   TEXT        NOT NULL,
    query      TEXT,
    filters    JSONB       NOT NULL DEFAULT '{}',
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (user_id, platform)
);

CREATE INDEX IF NOT EXISTS idx_search_configs_user_id ON search_configs(user_id);

-- ── Job Results ───────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS job_results (
    id         UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id    UUID        NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    platform   TEXT        NOT NULL,
    job_id     TEXT        NOT NULL,
    title      TEXT        NOT NULL,
    url        TEXT        NOT NULL,
    score      INTEGER     CHECK (score BETWEEN 1 AND 10),
    evaluation JSONB,
    status     TEXT        NOT NULL DEFAULT 'new'
                           CHECK (status IN ('new', 'applied', 'dismissed')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (user_id, platform, job_id)
);

CREATE INDEX IF NOT EXISTS idx_job_results_user_status ON job_results(user_id, status);
CREATE INDEX IF NOT EXISTS idx_job_results_user_score  ON job_results(user_id, score DESC);
