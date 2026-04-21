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

// Fallback palette for user-created custom categories. Picked to be
// visually distinct from each other AND from the built-in set above
// (no hue overlap — these are orange, sky, lime, purple, yellow,
// red/salmon, gray, green, blue-violet, teal-warm). Same
// bg-500/15 + text-300 + border-500/25 pattern so a custom badge
// reads identically to a built-in one.
const CUSTOM_CATEGORY_PALETTE = [
  "bg-orange-500/15 text-orange-300 border-orange-500/25",
  "bg-sky-500/15 text-sky-300 border-sky-500/25",
  "bg-lime-500/15 text-lime-300 border-lime-500/25",
  "bg-purple-500/15 text-purple-300 border-purple-500/25",
  "bg-yellow-500/15 text-yellow-300 border-yellow-500/25",
  "bg-red-500/15 text-red-300 border-red-500/25",
  "bg-stone-500/15 text-stone-300 border-stone-500/25",
  "bg-green-500/15 text-green-300 border-green-500/25",
  "bg-violet-400/15 text-violet-200 border-violet-400/25",
  "bg-teal-400/15 text-teal-200 border-teal-400/25",
];

/**
 * Deterministic color assignment for any category name.
 *
 * Built-in categories return their canonical color from CATEGORY_COLORS.
 * Custom categories (user-typed via "+ Create a new category…" in the
 * new-task / retroactive modals) hash into CUSTOM_CATEGORY_PALETTE, so
 * the same custom name always renders the same color across
 * /today, /calendar, /table, and dropdowns — no DB round-trip needed.
 *
 * Fixes the 2026-04-21 dogfood report: "categories don't persist
 * after creating a new category, it should assign a color." Prior
 * task-row.tsx guarded on `CATEGORY_COLORS[cat]` which returned
 * undefined for custom cats → no badge rendered at all. Now every
 * category gets a badge.
 *
 * Hash: simple char-code sum modulo palette length. Cheap, stable,
 * no external dep.
 */
export function getCategoryColor(cat: string | null | undefined): string | null {
  if (!cat) return null;
  const built = (CATEGORY_COLORS as Record<string, string>)[cat];
  if (built) return built;
  let hash = 0;
  for (let i = 0; i < cat.length; i++) {
    hash = (hash + cat.charCodeAt(i)) % CUSTOM_CATEGORY_PALETTE.length;
  }
  return CUSTOM_CATEGORY_PALETTE[hash];
}
