"use client";

import { useQuery } from "@tanstack/react-query";
import { getInsights, type Insight } from "@/lib/tasks";
import { cn } from "@/lib/utils";

const CONFIDENCE_STYLE: Record<string, { label: string; bg: string; text: string }> = {
  high: { label: "High confidence", bg: "bg-green-500/10 border-green-500/20", text: "text-green-400/70" },
  medium: { label: "Medium confidence", bg: "bg-yellow-500/5 border-yellow-500/15", text: "text-yellow-400/60" },
  low: { label: "Watching this pattern", bg: "bg-white/[0.02] border-white/8", text: "text-white/30" },
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

function ConfidenceBar({ current, next }: { current: number; next: number }) {
  const pct = Math.min(100, (current / next) * 100);
  return (
    <div className="mt-2 flex items-center gap-2">
      <div className="h-1 flex-1 overflow-hidden rounded-full bg-white/5">
        <div className="h-full rounded-full bg-white/20 transition-all" style={{ width: `${pct}%` }} />
      </div>
      <span className="text-[9px] text-white/20">{current}/{next}</span>
    </div>
  );
}

const CONFIDENCE_THRESHOLDS: Record<string, number> = { low: 6, medium: 15 };

function FeaturedCard({ insight }: { insight: Insight }) {
  const label = ID_LABELS[insight.id] ?? insight.id;
  return (
    <div className="rounded-xl border border-green-500/20 bg-green-500/[0.06] p-6">
      <div className="mb-1 flex items-center gap-2">
        <span className="rounded bg-green-500/15 px-2 py-0.5 text-[10px] font-medium uppercase tracking-wider text-green-300/70">
          {label}
        </span>
        <span className="text-[10px] text-green-400/50">
          High confidence ({insight.data_points} sessions)
        </span>
      </div>
      <p className="mt-3 text-base leading-relaxed text-white/90">{insight.observation}</p>
    </div>
  );
}

function StandardCard({ insight }: { insight: Insight }) {
  const conf = CONFIDENCE_STYLE[insight.confidence] ?? CONFIDENCE_STYLE.low;
  const label = ID_LABELS[insight.id] ?? insight.id;
  const nextTier = CONFIDENCE_THRESHOLDS[insight.confidence];

  return (
    <div className={cn("rounded-lg border p-4", conf.bg)}>
      <div className="mb-2 flex items-center justify-between">
        <span className="rounded bg-white/5 px-2 py-0.5 text-[10px] font-medium uppercase tracking-wider text-white/50">
          {label}
        </span>
        <span className={cn("text-[10px]", conf.text)}>
          {conf.label}
        </span>
      </div>
      <p className={cn(
        "text-sm leading-relaxed",
        insight.confidence === "low" ? "text-white/50" : "text-white/80"
      )}>
        {insight.observation}
      </p>
      {nextTier && (
        <ConfidenceBar current={insight.data_points} next={nextTier} />
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
  const featured = insights.find((i) => i.confidence === "high" && i.data_points >= 15);
  const standard = insights.filter((i) => i !== featured && i.confidence !== "low");
  const emerging = insights.filter((i) => i.confidence === "low");

  return (
    <div className="space-y-8">
      <div className="flex items-baseline justify-between">
        <h1 className="text-xl font-semibold text-white/80">Insights</h1>
        <span className="text-xs text-white/30">
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
          <h2 className="mb-3 text-xs font-medium uppercase tracking-wider text-white/30">
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
        <p className="text-sm text-white/50">
          Not enough data in any category yet. Keep logging sessions.
        </p>
      )}
    </div>
  );
}
