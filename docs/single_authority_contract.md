---
authority: active-contract
may_authorize_code: false
runtime_owner: none
created: 2026-06-29
---

# Single Authority Contract

Status: documentation-only governance contract. This pass does not authorize
runtime refactors, Jarvis deletion, OpenClaw product use, AI synthesis,
schema changes, or new user-facing claims.

## Core Invariant

```text
One owner per truth class.
Many producers.
Many views.
One mutation path.
One claim path.
```

LyraOS may have many screens, parsers, importers, notifications, and operator
tools. That is acceptable. The dangerous failure is duplicate truth authority:
two surfaces independently mutating state, classifying behavioral truth,
generating user-facing claims, creating exposure records, or importing external
obligations as native truth.

The intended architecture is:

```text
suggestion surfaces
-> canonical service
-> event/provenance record
-> Cortex / ClaimCompiler
-> registered views
```

The forbidden architecture is:

```text
surface A mutates directly
surface B mutates differently
surface C computes its own behavioral meaning
surface D renders a claim without exposure discipline
```

## Authority Taxonomy

Every surface must be classified before it is expanded or refactored.

| Authority level | Allowed | Not allowed | Examples |
|---|---|---|---|
| Truth owner | Mutate canonical state through tested invariants | Compete with another owner for the same truth class | `TaskManager`, `DeadlineManager`, stopwatch/session authority, exposure ledger, Cortex read-time projection, ClaimCompiler |
| Suggestion producer | Propose candidates or annotations | Commit canonical truth directly | brain dump parser, deadline preview, LLM enrichment, provider completion candidates, future AI synthesis drafts |
| View | Render or request explicit canonical actions | Own hidden truth, rewrite metrics, or mutate by reading | Pulse, Today, Calendar, Table, Insights, Operator dashboard |
| Operator shell | Inspect, reason, orchestrate, and request canonical actions | Become silent doctrine or hidden runtime mutation owner | OpenClaw, parked Jarvis compatibility endpoints, admin utilities |
| Transport | Deliver or acknowledge messages | Decide behavioral meaning or exposure truth by itself | notification queue, web notification host, OpenClaw relay, browser acknowledgement |

Most double-minded surfaces come from suggestion producers or operator shells
quietly acting like truth owners.

## Current Fracture Lines

| Fracture | Current risk | Direction |
|---|---|---|
| Jarvis vs OpenClaw | Two assistant/control planes can create divergent task, deadline, timer, or hypothesis histories. | OpenClaw is the operator-alert relay/reasoning shell. Jarvis active runtime routes are removed; historical data-model/export support may remain until an approved schema migration. |
| Parser vs brain dump vs LLM enrichment | Multiple systems parse, bind, and enrich user text with different confidence semantics. | Deterministic extraction and `deadline_heuristic.score_deadlines()` own candidate scoring; LLM enrichment may annotate only. |
| Notifications vs exposure vs relay | Queue insertion can be mistaken for user-visible exposure, and acknowledgement can be confused with render. | Queue insertion is not exposure. Delivery is not exposure. Browser render may create exposure-render truth. Acknowledgement, dismissal, or action may create interaction-outcome truth. |
| Analytics vs Cortex vs ClaimCompiler | Multiple modules compute behavior meaning with different clean filters, signs, buckets, and confidence terms. | Cortex owns clean read-time projection; ClaimCompiler owns bounded claim emission. |
| Moodle iCal vs Moodle WS | Provider adapters can import or backfill obligations through separate mutation paths. | Provider facts route through provider-aware normalizers and canonical deadline/completion services. |
| Pulse / Today / Calendar / Table | Same objects appear in multiple modes. | Acceptable if authority is clear: Pulse hub, Today execution, Calendar schedule placement, Table audit/history. |

## OpenClaw As Future AI Reasoning Engine

If AI synthesis is reopened after the freeze, OpenClaw is the preferred single
reasoning host for GPT-class synthesis models. This prevents scattered
in-app LLM surfaces from becoming separate product minds.

This identifies preferred future ownership only. It does not authorize runtime
AI synthesis, model integration, prompt execution, user-facing draft
generation, or OpenClaw-to-product wiring.

This means:

- OpenClaw may generate synthesis drafts from explicit evidence packets.
- OpenClaw may run adversarial critique, uncertainty mapping, and alternative
  hypotheses.
- OpenClaw may propose user-facing language only as a draft.
- ClaimCompiler and registered output surfaces remain the publication boundary.
- Canonical services remain the mutation boundary.
- Exposure lifecycle remains the behavior-shaping visibility boundary.

