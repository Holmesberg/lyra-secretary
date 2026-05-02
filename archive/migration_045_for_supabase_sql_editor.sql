-- Migration 045: reflection_view_log.event_class column + btree index.
-- Phase 1.5 of the 2026-05-02 system transition (docs/calibration_contract.md R7.1).
-- Apply BEFORE pulling code (per feedback_migration_first.md).
-- Run in Supabase SQL editor against project xrrboaxptttdzednaxwk.

-- 1. Add the column with DEFAULT — existing rows backfill to 'impression'.
--    All current rows ARE impressions (no telemetry types exist pre-Phase-6),
--    so DEFAULT is the correct backfill value.
ALTER TABLE reflection_view_log
  ADD COLUMN IF NOT EXISTS event_class VARCHAR(20) NOT NULL DEFAULT 'impression';

-- 2. Create the btree index for WHERE event_class = 'impression' /'telemetry' filters.
CREATE INDEX IF NOT EXISTS idx_reflection_view_event_class
  ON reflection_view_log(event_class);

-- 3. Bump alembic version table.
INSERT INTO alembic_version (version_num) VALUES ('045')
ON CONFLICT (version_num) DO NOTHING;
UPDATE alembic_version SET version_num = '045' WHERE version_num = '044';

-- Verify (paste into a new SQL editor query after running the above):
--   SELECT column_name, data_type, is_nullable, column_default
--     FROM information_schema.columns
--    WHERE table_name = 'reflection_view_log' AND column_name = 'event_class';
--
--   SELECT indexname FROM pg_indexes
--    WHERE tablename = 'reflection_view_log' AND indexname = 'idx_reflection_view_event_class';
--
--   SELECT version_num FROM alembic_version;  -- should return '045'
--
--   SELECT event_class, COUNT(*) FROM reflection_view_log GROUP BY event_class;
--   -- All rows should be 'impression' post-backfill.
