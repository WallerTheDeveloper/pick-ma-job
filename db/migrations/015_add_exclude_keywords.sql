ALTER TABLE profiles
  ADD COLUMN IF NOT EXISTS exclude_keywords TEXT[] DEFAULT '{}';
