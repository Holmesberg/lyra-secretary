"use client";

import { useEffect } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  getInsights,
  type Insight,
  type SuppressedInsightGenerator,
} from "@/lib/tasks";
import { cn } from "@/lib/utils";
import { ArchetypeInsightsCard } from "@/components/archetype-insights-card";
import { ackExposureRender } from "@/lib/api";

// Confidence-tier → brand text token. Replaces the traffic-light
// (green/yellow/red) palette the page shipped with; brand-unification
// plan (Phase 3b) maps HIGH→signal + neon glow, MEDIUM→dust,
// LOW→dust-deep. Standard cards no longer tint their background per
// tier — the grid stays calm and differentiation comes through text
// color + the confidence-bar fill only.
const CONFIDENCE_STYLE: Record<string, { label: string; text: string }> = {
  high: { label: "High confidence", text: "text-signal" },
  medium: { label: "Medium confidence", text: "text-dust" },
  low: { label: "Watching this pattern", text: "text-dust-deep" },
};

const ID_LABELS: Record<string, string> = {
  primary_synthesis: "Primary pattern",
  time_of_day_bias: "Time of day",
  readiness_predicts_outcome: "Readiness signal",
  abandonment_pattern: "Not started",
  estimation_accuracy_trend: "Estimation trend",
  best_category: "Best category",
  worst_category: "Worst category",
  discrepancy_signal: "Discrepancy",
  pause_pattern: "Pause pattern",
  morning_anchor_cascade: "Morning plan",
  retroactive_rate: "Retroactive rate",
  initiation_delay: "Start delay",
  // Archetype-aware emergent patterns (2026-04-22 clustering ship).
  // Fire after archetype is assigned and user has enough per-cell
  // personal data to compare against the archetype prior.
  archetype_divergence: "Starting profile drift",
  calibration_maturation: "Personal calibration",
};

function ConfidenceBar({
  current,
  next,
  confidence,
}: {
  current: number;
  next: number;
  confidence: string;
}) {
  const pct = Math.min(100, (current / next) * 100);
  const fillColor =
    confidence === "high"
      ? "bg-signal"
      : confidence === "medium"
        ? "bg-dust"
        : "bg-dust-deep";
  return (
    <div className="mt-3 flex items-center gap-2">
      <div className="h-1 flex-1 overflow-hidden rounded-full bg-hairline">
        <div
          className={cn("h-full rounded-full transition-all", fillColor)}
          style={{ width: `${pct}%` }}
        />
      </div>
      <span className="font-mono text-[10px] uppercase tracking-widest text-dust-deep tabular-nums">
        {current}/{next}
      </span>
    </div>
  );
}

const CONFIDENCE_THRESHOLDS: Record<string, number> = { low: 6, medium: 15 };

