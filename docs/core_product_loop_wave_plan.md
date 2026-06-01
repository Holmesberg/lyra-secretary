# Core Product Loop Wave Plan

**Status:** Active product-maintenance plan.
**Created:** 2026-06-01.
**Updated:** 2026-06-01.
**Authority:** Implementation guidance. Does not override `MANIFESTO.md`,
`docs/AUTHORITY.md`, `docs/academic_pressure_map_contract.md`,
`docs/academic_execution_substrate.md`, or provider adapter contracts.
**Wave -1 scan artifact:** `docs/wave_minus_1_repo_scan_2026_06_01.md`.

## Global Product Frame

Lyra is not an academic-only planner. The academic loop is the first concrete
module because the current operator and trusted users live inside academic
pressure, but the product category is broader:

```text
provider-agnostic schedule / obligation / recovery middleware
```

The generalized product loop is:

```text
capture/import obligations
-> normalize into provider-blind structure
-> relate tasks, deadlines, schedules, recurrences, resources, and dependencies
-> visualize pressure/occupancy
-> preview plans or recovery options
-> create or adjust state only after confirmation
-> track execution/recovery
-> produce insights and calibration
```

Academia is one adapter dialect: courses, lectures, assignments, LMS deadlines,
and exam pressure. The same substrate must later support work calendars,
meetings, tickets, spreadsheets, notes, recurring commitments, and personal
obligations without making the core branch on provider names.

Lyra's value is not "more tasks." The value is that real obligations become
visible, drift becomes recoverable, and the user remains in control.

## Current Product Loop

The dogfood loop for the current build is:

```text
brain dump -> bind to existing obligations -> pressure/occupancy map
-> confirmed task/recovery creation -> session tracking -> recovery/insights
```

Recent dogfood/repo findings:

- Tracking friction is still high; users forget timers are running.
- Browser-extension/passive activity capture may reduce friction, but only as
  scoped, opt-in, confirmation-gated weak evidence.
- Brain dump is the friction killer, but it must not create clutter.
- Existing code currently binds brain-dump tasks to deadlines parsed in the
  same dump; binding against already-existing obligations is the key gap.
- Pressure Map can expose recovery options, but confirmed recovery-plan task
  creation is not yet a complete user action path.
- Recovery needs its own research-backed vocabulary: state restoration,
  prospective-memory support, implementation-intention repair,
  obstacle-aware replanning, cognitive offloading, temporal recalibration,
  and adaptive disengagement.
- Overlapping tasks and multitasking use a separate terminology boundary; see
  `docs/tightened_docs/09_semantic_conflicts.md`.

## Definition Of Done

A user can:

1. Paste or import 5 messy obligations from their real week.
2. Bind at least 2 items to existing deadlines, scheduled commitments, or
   provider-imported obligations.
3. Open the pressure/occupancy map.
4. Confirm one recovery plan or planning block.
5. Run, pause, resume, and stop one session.
6. See the result reflected in recovery/insights.

The loop is not done if any step requires manual database correction.

Current trusted-user dogfood instance:

```text
A student can paste 5 messy academic tasks, bind at least 2 to existing
deadlines, open the pressure map, confirm one recovery plan, run/pause/resume/
stop one session, and see the result reflected in insights/recovery without
manual database correction.
```

## Global Product Primitives

External provider ecosystems keep rediscovering the same object families:
calendar events, tasks, due dates, recurrence, relations, online meetings,
spreadsheet rows/ranges, database/page properties, tickets, messages, reminders,
and status. Lyra should normalize those into provider-blind primitives before
the pressure map, recovery, estimates, or insights consume them.

