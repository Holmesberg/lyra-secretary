# Strategic Decisions — April 14, 2026 Evening Session

Four structural clarifications that reframed Lyra's strategic position. Each
resolves an implicit or confused framing elsewhere in the docs. All
referenced in tonight's methodology commit or follow-up commits.

---

## 1. Behavioral correction primary, research as quality infrastructure

**Previous implicit framing:** Lyra is a research instrument that happens to
have a product surface.

**Clarified framing:** Lyra is a behavioral correction tool. Research
methodology (pre-registration, validity threats, kill criteria, publication)
serves the behavioral-correction thesis by producing trustable product
accuracy. Papers are side-effects that sharpen the instrument and build
user trust, not primary deliverables.

**Implication:** "Kill H1 if ρ < 0.20" is not project failure; it is "this
specific cold-start prediction mechanism did not work, iterate to next
candidate." H1 is one of several possible mechanisms for predicting user
behavior before sufficient personal data accumulates. Clustering +
archetype is another. Cascade detection is another.

**Documented in:** `MANIFESTO.md` top-of-file Framing section (shipped
tonight, v1.4 commit).

---

## 2. Gamification refinement: progressive revelation is permitted

**Previous framing:** gamification broadly rejected per `docs/do_not_add.md`.

**Refined framing:** gamification that rewards *behavior* is rejected;
gamification that rewards *self-knowledge discovery* is permitted. The
mechanical structure can be similar (threshold-triggered reveals, milestone
framing) but the psychological frame differs.

**Distinguishing test:** does the reward require the user to do something
(rejected) or does the reward deliver information about the user's own
behavior (permitted)?

**Documented in:**
- `docs/do_not_add.md §Gamification — PERMITTED: progressive revelation`
- `docs/design_patterns/notification_patterns.md §Progressive Revelation Pattern`

---

## 3. Conflict detection forced override affordance

**Previous framing:** hard block on measurement-critical overlaps (Gate B).

**Refined framing:** hard block with an explicit override affordance.
Override is a logged user action, preserving research integrity while
respecting user authority. Override rate becomes a signal for tuning gate
thresholds rather than a rule violation.

**Documented in:**
- `docs/building_phases.md §Phase 4.5 Tier 1 — Conflict detection with forced override affordance`
- `docs/dogfood_findings_living.md §Conflict detection override rate monitoring`
- `docs/operator_interrogation_checklist.md §Notification and override patterns` (Day 10)

---

## 4. Cold-start with trusted users as legitimate experiment

**Previous framing:** cold-start is a launch risk that needs solving before
trusted-user launch.

**Refined framing:** cold-start with trusted users is an experiment that
tests whether Lyra's base measurement loop has intrinsic appeal without
personalization priors. Both outcomes are informative:

- If trusted users engage despite cold-start, the base product is strong.
- If they disengage, clustering/archetype is proven necessary for alpha
  launch, not optional.

Trusted users + early alpha users are trust-side cohorts who will tolerate
cold-start better than stranger-cohort alpha users. Phase 5 pre-alpha ships
clustering/archetype informed by trusted-user cold-start data, not
speculation.

**Documented in:**
- `docs/building_phases.md §Phase 4.5` vs `§Phase 5 — Pre-alpha ship list` scope split
- `docs/dogfood_findings_living.md §Cold-start engagement decay analysis`

**Operator note:** this decision is revisitable if Spring School (April
19–29) generates contrary signal. If trusted users disengage before the
session-3 mirror, accelerate clustering/archetype work ahead of the May 1
alpha launch.
