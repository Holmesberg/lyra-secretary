-- Migration 037: User alpha-funnel columns (North Star instrumentation)
-- Date: 2026-04-28
-- Apply BEFORE pulling the matching code commit (feedback_migration_first.md
-- — every SELECT 500s otherwise, sign-in breaks).

-- Three lazy-stamped timestamp columns for the alpha North Star
-- (task_created + timer_started within first 3 min):
--   first_task_at — stamped on first per-user task creation
--   first_timer_started_at — stamped on first timer start
--   d1_return_at — stamped on /users/me call ≥24h after user.created_at

ALTER TABLE "user" ADD COLUMN first_task_at TIMESTAMP NULL;
ALTER TABLE "user" ADD COLUMN first_timer_started_at TIMESTAMP NULL;
ALTER TABLE "user" ADD COLUMN d1_return_at TIMESTAMP NULL;

-- Update alembic_version so the Python migration recognises this as
-- already applied.
UPDATE alembic_version SET version_num = '037' WHERE version_num = '036';
