# Moodle LMS Integration

**Shipped:** 2026-04-29 (alembic 041)
**Status:** Live for ASU Engineering Faculty (lms.eng.asu.edu.eg) and any standard Moodle 3.x/4.x install. Tested against Moodle 2019052001.1.

This is the LMS-wedge integration — the bet that "connect your school and Lyra organizes your semester automatically" is the strongest single retention move for the Egyptian engineering student segment. Tier A1 of the strategic plan dated April 29.

---

## What it does

User pastes their private Moodle calendar `.ics` subscription URL into Settings → Integrations → Moodle → Connect. Backend:

1. Validates the URL shape (must contain `/calendar/export_execute.php` + `authtoken=`).
2. Fetches the feed once for preview, parses VEVENTs, returns sample to the user for confirmation.
3. On Connect, stores the URL on `user.moodle_ics_url`, runs an immediate sync, then schedules a periodic sync every 6 hours.
4. Imports each VEVENT as a Lyra `Deadline` with `external_source='moodle_ics'`, `external_id=<iCal UID>`, `imported_at=now()`.
5. Re-running the sync upserts: new events created, changed `due_at_utc` (deadline extensions) updated, unchanged are no-ops, voided rows are not resurrected.

The user sees imported deadlines on `/deadlines` with a small "Moodle" badge so they can distinguish them from Lyra-native ones.

---

## Architecture (file-by-file)

| Layer | Path | Responsibility |
|---|---|---|
| Schema | `backend/alembic/versions/041_moodle_lms_integration.py` | Adds `deadline.external_source`, `deadline.external_id`, `deadline.imported_at`, partial unique index `uq_deadline_external`, `user.moodle_ics_url`, `user.moodle_last_synced_at`, `user.moodle_disconnect_reason` |
| Schema (Supabase) | `archive/migration_041_for_supabase_sql_editor.sql` | The same DDL extracted as raw SQL for operator-side Supabase application BEFORE pulling new code on prod (per `feedback_migration_first` memory) |
| Models | `backend/app/db/models.py` | `Deadline.external_source / external_id / imported_at` columns; `User.moodle_ics_url / moodle_last_synced_at / moodle_disconnect_reason` |
| Sync service | `backend/app/services/moodle_ics_sync.py` | `fetch_ics()`, `parse_calendar()`, `_parse_one_event()`, `_extract_course_code()`, `preview()`, `sync_user()`, `validate_url_shape()`, `_redact_url()` |
| Mutation authority | `backend/app/services/deadline_manager.py` | New `DeadlineManager.upsert_external_deadline()` keyed on `(user_id, external_source, external_id)` — returns `created` / `updated` / `unchanged` / `skipped_voided` |
| Endpoints | `backend/app/api/v1/endpoints/moodle.py` | `POST /v1/integrations/moodle/preview`, `POST /connect`, `POST /sync-now`, `DELETE /disconnect` |
| Endpoints (status) | `backend/app/api/v1/endpoints/integrations.py` | `GET /v1/integrations` returns Moodle row with `last_synced_at` + `disconnect_reason` |
| Router | `backend/app/api/v1/router.py` | Registers the moodle router |
| APScheduler job | `backend/app/workers/jobs/moodle_ics_sync.py` + `backend/app/workers/scheduler.py` | Every 6h per user with `moodle_ics_url IS NOT NULL`, `max_instances=1` |
| Frontend registry | `frontend/lib/integrations.ts` | Moodle entry `available: true`, API helpers `previewMoodle`, `connectMoodle`, `syncMoodleNow`; `disconnectIntegration('moodle')` route |
| Frontend modal | `frontend/components/integrations/MoodleConnectModal.tsx` | 4-step flow: instructions → paste → preview → success |
| Frontend integration card | `frontend/components/integration-card.tsx` | Renders `url_subscription` shape (Connect button → `onConnectClick` callback); shows "Reconnect needed" when `disconnect_reason` set; shows "Last synced …" when `last_synced_at` set |
| Frontend section | `frontend/components/integrations-section.tsx` | Holds modal open state, wires `onConnected` callback to invalidate `["integrations"]` + `["deadlines"]` queries + show success banner |
| Frontend Deadline schema | `frontend/lib/deadlines.ts` + `backend/app/schemas/deadline.py` | `DeadlineResponse` extended with optional `external_source`, `external_id`, `imported_at` |
| Frontend deadline rows | `frontend/components/deadline-row.tsx` + `frontend/app/(app)/deadlines/page.tsx` | "Moodle" badge when `external_source === 'moodle_ics'` |
| Tests | `backend/tests/test_moodle_ics_sync.py` + `backend/tests/fixtures/moodle_sample.ics` | 21 tests: parsing (real fixture + synthetic edges) + url validation + redaction + upsert contract + multi-user isolation |
| Job-count gate | `backend/tests/test_state_consistency.py` | Updated `test_apscheduler_job_count` 12→13 |

