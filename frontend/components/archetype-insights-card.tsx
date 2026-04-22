"use client";
/**
 * Archetype insights card — shows at top of /insights page.
 *
 * Self-updating: reads /v1/users/me + /v1/analytics/bias_factor/lookup
 * via React Query. When the operator submits or skips the survey, the
 * ArchetypeSurvey component invalidates `["me"]` + `["bias_factor_*"]`
 * + `["insights"]` query keys, causing this card to auto-refetch and
 * re-render with the new archetype + updated blend.
 *
 * Display adapts to state:
 *   - NO archetype (no assignment): "Take the survey to unlock
 *     personalized predictions" + dead-end (link to Settings)
 *   - Diffuse Average (skipped or legitimately classified there):
 *     "Using population-average priors" + blend sample
 *   - Any other archetype: "Profile: <label> · predictions shifted
 *     <direction> <magnitude> on a representative cell"
 *
 * The "blend sample" fetches a representative bias_factor lookup
 * (category=development, tod=morning, planned=60min) so the user can
 * see the actual shift in action. This cell was chosen because it
 * maps to the highest-magnitude research prior (1.50, Buehler 1994)
 * and is where archetype differences are most visible.
 */
import { useQuery } from "@tanstack/react-query";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { api } from "@/lib/api";
import { ARCHETYPE_LABELS } from "@/lib/archetype";

interface MeArchetype {
  archetype_id: string | null;
  archetype_assignment_completed: boolean;
  archetype_latest_assignment_at: string | null;
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

// Representative cell — development/morning/60min is where research
// priors are strongest (1.50, Buehler 1994) so archetype scaling
// differences are most visible.
const SAMPLE_CATEGORY = "development";
const SAMPLE_TOD = "morning";
const SAMPLE_MINUTES = 60;

export function ArchetypeInsightsCard() {
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
    enabled: meQ.data != null,
  });

  if (!meQ.data) return null;

  const me = meQ.data;
  const blend = blendQ.data;

  const archetypeId = me.archetype_id;
  const label = archetypeId
    ? ARCHETYPE_LABELS[archetypeId] ?? archetypeId
    : null;
  const daysSince = me.archetype_latest_assignment_at
    ? Math.floor(
        (Date.now() - new Date(me.archetype_latest_assignment_at).getTime()) /
          (24 * 60 * 60 * 1000)
      )
    : null;

  // State classification.
  const state =
    archetypeId === null
      ? "none"
      : !me.archetype_assignment_completed
      ? "skipped"
      : "assigned";

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center justify-between gap-3">
          <span>Your archetype profile</span>
          {label && (
            <span className="rounded-sm bg-signal/10 px-2 py-0.5 font-mono text-[10px] font-medium uppercase tracking-widest text-signal">
              {label}
            </span>
          )}
        </CardTitle>
      </CardHeader>
      <CardContent className="p-4 pt-0">
        {state === "none" && (
          <p className="text-sm text-dust">
            No archetype assigned yet. Predictions currently use
            flat-1.0 fallback — take the{" "}
            <a
              href="/settings"
              className="text-signal underline-offset-2 hover:text-signal-neon hover:underline"
            >
              4-minute survey in Settings
            </a>{" "}
            to unlock personalized priors.
          </p>
        )}

        {state === "skipped" && (
          <p className="text-sm text-dust">
            You're using the population-average prior ({label}). Take
            the{" "}
            <a
              href="/settings"
              className="text-signal underline-offset-2 hover:text-signal-neon hover:underline"
            >
              survey in Settings
            </a>{" "}
            anytime to swap this for a prior tuned to how you actually
            work.
          </p>
        )}

        {state === "assigned" && daysSince !== null && (
          <p className="mb-3 text-sm text-dust">
            Profile assigned {daysSince === 0 ? "today" : `${daysSince} day${daysSince !== 1 ? "s" : ""} ago`}.
            Your predictions are now leaning on this prior — blending
            with your personal data as you accumulate sessions.
          </p>
        )}

        {/* Blend sample — shown for every state except "none" */}
        {state !== "none" && blend && typeof blend.bias_factor_final === "number" && (
          <BlendSample blend={blend} />
        )}
      </CardContent>
    </Card>
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
  const personalPct = personalSessions > 0 ? Math.round((personalValue - 1) * 100) : null;

  return (
    <div className="rounded-sm border border-hairline bg-void/30 p-3 font-mono text-[11px] leading-relaxed">
      <div className="mb-2 text-dust-deep">
        Sample: {SAMPLE_CATEGORY} · {SAMPLE_TOD} · {SAMPLE_MINUTES}-min tasks
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
          accumulate sessions, the personal weight grows and this number
          converges to your true pattern.
        </p>
      )}
    </div>
  );
}
