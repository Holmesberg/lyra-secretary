/**
 * Frozen category taxonomy — source of truth: docs/category_taxonomy.md.
 * DO NOT add categories without updating the doc and the experiment plan.
 * Adding a new category mid-experiment redistributes buckets and breaks
 * the per-(category, time_of_day) bias-factor model.
 */
export const CATEGORIES = [
  "fitness",
  "academic",
  "study",
  "development",
  "meeting",
  "prayer",
  "self_reflection",
  "network",
  "health",
  "work",
  "personal",
] as const;

export type Category = (typeof CATEGORIES)[number];

// Muted hues that read cleanly on a dark background.
export const CATEGORY_COLORS: Record<Category, string> = {
  fitness: "bg-emerald-500/15 text-emerald-300 border-emerald-500/25",
  academic: "bg-blue-500/15 text-blue-300 border-blue-500/25",
  study: "bg-indigo-500/15 text-indigo-300 border-indigo-500/25",
  development: "bg-violet-500/15 text-violet-300 border-violet-500/25",
  meeting: "bg-amber-500/15 text-amber-300 border-amber-500/25",
  prayer: "bg-teal-500/15 text-teal-300 border-teal-500/25",
  self_reflection: "bg-fuchsia-500/15 text-fuchsia-300 border-fuchsia-500/25",
  network: "bg-cyan-500/15 text-cyan-300 border-cyan-500/25",
  health: "bg-rose-500/15 text-rose-300 border-rose-500/25",
  work: "bg-slate-500/15 text-slate-300 border-slate-500/25",
  personal: "bg-pink-500/15 text-pink-300 border-pink-500/25",
};
