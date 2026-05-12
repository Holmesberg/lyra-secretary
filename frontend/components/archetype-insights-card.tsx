"use client";
/**
 * Archetype insights card — shows at top of /insights page.
 *
 * Self-updating via React Query: the survey submit invalidates
 * ["me"] + ["bias_factor*"] + ["insights"] + ["proximity*"], causing
 * this card to auto-refetch and re-render.
 *
 * Layout philosophy (revised 2026-04-27 per MANIFESTO Rule 17):
 *   - HERO = TOP-3 dynamic posterior over archetypes (last 14d window).
 *     Replaces the prior static "Profile: Procrastinator" identity
 *     framing with a moving-observation framing. Mitigates VT-25
 *     label-internalization (per Rule 17 §25a kill criterion).
 *   - TREND CAPTION = "a month ago you were Y — pattern is shifting
 *     toward X" — only renders when the prior window has data.
 *   - COLLAPSIBLE = blend math (archetype prior, personal weight,
 *     blended number). Tangentially-related but useful for the
 *     operator / research-minded users. Note: the disclosure shows
 *     the SURVEY-assigned archetype's prior (frozen at survey time);
 *     the dynamic posterior above shows current behavior. The two
 *     SHOULD diverge as data accumulates — that divergence is the
 *     literal claim of the system.
 *
 * Display adapts to state:
 *   - NO archetype: "Take the survey in Settings to unlock" + link
 *   - Archetype assigned, backend `ready=false`: backend-governed
 *     settling/rhythm copy, with no behavioral proximity bars.
 *   - Archetype assigned, backend `ready=true`: full dynamic posterior view.
 */
import { useState } from "react";
import { ChevronUp, Sigma } from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import { Card, CardContent } from "@/components/ui/card";
import { api } from "@/lib/api";
import {
  getArchetypeProximity,
  getArchetypeProximityTrend,
} from "@/lib/archetype";
import {
  ArchetypeProximityRows,
  ArchetypeSaturationNote,
  ArchetypeTrendCaption,
} from "@/components/archetype-proximity-display";
// ARCHETYPE_DESCRIPTIONS + ARCHETYPE_PLANNING_IMPLICATION imports
// dropped 2026-04-27 (Rule 17): the dynamic posterior view doesn't
// surface the prescriptive "people like you typically..." copy because
// that re-anchors users to identity framing — exactly the
// label-internalization risk Rule 17 mitigates. The dicts remain
// exported from @/lib/archetype for any future surface that wants them.

interface MeArchetype {
  archetype_id: string | null;
  archetype_assignment_completed: boolean;
  archetype_latest_assignment_at: string | null;
  executed_session_count: number;
}

interface BiasBlendSample {
  bias_factor_final?: number;
  archetype_id?: string;
  archetype_prior_for_cell?: number;
  archetype_scaling?: number;
  personal_weight?: number;
  prior_weight?: number;
  cell?: { bias_factor?: number; sessions?: number };
}

const SAMPLE_CATEGORY = "development";
const SAMPLE_TOD = "morning";
const SAMPLE_MINUTES = 60;

export function ArchetypeInsightsCard() {
  const [mathOpen, setMathOpen] = useState(false);

  const meQ = useQuery({
    queryKey: ["me"],
    queryFn: () => api<MeArchetype>("/v1/users/me"),
    staleTime: 60_000,
  });

  const blendQ = useQuery({
    queryKey: ["bias_factor", SAMPLE_CATEGORY, SAMPLE_TOD, SAMPLE_MINUTES],
    queryFn: () =>
      api<BiasBlendSample>(
        `/v1/analytics/bias_factor/lookup?category=${SAMPLE_CATEGORY}&tod=${SAMPLE_TOD}&planned_minutes=${SAMPLE_MINUTES}`
      ),
    staleTime: 60_000,
    enabled: meQ.data != null && mathOpen,
  });

  if (!meQ.data) return null;
  const me = meQ.data;
  const archetypeId = me.archetype_id;
  if (!archetypeId) {
    return (
      <Card>
        <CardContent className="p-5">
          <p className="text-sm text-dust">
            No profile yet. The{" "}
            <a
              href="/settings"
              className="text-signal underline-offset-2 hover:text-signal-neon hover:underline"
            >
              4-minute survey in Settings
            </a>{" "}
            gives Lyra a head start on how you tend to plan and work.
            Predictions still personalize as you log sessions.
          </p>
        </CardContent>
      </Card>
    );
  }

  return (
    <DynamicProximityCard
      archetypeId={archetypeId}
      mathOpen={mathOpen}
      onToggleMath={() => setMathOpen((o) => !o)}
      blendData={blendQ.data}
    />
  );
}

