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

## Category type field (design — Phase 4)

Each category will carry a `category_type` enum with two values:

| Type | Meaning | Examples | Analytics treatment |
|---|---|---|---|
| `estimable` | Duration is under the user's control. Planned vs executed delta is meaningful. | development, study, academic, fitness, work | Included in bias-factor estimation, H1 correlation, scheduling predictions |
| `time_anchored` | Duration is externally fixed or has negligible variance. Delta is noise, not signal. | prayer, meeting, health | Excluded from bias-factor cells. Shown in timeline but not in calibration analytics. |

**Why this matters:** The bias-factor model (`sum(executed) / sum(planned)` per cell) is only meaningful for categories where the user controls how long a task takes. Prayer is always ~15 min. Meetings end when the other party decides. Including these in the bias model dilutes the signal and produces false "accurate" bias factors that are really just "the externally-fixed tasks pulled the ratio toward 1.0."

**Implementation note (Phase 4):** Add a `category_type` column to `category_mapping` (default `estimable`), seed the two `time_anchored` categories (prayer, meeting), and filter on `category_type = 'estimable'` in the bias-factor query and the H1 analysis query. The query endpoint returns the field so the frontend can render type-appropriate UI (e.g., no delta badge on time-anchored tasks).

## Planned rename: `self_reflection` → `planning`

The `self_reflection` category name was inherited from the original seed and has caused confusion:

- Users type "planning session" and expect it to land in a category called `planning`, not `self_reflection`.
- The keyword mapping handles this (`planning` → `self_reflection`), but the mismatch between what users say and what the system stores is a friction point.
- The name `self_reflection` implies introspection/journaling, but the category also covers system calibration, brainstorming, and operational planning — activities that are better described as "planning."

**Rename plan (Phase 4, post-experiment freeze):**
1. Add Alembic migration: `UPDATE category_mapping SET category = 'planning' WHERE category = 'self_reflection'`
2. Update `task` table: `UPDATE task SET category = 'planning' WHERE category = 'self_reflection'`
3. Update `seed.py` to use `planning` as the canonical name.
4. Keep `self_reflection` as a keyword alias mapping to `planning` for backwards compatibility.
5. Update this taxonomy doc and any analytics queries that reference the old name.

This rename is blocked until the Apr 4–15 experiment window closes (MANIFESTO Rule #2).

## Adding keywords (allowed)

New keywords mapping into existing categories may be added at any time via `seed.py`. Document under the dated comment block.

## Adding categories (not allowed until Apr 16)

After the experiment closes, post-hoc analysis may justify splitting `work`, splitting `study` (academic vs personal), or merging rare buckets. Do that against the frozen Apr 4–15 dataset, not against live data.