---

## Research-integrity contract

Imported deadlines fundamentally differ from native (user-typed) deadlines in three ways:
- **Zero user agency in the timestamp** — the user didn't choose the time; the LMS did.
- **Different (deadline_distance, met_or_missed) distribution** — imported assignments cluster at end-of-week / midnight, native ones spread.
- **Different bias_factor regime per Rule 15.**

Therefore:

- All H2 read endpoints **default to filtering** `WHERE external_source IS NULL` so H2 stays a hypothesis about user-specified deadlines.
- The `/v1/analytics/deadline-shape?include_external=true` opt-in is the operator-only switch for running the **VT-29 contamination test** (effect size with vs without imports; threshold 0.30).
- The `reconcile_deadline_outcomes` job processes **both** native and imported deadlines (data preserved); filtering happens at analysis read time only — this is what enables the contamination test.

VT-29 is pre-registered in `MANIFESTO.md` with three distinguishing analyses (29a effect-size diff, 29b KS distribution test, 29c time-of-day clustering check). Activates with the first imported deadline.

---

## Credential discipline

`user.moodle_ics_url` contains a per-user `authtoken` — anyone with the URL can read the user's Moodle calendar. Treat as credential-equivalent.

- **Storage:** plaintext in v1, same trust class as `user.google_refresh_token`. Fernet encryption is Phase 6+ security debt.
- **Logging:** `_redact_url()` masks the authtoken before any `logger.warning()`. Never log full URLs.
- **API responses:** `GET /v1/integrations` returns `status` + `last_synced_at` + `disconnect_reason` only. Never echoes `moodle_ics_url`.
- **Errors:** error responses include status codes (e.g. `http_401`) but never the URL.

---

## Operational behaviors

**Sync cadence:** 6 hours per connected user. Matches Moodle's "several hours" propagation window from the docs. Faster polling would be impolite to LMS servers and not yield faster updates.

**Per-event upsert keying:** `(user_id, external_source, external_id)` where `external_id` = the iCal UID (e.g. `74913@lms.eng.asu.edu.eg`). UIDs are stable across Moodle's lifetime so the same event always maps to the same Lyra deadline row.

**Skip rules** (silent — these are normal in real feeds):
- Has `RRULE` → recurring lecture schedule, not a deadline.
- `DTSTART` is a `date` not `datetime` → all-day event, lacks deadline-time precision.
- Missing `UID`, `SUMMARY`, or `DTSTART` → can't anchor.

**Token revocation:** when `fetch_ics()` returns 4xx, the URL is auto-cleared, `moodle_disconnect_reason` is set to `token_invalid_<status>`, and the frontend shows "Reconnect needed". User pastes a fresh URL → reconnects.

**Transient LMS failures:** 5xx responses such as `http_503` are not treated as
token rotation. Lyra keeps the stored URL, leaves the integration connected,
and retries on the next 6h cycle. Operator notifications must distinguish 4xx
reconnect-needed failures from 5xx server-unavailable failures.

**Voided rows:** if a user explicitly voids an imported deadline, the next sync sees it and returns `skipped_voided` rather than resurrecting it. Permanent ignore. To reset, user disconnects + reconnects.

**Disconnect:** `DELETE /v1/integrations/moodle/disconnect` clears `moodle_ics_url` (sync stops). Optional `void_imported: true` body voids all `external_source='moodle_ics'` deadlines. Default is keep-as-is — sync stops, deadlines remain as Lyra-owned rows.

