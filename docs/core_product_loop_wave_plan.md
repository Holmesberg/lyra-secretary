# Core Product Loop Wave Plan

**Status:** Active product-maintenance plan.
**Created:** 2026-06-01.
**Updated:** 2026-06-03.
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

The abstract north star is:

```text
align intention with reality
```

That is broader than productivity and narrower than generic AI coaching. The
product should help users preserve contact between what they meant to do, what
constraints actually existed, what happened, and what recovery remains
available.

Near-term retention should come from this reality-contact loop, not from cheap
habit mechanics:

```text
pressure
-> execution attempt
-> reality diverges
-> recovery
-> reflection
-> next attempt is slightly better
-> trust increases
-> return when reality changes again
```

Bad retention pressure:

```text
streaks, guilt nudges, app-open manipulation, dependency loops
```

Acceptable retention pull:

```text
the plan no longer matches remaining time;
an unresolved interruption is still open;
a recovery option can reduce tomorrow's planning debt;
the user can leave with a better model than they arrived with.
```

Recovery conversations are a post-validation product direction, not an
immediate runtime authority. The current system may improve recovery surfaces
only inside existing explicit-action, exposure-logged, low-authority flows.
Stronger recovery dialogue, adaptive scheduling, or AI-mediated intervention
requires validated research and separate implementation authority.

## Alpha Sequencing

The current path is:

```text
Instrument
-> Measurement integrity
-> Recovery
-> Validated longitudinal mechanisms
-> LyraSim counterfactual scaling
-> University wedges
-> Middleware / organizations
```

Phase 1 - Instrument:

- current freeze/refactor work;
- operator cockpit clarity;
- exposure ledger integrity;
- clean traces;
- ClaimCompiler boundaries;
- reusable dogfood verification.

Primary question:

```text
Can Lyra measure execution honestly?
```

Phase 2 - Recovery:

- only after the instrument is trustworthy enough for a retaining cohort;
- improve recovery after plan collapse, stale work, missed blocks, open
  threads, and overrun cascades;
- keep recovery reversible, user-confirmed, and exposure-logged;
- avoid psychological labels, shame, or hidden steering.

Primary question:

```text
Can Lyra reduce recovery latency without corrupting baseline observability?
```

Phase 3 - Validation:

- first 30-50 retaining alpha users, likely students;
- longitudinal traces plus qualitative review;
- test whether recovery helps before increasing adaptive authority.

Primary questions:

```text
Did recovery latency decrease?
Did plans become more realistic?
Did open loops close sooner?
Did users voluntarily return under pressure?
Did estimate and recovery behavior improve without dependency?
```

Phase 4 - LyraSim:

- use real-user mechanisms as the seed;
- simulate extra chaos and boundary conditions only after real traces exist;
- never use simulation as a substitute for user reality.

Phase 5 - Scale:

- 100-200 users;
- university wedge, word of mouth, marketing, and institutional review;
- only then broader middleware paths for firms, enterprises, and
  organizations.

Feature requests during alpha should be treated as evidence, not automatic
scope:

```text
request
-> observed pain
-> hypothesis
-> parked or promoted
-> build only if it strengthens the core loop
```

Maintain a running record once alpha begins:

```text
Things Reality Changed
```

Each entry should capture:

- original assumption;
- observed reality;
- what changed;
- what stayed invariant;
- test or product adjustment.

## Current Product Loop

The dogfood loop for the current build is:

```text
brain dump -> bind to existing obligations -> pressure/occupancy map
-> confirmed task/recovery creation -> session tracking -> recovery/insights
```

Recent dogfood/repo findings:

- Tracking friction is still high; users forget timers are running.
- Browser-extension/passive activity capture may reduce friction later, but it
  is postponed until the core loop, provider imports, recurrence, privacy,
  confirmation, and recovery surfaces can absorb the added complexity.
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
- Context-switching is now documented as a footprint hypothesis, not a causal
  claim; see `docs/context_switching_footprint_hypothesis.md`.

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

