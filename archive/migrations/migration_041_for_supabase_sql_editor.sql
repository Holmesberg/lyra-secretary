-- Migration 041: Moodle LMS integration
-- Apply this to Supabase SQL Editor BEFORE pulling the model changes
-- on prod (per feedback_migration_first.md — reverse order = SELECT
-- 500s = sign-in breaks).
--
-- Adds:
--   * deadline.external_source, external_id, imported_at  (LMS deadlines marked vs native)
--   * Partial unique index for upsert keying on (user_id, external_source, external_id)
--   * user.moodle_ics_url, moodle_last_synced_at, moodle_disconnect_reason
--
-- All additions are nullable / additive; no existing data altered.

BEGIN;

-- Running upgrade 040 -> 041

ALTER TABLE deadline ADD COLUMN external_source VARCHAR(32);

ALTER TABLE deadline ADD COLUMN external_id VARCHAR(256);

ALTER TABLE deadline ADD COLUMN imported_at TIMESTAMP WITHOUT TIME ZONE;

CREATE UNIQUE INDEX uq_deadline_external
    ON deadline (user_id, external_source, external_id)
    WHERE external_source IS NOT NULL;

ALTER TABLE "user" ADD COLUMN moodle_ics_url TEXT;

ALTER TABLE "user" ADD COLUMN moodle_last_synced_at TIMESTAMP WITHOUT TIME ZONE;

ALTER TABLE "user" ADD COLUMN moodle_disconnect_reason VARCHAR(64);

UPDATE alembic_version SET version_num='041' WHERE version_num='040';

COMMIT;
