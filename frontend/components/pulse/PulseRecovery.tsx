"use client";
/**
 * PulseRecovery — daily-rhythm bar chart showing focus minutes per
 * day across the past 14 days. Signals "have I been recovering" over
 * a window long enough to see weekend dips and recovery streaks.
 *
 * Tremor BarChart styled with the cyan signal palette + a single
 * series. Heights are computed live from EXECUTED tasks via
 * focusMinutesByDay().
 */
import { BarChart } from "@tremor/react";
import { focusMinutesByDay } from "@/lib/pulse-aggregations";
import type { TaskRow } from "@/lib/tasks";

export interface PulseRecoveryProps {
  recentTasks: TaskRow[];
}

export function PulseRecovery({ recentTasks }: PulseRecoveryProps) {
  const series = focusMinutesByDay(recentTasks, 14);
  const max = series.reduce((m, p) => Math.max(m, p.minutes), 0);
  const sessions = series.reduce((s, p) => s + p.count, 0);
  const restDays = series.filter((p) => p.minutes === 0).length;

  return (
    <div className="terminal-panel relative flex h-full flex-col overflow-hidden p-5">
      <div className="mb-3 flex items-baseline justify-between">
        <div className="font-display text-[10px] font-medium uppercase tracking-macro text-dust">
          <span className="opacity-50">[ </span>
          Recovery rhythm
          <span className="opacity-50"> ]</span>
        </div>
        <span className="font-mono text-[9px] uppercase tracking-widest text-dust-deep">
          14d
        </span>
      </div>

      <div className="mb-3 flex items-baseline gap-4 text-[11px] text-dust">
        <div>
          <span className="font-display text-base font-semibold tabular-nums text-signal">
            {sessions}
          </span>{" "}
          sessions
        </div>
        <div>
          <span className="font-display text-base font-semibold tabular-nums text-parchment">
            {Math.round(max)}
            <span className="text-[10px] text-dust">m</span>
          </span>{" "}
          peak day
        </div>
        <div>
          <span className="font-display text-base font-semibold tabular-nums text-dust">
            {restDays}
          </span>{" "}
          rest
        </div>
      </div>

      <div className="relative -mx-1 flex-1 min-h-[110px]">
        <BarChart
          className="h-full"
          data={series}
          index="label"
          categories={["minutes"]}
          colors={["cyan"]}
          showLegend={false}
          showGridLines={false}
          showXAxis={true}
          showYAxis={false}
          showAnimation={true}
          valueFormatter={(v) => `${v}m`}
        />
      </div>
    </div>
  );
}
