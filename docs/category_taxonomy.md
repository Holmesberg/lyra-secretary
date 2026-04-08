# Category Taxonomy (Frozen — Apr 8 2026)

The category vocabulary is **frozen** for the duration of the April 4–15 measurement window. New keywords may be added; new *categories* may not, until post-experiment analysis.

## Rationale

Adding categories mid-experiment redistributes sessions across buckets and breaks the per-(category, time_of_day) bias-factor model. Bucket counts must remain monotonic over the window.

## Frozen list

| Category | Notes |
|---|---|
| fitness | Exercise / movement |
| academic | Lectures, classes, course-bound work |
| study | Self-directed learning, problem sets, reading |
| development | Coding, debugging, building (Lyra and other) |
| meeting | Synchronous calls, standups, interviews-as-meeting |
| prayer | Salah and related |
| self_reflection | Journaling, planning, calibration, refinement, brainstorming, reflection |
| network | Outreach, LinkedIn, networking interviews |
| health | Sleep, medical, recovery |
| work | Generic work fallback (quick / unplanned tasks) |
| personal | Meals and personal time |

## Apr 8 merge: `planning` → `self_reflection`

`planning`, `calibration`, `plan`, `friction` were originally seeded into a separate `planning` category. This was a bookkeeping mistake — they belong with `self_reflection`. The two categories were semantically identical (both are meta-work *about* the system rather than execution). Two cells split a tiny bucket and would have produced false-negative bias estimates.

**Action taken (Apr 8):** all `planning`-categorized rows in `task` and `category_mapping` repointed to `self_reflection`. The `planning` category is dead. Pre-registered as MANIFESTO Rule #2.

## Adding keywords (allowed)

New keywords mapping into existing categories may be added at any time via `seed.py`. Document under the dated comment block.

## Adding categories (not allowed until Apr 16)

After the experiment closes, post-hoc analysis may justify splitting `work`, splitting `study` (academic vs personal), or merging rare buckets. Do that against the frozen Apr 4–15 dataset, not against live data.
