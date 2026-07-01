# Import Integrations — Capability Map

**Status:** Historical research artifact, 2026-04-21. Not committed
implementation. This document cannot authorize new provider adapters, passive
tracking, schema work, provider completion truth, or runtime import behavior
during the architecture freeze.

Semantic mappings below are capability hypotheses only. Current provider data
must enter Lyra as provider facts/candidates with provenance; it must not become
clean execution truth or canonical task/deadline completion without explicit
user confirmation and active-contract authority.

**Context:** After dogfood 2026-04-21 showed external users don't plan ahead in the calendar sense (0/9 tasks had >30 min lead), operator pivoted Path B away from custom onboarding UX toward **importing users' existing plans from the tools they already live in.** Rationale: the plans exist, they're just not in Lyra — meeting users where their corpus already is beats any new UI we design.

Six platforms surveyed. Ranked build order at the bottom.

---

## 1. Google Calendar (API v3)

- **Availability:** Public REST API, mature. OAuth 2.0.
- **Auth complexity:** LOW. The app already has Google OAuth via NextAuth. Add scope `https://www.googleapis.com/auth/calendar.events.readonly`, re-consent users. GCP Console: enable Calendar API on the existing client ID. ~2-4 hrs operator setup + ~1 day consent-flow UX on the frontend.
- **Data shape mapping:** EXCELLENT.
  - `events.list` → `summary` = title
  - `start.dateTime` / `end.dateTime` = `planned_start_utc` / `planned_end_utc` (already ISO-8601 with tz)
  - `description` = `description`
  - Duration = end − start
  - Category has no native field — derive from `colorId` or source calendar name ("Work" calendar → category=`work`)
  - All-day events use `start.date` only (no time) — either skip or default duration
- **Rate limits:** Per-minute per-user quota (post-2021 model), 1M queries/day project-wide. 100 users × 1 pull/day = trivial. 1000 users × hourly polling also safe with per-user batching.
- **Sync model:** One-shot import at opt-in is cleanest v1. For ongoing: push notifications (`watch` channels) are real-time but require HTTPS endpoint + channel renewal every ~7 days — heavier than polling. Recommend: import-on-connect + incremental `syncToken` poll every 1-6 hrs.
- **Pitfalls:**
  - Recurring events require `singleEvents=true` + `timeMin` / `timeMax` to expand instances; unbounded RRULEs blow up otherwise.
  - Attendee privacy — don't import others' calendars by default.
  - Multi-calendar UX — user must pick which calendars to import from.
  - Declined events included unless filtered (`response.status=="declined"`).
- **Libraries:** `google-api-python-client` (official, maintained), `google-auth` — both actively shipped.

## 2. Notion (import direction)

- **Availability:** Public API. OAuth 2.0 (public integrations) or internal token.
- **Auth complexity:** MEDIUM. Public OAuth integrations require submission to Notion review (~1 week). Internal-token flow is instant but requires user to paste a token — bad UX for external users. ~1 day for internal token flow, ~1 week wall-clock for OAuth review.
- **Data shape mapping:** MESSY. Every user's Notion task DB has arbitrary schema. Needs a column-mapping UI: user picks which property is title / date / category.
  - Title property always present
  - `date` properties → `planned_start` / `planned_end` (date ranges supported)
  - `multi_select` / `select` → category
  - `rich_text` → description
  - No duration field — derive from date range or default
- **Rate limits:** 3 req/sec sustained, burst to ~10/sec, 429 on breach. 1000 req/15-min per user cap. 100 users daily = safe; 1000 users polling hourly needs per-integration queueing.
- **Sync model:** One-shot on connect is best v1. Webhooks (API version 2025-09-03+) support page/db change events — v2 candidate, but 50 subscriptions per integration is a ceiling to plan around.
- **Pitfalls:**
  - Schema variance is the killer — every user's "Tasks DB" looks different.
  - Timezone: date properties store date+time with user's tz context.
  - Archived pages leak unless filtered.
  - Nested pages (tasks inside pages) vs DB rows — pick DB-rows-only for v1.
  - Operator already has push-direction code (`backend/app/services/notion_client.py`) — OAuth / retry / rate-limit plumbing cribbable.
- **Libraries:** `notion-client` (Python), `@notionhq/client` (TS, official).

