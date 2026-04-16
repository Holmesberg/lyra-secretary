"use client";

/**
 * /insights — placeholder route (Apr 16 2026 evening scaffold).
 *
 * Route file exists so that (a) Next.js compile stays warm and (b) a
 * typo'd or deep link to /insights returns a readable 200 instead of
 * 404 during the trusted-user window. Real rendering ships tomorrow
 * (Apr 17) with browser-verify — see docs/building_phases.md §Phase
 * 4.5 Tier 1 §/insights tab v1.
 *
 * Planned structure (to build tomorrow):
 *   - Fetch GET /v1/analytics/insights (returns list of 11 generator
 *     outputs; each is Optional[dict] with observation + evidence +
 *     strength fields).
 *   - If EXECUTED task count < 3 for this user → progress framing
 *     "Insights unlock in N more sessions" per docs/do_not_add.md
 *     §Gamification PERMITTED: progressive revelation.
 *   - If count >= 3 → render the non-None insight cards. Use
 *     @tremor/react (already in package.json ^3.18.7) for the
 *     three VT-12 companion charts (discrepancy × delta, readiness
 *     × focus, cascade trend).
 *   - Sections: (a) Insights unlock progress, (b) per-insight cards,
 *     (c) cascade_score trend, (d) bias_factor-by-category strip,
 *     (e) pause pattern card (pause_reason enum counts).
 *   - No confrontation dialect yet — metric dialect only per
 *     notification_patterns.md §Surface ordering.
 */
export default function InsightsPage() {
  return (
    <div className="flex min-h-[60vh] flex-col items-center justify-center gap-3 text-center">
      <h1 className="text-xl font-semibold text-white/80">Insights</h1>
      <p className="max-w-md text-sm text-white/50">
        Your patterns show up here as data accumulates. This surface ships
        April 17 — track one more session today to seed the first cards.
      </p>
    </div>
  );
}
