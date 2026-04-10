-- Migration 002: allow multiple search configs per platform
-- Drops the UNIQUE (user_id, platform) constraint so a user can have
-- multiple configs for the same platform with different queries/filters.
--
-- Safe to run once against an existing database.
-- The schema.sql already reflects the post-migration state.

ALTER TABLE search_configs
    DROP CONSTRAINT IF EXISTS search_configs_user_id_platform_key;