| Primitive | Normalized meaning | Common provider dialects |
| --- | --- | --- |
| `external_obligation` | Something the user may need to account for. | LMS assignment, Jira issue, Linear issue, Notion row, spreadsheet row, email/chat action item. |
| `scheduled_event` | Time-bounded calendar structure. | iCalendar `VEVENT`, Google Calendar event, Outlook event, recurring class, meeting. |
| `task_intention` | User-accepted work item Lyra may plan or track. | Brain-dump task, Google Task, Microsoft To Do task, Notion task row, Jira subtask. |
| `deadline` | Due point or due window, not proof of execution. | iCalendar `DUE`, Google Task `due`, Microsoft `dueDateTime`, Notion date, Jira due date. |
| `recurrence_rule` | Rule for producing bounded future instances. | iCalendar `RRULE`/`EXDATE`, Google Calendar recurrence, Microsoft patterned recurrence. |
| `resource_artifact` | Context that may support work but is not work truth. | Sheet, Excel table/range, Notion page, LMS attachment, meeting link, Slack thread. |
| `relation` | Link between pieces of work. | Parent-child, `part_of`, blocked-by, blocking, related, duplicate, linked resource. |
| `participant_owner` | Human or group context. | Assignee, attendee, organizer, owner, channel, team. |
| `status_signal` | Provider-native state, weak until confirmed. | Not started, in progress, completed, canceled, deferred, done, archived. |
| `estimate_signal` | Planning footprint or complexity hint. | Duration, estimate points, t-shirt size, calendar block length, AI prior. |
| `availability_block` | Occupied or constrained time. | Calendar busy block, class schedule, meeting, recurring appointment. |
| `reminder_signal` | Nudge or alert context. | Calendar alarm, task reminder, Slack scheduled message, provider notification. |
| `confirmation` | User action that authorizes mutation or stronger truth. | Accept binding, create task, confirm activity, edit imported candidate. |
| `execution_session` | Lyra-tracked active work session. | Stopwatch session, confirmed passive candidate, recovered paused work. |
| `recovery_option` | User-facing next-step repair candidate. | Resume, shrink, split, reschedule, mark irrelevant, drop, convert to task. |

Provider-specific labels may appear at the surface. Core services should reason
over these primitives plus `provenance`, `trust_state`, `authority_level`,
`redaction_status`, and user confirmation.

## Provider Matrix

This is a planning map, not an authorization to build every adapter now.

| Source/provider | Current or near-term role | Normalize into | Useful for | Not allowed yet |
| --- | --- | --- | --- | --- |
| Brain dump | Manual capture and friction reduction. | `external_obligation`, `task_intention`, `deadline`, `relation`. | Turning messy human language into previewable candidates. | Silent task creation or silent deadline binding. |
| ICS / CalDAV | Universal schedule import fallback. | `scheduled_event`, `deadline`, `recurrence_rule`, `availability_block`. | Recurring classes, appointments, calendar exports across ecosystems. | Unbounded recurrence expansion or execution truth. |
| Google Calendar / Meet | Calendar context, meetings, recurring events. | `scheduled_event`, `availability_block`, `resource_artifact`, `recurrence_rule`. | Time constraints, meeting links, obligation context. | Attendance truth, completion truth, or raw meeting URL leakage. |
| Google Tasks | Lightweight external tasks. | `task_intention`, `deadline`, `status_signal`, `resource_artifact`. | Importing user-maintained task lists and linked Google surfaces. | Precise scheduled time assumptions; API due-time support is limited. |
| Outlook / Teams / Microsoft Graph | Calendar, To Do, online meetings, enterprise schedules. | `scheduled_event`, `task_intention`, `deadline`, `resource_artifact`, `participant_owner`. | Work/school commitments, Teams meeting context, Microsoft To Do. | Attendance/participation truth or tenant-wide surveillance. |
| Sheets / Excel | Structured planning data. | `external_obligation`, `resource_artifact`, `estimate_signal`. | Reading rows/ranges/tables that users already maintain. | Treating arbitrary spreadsheet rows as clean tasks without mapping/confirmation. |
| Moodle / Baseet / LMS | Academic provider module. | `external_obligation`, `deadline`, `resource_artifact`, `status_signal`. | Assignments, course context, resources, exam/deadline pressure. | Study proof or provider-completion truth. |
| Notion | User-defined databases and relations. | `external_obligation`, `task_intention`, `deadline`, `relation`, `resource_artifact`. | Flexible task/project imports once mapping UI exists. | Assuming every workspace has the same schema. |
| Jira / Linear | Work tickets and issue relationships. | `external_obligation`, `task_intention`, `relation`, `estimate_signal`, `status_signal`. | Dependencies, blockers, parent-child work, estimates. | Treating ticket status as human execution truth. |
| Slack / chat surfaces | Conversation context and possible action items. | `resource_artifact`, `external_obligation`, `reminder_signal`. | Follow-up candidates tied to a source thread. | Reading message history broadly, private surveillance, or auto-created obligations. |

