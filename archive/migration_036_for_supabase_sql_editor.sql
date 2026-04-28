-- Migration 036 — Task LLM enrichment columns (Workstream 1, magic-for-alpha).
--
-- Paste into Supabase SQL editor and Run. Same pooler-rolls-back-DDL
-- workaround as 033, 034, 035. Adds `llm_*` columns to `task` that the
-- async background parser (llm_enrichment APScheduler job) populates
-- after task creation. Critical guardrails:
--   - llm_inferred_deadline_id does NOT replace deadline_id; user must
--     confirm via POST /v1/tasks/{id}/llm-confirm.
--   - llm_parse_status defaults to 'pending'; flips to 'enriched',
--     'unavailable', or 'failed'.
--   - All fields are nullable except llm_parse_status (which has a
--     server default).

BEGIN;

-- Running upgrade 035 -> 036

ALTER TABLE task ADD COLUMN llm_parse_status VARCHAR(20) NOT NULL DEFAULT 'pending';

ALTER TABLE task ADD COLUMN llm_priority INTEGER;

ALTER TABLE task ADD COLUMN llm_inferred_deadline_id VARCHAR(36) REFERENCES deadline(deadline_id) ON DELETE SET NULL;

ALTER TABLE task ADD COLUMN llm_deadline_match_confidence FLOAT;

-- Tier system (2026-04-28): list of top candidates with confidences.
-- Shape: [{"deadline_id": "...", "title": "...", "confidence": 0..1}, ...]
-- Ordered desc, max 5 entries. Frontend tier logic reads this directly.
ALTER TABLE task ADD COLUMN llm_deadline_candidates JSONB;

ALTER TABLE task ADD COLUMN llm_sub_items JSONB;

ALTER TABLE task ADD COLUMN llm_parsed_at TIMESTAMP;

ALTER TABLE task ADD COLUMN llm_binding_rejected_at TIMESTAMP;

CREATE INDEX idx_task_llm_parse_pending ON task (llm_parse_status, created_at);

UPDATE alembic_version SET version_num='036' WHERE alembic_version.version_num = '035';

COMMIT;
