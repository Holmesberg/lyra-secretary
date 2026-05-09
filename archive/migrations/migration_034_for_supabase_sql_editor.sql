-- Migration 034 — calibration_nudge_event (Loop 1 outcome log).
--
-- Paste this into the Supabase SQL editor and run. Apr 27 dogfood
-- confirmed Supabase's transaction-mode pooler (port 6543) silently
-- rolls back DDL transactions issued by alembic, so we apply manually.
-- Same pattern as migration_033_for_supabase_sql_editor.sql.

BEGIN;

-- Running upgrade 033 -> 034

CREATE TABLE calibration_nudge_event (
    event_id VARCHAR(36) NOT NULL,
    user_id INTEGER NOT NULL,
    task_id VARCHAR(36) NOT NULL,
    suggested_duration_minutes INTEGER NOT NULL,
    user_planned_duration_minutes INTEGER NOT NULL,
    bias_factor DOUBLE PRECISION NOT NULL,
    sample_size INTEGER NOT NULL,
    user_decision VARCHAR(16) NOT NULL,
    decided_at TIMESTAMP WITHOUT TIME ZONE NOT NULL,
    executed_duration_minutes INTEGER,
    resolved_at TIMESTAMP WITHOUT TIME ZONE,
    voided_at TIMESTAMP WITHOUT TIME ZONE,
    PRIMARY KEY (event_id),
    FOREIGN KEY (user_id) REFERENCES "user" (user_id),
    FOREIGN KEY (task_id) REFERENCES task (task_id)
);

CREATE INDEX idx_cne_user_decided ON calibration_nudge_event (user_id, decided_at);

CREATE INDEX idx_cne_task ON calibration_nudge_event (task_id);

UPDATE alembic_version SET version_num='034' WHERE alembic_version.version_num = '033';

COMMIT;
