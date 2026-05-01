-- Migration 043: Moodle Web Services token + sync metadata
-- Apply this to Supabase SQL Editor BEFORE pulling the model changes
-- on prod (per feedback_migration_first.md — reverse order = SELECT
-- 500s = sign-in breaks).
--
-- Adds three columns to "user":
--   * moodle_ws_token TEXT — Web Services API token, plaintext per
--                            existing trust class (matches moodle_ics_url +
--                            google_refresh_token); Fernet encryption
--                            deferred to Phase 6+ security debt
--   * moodle_ws_last_synced_at TIMESTAMP — last successful submissions
--                                          sync time; surfaces in Settings
--   * moodle_ws_disconnect_reason VARCHAR(64) — set on permanent failure
--                                                (e.g., 'invalidtoken'
--                                                from Moodle 4xx); cleared
--                                                on successful reconnect
--
-- All additions are nullable / additive; no existing data altered.

BEGIN;

-- Running upgrade 042 -> 043

ALTER TABLE "user" ADD COLUMN moodle_ws_token TEXT;

ALTER TABLE "user" ADD COLUMN moodle_ws_last_synced_at TIMESTAMP WITHOUT TIME ZONE;

ALTER TABLE "user" ADD COLUMN moodle_ws_disconnect_reason VARCHAR(64);

UPDATE alembic_version SET version_num='043' WHERE version_num='042';

COMMIT;