OpenClaw/GPT must not:

- mutate task, deadline, timer, provider, exposure, or insight state directly;
- create confidence, causality, identity, motivation, or hidden evidence;
- bypass Cortex clean profiles or ClaimCompiler;
- treat operator discussion as user-facing truth;
- recreate Jarvis as a second runtime assistant.

If a draft is rejected by ClaimCompiler or surface policy, OpenClaw may propose a
new draft from the same evidence packet, but this is not reinforcement learning
over user behavior and must not silently tune prompts from private traces.

## Exposure Lifecycle Boundary

Exposure is not the same as notification existence, transport delivery, or
button acknowledgement.

```text
queued
-> delivered
-> rendered
-> dismissed / acknowledged / acted
-> interaction outcome recorded
```

Rules:

- Queue insertion is not exposure.
- Delivery to a client or relay is not exposure.
- Browser render may create exposure-render truth.
- Seeing a surface without clicking is still exposure.
- Acknowledgement, dismissal, or action are later interaction outcomes.
- Not every exposure requires acknowledgement.
- Notification workers must not mark exposure at enqueue time.
- Analytics routes must not write exposure rows except through output-surface
  lifecycle APIs.

### Task-Creation Duration Nudge

The task creation duration suggestion is behavior-shaping. If a user changes
their planned duration because Lyra says `Use X min`, that must be treated as
exposure plus an interaction outcome.

Current implementation shape, as of 2026-06-29:

- `task.creation_nudge` is a registered output surface.
- `NewTaskModal` acknowledges render through
  `/v1/exposures/{exposure_id}/ack/render`.
- Clicking `Use X min` or `Keep Y min` stores `nudge_decision` in the create
  payload.
- `TaskManager.create_task()` writes `CalibrationNudgeEvent` with
  `accepted` or `dismissed`.

Doctrine gap:

```text
render exposure exists;
duration-decision outcome exists;
the original render -> interaction outcome link must remain first-class.
```

Future cleanup should avoid creating a second ambiguous render when recording
the outcome. The canonical model should be: one render row, then a linked
interaction-outcome row for `accepted` / `dismissed` / `ignored`.

## Refactor Principle

Do not start by deleting code. Start by making authority illegal in the wrong
places.

```text
Jarvis is parked and may not suggest, execute tools, call models, or mutate.
OpenClaw may reason and orchestrate.
LLMs may enrich.
Providers may report.
Frontend may display and request explicit canonical actions.
Only canonical services may mutate.
Only Cortex / ClaimCompiler may authorize behavioral claims.
Only exposure lifecycle may mark exposure.
```

The app does not need fewer surfaces first. It needs fewer sovereigns.

## Enforcement Targets

These are doctrine-level guardrails now and should become tests or static
checks before broad extraction work:

- Non-owner modules must not call `db.commit()` for task, deadline, timer,
  exposure, notification, provider, or insight state.
- OpenClaw tools and any parked Jarvis compatibility code must not call
  mutation methods except through canonical commands.
- Frontend views must not derive behavioral claims locally.
- Provider adapters must emit provider facts/candidates, not native truth.
- Notification workers must not mark exposure at enqueue time.
- Analytics routes must not write exposure rows except through output-surface
  lifecycle APIs.
- EvidencePacket packaging must not decide row eligibility.
- ClaimCompiler must not admit evidence that bypassed the Admission/Coverage
  Gate.

## Freeze-Safe Next Tasks

These are documentation and audit tasks unless separately authorized by a
current implementation plan:

1. List every surface that can mutate task, deadline, timer, exposure,
   notification, provider, or insight state.
2. Mark each surface as truth owner, suggestion producer, view, operator shell,
   or transport.
3. Keep Jarvis active runtime parked while historical rows remain exportable and
   deletable.
4. Choose one OpenClaw delivery path for operator alerts; retire the other.
5. Make notification lifecycle explicit:
   `queued -> delivered -> rendered -> dismissed/acknowledged/acted -> outcome`.
6. Promote `deadline_heuristic.score_deadlines()` as the single deterministic
   deadline-binding scorer.
7. Route Moodle WS deadline creation/backfill through canonical deadline
   mutation authority.
8. Make analytics and frontend surfaces consume Cortex/ClaimCompiler
   outputs instead of recomputing behavior truth.
9. Add tests later that fail when non-owner modules mutate canonical state
   directly.