// ──────────────────────────────────────────────────────────────────────
// Dynamic posterior reveal (MANIFESTO Rule 17, 2026-04-27).
// ──────────────────────────────────────────────────────────────────────

function DynamicProximityCard({
  archetypeId,
  mathOpen,
  onToggleMath,
  blendData,
}: {
  archetypeId: string;
  mathOpen: boolean;
  onToggleMath: () => void;
  blendData?: BiasBlendSample;
}) {
  const proximityQ = useQuery({
    queryKey: ["proximity", 14],
    queryFn: () => getArchetypeProximity(14),
    staleTime: 60_000,
  });
  const trendQ = useQuery({
    queryKey: ["proximity-trend", 14, 14],
    queryFn: () => getArchetypeProximityTrend(14, 14),
    staleTime: 60_000,
    enabled: proximityQ.data?.ready === true,
  });

  if (proximityQ.isLoading) {
    return (
      <Card>
        <CardContent className="flex flex-col gap-3 p-5">
          <div className="font-mono text-[10px] uppercase tracking-widest text-dust-deep">
            Your pattern
          </div>
          <div className="h-20 animate-pulse rounded-sm bg-void/30" />
        </CardContent>
      </Card>
    );
  }
  if (!proximityQ.data) return null;

  // Backend readiness is authoritative. The frontend may choose copy for a
  // display mode, but it must not invent readiness or render bars when the
  // registered surface says this interpretation is still suppressed.
  const backendSaysNotReady = proximityQ.data.ready === false;
  if (backendSaysNotReady || proximityQ.data.n_tasks < 3) {
    const eligibleCount =
      proximityQ.data.eligible_sample_count ?? proximityQ.data.n_tasks ?? 0;
    const minRequired = proximityQ.data.min_n_required ?? 3;
    const remaining = Math.max(0, minRequired - eligibleCount);
    const displayMode = proximityQ.data.display_mode ?? "settling_in";
    const isSettlingIn = displayMode === "settling_in";
    return (
      <Card>
        <CardContent className="flex flex-col gap-3 p-5">
          <div className="font-mono text-[10px] uppercase tracking-widest text-dust-deep">
            {isSettlingIn ? "Settling in" : "Your pattern"}
          </div>
          <p className="text-sm leading-relaxed text-dust">
            {isSettlingIn
              ? "Lyra is using your survey quietly in the background while it waits for observed sessions. "
              : "Lyra needs a few more recent sessions before it can show behavioral proximity. "}
            {remaining > 0
              ? `After ${remaining === 1 ? "one more eligible session" : `${remaining} more eligible sessions`}, this card can compare recent traces without turning the survey into an identity label.`
              : "The backend has not marked this surface ready yet, so Lyra is keeping the interpretation hidden for now."}
          </p>
        </CardContent>
      </Card>
    );
  }

  const top3 = proximityQ.data.proximity.slice(0, 3);
  const top = top3[0];

  return (
    <Card>
      <CardContent className="flex flex-col gap-4 p-5">
        <div>
          <div className="mb-2 font-mono text-[10px] uppercase tracking-widest text-dust-deep">
            Your last 14 days look most like…
          </div>
          <ArchetypeProximityRows top3={top3} trend={trendQ.data} />
        </div>

        {trendQ.data && (
          <ArchetypeTrendCaption top={top} trend={trendQ.data} />
        )}

        <ArchetypeSaturationNote top={top} />

        <p className="text-[11px] leading-relaxed text-dust-deep">
          These tendencies shift as Lyra sees more of how you actually work.
          Not a fixed identity — a moving observation.
        </p>

        {/* Math disclosure — icon-only toggle, low-prominence. The blend
            math here is about the SURVEY-assigned archetype's prior (frozen
            at survey time). The pattern above is current behavior — these
            two SHOULD diverge over time. */}
        {blendData && typeof blendData.bias_factor_final === "number" && (
          <MathDisclosure
            open={mathOpen}
            onToggle={onToggleMath}
            blend={blendData}
          />
        )}
      </CardContent>
    </Card>
  );
}