## Minimal Task Grouping Primitive

Brain dump, imports, and recovery plans will create flat clutter unless Lyra can
represent grouped work. Do not build a full arbitrary DAG in the next pass.
Start with a minimal grouping contract:

| Field | Meaning |
| --- | --- |
| `parent_task_id` or `task_group_id` | Optional parent/group for subtasks or imported work packages. |
| `external_obligation_id` / `deadline_id` | Existing obligation the task supports. |
| `relation_type` | Start with `part_of`, `supports`, `blocks`, `follows`, `related`. |
| `source` | `brain_dump`, `manual`, `import`, `recovery_plan`, `provider_adapter`. |
| `provenance` | Why Lyra believes the relation exists. |
| `confidence` | Low/medium/high preview confidence, never hidden truth. |
| `confirmed_by_user` | Required before canonical mutation affects planning/calibration. |

Near-term rule:

```text
Represent parent-child and support/blocking relations.
Do not build generic graph algorithms until real pressure-map failures require them.
```

## Wave -1: Repo Scan And Reality Check

Goal: avoid blind implementation and make every wave earn its complexity.

Run four review agents before changing product behavior:

| Agent | Scope | Output |
| --- | --- | --- |
| Code Agent A | Frontend/product loop. | Existing UI paths, broken links, missing browser checks, duplicate surfaces. |
| Code Agent B | Backend/state/data integrity. | Models, endpoints, invariants, user scoping, idempotency, test gaps. |
| Docs Agent A | Product/global positioning. | Academic-only wording, global middleware framing gaps, obsolete claims. |
| Docs Agent B | Authority/contracts/provider boundaries. | Confirmation gates, privacy risks, provider-truth violations, parking candidates. |

Each agent must report:

- what already exists,
- what is missing,
- what is duplicated,
- what should be deleted,
- what should be parked,
- what must be browser-verified.

Browser verify after this pass:

- No product behavior changes are expected.
- The dogfood checklist is updated from the audit output.
- Parked ideas are visibly separated from authorized work.

## Wave 0: Stabilize The Existing Loop

Goal: verify the current product loop without adding new inference machinery.

Implementation posture:

- No broad passive tracking.
- No automatic task/calendar mutation.
- No pressure-map plan creation without explicit confirmation.
- No Teams/Outlook/Sheets/Excel promises beyond current integration state.

Browser verify after this pass:

- `/pulse` is the main loop hub.
- Brain dump opens from Pulse quick capture at the bottom of the page.
- Any Pulse brain-dump link points to `/pulse#quick-capture`, not `/today`.
- Timer start/pause/resume/stop survives refresh and page switches.
- Resume banner copy is continuity support: "Pick it back up?"
- Export/delete/account settings still work.
- Two accounts do not leak tasks, deadlines, pressure, or banners.

## Wave 1: Brain Dump To Existing Obligations

Goal: make brain dump obligation-aware enough to protect the pressure map.

Implementation posture:

- Parse messy input as today.
- Include existing bindable deadlines, scheduled events, and imported
  obligations in the preview candidate set.
- Keep same-dump bindings and existing-obligation bindings visually distinct.
- High-confidence candidate may be prechecked.
- Ambiguous candidate requires explicit Yes/No.
- No canonical binding without user confirmation.
- Partial commit failures must be visible.

Browser verify after this pass:

- Create or import at least one deadline/scheduled obligation first.
- Paste 5 messy real-world tasks into Pulse quick capture.
- Confirm at least 2 bindings to existing obligations.
- Lock in.
- Open task rows, obligation/deadline details, and Pressure Map.
- Verify linked tasks count toward visible load.
- Verify no duplicate junk appears.
- Verify invalid/past items produce clear failure rows.

## Wave 2: Pressure/Occupancy Map To Confirmed Plan

Goal: turn pressure-map recovery copy into an explicit preview-and-confirm flow.

Implementation posture:

- Pressure Map remains a diagnostic planning surface.
- `create_plan` opens a preview, not an automatic mutation.
- Preview rows show title, linked obligation, suggested duration, start/window,
  estimate source, and editable fields.
- Commit creates tasks only after explicit confirmation.
- Created tasks preserve obligation links and duration provenance.
- User can dismiss without side effects.

Browser verify after this pass:

- Seed no obligations, one obligation, many obligations, stale obligation,
  due-today, due-tomorrow, obligation with no linked tasks, and obligation with
  multiple linked tasks.
- Open week/day pressure views.
- Confirm one recovery plan.
- Verify tasks appear in Today/Calendar and remain linked to obligations.
- Verify dismissing the preview creates nothing.
- Verify the UI never says Lyra knows exact hours or completion truth.

## Wave 3: Session Tracking And Recovery Intelligence

Goal: make recovery useful without turning it into pressure or surveillance.

Implementation posture:

- Execution Time remains active work.
- Session Span includes pause/interruption span.
- Pause Overhead and Occupancy Time remain planning/recovery signals.
- Recovery copy must support continuity, not compliance.
- Missed-plan recovery should offer: keep, shrink, reschedule, mark done,
  mark irrelevant, or drop.
- Passive signals, if present later, ask for confirmation before becoming task
  state.

Browser verify after this pass:

- Start a planned task, pause it, leave, return, resume, stop.
- Confirm executed time excludes pause.
- Confirm session span includes pause.
- Confirm post-stop mirror is short and factual.
- Pause a task past resume threshold; verify one banner, correct task, and
  cooldown/dismiss behavior.
- Let a planned task pass without starting; verify recovery options are
  useful and non-shaming.

## Wave 4: Estimates And AI Priors

Goal: help cold-start planning without contaminating measurement.

Implementation posture:

- AI estimates may draft ranges only when no personal/session evidence exists.
- Estimate provenance must be visible.
- Accepted system estimates are not pure user estimates.
- Unchanged system suggestions stay out of clean user-estimate calibration.
- Use robust ranges before point estimates.
- Provider block length may inform occupancy, but not execution truth.

Browser verify after this pass:

- Create/edit tasks with no history.
- Verify `Execution Time`, `Pause Overhead`, and `Occupancy Time` rows render.
- Verify `Use Z min` updates the planning window, not the executed truth.
- Verify copy says prior/draft/range, not certainty.
- Verify personal evidence replaces priors when enough clean sessions exist.

## Wave 5: Repeated Schedules And Provider Imports

Goal: handle repeated commitments as structure import, not ordinary task
duplication.

Implementation posture:

- Recurring events/tasks need a recurrence contract first.
- Prefer ICS import and recurrence expansion before manual repeated-task UI.
- Expand recurring events with bounded horizon, timezone rules, duplicate
  protection, RRULE/EXDATE handling, and provider provenance.
- Google Calendar, Moodle/Baseet, Outlook, Teams, Sheets, Excel, Notion,
  Jira/Linear, and Slack must stay adapter-specific until each has idempotency,
  redaction, disconnect, and user-scoping rules.

Browser verify after this pass:

- Import a recurring schedule with a bounded horizon.
- Verify duplicate import does not duplicate tasks/deadlines/events.
- Verify disconnect behavior is understandable.
- Verify imported structure appears on Pressure Map as structure, not
  completed work.
- Verify recurring items can be corrected without corrupting the series.

## Wave 6: Passive Browser Extension Candidate