## Wave Status Snapshot

This is a planning snapshot, not a release claim.

| Wave | Current status | Implementation verdict |
| --- | --- | --- |
| Wave -1 Repo Scan | Completed. | Keep as audit artifact and complexity gate. |
| Wave 0 Existing Loop Stabilization | Mostly implemented; keep dogfooding. | Pulse is hub, quick capture is top-mounted, timer/recovery/account smoke exists. |
| Wave 1 Brain Dump To Existing Obligations | Implemented for bindable deadlines/imported deadline rows. | Brain dump preview can suggest existing obligations, commit can bind confirmed tasks to them, and same-dump vs existing bindings are distinct. Live scheduled-event binding remains Wave 5/provider-contract work. |
| Wave 2 Pressure/Occupancy Map To Confirmed Plan | Implemented for deadline-backed recovery blocks. | Pressure Map has day/week/14d views, explicit preview rows, editable title/start/duration, dismiss-without-side-effects, and confirmed task creation with obligation links. Duration provenance is visible and saved in task description; no dedicated schema field yet. |
| Wave 3 Session Tracking And Recovery Intelligence | Partially implemented. | Stopwatch, pause/resume, resume banner, occupancy metrics, and correction paths exist; missed-plan recovery options are still incomplete. |
| Wave 3.5 Context-Switching Footprint | Documentation-only / planned. | Treat switching as observable consequence topology first, causal hypothesis second. Derived metrics may support re-entry and insights later, but no passive tracking, automatic mutation, or failure prediction. |
| Wave 4 Estimates And AI Priors | Partially implemented. | Bias/occupancy rows exist; explicit AI cold-start ranges with provenance are not complete. |
| Wave 5 Repeated Schedules And Provider Imports | Partially implemented for narrow providers only. | Moodle ICS/submissions and Google Calendar read-only context exist; general recurrence/import contract is not complete. |
| Passive Browser Extension Candidate | Parked/postponed. | Do not implement until system complexity can handle passive evidence without breaking intention -> execution -> drift -> interruption -> recalibration. |

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
- Brain dump opens from Pulse quick capture at the top of the page.
- Do not permanently duplicate quick capture top and bottom; use a small
  floating/collapsible affordance later only if dogfood proves it is needed.
- Any Pulse brain-dump link points to `/pulse#quick-capture`, not `/today`.
- Timer start/pause/resume/stop survives refresh and page switches.
- Resume banner copy is continuity support: "Pick it back up?"
- Export/delete/account settings still work.
- Two accounts do not leak tasks, deadlines, pressure, or banners.

## Wave 1: Brain Dump To Existing Obligations

Goal: make brain dump obligation-aware enough to protect the pressure map.

Implementation posture:

- Parse messy input as today.
- Include existing bindable deadlines and imported deadline obligations in the
  preview candidate set. Live scheduled events remain context until Wave 5
  defines a canonical recurrence/provider binding contract.
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
- Preview rows show title, linked obligation, editable start/end window,
  derived duration, estimate source, and editable fields.
- Estimate source order is evidence-first: same-obligation planned/executed
  history, pause/occupancy overhead, completion-adjusted active work, dominant
  category behavior, then archetype/research priors for cold start.
- Occupancy evidence must exclude forgotten-timer-scale pause anomalies and
  stale/dirty/auto-repaired sessions. Long pauses can remain descriptive
  recovery facts, but they do not enter average pause-overhead estimates.
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

Current re-entry anchor:

- External outreach re-entry should usually land on `https://lyraos.org` so
  returning users re-enter through the product frame before choosing a path.
  In-app brain-dump links still target `/pulse#quick-capture`.
- In-app re-entry should then be anchored on Pulse, using existing confirmed
  state only: paused sessions, auto-skipped/missed plans, and overdue planned
  blocks.
- The surface may offer explicit actions such as resume, open, mark done
  retroactively, hide, drop, or reschedule. It must not infer execution from
  absence, presence, or passive activity.
