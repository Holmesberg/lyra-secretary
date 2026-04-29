"use client";
/**
 * FocusTimerHero — large mono timer when a session is active, calm
 * "ready when you are" state when idle.
 *
 * Reads /v1/stopwatch/status. Paused state shows the elapsed in dust
 * + an ember-toned "PAUSED" pill. Running state shows neon-cyan with
 * a subtle pulse-glow breathing animation.
 *
 * The component is presentational only — it does NOT start/stop. For
 * starting, the operator goes to /today and clicks Start on a row;
 * the timer hero on /pulse becomes alive once a session is running.
 * This keeps the prototype scope tight and avoids duplicating the
 * readiness-modal flow.
 */
import { useEffect, useState } from "react";
import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { getStopwatchStatus, type StopwatchStatus } from "@/lib/tasks";

function pad2(n: number): string {
  return n.toString().padStart(2, "0");
}

function fmtElapsed(totalSeconds: number): string {
  const h = Math.floor(totalSeconds / 3600);
  const m = Math.floor((totalSeconds % 3600) / 60);
  const s = totalSeconds % 60;
  if (h > 0) return `${h}:${pad2(m)}:${pad2(s)}`;
  return `${pad2(m)}:${pad2(s)}`;
}

export function FocusTimerHero() {
  const statusQ = useQuery<StopwatchStatus>({
    queryKey: ["stopwatch-status"],
    queryFn: getStopwatchStatus,
    refetchInterval: 5_000,
    refetchOnWindowFocus: true,
  });
  // Local-tick: increment elapsed every second client-side between
  // server-confirmed elapsed_seconds snapshots so the digits move.
  const [tickSeconds, setTickSeconds] = useState(0);
  const [baseSeconds, setBaseSeconds] = useState(0);
  const [baseAt, setBaseAt] = useState<number>(Date.now());

  useEffect(() => {
    if (!statusQ.data?.active || statusQ.data.paused) {
      setTickSeconds(statusQ.data?.elapsed_seconds ?? 0);
      return;
    }
    setBaseSeconds(statusQ.data.elapsed_seconds ?? 0);
    setBaseAt(Date.now());
    const id = setInterval(() => {
      setTickSeconds(
        (statusQ.data?.elapsed_seconds ?? 0) +
          Math.floor((Date.now() - Date.now()) / 1000)
      );
    }, 1000);
    return () => clearInterval(id);
    // baseAt + baseSeconds intentionally omitted from deps — reset on
    // every server-snapshot, which IS in deps via statusQ.data.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [statusQ.data?.active, statusQ.data?.paused, statusQ.data?.elapsed_seconds]);

  // Recompute the displayed seconds on each render based on wall-clock
  // delta from the most recent snapshot (more honest than incrementing
  // a useState counter, which can drift).
  const displayedSeconds =
    statusQ.data?.active && !statusQ.data.paused
      ? baseSeconds + Math.floor((Date.now() - baseAt) / 1000) + tickSeconds * 0
      : (statusQ.data?.elapsed_seconds ?? 0);

  const status = statusQ.data;
  const isActive = !!status?.active;
  const isPaused = !!status?.paused;
  const taskTitle = status?.task_title ?? null;
  const planned = status?.planned_duration_minutes ?? null;
  const overflow =
    isActive && planned ? Math.max(0, displayedSeconds - planned * 60) : 0;
  const isOverflow = overflow > 0;

  return (
    <div className="terminal-panel relative flex flex-col gap-3 overflow-hidden px-6 py-5">
      <div className="flex items-baseline justify-between gap-3">
        <div className="font-display text-[10px] font-medium uppercase tracking-macro text-dust">
          <span className="opacity-50">[ </span>
          {isActive ? (isPaused ? "Paused" : isOverflow ? "Overflow" : "Focus") : "Focus session"}
          <span className="opacity-50"> ]</span>
        </div>
        {isActive && (
          <span
            className="status-dot"
            aria-hidden
            style={{
              ["--dot-color" as string]: isPaused
                ? "#F5A96A"
                : isOverflow
                  ? "#FF8A3D"
                  : "#00E5FF",
            }}
          />
        )}
      </div>

      {isActive ? (
        <>
          <div
            className={`font-display text-[3rem] font-semibold leading-none tabular-nums ${
              isPaused
                ? "text-ember"
                : isOverflow
                  ? "neon-ember"
                  : "neon-cyan"
            } ${!isPaused && !isOverflow ? "animate-pulse-glow" : ""}`}
            style={{ letterSpacing: "-0.03em" }}
          >
            {fmtElapsed(displayedSeconds)}
          </div>
          {taskTitle && (
            <div
              className="truncate text-xs text-parchment/85"
              title={taskTitle}
            >
              {taskTitle}
            </div>
          )}
          {planned !== null && (
            <div className="font-mono text-[10px] uppercase tracking-widest text-dust-deep">
              {isOverflow ? (
                <>
                  +{Math.floor(overflow / 60)}m past planned · target {planned}m
                </>
              ) : (
                <>
                  {Math.floor(displayedSeconds / 60)}m of {planned}m planned
                </>
              )}
            </div>
          )}
        </>
      ) : (
        <>
          <div className="font-display text-[3rem] font-semibold leading-none tabular-nums text-dust-deep">
            {fmtElapsed(0)}
          </div>
          <div className="text-xs text-dust">
            No session running.
          </div>
          <Link
            href="/today"
            className="inline-flex w-fit items-center gap-2 rounded-sm border border-signal/40 bg-signal/10 px-3 py-1.5 font-mono text-[11px] uppercase tracking-widest text-signal transition-colors hover:bg-signal/20 hover:text-signal-neon"
          >
            <span className="text-signal/60">→</span> Start one on Today
          </Link>
        </>
      )}
    </div>
  );
}