## 3. iCal / ICS file import

- **Availability:** No API — it's a file format / URL subscription. User uploads `.ics` or pastes subscription URL.
- **Auth complexity:** NONE for file upload. URL subscribe = no auth unless private.
- **Data shape mapping:** EXCELLENT for candidate extraction. VEVENT can
  propose task-like fields, but imported calendar events remain provider
  facts/candidates until user confirmation and canonical service handling:
  - `SUMMARY` → title
  - `DTSTART` / `DTEND` → start / end
  - `DESCRIPTION` → description
  - `CATEGORIES` → category
- **Rate limits:** N/A (local parse).
- **Sync model:** Drag-drop one-shot is the canonical UX. URL subscribe = periodic fetch (daily).
- **Pitfalls:**
  - RRULE expansion to infinity — must cap window (e.g. next 90 days).
  - TZID handling: floating times, `TZID=Africa/Cairo` vs UTC `Z` suffix.
  - EXDATE (recurrence exceptions) easy to miss.
  - VTODO vs VEVENT — different shapes; decide whether to import both.
- **Libraries:** `icalendar` (Python, maintained) + `python-dateutil` for RRULE, OR `recurring-ical-events` (purpose-built for RRULE expansion, actively maintained 2025). Recommend `icalendar` + `recurring-ical-events` combo.

## 4. Todoist