- Email, notification, and browser-extension ideas are acquisition/re-entry
  candidates only when they return the user to this explicit confirmation loop.

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

## Wave 3.5: Context-Switching Footprint And Re-entry Intelligence

Goal: model context switching as a recoverable execution footprint without
claiming Lyra knows why the switch happened.

Primary product posture:

```text
open threads -> recovery options
```

Not:

```text
switches -> fragmentation score
```

The near-term surface should strengthen re-entry, not produce a weekly insight
that says the user switches a lot.

Hypothesis:

```text
Explicit task switches and interruption chains may correlate with later
recovery friction, planning-window overhead, and execution drift.
```

Non-claim:

```text
High switching does not yet prove the cause of fragmentation.
```

Implementation posture:

- Use existing explicit state only: `PauseEvent`, `StopwatchSession`,
  `Task.parent_task_id`, `Task.interruption_type`, active execution duration,
  completion percentage, missed plans, obligation/deadline links, and exposure
  state.
- Treat metacognitive discrepancy as a modifier: switched work that also
  resembles prior over-plan work is stronger recovery-risk evidence than switch
  topology alone.
- Do not use passive browser activity, provider completion, calendar
  attendance, or security/audit state.
- Do not add pause overhead to `executed_duration_minutes`.
- Do not surface "failure," "degradation," "focus," "motivation,"
  "avoidance," or identity language.
- V1 is read-only derived metrics. Add a durable switch-event table only if
  exact edge attribution cannot be reconstructed from existing rows.

Candidate derived metrics:

- `task_switch_count`
- `interruption_chain_count`
- `parked_task_count`
- `reentry_latency_minutes`
- `reentry_resolution_type`
- `time_to_resolution_minutes`
- `open_thread_end_of_day_count`
- `switch_load_level`
- `post_switch_active_delta_minutes`
- `planning_window_footprint_minutes`

Resolution outcomes are required before interpreting whether switching
mattered: resumed, completed later, rescheduled, dropped, marked irrelevant,
stale/open at day end, or auto-closed.

Validity threats to preserve in code/docs:

- hard tasks, unclear tasks, emergencies, deadline overload, excessive
  commitments, emotional avoidance, provider changes, and forgotten timers can
  produce similar switch signatures;
- exposure to a switch-footprint insight changes future switching behavior;
- session span and execution efficiency are footprint metrics, not proof of
  causal degradation.

Kill criteria:

- usefulness requires passive tracking;
- user-facing copy implies Lyra knows why the user switched;
- false positives dominate trusted-user feedback;
- the surface causes shame, pressure, or churn;
- exposure logging cannot separate clean behavior from post-insight behavior;
- switch topology adds no lift over simpler "paused work" and "missed plan"
  recovery affordances.
- the feature becomes a `fragmentation_score`, `switching_score`, or other
  user-facing scalar judgment.

Browser verify after this pass:

- Start a task, start another as interruption, then switch back.
- Verify the parent remains recoverable from Today and Pulse.
- Verify any re-entry copy is neutral and action-oriented.
- Verify user-facing copy says "open threads" or "parked work," not
  `context_switching_footprint`.
- Verify each open thread offers explicit actions: pick it back up,
  reschedule, drop, mark done, or keep parked.
- Verify resolution outcome is visible internally before any insight uses the
  switch.
- Verify no execution duration includes pause overhead.
- Verify no passive/provider evidence becomes canonical execution truth.
- Verify insights remain hidden or low-confidence until sample support exists.

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

## Parked: Passive Browser Extension Candidate

Status: postponed until the system can handle the complexity safely.

Goal, when revisited: reduce timer friction without creating surveillance
hallucination or breaking the core invariant:

```text
intention -> execution -> drift -> interruption -> recalibration
```

This is not Wave 6 implementation work. It is a parked candidate that may be
reopened only after Waves 1-5 have enough stability and browser verification.

Implementation posture:

- Not part of current wave execution.
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