**Cap:** `MAX_EVENTS_PER_SYNC = 500` per fetch — defensive ceiling against malformed feeds.

---

## Known limitations (v1)

1. **No deletion sync.** If a Moodle event is deleted server-side, the corresponding Lyra deadline isn't auto-voided. Reason: `preset_time=recentupcoming` only spans ~60 days, so an event missing from the fetch could be either deleted OR aged out of the window. To distinguish safely, we'd need to track each fetch's window bounds and only consider rows in-window. Defer to v1.1.
2. **Title cleanup.** Imported titles include the "is due" suffix Moodle adds (e.g. "HandsOn Lab8 is due"). Could strip with `re.sub(r'\s+is due$', '', title)`. Kept raw in v1 because the suffix is information-bearing ("this is an assignment, not a class"). Polish later.
3. **No de-dup against native deadlines.** If the user manually creates "BCI Project due 16/5" and Moodle later imports the same thing, you get two rows. v1.1 should add a Levenshtein-similarity de-dup heuristic.
4. **Course code extraction is regex-only.** `^([A-Z]{2,4}\d{2,4})\b` matches typical patterns (CSE281, ABC101, PHM123) but misses non-standard formats. Document any failure modes in the dogfood log.
5. **No Fernet encryption.** Per Phase 6+ security debt; matches existing `google_refresh_token` convention.
6. **No file-upload fallback.** If a school's Moodle gates the `.ics` URL behind a session cookie (some installs do), Path A fails. Path C (manual `.ics` file upload, Phase 7+) is the fallback.

---

## Operator deploy runbook

Per `feedback_migration_first` memory: SQL migration on Supabase BEFORE pulling on prod.

1. **Apply the schema.** Copy `archive/migration_041_for_supabase_sql_editor.sql` into Supabase SQL Editor. Paste, click Run. Verify `alembic_version` table shows `version_num='041'`.
2. **Install the new dependency.** On the production host: `pip install icalendar==5.0.11` (or `pip install -r backend/requirements.txt` from a fresh venv).
3. **Pull the code.** `git pull origin main` on the prod host.
4. **Restart backend + frontend.** `docker-compose restart backend` (backend will register the new APScheduler job). `cd frontend && npm run build && npm run start` (cold restart per `feedback_nextjs_dev_restart` memory).
5. **Smoke test.** Visit `lyraos.org/settings`, confirm Moodle card now shows "Not connected" with a Connect button. Click Connect, paste your own ASU Moodle URL, confirm preview shows your real assignments, click Connect, confirm `/deadlines` shows them with the "Moodle" badge.
6. **Verify the job.** `docker-compose logs backend | grep moodle` should show `moodle: user N sync ok` lines after the first 6h tick.

If anything blocks, the rollback is: `DELETE FROM "user" WHERE moodle_ics_url IS NOT NULL` (clears all Moodle data) + revert the commit. Imported deadlines are still Lyra rows so they persist with `external_source='moodle_ics'` — the `WHERE external_source IS NULL` filters keep H2 safe even if the integration is rolled back.

---

## v1.1 — Web Services submission detection + backfill (2026-05-01)

`backend/app/services/moodle_submissions_sync.py` adds a second sync layer using Moodle's REST API (token from Moodle → Preferences → Security keys, stored on `user.moodle_ws_token` per alembic 043). Runs every 6h alongside the iCal job.

**Two responsibilities:**

1. **Mark complete.** Match each active iCal-imported deadline to a Moodle assignment (course-code constrained — see operator decision below — then title-fuzzy + due-date proximity); if Moodle reports `submission.status='submitted'` or any non-null grade, transition the deadline to `state='completed'` with `completed_at=now()`.

