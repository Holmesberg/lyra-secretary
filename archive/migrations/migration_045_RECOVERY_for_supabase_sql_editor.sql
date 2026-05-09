-- Migration 045 RECOVERY — re-apply schema-only parts.
-- The original migration_045_for_supabase_sql_editor.sql failed mid-transaction
-- on the alembic_version UPDATE (duplicate key), and Supabase rolled back the
-- entire transaction including the ALTER TABLE + CREATE INDEX. Result: JARVIS
-- 500s on analyze_behavioral_signature because event_class doesn't exist.
--
-- Run JUST these two statements. Both are idempotent (IF NOT EXISTS), so safe
-- to run even if the column already partially exists.

ALTER TABLE reflection_view_log
  ADD COLUMN IF NOT EXISTS event_class VARCHAR(20) NOT NULL DEFAULT 'impression';

CREATE INDEX IF NOT EXISTS idx_reflection_view_event_class
  ON reflection_view_log(event_class);

-- Verify (should return 1 row each):
--   SELECT column_name FROM information_schema.columns
--    WHERE table_name = 'reflection_view_log' AND column_name = 'event_class';
--
--   SELECT indexname FROM pg_indexes
--    WHERE tablename = 'reflection_view_log' AND indexname = 'idx_reflection_view_event_class';
--
-- Confirm all existing rows backfilled:
--   SELECT event_class, COUNT(*) FROM reflection_view_log GROUP BY event_class;
--   -- All rows should be 'impression'.
--
-- alembic_version is already at '045' from the prior partial run, no change needed.
