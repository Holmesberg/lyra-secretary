# Academic Pressure Map Contract

**Status:** Active implementation contract.
**Created:** 2026-05-17.
**Scope:** Trust-state copy, pressure-map response shape, and Day-0 rules for
Academic Pressure Map surfaces.

This contract cross-links the Academic Pressure Map to validity threats and
research integrity before expanding the UI. Any future pressure-map, plan
preview, assumption-correction, or recalibration work must check:

- `MANIFESTO.md`, especially "Manifesto Governance Rule", "Substrate Kill
  Criterion", and "Academic Execution Substrate Governance". The manifesto is
  the highest-authority research/product boundary document.
- `docs/academic_execution_substrate.md` for academic evidence boundaries,
  passive activity limits, exposure contamination, and provider leakage rules.
- `docs/research_mapping.md` for measurement-validity threats and uncertainty
  language.
- `LyraOS/03_Concepts/Measurement Validity.md` for claim discipline.
- `LyraOS/03_Concepts/Exposure Contamination.md` and
  `LyraOS/02_Domains/Exposure_Ledger/Exposure Ledger.md` before adding any
  user-visible suggestion that may affect later behavior.
- `LyraOS/03_Concepts/Clean Data Profile.md` before admitting any academic
  event into calibration or baseline inference.
- `docs/academic_asset_velocity_and_evidence_fusion_plan.md` before adding
  asset-level duration priors, cohort workload estimates, passive activity
  signals, evidence tiers, or contradiction scoring.

## Product Promise

The Academic Pressure Map exists to create clarity and agency:

```text
Holy shit, this finally explains my week.
```

It must help the student see:

- what is due,
- what is big,
- what is soon,
- what is uncertain,
- what is already scheduled,
- where the week is compressed,
- and what can be done next without panic.

Day-0 value is bounded legibility, not omniscience. The first pressure map may
be only semi-accurate: it should make the scale and shape of the week visible
using provider structure, native deadlines, study/academic tasks, and labeled
duration priors. It becomes more personal only as accepted intentions,
corrections, execution traces, and cohort-safe asset estimates accumulate.

This is intentional. Lyra can be useful before it is deeply adaptive if it
shows approximate pressure honestly and lets the user correct it.

## Category Boundary

The pressure map includes both `academic` and `study` rows, but they do not
mean the same thing.

- `academic`: institution/provided or prescheduled academic structure,
  including deadlines, imported Baseet/Moodle obligations, lectures,
  tutorials, labs, classes, sections, and similar course events.
- `study`: user-owned self-study sessions, including revision, reading,
  slide review, problem solving, homework/assignment work blocks, and exam
  preparation the student schedules for themselves.

Both categories may appear on the same pressure surface because both consume
academic capacity. They must keep distinct source labels and assumptions:
provider/prescheduled structure is not self-study behavior, and self-study
intention is not provider coverage truth.

It must not imply:

- exact-hour certainty,
- learning/completion truth,
- hidden tracking,
- provider authority over truth,
- or productivity/moral judgment.

## Response Fields

The pressure snapshot may expose:

- `pressure_summary`: one concise explanation of visible academic pressure.
- `compression_points`: specific deadlines, clusters, overdue items, or
  known-load collisions that make the week feel compressed.
- `recovery_options`: bounded next actions such as confirm coverage, split a
  block, create a plan, or clear an irrelevant item.
- `coverage_questions`: assumptions that must be confirmed before plan
  generation.
- `capacity_context`: visible calendar/task load only. It must not pretend to
  know true free time unless the source coverage supports that claim.

## Trust-State Copy

Use the same meaning everywhere: pressure snapshot, plan-preview warnings,
assumption correction, and future provider-native surfaces.

| Trust state | User-facing meaning |
| --- | --- |
| `verified_exact` | Lyra has an authoritative source for this structure. It still does not prove execution, learning, or completion. |
| `verified_reachable` | Lyra reached/imported the source item. Coverage and correctness may still need confirmation. |
| `ambiguous` | Lyra sees more than one plausible interpretation and needs a user or moderator to disambiguate. |
| `requires_user_confirmation` | Lyra has a usable candidate, but the user must confirm before it drives a plan. |
| `stale` | The source may be outdated. Re-check before planning. |
| `dead_link` | The referenced source could not be reached. Do not use it as coverage truth. |
| `access_denied` | Lyra cannot inspect the source. Ask the user or provider for a safer path. |

## Coverage Validation Threshold

Do not ask every student to answer generalizable coverage questions.

- A moderator, instructor, or source-of-truth answer crosses the threshold
  immediately.
- Three to five student confirmations may validate quiz coverage, link
  validity, resource scope, or assignment structure for the cohort.
- Provider metadata may validate structure, but not learning or completion.
- Individual user corrections personalize that user's map immediately.
- AI/RAG output is a low-confidence candidate only.

Authority order:

1. instructor, moderator, or source-of-truth metadata,
2. provider/LMS structure,
3. 3-5 student confirmations,
4. individual user correction,
5. AI suggestion.

## Copy Rules

Copy must protect psychological safety. That does not mean hiding pressure or
making the system falsely comforting. It means pressure is described as a
structural condition, not as a moral failure or identity label.

Allowed:

```text
This week looks compressed.
Here are the pressure points.
This source is reachable, but coverage still needs confirmation.
Confirm coverage before turning this into a plan.
```

Forbidden:

```text
You are behind.
You are overloaded.
You failed to study.
Lyra knows exactly how long this will take.
```

## Calibration Rule

Planning calibration requires accepted intention plus observed execution.

Allowed first recalibration copy:

```text
Quiz 2 prep took 40% longer than estimated.
Lyra will widen ranges for this course going forward.
```

Forbidden:

```text
You are slow.
You wasted time.
This lecture activity proves you learned the material.
```

Passive academic activity is weak evidence. It must not become planned
execution calibration unless the user accepted or confirmed an intention.

## Architecture-Freeze Note

Asset-velocity estimates and passive/explicit evidence fusion are future work.
The current implementation is still `heuristic_v1`: static obligation priors,
title/category complexity heuristics, rounded uncertainty ranges, and no
lecture/tutorial/resource counts or personal execution history applied to the
estimate.

Future cohort-derived duration estimates must preserve estimate provenance,
minimum-N privacy thresholds, clean-data filters, and low-authority copy.
Passive activity may reduce manual friction, but must remain contextual
evidence, not execution truth.

Approximate-now/refined-later rule:

```text
heuristic pressure map
  -> user correction and accepted intention
  -> clean execution traces
  -> cohort-safe asset or course priors
  -> narrower future ranges
```

No range may become more authoritative unless its source, confidence, and
admission profile are visible to downstream consumers.