- **Availability:** Public REST API v2. OAuth 2.0 or personal token.
- **Auth complexity:** LOW-MEDIUM. OAuth app registration ~1 hr. ~4-6 hrs total.
- **Data shape mapping:** GOOD but imperfect.
  - `content` → title
  - `due.datetime` → planned_start (but due is a **deadline**, not a scheduled start — semantic mismatch with Lyra's PLANNED model)
  - `duration.amount` + `unit` → duration_minutes (often null)
  - `project_id` → category lookup
  - `description` → description
  - No `end_time` — compute from start + duration, or default
- **Rate limits:** ~450 req/min OR 1000/15-min per user (conflicting docs). Adequate.
- **Sync model:** One-shot import + periodic sync. Sync API v9 offers delta sync via `sync_token` — cleaner for ongoing.
- **Pitfalls:**
  - Deadline-vs-scheduled-start semantic mismatch is the real issue. Users may have 500 "someday" tasks with no due date — filter.
  - Recurring tasks don't pre-expand — their "next due" is server-computed.
- **Libraries:** `todoist-api-python` (official, maintained).

## 5. Apple Reminders / iCloud

- **Availability:** BAD. No first-party public API. CalDAV works for calendars but not for reminders/tasks on iCloud per community library docs.
- **Auth complexity:** HIGH. App-specific password (16 chars generated at appleid.apple.com) — poor UX, and 2FA complicates server-side flows.
- **Data shape mapping:** Reminders have title, due date, notes, list. Fine *if* you can read them.
- **Rate limits:** Undocumented; anti-scraping is aggressive.
- **Sync model:** Polling only.
- **Pitfalls:** Apple routinely blocks non-browser CalDAV clients. `pyicloud` and forks (`pyicloudreminders`) are community-maintained, fragile, break on Apple backend shifts. Not production-viable for a hosted web app serving strangers.
- **Libraries:** `caldav` (maintained, but iCloud tasks unsupported), `pyicloud` / `pyicloudreminders` (fragile).
- **Verdict:** SKIP for v1. Offer ICS-export workaround.

## 6. Microsoft To Do / Outlook Calendar (Graph API)

- **Availability:** Microsoft Graph, public and solid.
- **Auth complexity:** MEDIUM-HIGH. New Azure AD app registration (separate from Google OAuth), multi-tenant consent, refresh token handling, `offline_access` scope required. ~1 day operator setup, more if Egyptian university tenants require admin consent.
- **Data shape mapping:** GOOD.
  - Outlook events: `subject` → title, `start` / `end` → start/end_utc (includes `timeZone`), `body.content` → description
  - To Do: `title`, `dueDateTime`, `reminderDateTime`, no duration
  - Scopes: `Calendars.Read`, `Tasks.Read`, `offline_access`
- **Rate limits:** Graph throttles at 10k req/10min per app per tenant — ample.
- **Sync model:** Delta queries (`/me/calendarview/delta`) for incremental sync, or subscriptions (webhooks). Delta is the idiomatic path.
- **Pitfalls:**
  - Students in Cairo overwhelmingly have Google, not Microsoft — likely low ROI.
  - Admin-consent blocks on university tenants.
  - Timezone: Graph returns `start.timeZone` string — must convert.
- **Libraries:** `msgraph-sdk-python` (official, maintained), `msal` (auth).

---

## Ranked Build Order (post-Spring-School)

1. **ICS file import** — SHIP FIRST. Zero auth, zero rate limits, zero ongoing-sync complexity. Covers Outlook / Apple / Fastmail / Google-export as a universal fallback. ~2 days of work. Validates the import UX pattern and the first real "does imported planned-duration data produce the VT-22 scope-inflation signature the same way manually-entered data does?" research question, cheaply.
2. **Google Calendar** — SECOND. Highest user overlap with Cairo students (Gmail-default), OAuth already plumbed, cleanest data shape mapping, lowest new-infra cost.
3. **Notion** — THIRD. Operator already has write-direction code to crib OAuth / error-handling from, and it differentiates Lyra from generic calendar importers — but the schema-mapping UI is a real v1 tax, so it belongs after something simpler ships.

**SKIP for alpha:** Apple (API hostile), Microsoft (low overlap), Todoist (semantic mismatch + small segment).

**Ship-first recommendation: ICS.** At n=7, a drag-drop ICS importer lets every current user import from *any* platform — including ones we'd otherwise never build for — costs ~2 days, has no OAuth review wall, and generates the first real signal on whether imported data behaves the same as manually-entered data under VT-22. That's the only question worth burning pre-alpha engineering cycles on.

---

## Research measurement questions to pre-register alongside import

Each of these gets its own VT-number when implementation starts; listed here so the import features don't ship as "just UX" without a research claim to test:

- **IMP-1 (scope inflation on imported data):** Do tasks imported from an external calendar show the same `duration_delta_minutes` distribution as tasks created inside Lyra? If imported tasks systematically under-run (user set 60 min in GCal but executed in 40), that's Lyra's first external validation of VT-22 beyond the operator's own data.
- **IMP-2 (category coverage):** Does the external-data category taxonomy survive translation? If GCal imports overwhelmingly land in one category (e.g., all "meeting"), the downstream bias_factor analysis degrades — flag as data-integrity issue.
- **IMP-3 (retention lift):** Do users who connect at least one import source have >2x the D7 session count of users who don't? If yes, imports drive retention; if no, they're a vanity feature.

Kill criterion (pre-register when ICS ships): if IMP-3 D7 ratio < 1.25 at n ≥ 20 import-connected users, the import feature is retention-neutral — keep it for data coverage but don't invest further integrations. If > 2.0, prioritize #2 (Google Calendar) immediately.

---

## Sources consulted

- [Google Calendar API recurring events](https://developers.google.com/workspace/calendar/api/guides/recurringevents)
- [Google Calendar events.list reference](https://developers.google.com/workspace/calendar/api/v3/reference/events/list)
- [Google Calendar API quota management](https://developers.google.com/workspace/calendar/api/guides/quota)
- [Notion API 2025-09-03 upgrade guide (webhooks)](https://developers.notion.com/docs/upgrade-guide-2025-09-03)
- [recurring-ical-events (PyPI)](https://pypi.org/project/recurring-ical-events/)
- [allenporter/ical (GitHub)](https://github.com/allenporter/ical)
- [Todoist REST API v2 reference](https://developer.todoist.com/rest/v2/)
- [Todoist Sync API v9](https://developer.todoist.com/sync/v9/)
- [python-caldav library](https://caldav.readthedocs.io/latest/about.html)
- [python-caldav iCloud support issue](https://github.com/python-caldav/caldav/issues/3)
- [pyicloud (GitHub)](https://github.com/picklepete/pyicloud)
- [Microsoft Graph scopes & permissions](https://learn.microsoft.com/en-us/entra/identity-platform/scopes-oidc)
- [Microsoft Graph todoTask resource](https://learn.microsoft.com/en-us/graph/api/resources/todotask?view=graph-rest-1.0)
