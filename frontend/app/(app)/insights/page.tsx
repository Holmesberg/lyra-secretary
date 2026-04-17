"use client";

import { useQuery } from "@tanstack/react-query";
import { getInsights, type Insight } from "@/lib/tasks";
import { cn } from "@/lib/utils";

const CONFIDENCE_STYLE: Record<string, { label: string; color: string }> = {
  low: { label: "Low confidence", color: "text-white/30" },
  medium: { label: "Medium confidence", color: "text-yellow-400/60" },
  high: { label: "High confidence", color: "text-green-400/60" },
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

function InsightCard({ insight }: { insight: Insight }) {
  const conf = CONFIDENCE_STYLE[insight.confidence] ?? CONFIDENCE_STYLE.low;
  const label = ID_LABELS[insight.id] ?? insight.id;

  return (
    <div className="rounded-lg border border-white/10 bg-white/[0.02] p-4">
      <div className="mb-2 flex items-center justify-between">
        <span className="rounded bg-white/5 px-2 py-0.5 text-[10px] font-medium uppercase tracking-wider text-white/50">
          {label}
        </span>
        <span className={cn("text-[10px]", conf.color)}>
          {conf.label} ({insight.data_points} sessions)
        </span>
      </div>
      <p className="text-sm leading-relaxed text-white/80">{insight.observation}</p>
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
        <h1 className="text-xl font-semibold text-white/80">Insights</h1>
        <div className="space-y-3">
          {[1, 2, 3].map((i) => (
            <div key={i} className="h-24 animate-pulse rounded-lg border border-white/5 bg-white/[0.02]" />
          ))}
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="space-y-4">
        <h1 className="text-xl font-semibold text-white/80">Insights</h1>
        <div className="rounded border border-red-500/30 bg-red-500/10 p-4 text-sm text-red-200">
          Failed to load insights. Check your connection and try again.
        </div>
      </div>
    );
  }

  if (!data?.ready) {
    const remaining = (data?.min_sessions_required ?? 3) - (data?.sessions_analyzed ?? 0);
    return (
      <div className="flex min-h-[60vh] flex-col items-center justify-center gap-3 text-center">
        <h1 className="text-xl font-semibold text-white/80">Insights</h1>
        <p className="max-w-md text-sm text-white/50">
          Insights unlock in{" "}
          <span className="font-medium text-white/70">{Math.max(1, remaining)} more session{remaining !== 1 ? "s" : ""}</span>.
          Complete tasks to see your patterns emerge here.
        </p>
        <div className="mt-2 h-1.5 w-48 overflow-hidden rounded-full bg-white/10">
          <div
            className="h-full rounded-full bg-white/30 transition-all"
            style={{ width: `${Math.min(100, ((data?.sessions_analyzed ?? 0) / (data?.min_sessions_required ?? 3)) * 100)}%` }}
          />
        </div>
        <p className="text-[11px] text-white/30">
          {data?.sessions_analyzed ?? 0} / {data?.min_sessions_required ?? 3} sessions analyzed
        </p>
      </div>
    );
  }

  const insights = data.insights;

  return (
    <div className="space-y-6">
      <div className="flex items-baseline justify-between">
        <h1 className="text-xl font-semibold text-white/80">Insights</h1>
        <span className="text-xs text-white/30">
          {data.sessions_analyzed} sessions analyzed
        </span>
      </div>

      {insights.length === 0 ? (
        <p className="text-sm text-white/50">
          Not enough data in any category yet. Keep logging sessions.
        </p>
      ) : (
        <div className="grid gap-4 sm:grid-cols-1 lg:grid-cols-2">
          {insights.map((insight) => (
            <InsightCard key={insight.id} insight={insight} />
          ))}
        </div>
      )}
    </div>
  );
}
