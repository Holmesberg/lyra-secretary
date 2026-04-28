-- Migration 039: Task llm_alternative_suggestion (trust-not-rewrite, 2026-04-28)
-- Apply BEFORE pulling the matching code commit (feedback_migration_first.md).
--
-- Adds the JSONB column the magic-for-alpha "possible better match" flow
-- uses to surface LLM disagreements with heuristic/user bindings without
-- silently overwriting task.deadline_id.

ALTER TABLE task ADD COLUMN llm_alternative_suggestion JSONB NULL;

UPDATE alembic_version SET version_num = '039' WHERE version_num = '038';
