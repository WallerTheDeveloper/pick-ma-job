-- Migration 001: expand profiles table with explicit columns
-- Replaces the generic `skills` JSONB column with tiered TEXT[] columns
-- and adds role, background, notable_projects, languages.
--
-- Safe to run once against an existing database.
-- The schema.sql already reflects the post-migration state.

ALTER TABLE profiles
    ADD COLUMN IF NOT EXISTS role             TEXT,
    ADD COLUMN IF NOT EXISTS primary_skills   TEXT[]  NOT NULL DEFAULT '{}',
    ADD COLUMN IF NOT EXISTS secondary_skills TEXT[]  NOT NULL DEFAULT '{}',
    ADD COLUMN IF NOT EXISTS tertiary_skills  TEXT[]  NOT NULL DEFAULT '{}',
    ADD COLUMN IF NOT EXISTS not_a_good_fit   TEXT[]  NOT NULL DEFAULT '{}',
    ADD COLUMN IF NOT EXISTS background       TEXT[]  NOT NULL DEFAULT '{}',
    ADD COLUMN IF NOT EXISTS notable_projects JSONB   NOT NULL DEFAULT '[]',
    ADD COLUMN IF NOT EXISTS languages        TEXT[]  NOT NULL DEFAULT '{}';

-- Migrate existing flat skills data into primary_skills, then drop old column.
UPDATE profiles
SET primary_skills = ARRAY(SELECT jsonb_array_elements_text(skills))
WHERE skills IS NOT NULL AND skills != '[]'::jsonb;

ALTER TABLE profiles DROP COLUMN IF EXISTS skills;
