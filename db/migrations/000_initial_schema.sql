-- Migration 000: initial schema (baseline)
-- This file captures the full schema state as of the migration system introduction.
-- Applied automatically on fresh installs. On existing DBs bootstrapped via schema.sql,
-- this migration is pre-populated as already applied in schema_migrations.

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
    role              TEXT,
    experience        TEXT,
    rate              TEXT,
    primary_skills    TEXT[]      NOT NULL DEFAULT '{}',
    secondary_skills  TEXT[]      NOT NULL DEFAULT '{}',
    tertiary_skills   TEXT[]      NOT NULL DEFAULT '{}',
    not_a_good_fit    TEXT[]      NOT NULL DEFAULT '{}',
    background        TEXT[]      NOT NULL DEFAULT '{}',
    notable_projects  JSONB       NOT NULL DEFAULT '[]',
    languages         TEXT[]      NOT NULL DEFAULT '{}',
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
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
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

-- ── Pipeline Runs ────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS pipeline_runs (
    id           UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id      UUID        NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    status       TEXT        NOT NULL DEFAULT 'pending'
                             CHECK (status IN ('pending', 'running', 'completed', 'failed')),
    result       JSONB,
    error        TEXT,
    started_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    completed_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_pipeline_runs_user_id ON pipeline_runs(user_id);

-- ── Job Lists ─────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS job_lists (
    id         UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id    UUID        NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name       TEXT        NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_job_lists_user_id ON job_lists(user_id);

CREATE TABLE IF NOT EXISTS job_list_items (
    list_id       UUID        NOT NULL REFERENCES job_lists(id) ON DELETE CASCADE,
    job_result_id UUID        NOT NULL REFERENCES job_results(id) ON DELETE CASCADE,
    added_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (list_id, job_result_id)
);

CREATE INDEX IF NOT EXISTS idx_job_list_items_job_result_id ON job_list_items(job_result_id);
