"use client";
/**
 * PulseFocusCard — center hero card containing the radial focus
 * timer, the active task title, and Start/Plan CTAs.
 *
 * State-aware:
 *   - Active running: shows the task title + "Focus Session" eyebrow,
 *     the radial timer ticks live, "Open task" button routes back to
 *     /today.
 *   - Active paused: ember tone, "Paused" eyebrow, "Resume on /today".
 *   - Idle: "Ready when you are" copy + Start CTA → /today (the
 *     readiness-modal flow lives there).
 */
import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { Pause, Play, Plus } from "lucide-react";
import { getStopwatchStatus, type StopwatchStatus } from "@/lib/tasks";
import { RadialFocusTimer } from "@/components/pulse/RadialFocusTimer";

export function PulseFocusCard() {
  const statusQ = useQuery<StopwatchStatus>({
    queryKey: ["stopwatch-status"],
    queryFn: getStopwatchStatus,
    refetchInterval: 5_000,
    refetchOnWindowFocus: true,
  });

  const status = statusQ.data;
  const isActive = !!status?.active;
  const isPaused = !!status?.paused;
  const taskTitle = status?.task_title ?? null;

  const eyebrow = !isActive
    ? "Current focus session"
    : isPaused
      ? "Session paused"
      : "Current focus session";

  return (
    <div className="terminal-panel relative flex flex-col items-center overflow-hidden px-6 py-7">
      {/* Eyebrow + task title */}
      <div className="mb-3 flex w-full flex-col items-center text-center">
        <div className="font-display text-[10px] font-medium uppercase tracking-macro text-dust">
          <span className="opacity-50">[ </span>
          {eyebrow}
          <span className="opacity-50"> ]</span>
        </div>
        {isActive && taskTitle ? (
          <h2
            className="mt-2 line-clamp-2 max-w-md text-center text-lg font-semibold tracking-tight text-parchment"
            title={taskTitle}
          >
            {taskTitle}
          </h2>
        ) : (
          <h2 className="mt-2 text-lg font-semibold tracking-tight text-dust">
            Ready when you are
          </h2>
        )}
      </div>

      {/* Radial timer */}
      <div className="my-1">
        <RadialFocusTimer status={status} />
      </div>

      {/* CTAs */}
      <div className="mt-5 flex w-full items-center justify-center gap-3">
        {isActive ? (
          <>
            <Link
              href="/today"
              className="inline-flex items-center gap-2 rounded-sm border border-signal/40 bg-signal/15 px-5 py-2.5 font-mono text-[11px] uppercase tracking-widest text-signal transition-colors hover:bg-signal/25 hover:text-signal-neon"
            >
              {isPaused ? <Play className="h-3.5 w-3.5" /> : <Pause className="h-3.5 w-3.5" />}
              {isPaused ? "Resume on Today" : "Open on Today"}
            </Link>
          </>
        ) : (
          <>
            <Link
              href="/today"
              className="inline-flex items-center gap-2 rounded-sm border border-signal/40 bg-signal/15 px-5 py-2.5 font-mono text-[11px] uppercase tracking-widest text-signal transition-colors hover:bg-signal/25 hover:text-signal-neon"
            >
              <Play className="h-3.5 w-3.5" />
              Start a session
            </Link>
            <Link
              href="/today"
              className="inline-flex items-center gap-2 rounded-sm border border-hairline bg-void-2/40 px-5 py-2.5 font-mono text-[11px] uppercase tracking-widest text-dust transition-colors hover:border-signal/40 hover:text-parchment"
            >
              <Plus className="h-3.5 w-3.5" />
              Plan a session
            </Link>
          </>
        )}
      </div>
    </div>
  );
}