2. **Backfill (operator request 2026-05-01).** For Moodle assignments that don't match any existing Lyra deadline (because the iCal feed's "Recent and upcoming" filter excluded them), create new deadlines tagged `external_source='moodle_ws_backfill'`:
   - Submitted → `state='completed'`, `completed_at` from Moodle's `submission.timemodified`
   - Unsubmitted + past due → `state='missed'`
   - Unsubmitted + future due → `state='planned'`

   Window: 90 days back + all future. Dedup against any existing iCal/backfill deadline (including voided rows so explicit user voids aren't resurrected) via three tiers: exact `external_id`, course-code + due-date within 6h, fuzzy title + course-code + due-date within 24h.

**Course-code constraint.** Match logic requires the same course code (regex `\b[A-Z]{2,5}\d{2,4}\b` against `category_hint` for Lyra side and `course.shortname` for Moodle side) before considering title similarity. Came from the operator's false-positive: "Formative quiz 1 closes" (CSE281) was matching "Quiz 1 (5 marks)" (PHM112) on text alone. Course code is the structural noise filter; title is the within-course tie-breaker.

**Research integrity (VT-29 / H1).** Backfilled deadlines carry `external_source='moodle_ws_backfill'`, so research queries filtering `WHERE external_source IS NULL` continue to exclude them — same template as the iCal layer.

## v1.2 — Multi-user + Fernet encryption (2026-05-01, alembic 044)

Discovered while answering operator's question "would [WS backfill] also work for users too?" — answer was no, the v1.1 ship resolved Moodle's userid from a single global env (`MOODLE_WS_USERID`). Any non-operator user connecting WS would hit Moodle's permission model: a wstoken is bound to its user, so `core_enrol_get_users_courses(userid=<other>)` raises `accessexception` → my code flips `moodle_ws_disconnect_reason='invalidtoken'` even though the token is valid. Net effect: alpha-blocking.

**Schema (alembic 044):**
- `user.moodle_userid INTEGER` — captured from `core_webservice_get_site_info`'s response at WS connect.
- `user.moodle_base_url VARCHAR(512)` — per-user (different schools = different Moodle hosts; ASU is `lms.eng.asu.edu.eg`, but the column makes us host-agnostic for future cohorts).

**Resolution chain at connect time** (in priority order):
1. Body param `base_url` (explicit override)
2. Derive from `user.moodle_ics_url` host (works whenever the user has connected the iCal calendar)
3. Env `MOODLE_WS_BASE_URL` (legacy operator fallback)

For the alpha (ASU only), the env fallback handles users who paste only the WS token without the calendar URL — they're all on the same Moodle host. Once the cohort expands, the iCal-derive path covers any school the user has connected; the env can be retired.

**Encryption (Fernet, `utils/encryption.py`):**
Token stored as `"fernet:" + base64(encrypted)`. Key derived from `SECRET_KEY` via SHA-256 → urlsafe-base64. The legacy operator's plaintext token continues to work via prefix-sniff: `decrypt_secret()` returns the value unchanged if it doesn't carry the `fernet:` prefix. No forced re-connect, no data migration.

Future rotation: rotating `SECRET_KEY` invalidates all Fernet-encrypted tokens. Phase 6+ will add an HKDF salt + key-version column for safe rotation; for v1.2 the trade-off is "encrypt the WS token now, accept that key rotation = forced re-connect."

**Sync_user resolution chain** (similar pattern):
- `moodle_userid`: `user.moodle_userid` → env fallback (`MOODLE_WS_USERID`)
- `base_url`: `user.moodle_base_url` → env fallback (`MOODLE_WS_BASE_URL`)
- token: decrypt if `fernet:`-prefixed, else raw

**Current one-time-entry behavior (May 16, 2026):**
- `moodle_userid`: `user.moodle_userid` -> live
  `core_webservice_get_site_info` using the stored token -> env fallback
  (`MOODLE_WS_USERID`)
- `base_url`: `user.moodle_base_url` -> origin derived from
  `user.moodle_ics_url` -> env fallback (`MOODLE_WS_BASE_URL`)

The live `site_info` recovery makes old one-time entries durable: if a user
connected WS before `moodle_userid`/`moodle_base_url` existed, the next sync can
self-heal those columns without asking for the token again. Re-entry is only
required when Moodle rejects the token/URL with a permanent 4xx/auth response.

**Tests** (`test_moodle_submissions_sync.py`):
- `test_sync_user_uses_per_user_moodle_userid_when_set` — two users with different IDs each get their own
- `test_sync_user_falls_back_to_env_when_per_user_userid_null` — legacy operator path
- `test_sync_user_decrypts_fernet_prefixed_token` — round-trip through encryption
