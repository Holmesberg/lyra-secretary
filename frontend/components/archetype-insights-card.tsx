"use client";
/**
 * Archetype insights card — shows at top of /insights page.
 *
 * Self-updating via React Query: the survey submit invalidates
 * ["me"] + ["bias_factor*"] + ["insights"], causing this card to
 * auto-refetch and re-render with the new archetype + updated blend.
 *
 * Layout philosophy (operator note 2026-04-23, "outputs the math not
 * the archetype"):
 *   - HERO = archetype name + behavioral description + planning
 *     implication. This is the identity the user cares about.
 *   - COLLAPSIBLE = blend math (archetype prior, personal weight,
 *     blended number). Useful for the operator / research-minded
 *     users, noise for everyone else.
 *
 * Display adapts to state:
 *   - NO archetype: "Take the survey in Settings to unlock" + link
 *   - Archetype assigned: hero label + description + implication +
 *     "Show calibration math" disclosure
 */
import { useState } from "react";
import { ChevronUp, Sigma } from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import { Card, CardContent } from "@/components/ui/card";
import { api } from "@/lib/api";
import {
  ARCHETYPE_DESCRIPTIONS,
  ARCHETYPE_LABELS,
  ARCHETYPE_PLANNING_IMPLICATION,
} from "@/lib/archetype";

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
    enabled: meQ.data != null,
  });

  if (!meQ.data) return null;
  const me = meQ.data;
  const archetypeId = me.archetype_id;
  if (!archetypeId) {
    return (
      <Card>
        <CardContent className="p-5">
          <p className="text-sm text-dust">
            No archetype assigned yet. Take the{" "}
            <a
              href="/settings"
              className="text-signal underline-offset-2 hover:text-signal-neon hover:underline"
            >
              4-minute survey in Settings
            </a>{" "}
            to unlock personalized priors. Predictions currently use
            the flat population prior.
          </p>
        </CardContent>
      </Card>
    );
  }

  const label = ARCHETYPE_LABELS[archetypeId] ?? archetypeId;
  const description = ARCHETYPE_DESCRIPTIONS[archetypeId];
  const implication = ARCHETYPE_PLANNING_IMPLICATION[archetypeId];
  const daysSince = me.archetype_latest_assignment_at
    ? Math.floor(
        (Date.now() - new Date(me.archetype_latest_assignment_at).getTime()) /
          (24 * 60 * 60 * 1000)
      )
    : null;

  return (
    <Card>
      <CardContent className="flex flex-col gap-4 p-5">
        {/* Hero: label + assignment recency */}
        <div>
          <div className="mb-1 font-mono text-[10px] uppercase tracking-widest text-dust-deep">
            Your archetype
          </div>
          <div className="flex flex-wrap items-baseline gap-x-3 gap-y-1">
            <h2 className="text-2xl font-semibold tracking-tight text-parchment">
              {label}
            </h2>
            {daysSince !== null && (
              <span className="text-[11px] text-dust-deep">
                {daysSince === 0
                  ? "assigned today"
                  : `assigned ${daysSince} day${daysSince !== 1 ? "s" : ""} ago`}
              </span>
            )}
          </div>
        </div>

        {/* Description — what this archetype means */}
        {description && (
          <p className="text-sm leading-relaxed text-dust">{description}</p>
        )}

        {/* Planning implication — what it means for the user's workflow */}
        {implication && (
          <div className="rounded-sm border border-hairline bg-void/30 px-3 py-2 text-xs leading-relaxed text-parchment">
            {implication}
          </div>
        )}

        {/* Math disclosure — icon-only toggle, low-prominence */}
        {blendQ.data && typeof blendQ.data.bias_factor_final === "number" && (
          <MathDisclosure
            open={mathOpen}
            onToggle={() => setMathOpen((o) => !o)}
            blend={blendQ.data}
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
