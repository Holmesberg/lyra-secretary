-- Migration 044: per-user Moodle userid + base URL.
-- Apply BEFORE pulling code (per feedback_migration_first.md).
-- Run in Supabase SQL editor against project xrrboaxptttdzednaxwk.

ALTER TABLE "user" ADD COLUMN IF NOT EXISTS moodle_userid INTEGER;
ALTER TABLE "user" ADD COLUMN IF NOT EXISTS moodle_base_url VARCHAR(512);

-- Bump alembic version table.
INSERT INTO alembic_version (version_num) VALUES ('044')
ON CONFLICT (version_num) DO NOTHING;
UPDATE alembic_version SET version_num = '044' WHERE version_num = '043';

-- Verify:
-- SELECT column_name FROM information_schema.columns
--  WHERE table_name = 'user' AND column_name IN ('moodle_userid','moodle_base_url');
