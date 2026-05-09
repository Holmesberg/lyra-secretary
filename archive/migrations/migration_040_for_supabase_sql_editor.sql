-- Migration 040: Feedback table (alpha-cohort feedback channel, 2026-04-28)
-- Apply BEFORE pulling matching code commit (feedback_migration_first.md).

CREATE TABLE feedback (
    feedback_id VARCHAR(36) PRIMARY KEY,
    user_id INTEGER NULL REFERENCES "user"(user_id) ON DELETE SET NULL,
    submitted_at TIMESTAMP NOT NULL,
    kind VARCHAR(20) NOT NULL,            -- 'bug' | 'suggestion' | 'confused' | 'other'
    body TEXT NOT NULL,
    page_url VARCHAR(500) NULL,
    user_agent VARCHAR(500) NULL,
    error_context JSONB NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'unread',
                                          -- 'unread' | 'read' | 'acted_on' | 'dismissed'
    operator_note TEXT NULL,
    resolved_at TIMESTAMP NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_feedback_status_submitted ON feedback(status, submitted_at DESC);

UPDATE alembic_version SET version_num = '040' WHERE version_num = '039';
