-- Migration 035 — reflection_view_log.outcome (V3 engagement-signal coverage).
--
-- Paste into Supabase SQL editor and Run. Same pooler-rolls-back-DDL workaround
-- as migrations 033 and 034. Closes the V3 logging-spec gap caught in the
-- Apr 27 drift audit per docs/phase_6_architecture_backlog.md:227.

BEGIN;

-- Running upgrade 034 -> 035

ALTER TABLE reflection_view_log ADD COLUMN outcome VARCHAR(20);

UPDATE alembic_version SET version_num='035' WHERE alembic_version.version_num = '034';

COMMIT;
