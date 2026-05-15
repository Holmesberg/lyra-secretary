# Structural Invariants vs Behavioral Constraints

**Owner:** Operator
**Created:** April 16, 2026 (emerged during Path A walk-back from the Apr 14 hard-block Gate B to the Apr 16 severity-classified Gate B)
**Status:** Canonical. Applies to every user-facing rule the system enforces.

The system has two distinct kinds of "rules" that must not be confused.

**Structural invariants** protect measurement integrity and data consistency. They are non-negotiable internal constraints the system enforces regardless of user preference. Examples:

- Single mutation authority (one active stopwatch timer at a time)
- No silent defaults on research-relevant fields
- State machine transition validity
- Voided tasks excluded from aggregations
- User scoping on all queries

**Behavioral constraints** shape user-facing interactions. They should maximize user agency unless they directly protect an invariant. Examples of behavioral constraints that should be soft, not hard:

- Can user plan a task during an active execution window? (YES — planning and executing are different activities)
- Can user override a duplicate-title warning? (YES — with confirmation)
- Can user edit a task title while executing? (YES — title doesn't affect measurement)

## Diagnostic test for every user-facing rule

Ask: "Does this rule prevent data corruption, or does it just prevent user behavior I didn't anticipate?"

- If the former → keep it, enforce as invariant
- If the latter → soften it, let user decide

## Why this matters

Research discipline produces clean data. But that discipline should be invisible to the user. The user should experience "the system respects my agency and gets out of my way." Research discipline leaking into UX creates friction that harms retention without protecting the research goal.

This principle emerged April 16 during Path A walk-back to Option C. Original Path A hard-blocked EXECUTING-vs-planned overlaps. Dogfood revealed this reflected real-world scheduling poorly (users plan multiple tasks during execution windows knowing only some execute). Option C relaxed to soft warning. Single mutation authority (structural) preserved; planning-during-execution rigidity (behavioral, unjustified) removed.

## Applied examples

- Hard-block two simultaneous EXECUTING timers: **INVARIANT** (measurement integrity)
- Hard-block creating PLANNED task during EXECUTING: was **behavioral constraint masquerading as invariant**; relaxed to soft warning
- Force-override on conflict: respects user agency without violating invariants (override is logged user action, not silent bypass)
- Silent pause default: was **hardcoded default masquerading as convenience**; identified as invariant violation (Hard Rule 4), fix removes silent path entirely
- Pause-anywhere silent default (shipped fix Apr 16): clicks outside the pause-reason picker silently pauses the timer with `pause_reason="external_interruption"`. Was a hardcoded default masquerading as convenience ("least-wrong assumption" per the original code comment). Identified as invariant violation (Hard Rule 4 + `do_not_add.md §Hardcoded default values`); fix removes the silent path entirely — click-outside dismisses the picker, user must explicitly pick a reason to pause. Data-quality note: any `pause_event` rows with `pause_reason="external_interruption"` AND `pause_initiator="self"` written before Apr 16 on non-voided tasks are suspect — the Apr 14 migration-020 retrofit flag did NOT cover this pattern (it only flagged `pause_reason="intentional_break"`), so these rows leaked polluted data into VT-17 analytics for ~2 days.

## References

- `MANIFESTO.md §Shipping Philosophy` — retention mechanism first, research discipline invisible to user
- `docs/do_not_add.md §Hardcoded default values for any research-relevant field` — the canonical list of structural invariants for research-relevant fields
- `docs/strategic_decisions_april_14.md §3` — conflict-detection override model + Apr 16 refinement (Path A)
- `openclaw/skills/lyra-secretary/SKILL.md §Hard Rules` — agent-facing structural invariants (Hard Rules 3–5, 9)
- `docs/design_patterns/notification_patterns.md §Principles` — the non-blocking / no-guilt principles are behavioral-constraint decisions downstream of this one

## Integration-not-isolation principle
*Emerged from operator observation April 17, 2026: "we collect a LOT of data but feedback could be utilized MUCH better." The fix is not more data — it is more connections between existing data.*

**Rule:** Every new data source or feature must connect to ≥3 existing computation variables. Isolated additions that create new data streams without feeding existing computations are architectural debt.

**Diagnostic for any proposed feature:**
"Which existing variables does this touch?"
- ≥3 variables: integrated addition, proceed
- <3 variables: redesign to integrate, or park until integration path is clear

**Examples:**
- Brain dump textarea: isolated if just stored. Integrated when feeding `bias_factor` + `archetype` + `cascade_score` + `category_mapping` + `calibration_nudge` (8 variables).
- Deadline field: isolated if just displayed. Integrated when cross-referenced against `delta` + `initiation_delay` + `override_rate` + `scheduling_density` + `cascade_score` (5 variables).
- Mid-session check-in: isolated if just stored. Integrated when feeding `bias_factor` + `micro_mirror` + `insights` + `fragmentation_index` (4 variables).

**This principle does NOT mean:**
- Build all integrations at once (sequence them by phase)
- Reject simple fixes (bug fixes are not features)
- Reject seed-phase additions (Phase 4.5 description field stores data, Phase 6 integrates it — both are valid steps)

**Reference:** See `docs/parked_ideas.md` §Feature integration map for the current connection graph.

---

## Authority

Designed by operator (Ali Nasser) in conversation with assistant runtime (hosted model provider), April 16, 2026. Triggered by the Apr 15 dogfood finding "Conflict detection too strict for planned tasks" and the resulting Path A walk-back of the Apr 14 Gate B spec. Applies to every new user-facing rule from this date forward. Any rule proposed as "hard" must first pass the diagnostic test. Integration-not-isolation principle added April 17, 2026.
