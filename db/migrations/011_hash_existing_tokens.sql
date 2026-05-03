-- Existing rows have plain-text tokens; they are short-lived so truncating
-- is acceptable. Invalidate all current sessions and magic links on deploy.
TRUNCATE sessions;
TRUNCATE magic_links;