function MathDisclosure({
  open,
  onToggle,
  blend,
}: {
  open: boolean;
  onToggle: () => void;
  blend: BiasBlendSample;
}) {
  if (!open) {
    return (
      <button
        type="button"
        onClick={onToggle}
        aria-label="Show calibration math"
        title="Show calibration math"
        className="inline-flex h-6 w-6 items-center justify-center self-end rounded-sm text-dust-deep transition-colors hover:text-signal"
      >
        <Sigma className="h-3.5 w-3.5" />
      </button>
    );
  }
  return (
    <div className="flex flex-col gap-2">
      <div className="flex items-center justify-between gap-2">
        <div className="inline-flex items-center gap-2 font-mono text-[10px] uppercase tracking-widest text-dust-deep">
          <Sigma className="h-3 w-3" />
          Calibration math
        </div>
        <button
          type="button"
          onClick={onToggle}
          aria-label="Hide calibration math"
          title="Hide calibration math"
          className="inline-flex h-6 w-6 items-center justify-center rounded-sm text-dust-deep transition-colors hover:text-parchment"
        >
          <ChevronUp className="h-3.5 w-3.5" />
        </button>
      </div>
      <BlendSample blend={blend} />
    </div>
  );
}

function BlendSample({ blend }: { blend: BiasBlendSample }) {
  const final = blend.bias_factor_final ?? 0;
  const personalWeight = blend.personal_weight ?? 0;
  const priorWeight = blend.prior_weight ?? 1;
  const personalSessions = blend.cell?.sessions ?? 0;
  const archPrior = blend.archetype_prior_for_cell ?? 0;
  const personalValue = blend.cell?.bias_factor ?? 0;
  const finalPct = Math.round((final - 1) * 100);
  const personalPct =
    personalSessions > 0 ? Math.round((personalValue - 1) * 100) : null;

  return (
    <div className="mt-2 rounded-sm border border-hairline bg-void/30 p-3 font-mono text-[11px] leading-relaxed">
      <div className="mb-2 text-dust-deep">
        Reference cell: {SAMPLE_CATEGORY} · {SAMPLE_TOD} · {SAMPLE_MINUTES}-min
      </div>
      <div className="flex flex-wrap gap-x-4 gap-y-1">
        <div>
          <span className="text-dust-deep">archetype prior:</span>{" "}
          <span className="text-parchment">{archPrior.toFixed(2)}</span>{" "}
          <span className="text-dust-deep">
            × {priorWeight.toFixed(2)} weight
          </span>
        </div>
        <div>
          <span className="text-dust-deep">personal:</span>{" "}
          {personalSessions > 0 ? (
            <>
              <span className="text-parchment">
                {personalValue.toFixed(2)}
              </span>{" "}
              <span className="text-dust-deep">
                × {personalWeight.toFixed(2)} weight ({personalSessions}{" "}
                session{personalSessions !== 1 ? "s" : ""})
              </span>
            </>
          ) : (
            <span className="text-dust-deep">no data yet</span>
          )}
        </div>
        <div>
          <span className="text-dust-deep">blended:</span>{" "}
          <span className="text-signal">{final.toFixed(3)}</span>{" "}
          <span className="text-dust-deep">
            ({finalPct > 0 ? "+" : ""}
            {finalPct}% vs plan)
          </span>
        </div>
      </div>
      {personalPct !== null && Math.abs(personalPct - finalPct) > 5 && (
        <p className="mt-2 text-[11px] text-dust-deep">
          {personalPct > finalPct ? "Shrinkage pulls" : "Shrinkage lifts"}{" "}
          your noisy personal estimate ({personalPct > 0 ? "+" : ""}
          {personalPct}%) toward the research-backed prior. As you
          accumulate sessions, the personal weight grows and this
          number converges to your true pattern.
        </p>
      )}
    </div>
  );
}
