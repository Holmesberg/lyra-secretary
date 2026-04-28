-- Migration 038: Resume prediction log (W2 magic-for-alpha 2026-04-28)
-- Apply BEFORE pulling the matching code commit (feedback_migration_first.md
-- — running new model code on un-migrated prod schema = sign-in breaks).

CREATE TABLE resume_prediction_log (
    firing_id VARCHAR(36) PRIMARY KEY,
    user_id INTEGER NOT NULL,
    session_id VARCHAR(36) NOT NULL REFERENCES stopwatch_session(session_id) ON DELETE CASCADE,
    task_id VARCHAR(36) NOT NULL REFERENCES task(task_id) ON DELETE CASCADE,
    fired_at TIMESTAMP NOT NULL,
    paused_for_minutes FLOAT NOT NULL,
    p75_pause_minutes FLOAT NULL,
    mechanism VARCHAR(40) NOT NULL,        -- 'category_tod' | 'cold_start_synthetic'
    confidence FLOAT NOT NULL,
    sample_size INTEGER NOT NULL,
    user_response VARCHAR(20) NULL,        -- 'resumed_within_window' | 'ignored' | 'snoozed' | 'no_response'
    response_at TIMESTAMP NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_resume_pred_user_fired_at ON resume_prediction_log(user_id, fired_at);
CREATE INDEX idx_resume_pred_session ON resume_prediction_log(session_id);

UPDATE alembic_version SET version_num = '038' WHERE version_num = '037';
