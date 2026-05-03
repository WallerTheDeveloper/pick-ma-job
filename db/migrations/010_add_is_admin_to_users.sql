-- Migration 010: add is_admin column to users table
-- Replaces the single-admin ADMIN_EMAIL env-var check with a DB-backed flag.

ALTER TABLE users ADD COLUMN IF NOT EXISTS is_admin BOOLEAN NOT NULL DEFAULT FALSE;