Goal: reduce timer friction without creating surveillance hallucination.

Implementation posture:

- Private, opt-in prototype only.
- Visible tracking indicator.
- Capture session candidates, not execution truth.
- User can confirm, edit, discard, or mark private.
- No raw browsing history in clean execution metrics.
- Passive-only data never enters clean calibration.

Browser verify after this pass:

- Open a known resource page.
- Work long enough to generate a candidate.
- Verify Lyra asks "Confirm, edit, or discard?"
- Verify discard/private leaves no task truth behind.
- Verify confirmed activity becomes labeled, user-confirmed evidence.
- Verify false positives feel safe to correct.

## Adversarial Parking Gate

Every proposed addition must receive one decision:

```text
ship now
browser-verify candidate
park for later
reject
```

Stress-test questions:

- Does this strengthen the core loop this week?
- Does it preserve explicit user confirmation before mutation?
- Does it normalize provider data into provider-blind primitives?
- Does it reduce manual friction without turning passive context into truth?
- Does it have a one-pass browser verification script?
- Does it avoid replacing the user's existing workflow too early?
- Does it have privacy/scoping/redaction rules before persistence?
- Does it avoid adding a new subsystem when a doc/watchlist is enough?

If any answer is "no," park the idea instead of implementing it.

## External Primitive References

These references are not product commitments; they are vocabulary sources for
the provider-blind primitive model.

- iCalendar RFC 5545 defines calendar components such as `VEVENT`, `VTODO`,
  `VJOURNAL`, `RRULE`, `DUE`, `DURATION`, `ATTENDEE`, `CATEGORIES`, and
  `SUMMARY`: https://datatracker.ietf.org/doc/html/rfc5545
- CalDAV RFC 4791 frames server-stored calendar object resources around
  iCalendar objects such as events and todos:
  https://www.rfc-editor.org/rfc/rfc4791.html
- Google Calendar events expose start/end, recurrence, `iCalUID`, and
  `conferenceData` for Google Meet context:
  https://developers.google.com/calendar/api/v3/reference/events
- Google Tasks exposes task lists with title, notes, due date, status, links,
  and assignment/source context:
  https://developers.google.com/tasks/reference/rest/v1/tasks
- Microsoft Graph event and online meeting resources expose start/end,
  recurrence, attendees, online meeting info, and Teams meeting context:
  https://learn.microsoft.com/en-gb/graph/api/resources/event?view=graph-rest-1.0
  and https://learn.microsoft.com/graph/api/resources/onlinemeeting?view=graph-rest-1.0
- Microsoft Graph To Do tasks expose due date, recurrence, reminder, status,
  checklist items, and linked resources:
  https://learn.microsoft.com/en-us/graph/api/resources/todotask
- Google Sheets and Microsoft Excel APIs expose structured spreadsheet ranges,
  values, workbooks, worksheets, tables, ranges, and charts:
  https://developers.google.com/sheets/api/reference/rest/v4/spreadsheets.values
  and https://learn.microsoft.com/en-us/graph/api/resources/excel?view=graph-rest-1.0
- Notion databases/pages expose schema-shaped properties such as date, status,
  relation, person, files, URL, created time, and last edited time:
  https://developers.notion.com/reference/database and
  https://developers.notion.com/reference/property-value-object
- Linear issue relations and estimates show common product-work primitives:
  blocked, blocking, related, duplicate, estimates, cycles, and effort:
  https://linear.app/docs/issue-relations/ and
  https://linear.app/docs/estimates
- Jira issue links/subtasks and Asana dependencies represent dependency and
  parent-child task structures:
  https://developer.atlassian.com/cloud/jira/platform/rest/v2/api-group-issue-links/
  and https://help.asana.com/s/article/task-dependencies
- Slack conversations and scheduled messages are useful as context/reminder
  sources, but the privacy and rate-limit profile makes broad message ingestion
  a parked adapter, not core loop work:
  https://api.slack.com/methods/conversations.history and
  https://api.slack.com/messaging/scheduling
