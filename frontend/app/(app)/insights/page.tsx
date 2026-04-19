"use client";

import { useQuery } from "@tanstack/react-query";
import { getInsights, type Insight } from "@/lib/tasks";
import { cn } from "@/lib/utils";

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
  time_of_day_bias: "Time of day",
  readiness_predicts_outcome: "Readiness signal",
  abandonment_pattern: "Abandonment",
  estimation_accuracy_trend: "Estimation trend",
  best_category: "Best category",
  worst_category: "Worst category",
  discrepancy_signal: "Discrepancy",
  pause_pattern: "Pause pattern",
  morning_anchor_cascade: "Morning cascade",
  retroactive_rate: "Retroactive rate",
  initiation_delay: "Start delay",
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

export default function InsightsPage() {
  const { data, isLoading, error } = useQuery({
    queryKey: ["insights"],
    queryFn: getInsights,
    staleTime: 60_000,
  });

  if (isLoading) {
    return (
      <div className="space-y-4">
        <h1 className="font-display text-2xl font-medium tracking-tight text-parchment">
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
        <h1 className="font-display text-2xl font-medium tracking-tight text-parchment">
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
      <div className="flex min-h-[60vh] flex-col items-center justify-center gap-3 text-center">
        <h1 className="font-display text-2xl font-medium tracking-tight text-parchment">
          Insights
        </h1>
        <p className="max-w-md text-sm text-dust">
          Insights unlock in{" "}
          <span className="font-medium text-parchment">
            {Math.max(1, remaining)} more session
            {remaining !== 1 ? "s" : ""}
          </span>
          . Complete tasks to see your patterns emerge here.
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
    );
  }

  const insights = data.insights;
  const featured = insights.find(
    (i) => i.confidence === "high" && i.data_points >= 15
  );
  const standard = insights.filter(
    (i) => i !== featured && i.confidence !== "low"
  );
  const emerging = insights.filter((i) => i.confidence === "low");

  return (
    <div className="space-y-8">
      <div className="flex items-baseline justify-between">
        <h1 className="font-display text-2xl font-medium tracking-tight text-parchment">
          Insights
        </h1>
        <span className="font-mono text-[10px] uppercase tracking-widest text-dust">
          {data.sessions_analyzed} sessions analyzed
        </span>
      </div>

      {featured && <FeaturedCard insight={featured} />}

      {standard.length > 0 && (
        <div className="grid gap-4 sm:grid-cols-1 lg:grid-cols-2">
          {standard.map((insight) => (
            <StandardCard key={insight.id} insight={insight} />
          ))}
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
    </div>
  );
}
