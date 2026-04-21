/**
 * Frozen category taxonomy — source of truth: docs/product.md §1.
 * DO NOT add categories without updating the doc and the experiment plan.
 * Adding a new category mid-experiment redistributes buckets and breaks
 * the per-(category, time_of_day) bias-factor model.
 *
 * 2026-04-21: `self_reflection` → `planning` rename (Path B commitment).
 * The April 8 merge collapsed `planning` into `self_reflection` because
 * usage data showed operator-dominated self-reflection logging. Dogfood
 * data on 2026-04-21 (0/9 external tasks with >30min planning lead)
 * reversed that call — the product now needs to engineer planning as a
 * habit, so the category surface must invite planning not self-reflection.
 * Pure rename, same slot; bias_factor priors remain stable because the
 * (category, time_of_day) key space is unchanged. See
 * docs/strategic_decisions_april_21.md for the full reasoning.
 */
export const CATEGORIES = [
  "fitness",
  "academic",
  "study",
  "development",
  "meeting",
  "prayer",
  "planning",
  "network",
  "health",
  "work",
  "personal",
] as const;

export type Category = (typeof CATEGORIES)[number];

// Brand-unified state badges (Phase 3c). Mapped from the old traffic-
// light convention (blue/yellow/green/red) to the brand's two-accent
// palette + dust ramp, matching the active-timer-banner (Phase 3a)
// which uses signal for active and ember for paused:
//   PLANNED   → dust      (neutral, not yet started)
//   EXECUTING → signal    (active cyan — same as active-timer pulse)
//   PAUSED    → ember     (attention amber — same as paused-timer)
//   EXECUTED  → dust      (completed, greyed so planned rows lead the eye)
//   SKIPPED   → dust-deep (muted terminal state)
//   DELETED   → dust-deep/50 (archived)
export const STATE_STYLES: Record<string, string> = {
  PLANNED: "bg-void-2 text-dust border-hairline",
  EXECUTING: "bg-signal/15 text-signal border-signal/40",
  PAUSED: "bg-ember/15 text-ember border-ember/40",
  EXECUTED: "bg-dust/10 text-dust border-dust/30",
  SKIPPED: "bg-void-2 text-dust-deep border-hairline",
  DELETED: "bg-void-2/50 text-dust-deep/50 border-hairline/50",
};

export const CATEGORY_COLORS: Record<Category, string> = {
  fitness: "bg-emerald-500/15 text-emerald-300 border-emerald-500/25",
  academic: "bg-blue-500/15 text-blue-300 border-blue-500/25",
  study: "bg-indigo-500/15 text-indigo-300 border-indigo-500/25",
  development: "bg-violet-500/15 text-violet-300 border-violet-500/25",
  meeting: "bg-amber-500/15 text-amber-300 border-amber-500/25",
  prayer: "bg-teal-500/15 text-teal-300 border-teal-500/25",
  planning: "bg-fuchsia-500/15 text-fuchsia-300 border-fuchsia-500/25",
  network: "bg-cyan-500/15 text-cyan-300 border-cyan-500/25",
  health: "bg-rose-500/15 text-rose-300 border-rose-500/25",
  work: "bg-slate-500/15 text-slate-300 border-slate-500/25",
  personal: "bg-pink-500/15 text-pink-300 border-pink-500/25",
};
