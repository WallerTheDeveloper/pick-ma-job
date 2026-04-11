-- Migration 005: composite index on search_configs(user_id, platform)
--
-- find_by_user_and_platform filters on both user_id AND platform. The existing
-- single-column user_id index forces a post-filter step in memory. The composite
-- index satisfies both the equality filter and covers user_id-only queries via
-- the leftmost-prefix rule, making the old single-column index redundant.

DROP INDEX IF EXISTS idx_search_configs_user_id;

CREATE INDEX IF NOT EXISTS idx_search_configs_user_platform
    ON search_configs(user_id, platform);
