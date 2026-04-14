# Structural Investigation Rule

**Owner:** Operator
**Created:** April 14, 2026 (triggered by pause-prediction spec vs schema mismatch)
**Status:** Canonical. Applies to any Claude Code work that touches measurement, data flow, or research-relevant fields. Applies to Claude in chat discussion of such features as well.

This document is referenced by `CLAUDE.md`. If you are about to implement a feature that touches the Lyra measurement instrument — stop and read this before producing a design or any code.

---

## Why this rule exists

Lyra is a measurement instrument first and a product second. A feature that ships with a hidden design tension does not simply "cause a bug"; it corrupts the research signal retroactively and silently. Unlike a normal product bug, the cost compounds over time — data collected under the broken assumption cannot be reclassified after the fact.

The rule was forged on April 14, 2026 after a pause-prediction feature spec assumed pause *event* history existed in the schema, when in fact the schema only retained the most-recent pause per session (cleared on resume). Catching that at design time cost one conversation turn. Catching it after shipping would have meant a week of prediction data with no valid foundation, a research commit that had to be backed out, and a Validity Threat entry written retroactively. That asymmetry is the motivation.

The rule encodes the principle: **the cost of finding an architectural tension at design time is low; the cost of finding it after shipping is high.**

---

## When the rule applies

A feature triggers the rule if ANY of the following is true:

- It writes, reads, derives, or changes the persistence of a research-relevant field — see `docs/do_not_add.md §Hardcoded default values` for the canonical list (readiness, reflection, completion percentage, pause reason, pause initiator, unplanned reason, void reason, bias_factor inputs, any field consumed by MANIFESTO hypotheses).
- It adds, changes, or bypasses a notification surface — see `docs/design_patterns/notification_patterns.md`.
- It introduces a new signal stream (V1/V3/V5 candidate) or changes how an existing signal is captured.
- It touches the state machine, stopwatch lifecycle, or any boundary where planned/executed time is computed.
- It proposes a new derived metric (ratios, deltas, indices) or changes the formula of an existing one.
- It introduces scheduler jobs, polling intervals, or any cadence that could fire notifications or write data.

A feature does NOT trigger the rule if it is ALL of the following:

- A pure correctness fix (bug that makes existing behavior match intended behavior without changing the measurement contract).
- A rename or refactor that leaves data-shape and field-semantics unchanged.
- A docstring, comment, or non-functional documentation edit.
- A typing annotation addition that does not change runtime behavior.

When in doubt, the rule applies. A five-minute scan is cheap insurance.

---

## The six steps

Before proposing an implementation, execute each step in order. A "pass" on one step does not let you skip a later step.

### Step 1 — Scan the data domain

What's collected, what's derived, what relationships already exist. Read the relevant models, migrations, and schemas. Confirm the data the spec assumes is actually persisted — not just referenced in a UI flow or log line.

Ask: "If I ran `SELECT` right now, would I get the rows the spec assumes I'd get?"

### Step 2 — Scan the implementation domain

What endpoints, services, scheduler jobs, or delivery paths already serve adjacent use cases. Adjacent code often reveals the intended pattern and also the pitfalls.

Ask: "Where does the existing codebase already solve a problem shaped like this one? What did they do, and what did they not do?"

### Step 3 — Scan the research-integrity domain

Which validity threats, hard rules, or pre-registrations would the proposed feature intersect with. The canonical references:

- `MANIFESTO.md §The Validity Register` — VT-1..VT-n
- `openclaw/skills/lyra-secretary/SKILL.md §Hard Rules`
- `docs/do_not_add.md` — rejected patterns
- `docs/design_patterns/notification_patterns.md` — notification principles
- `docs/phase_6_architecture_backlog.md` — routed/conditional behavior

Ask: "If I ship this, which VT could become load-bearing? Which Hard Rule is in the neighborhood? Which `do_not_add.md` pattern is close enough that I need to actively rule it out?"

### Step 4 — Surface findings BEFORE proposing implementation

Produce a written report, in-message or in a plan file. Four required sections:

- **Spec-vs-reality gaps:** what the spec assumed that the schema, existing services, or notification layer does not actually support.
- **Load-bearing design tensions:** architectural choices that force a downstream trade-off (surface type, delivery channel, state-machine scope, rate-limit granularity).
- **Research-integrity risks:** VT candidates, Hard Rule adjacencies, pre-registration exposures.
- **Reusable infrastructure:** what already exists that the implementation should plug into rather than rebuild.

If any of the four sections is empty, say so explicitly — "no research-integrity risks identified" is a valid finding. A missing section is not.

### Step 5 — Propose 2–3 solution options with explicit pro/con

Include rejected options with reasoning. A one-option design is a decision disguised as a finding.

Each option names: the mechanism, the code scope delta, the pros, the cons, and — critically — which Validity Threats or Hard Rules it brushes against.

### Step 6 — Pre-register measurement and kill criteria

Before the feature ships to users, write down:

- The exact formula for whatever metric decides "this feature works" — numerator, denominator, window, per-user vs aggregate.
- The ship threshold and the kill threshold (≥X ship, <Y kill, reviewed after N days).
- The window start — a timestamp, not a relative "after 7 days of use."
- The planned Validity Threat entries (even if deferred; candidates go in the register as "VT-n candidate" immediately).

Pre-registration is for research honesty: post-hoc threshold adjustment is indistinguishable from p-hacking to a future reviewer, including future-you.

---

## Halt for operator review

After producing the Step 4 findings and Step 5 options — **stop**. Do not write code. Do not start a migration. Do not touch a scheduler.

Surface the findings to the operator. Wait for explicit yes/no on:

- Which option to proceed with.
- Any constraints on scope, timing, or tier placement.
- Any adjacent cleanups discovered during the scan that the operator wants bundled in (the scan often surfaces latent issues — the operator decides whether to pull them into scope or leave them).
- The pre-registered kill criterion formula (Step 6).

A single yes-or-no round is usually enough. Multi-round halts mean the spec was too vague to investigate cleanly — that is the operator's signal, not a failure.

The explicit halt-before-code rule is non-negotiable. The prior conversation has no memory of the design tension once the next feature starts; the commit message does not record it; the test suite does not re-verify it. If the finding is not surfaced before code is written, it may as well not have been found.

---

## Exceptions

These can skip the rule:

- Pure correctness fixes with no measurement implications (bug fixes that restore intended behavior, no field semantics changed).
- Rename / refactor operations that preserve data shape and field semantics.
- Docstring, comment, or formatting edits.
- Pure typing improvements (annotations that do not change runtime).

These CANNOT skip the rule even if they feel small:

- "Just adding a column" — migrations are measurement commitments.
- "Just a scheduler job" — cadence is a feature, and cadence shapes user behavior.
- "Just a notification" — see `notification_patterns.md` for why this is never "just."
- "Just a default value" — see `do_not_add.md §Hardcoded default values`.

---

## What this rule is not

- Not a gate designed to slow the operator down. The scan is cheap when applied to a well-bounded spec.
- Not a substitute for operator judgment. It surfaces findings; the operator chooses the path.
- Not a research-protocol review board. Pre-registration here is lightweight (one paragraph, one formula) — not an IRB submission.
- Not a reason to over-engineer. Step 5 always includes an option that is "ship what's structurally right, even if smaller." Usually that wins.

---

## References

- `CLAUDE.md` §Structural Investigation Rule — short pointer to this doc
- `docs/design_patterns/notification_patterns.md` — notification surface authority
- `docs/design_patterns/two_stage_destruction.md` — adjacent design-pattern canon
- `docs/do_not_add.md` — rejected patterns, canonical list of research-relevant fields
- `MANIFESTO.md §The Validity Register` — where VT candidates land
- `docs/phase_6_architecture_backlog.md` — routed behavior, signal mapping

---

## Authority

Designed by operator (Ali Nasser) in conversation with Claude (Anthropic), April 14, 2026. Triggered by the pause-prediction spec vs. schema mismatch: spec assumed a pause-event history table existed; schema retained only one pause per session, cleared on resume. Rule is canonical. Features ship under its authority after April 14, 2026.