function FeaturedCard({ insight }: { insight: Insight }) {
  const label = ID_LABELS[insight.id] ?? insight.id;
  return (
    <div className="terminal-panel p-6">
      <div className="mb-3 flex items-center gap-3">
        <span className="neon-cyan font-mono text-xs font-medium uppercase tracking-widest">
          {label}
        </span>
        <span className="font-mono text-[10px] uppercase tracking-widest text-dust">
          High confidence · {insight.data_points} sessions
        </span>
      </div>
      <p className="text-base leading-relaxed text-parchment">
        {insight.observation}
      </p>
      {insight.evidence && insight.evidence.length > 0 && (
        <div className="mt-5 grid gap-3 border-t border-hairline pt-4 sm:grid-cols-2">
          {insight.evidence.map((item) => (
            <div key={`${item.source_insight_id}-${item.label}`} className="min-w-0">
              <div className="font-mono text-[10px] uppercase tracking-widest text-dust-deep">
                {item.label}
              </div>
              <div className="mt-1 break-words text-xs leading-relaxed text-dust">
                {item.value}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function StandardCard({ insight }: { insight: Insight }) {
  const conf = CONFIDENCE_STYLE[insight.confidence] ?? CONFIDENCE_STYLE.low;
  const label = ID_LABELS[insight.id] ?? insight.id;
  const nextTier = CONFIDENCE_THRESHOLDS[insight.confidence];
  const bodyColor =
    insight.confidence === "low" ? "text-dust-deep" : "text-parchment";

  return (
    <div className="rounded-sm border border-hairline bg-void-2/60 p-4">
      <div className="mb-2 flex items-center justify-between">
        <span className="font-mono text-[10px] font-medium uppercase tracking-widest text-dust">
          {label}
        </span>
        <span
          className={cn(
            "font-mono text-[10px] uppercase tracking-widest",
            conf.text
          )}
        >
          {conf.label}
        </span>
      </div>
      <p className={cn("text-sm leading-relaxed", bodyColor)}>
        {insight.observation}
      </p>
      {nextTier && (
        <ConfidenceBar
          current={insight.data_points}
          next={nextTier}
          confidence={insight.confidence}
        />
      )}
    </div>
  );
}

function SuppressedInsightsPanel({
  generators,
}: {
  generators: SuppressedInsightGenerator[];
}) {
  const shown = generators.filter(
    (generator) => generator.suppressed_reason === "requires_insights_rewrite"
  );
  if (shown.length === 0) return null;

  return (
    <div className="rounded-sm border border-hairline bg-void-2/40 p-4">
      <div className="mb-3 flex items-baseline justify-between gap-3">
        <h2 className="font-mono text-[11px] font-medium uppercase tracking-widest text-dust">
          Held for rewrite
        </h2>
        <span className="font-mono text-[10px] uppercase tracking-widest text-dust-deep">
          {shown.length} paused
        </span>
      </div>
      <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
        {shown.map((generator) => (
          <div
            key={generator.id}
            className="rounded-sm border border-hairline/70 bg-void/40 px-3 py-2"
          >
            <div className="font-mono text-[10px] uppercase tracking-widest text-dust">
              {ID_LABELS[generator.id] ?? generator.id}
            </div>
            <div className="mt-1 text-xs text-dust-deep">
              Pending safer wording
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

export default function InsightsPage() {
  const { data, isLoading, error } = useQuery({
    queryKey: ["insights"],
    queryFn: getInsights,
    staleTime: 60_000,
  });

  useEffect(() => {
    if (data?.ready && data.exposure_id) {
      void ackExposureRender(data.exposure_id);
    }
  }, [data?.ready, data?.exposure_id]);

  if (isLoading) {
    return (
      <div className="space-y-4">
        <h1 className="text-2xl font-semibold tracking-tight text-parchment">
          Insights
        </h1>
        <div className="space-y-3">
          {[1, 2, 3].map((i) => (
            <div
              key={i}
              className="h-24 animate-pulse rounded-sm border border-hairline bg-void-2/60"
            />
          ))}
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="space-y-4">
        <h1 className="text-2xl font-semibold tracking-tight text-parchment">
          Insights
        </h1>
        <div className="rounded-sm border border-ember/40 bg-ember/5 p-4 text-sm text-ember">
          Failed to load insights. Check your connection and try again.
        </div>
      </div>
    );
  }

  if (!data?.ready) {
    const remaining =
      (data?.min_sessions_required ?? 3) - (data?.sessions_analyzed ?? 0);
    return (
      <div className="space-y-8">
        <h1 className="text-2xl font-semibold tracking-tight text-parchment">
          Insights
        </h1>

        <ArchetypeInsightsCard />

        <div className="flex min-h-[40vh] flex-col items-center justify-center gap-3 text-center">
          <p className="max-w-md text-sm text-dust">
            {data?.message ?? (
              <>
                Insights unlock in{" "}
                <span className="font-medium text-parchment">
                  {Math.max(1, remaining)} more session
                  {remaining !== 1 ? "s" : ""}
                </span>
                . Complete tasks to see your patterns emerge here.
              </>
            )}
          </p>
          <div className="mt-2 h-1.5 w-48 overflow-hidden rounded-full bg-hairline">
            <div
              className="h-full rounded-full bg-signal transition-all"
              style={{
                width: `${Math.min(100, ((data?.sessions_analyzed ?? 0) / (data?.min_sessions_required ?? 3)) * 100)}%`,
              }}
            />
          </div>
          <p className="font-mono text-[10px] uppercase tracking-widest text-dust-deep">
            {data?.sessions_analyzed ?? 0} / {data?.min_sessions_required ?? 3}{" "}
            sessions analyzed
          </p>
        </div>
      </div>
    );
  }

  const insights = data.insights;
  const suppressedGenerators = data.suppressed_generators ?? [];
  const analyzedLabel =
    data.sessions_analyzed > 0
      ? `${data.sessions_analyzed} sessions analyzed`
      : `${data.history_events_analyzed ?? data.eligible_sample_count ?? 0} history events read`;
  const primary = insights.find((i) => i.id === "primary_synthesis") ?? null;
  const nonPrimaryInsights = insights.filter((i) => i !== primary);
  const highConfidence = nonPrimaryInsights.filter(
    (i) => i.confidence === "high"
  );
  const mediumConfidence = nonPrimaryInsights.filter(
    (i) => i.confidence === "medium"
  );
  const emerging = nonPrimaryInsights.filter((i) => i.confidence === "low");

  return (
    <div className="space-y-8">
      <div className="flex items-baseline justify-between">
        <h1 className="text-2xl font-semibold tracking-tight text-parchment">
          Insights
        </h1>
        <span className="font-mono text-[10px] uppercase tracking-widest text-dust">
          {analyzedLabel}
        </span>
      </div>

      {/* Archetype profile card — self-updates when the survey is taken
          via React Query invalidation. See ArchetypeInsightsCard. */}
      <ArchetypeInsightsCard />

      {primary && <FeaturedCard insight={primary} />}

      {highConfidence.length > 0 && (
        <div>
          <h2 className="terminal-prefix mb-3 font-mono text-[11px] font-medium uppercase tracking-widest text-dust">
            High confidence
          </h2>
          <div className="grid gap-4 sm:grid-cols-1 lg:grid-cols-2">
            {highConfidence.map((insight) => (
              <StandardCard key={insight.id} insight={insight} />
            ))}
          </div>
        </div>
      )}

      {mediumConfidence.length > 0 && (
        <div>
          <h2 className="terminal-prefix mb-3 font-mono text-[11px] font-medium uppercase tracking-widest text-dust">
            Medium confidence
          </h2>
          <div className="grid gap-4 sm:grid-cols-1 lg:grid-cols-2">
            {mediumConfidence.map((insight) => (
              <StandardCard key={insight.id} insight={insight} />
            ))}
          </div>
        </div>
      )}

      {emerging.length > 0 && (
        <div>
          <h2 className="terminal-prefix mb-3 font-mono text-[11px] font-medium uppercase tracking-widest text-dust">
            Emerging patterns
          </h2>
          <div className="grid gap-3 sm:grid-cols-1 lg:grid-cols-2">
            {emerging.map((insight) => (
              <StandardCard key={insight.id} insight={insight} />
            ))}
          </div>
        </div>
      )}

      {insights.length === 0 && (
        <p className="text-sm text-dust">
          Not enough data in any category yet. Keep logging sessions.
        </p>
      )}

      <SuppressedInsightsPanel generators={suppressedGenerators} />
    </div>
  );
}
