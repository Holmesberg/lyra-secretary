"use client";
/**
 * PulseSystemInsight — narrative insight card with a mini line chart
 * of the past 7 days of focus minutes.
 *
 * Insight text is derived live: the longest free planned slot today
 * (via lib/pulse-aggregations.nextFreeBlock) reads as the system's
 * one-line read on the day. When no free block, surfaces "rest of
 * the day is busy" or "no plan yet" calls.
 *
 * The chart uses Tremor's AreaChart with a single 'minutes' series
 * styled to match the Neural Noir cyan signal accent.
 */
import { format } from "date-fns";
import { AreaChart } from "@tremor/react";
import {
  focusMinutesByDay,
  nextFreeBlock,
  type DailyPoint,
} from "@/lib/pulse-aggregations";
import type { TaskRow } from "@/lib/tasks";

export interface PulseSystemInsightProps {
  tasksToday: TaskRow[];
  /** Past 7-14 days of tasks for the chart aggregation. */
  recentTasks: TaskRow[];
}

function fmtTimeRange(startISO: string, endISO: string): string {
  try {
    return `${format(new Date(startISO), "h:mm a")} – ${format(
      new Date(endISO),
      "h:mm a"
    )}`;
  } catch {
    return "—";
  }
}

function fmtMinutes(m: number): string {
  if (m < 60) return `${m} min`;
  const h = Math.floor(m / 60);
  const rem = m % 60;
  return rem === 0 ? `${h}h` : `${h}h ${rem}m`;
}

export function PulseSystemInsight({
  tasksToday,
  recentTasks,
}: PulseSystemInsightProps) {
  const free = nextFreeBlock(tasksToday);
  const series: DailyPoint[] = focusMinutesByDay(recentTasks, 7);
  const sevenDayTotal = series.reduce((s, p) => s + p.minutes, 0);
  const avgPerDay = Math.round(sevenDayTotal / 7);

  return (
    <div className="terminal-panel relative flex h-full flex-col overflow-hidden p-5">
      <div className="mb-3 flex items-baseline justify-between">
        <div className="font-display text-[10px] font-medium uppercase tracking-macro text-dust">
          <span className="opacity-50">[ </span>
          System insight
          <span className="opacity-50"> ]</span>
        </div>
        <span className="font-mono text-[9px] uppercase tracking-widest text-dust-deep">
          7d trend
        </span>
      </div>

      {/* Insight headline — the live "what's the system noticing right
          now" line. */}
      <div className="mb-1 text-[15px] text-parchment">
        {free ? (
          <>
            <span className="font-display text-signal">
              {fmtMinutes(free.minutes)}
            </span>{" "}
            free between{" "}
            <span className="font-mono text-parchment/85">
              {fmtTimeRange(free.startISO, free.endISO)}
            </span>
          </>
        ) : tasksToday.length === 0 ? (
          <>No plan for today yet — brain-dump to start.</>
        ) : (
          <>The rest of today is mostly committed.</>
        )}
      </div>
      <div className="mb-3 font-mono text-[10px] uppercase tracking-widest text-dust-deep">
        avg {avgPerDay}m/day · {fmtMinutes(sevenDayTotal)} this week
      </div>

      {/* Mini area chart. Tremor handles the SVG; we pass colors from
          the cyan family. The chart is intentionally compact — labels
          off, gridlines off — so it reads as a sparkline. */}
      <div className="relative -mx-1 flex-1 min-h-[110px]">
        <AreaChart
          className="h-full"
          data={series}
          index="label"
          categories={["minutes"]}
          colors={["cyan"]}
          showLegend={false}
          showGridLines={false}
          showXAxis={true}
          showYAxis={false}
          startEndOnly={false}
          curveType="natural"
          autoMinValue={true}
          showAnimation={true}
          valueFormatter={(v) => `${v}m`}
        />
      </div>
    </div>
  );
}
