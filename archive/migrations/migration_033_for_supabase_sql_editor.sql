BEGIN;

-- Running upgrade 032 -> 033

CREATE TABLE deadline (
    deadline_id VARCHAR(36) NOT NULL,
    user_id INTEGER NOT NULL,
    title VARCHAR(255) NOT NULL,
    description TEXT,
    due_at_utc TIMESTAMP WITHOUT TIME ZONE NOT NULL,
    category_hint VARCHAR(100),
    state VARCHAR(20) DEFAULT 'planned' NOT NULL,
    completed_at TIMESTAMP WITHOUT TIME ZONE,
    voided_at TIMESTAMP WITHOUT TIME ZONE,
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now() NOT NULL,
    PRIMARY KEY (deadline_id),
    FOREIGN KEY(user_id) REFERENCES "user" (user_id)
);

CREATE INDEX idx_deadline_user_state ON deadline (user_id, state, voided_at);

CREATE TABLE task_deadline_outcome (
    task_id VARCHAR(36) NOT NULL,
    user_id INTEGER NOT NULL,
    computed_at TIMESTAMP WITHOUT TIME ZONE NOT NULL,
    deadline_utc_at_compute TIMESTAMP WITHOUT TIME ZONE NOT NULL,
    executed_end_utc_at_compute TIMESTAMP WITHOUT TIME ZONE NOT NULL,
    deadline_met BOOLEAN NOT NULL,
    delay_minutes INTEGER NOT NULL,
    voided_at TIMESTAMP WITHOUT TIME ZONE,
    PRIMARY KEY (task_id),
    FOREIGN KEY(task_id) REFERENCES task (task_id)
);

CREATE INDEX idx_tdo_user_computed ON task_deadline_outcome (user_id, computed_at);

ALTER TABLE task ADD COLUMN deadline_id VARCHAR(36);

ALTER TABLE task ADD FOREIGN KEY(deadline_id) REFERENCES deadline (deadline_id);

ALTER TABLE task ADD COLUMN deadline_match_confidence FLOAT;

ALTER TABLE task ADD COLUMN deadline_match_source VARCHAR(20);

ALTER TABLE task ADD COLUMN scope_bullet_count_at_plan INTEGER;

ALTER TABLE task ADD COLUMN scope_bullet_count_at_execute INTEGER;

CREATE INDEX idx_task_deadline_id ON task (deadline_id);

UPDATE alembic_version SET version_num='033' WHERE alembic_version.version_num = '032';

COMMIT;
