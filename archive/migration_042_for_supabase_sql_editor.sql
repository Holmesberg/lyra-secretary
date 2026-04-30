-- Migration 042: JARVIS invocation audit log
-- Apply this to Supabase SQL Editor BEFORE pulling the model changes
-- on prod (per feedback_migration_first.md — reverse order = SELECT
-- 500s = sign-in breaks).
--
-- Adds:
--   * jarvis_invocation table — audit trail for every JARVIS tool call
--   * Composite index (user_id, invoked_at) for the recency-per-user query
--
-- TaskSource enum gains a 'jarvis' value at the Python layer only — the
-- task.source column is VARCHAR(20), not a Postgres ENUM, so no schema
-- change is required for that part.
--
-- All additions are additive; no existing data altered.

BEGIN;

-- Running upgrade 041 -> 042

-- Extend task.source CHECK constraint to permit 'jarvis' (added in alembic
-- 016 with 'web', now extended again). Postgres requires drop + add since
-- the constraint name is reused.
ALTER TABLE task DROP CONSTRAINT IF EXISTS check_source;
ALTER TABLE task ADD CONSTRAINT check_source
    CHECK (source IN ('manual', 'voice', 'web', 'jarvis'));

CREATE TABLE jarvis_invocation (
    invocation_id        VARCHAR(36) NOT NULL,
    user_id              INTEGER NOT NULL,
    tool_name            VARCHAR(64) NOT NULL,
    tool_args            JSONB,
    tool_result_summary  VARCHAR(500),
    status               VARCHAR(32) NOT NULL DEFAULT 'executed',
    invoked_at           TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT now(),
    confirmed_at         TIMESTAMP WITHOUT TIME ZONE,
    PRIMARY KEY (invocation_id),
    FOREIGN KEY (user_id) REFERENCES "user" (user_id) ON DELETE CASCADE
);

CREATE INDEX ix_jarvis_invocation_user_id
    ON jarvis_invocation (user_id);

CREATE INDEX ix_jarvis_invocation_tool_name
    ON jarvis_invocation (tool_name);

CREATE INDEX ix_jarvis_invocation_user_invoked_at
    ON jarvis_invocation (user_id, invoked_at);

UPDATE alembic_version SET version_num='042' WHERE version_num='041';

COMMIT;
