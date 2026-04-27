"use client";
/**
 * Shared archetype-proximity rendering — top-3 bars + trend caption.
 * Used by both archetype-insights-card.tsx (/today) and
 * archetype-profile-section.tsx (/settings).
 *
 * Pre-registered MANIFESTO Rule 17 (2026-04-27 — VT-25 dynamic-reveal).
 * Replaces the prior static "Profile: Procrastinator" identity framing
 * with a moving-observation view: top-3 archetypes + percentages +
 * trend arrows + "two weeks ago you were Y" caption.
 *
 * Copy guidance (from feedback_warm_tone_copy memory):
 *   - Avoid "calibration", "prior", "Bayesian", "posterior" in user
 *     strings — those are research vocab. Use "tendencies", "patterns",
 *     "shifts", "rhythm".
 *   - Treat label as observation, not identity. "Your last 14 days look
 *     most like X" instead of "You ARE X."
 */
import { ArrowDown, ArrowUp, Minus } from "lucide-react";
import {
  ARCHETYPE_LABELS,
  type ArchetypeProximity,
  type ProximityTrend,
} from "@/lib/archetype";


/**
 * Renders the top-3 archetypes as labeled bars with percentages + trend arrows.
 * Caller passes the proximity result; this just renders it.
 */
export function ArchetypeProximityRows({
  top3,
  trend,
}: {
  top3: ArchetypeProximity[];
  trend: ProximityTrend | undefined;
}) {
  return (
    <div className="flex flex-col gap-1.5">
      {top3.map((arch, idx) => {
        const delta = trend?.delta_per_archetype[arch.archetype_id] ?? 0;
        const label = ARCHETYPE_LABELS[arch.archetype_id] ?? arch.label;
        const pct = Math.round(arch.score * 100);
        return (
          <div key={arch.archetype_id} className="flex items-center gap-3">
            <div
              className={
                idx === 0
                  ? "min-w-[140px] text-sm font-medium text-parchment"
                  : "min-w-[140px] text-sm text-dust"
              }
            >
              {label}
            </div>
            <ArchetypeTrendArrow delta={delta} />
            <div className="relative h-2 flex-1 overflow-hidden rounded-sm bg-void/40">
              <div
                className={
                  idx === 0
                    ? "absolute left-0 top-0 h-full bg-signal"
                    : "absolute left-0 top-0 h-full bg-dust/60"
                }
                style={{ width: `${Math.max(2, pct)}%` }}
              />
            </div>
            <div
              className={
                idx === 0
                  ? "min-w-[36px] text-right font-mono text-sm text-parchment"
                  : "min-w-[36px] text-right font-mono text-sm text-dust"
              }
            >
              {pct}%
            </div>
          </div>
        );
      })}
    </div>
  );
}

/**
 * Trend arrow for a single row. ↑ = trending toward this archetype,
 * ↓ = trending away, • = stable. Threshold of 0.05 in posterior delta
 * means a meaningful shift; below that we render stable.
 */
export function ArchetypeTrendArrow({ delta }: { delta: number }) {
  if (delta > 0.05) {
    return (
      <ArrowUp
        className="h-3 w-3 flex-shrink-0 text-green"
        aria-label="trending toward"
      />
    );
  }
  if (delta < -0.05) {
    return (
      <ArrowDown
        className="h-3 w-3 flex-shrink-0 text-accent3"
        aria-label="trending away"
      />
    );
  }
  return (
    <Minus
      className="h-3 w-3 flex-shrink-0 text-dust-deep"
      aria-label="stable"
    />
  );
}

/**
 * Trend caption: "Two weeks ago you were Y (XX%). Pattern is consolidating
 * toward X." Returns null when the prior window has no qualifying tasks
 * (uniform distribution → no comparison signal).
 */
export function ArchetypeTrendCaption({
  top,
  trend,
}: {
  top: ArchetypeProximity;
  trend: ProximityTrend;
}) {
  if (!trend.prior.length || trend.prior[0].n_tasks === 0) return null;
  const priorTop = trend.prior[0];
  const priorLabel = ARCHETYPE_LABELS[priorTop.archetype_id] ?? priorTop.label;
  const priorPct = Math.round(priorTop.score * 100);
  const currentLabel = ARCHETYPE_LABELS[top.archetype_id] ?? top.label;

  let pattern: string;
  if (priorTop.archetype_id === top.archetype_id) {
    const scoreDelta = top.score - priorTop.score;
    if (scoreDelta > 0.10) {
      pattern = `consolidating toward ${currentLabel}`;
    } else if (scoreDelta < -0.10) {
      pattern = "becoming less consolidated";
    } else {
      pattern = "stable";
    }
  } else {
    pattern = `shifting from ${priorLabel} toward ${currentLabel}`;
  }

  return (
    <p className="text-xs leading-relaxed text-dust">
      Two weeks ago you were{" "}
      <span className="text-parchment">{priorLabel}</span>{" "}
      <span className="text-dust-deep">({priorPct}%)</span>. Pattern is{" "}
      <span className="text-parchment">{pattern}</span>.
    </p>
  );
}
