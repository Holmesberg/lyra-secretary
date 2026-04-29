"use client";
/**
 * PulseFocusCard — inline timer command surface (2026-04-30 ship).
 *
 * Operator narrowing on the v2 dashboard plan: this card has to
 * absorb the full daily action loop so /pulse becomes a daily-driver
 * without exiting to /today. Minimum interaction set per operator:
 *   - Start (with task picker + readiness slider)
 *   - Pause (one-tap, defaults to intentional_break)
 *   - Resume
 *   - Stop (with inline reflection slider)
 *   - Quick-pick next PLANNED task after stop
 *
 * Deliberately NOT included (operator scope cut):
 *   - Switch-to-other-paused
 *   - Reason picker on pause (default 'intentional_break' is fine)
 *   - Early-stop confirmation modal (handled via inline confirm button
 *     when backend returns requires_confirmation)
 *   - Scope outcome / completion percentage on stop
 *
 * Mobile-first sizing: every interactive target is ≥44px (Apple HIG
 * touch threshold). Slider thumb is generous. No hover-only affordances
 * — every state visible without hovering.
 *
 * State source-of-truth split:
 *   - Active session state (running, paused, elapsed) → server
 *     /v1/stopwatch/status query, polls every 5s
 *   - Local mode (which sub-UI is showing) → useState
 *     'idle' | 'readiness' | 'reflection'
 */
import { useEffect, useRef, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Loader2, Pause, Play, Square } from "lucide-react";
import {
  getStopwatchStatus,
  pauseStopwatch,
  resumeStopwatch,
  startStopwatch,
  stopStopwatch,
  type StartStopwatchResponse,
  type StopResponse,
  type StopwatchStatus,
  type TaskRow,
} from "@/lib/tasks";
import { RadialFocusTimer } from "@/components/pulse/RadialFocusTimer";

type Mode =
  | "idle" // no session, picker + readiness shown
  | "reflection" // stopping, reflection slider shown
  | "next-prompt"; // after finish, "Start next?" suggestion

export interface PulseFocusCardProps {
  /** Today's tasks from the parent's already-fetched query. Used to
   *  populate the task picker (PLANNED only) and the next-task prompt. */
  todaysTasks: TaskRow[];
}

function fmtTime(iso: string | null | undefined): string {
  if (!iso) return "—";
  try {
    const d = new Date(iso);
    return d.toLocaleTimeString(undefined, { hour: "numeric", minute: "2-digit" });
  } catch {
    return "—";
  }
}

const READINESS_LABELS = ["Drained", "Low", "Steady", "Sharp", "Peak"];

export function PulseFocusCard({ todaysTasks }: PulseFocusCardProps) {
  const qc = useQueryClient();
  const statusQ = useQuery<StopwatchStatus>({
    queryKey: ["stopwatch-status"],
    queryFn: getStopwatchStatus,
    refetchInterval: 5_000,
    refetchOnWindowFocus: true,
  });

  const status = statusQ.data;
  const isActive = !!status?.active;
  const isPaused = !!status?.paused;

  // Local mode — only meaningful when status is NOT active. When status
  // flips active, we render the running view regardless of local mode.
  // After stop completes (status flips back to inactive), we set mode
  // to 'next-prompt' so the user sees "Start next?".
  const [mode, setMode] = useState<Mode>("idle");

  // Picker / readiness state
  const plannedTasks = todaysTasks
    .filter((t) => t.state === "PLANNED" && !t.voided_at)
    .sort((a, b) => {
      const ax = a.start ? new Date(a.start).getTime() : Infinity;
      const bx = b.start ? new Date(b.start).getTime() : Infinity;
      return ax - bx;
    });
  const [selectedTaskId, setSelectedTaskId] = useState<string | null>(null);
  const [readiness, setReadiness] = useState<number>(3);

  // Default selection — first planned task, refreshed when the list
  // changes.
  useEffect(() => {
    if (selectedTaskId && plannedTasks.some((t) => t.task_id === selectedTaskId)) {
      return;
    }
    setSelectedTaskId(plannedTasks[0]?.task_id ?? null);
  }, [plannedTasks, selectedTaskId]);

  // Reflection state
  const [reflection, setReflection] = useState<number>(3);
  const [stoppedSummary, setStoppedSummary] = useState<{
    minutes: number;
    delta: number | null;
  } | null>(null);

  // Error surface
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  // Track which task we just stopped so the "next" prompt can exclude it.
  const lastStoppedTaskIdRef = useRef<string | null>(null);

  // ─── Mutations ────────────────────────────────────────────────────

  const startM = useMutation<StartStopwatchResponse, Error, { taskId: string; readiness: number }>({
    mutationFn: ({ taskId, readiness }) => startStopwatch(taskId, readiness),
    onSuccess: () => {
      setMode("idle"); // running view derives from server
      setErrorMsg(null);
      // Snappy refetch — don't wait for the 5s poll.
      qc.invalidateQueries({ queryKey: ["stopwatch-status"] });
      qc.invalidateQueries({ queryKey: ["tasks"] });
    },
    onError: (e) => setErrorMsg(e.message ?? "Failed to start"),
  });

  const pauseM = useMutation<unknown, Error, void>({
    mutationFn: () => pauseStopwatch("intentional_break"),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["stopwatch-status"] });
    },
    onError: (e) => setErrorMsg(e.message ?? "Failed to pause"),
  });

  const resumeM = useMutation<unknown, Error, void>({
    mutationFn: () => resumeStopwatch(),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["stopwatch-status"] });
    },
    onError: (e) => setErrorMsg(e.message ?? "Failed to resume"),
  });

  const stopM = useMutation<StopResponse, Error, { reflection: number; confirmed?: boolean }>({
    mutationFn: ({ reflection, confirmed }) => stopStopwatch(reflection, { confirmed }),
    onSuccess: (res) => {
      if (res.requires_confirmation) {
        // Backend wants explicit confirm (early-stop gate). Surface
        // inline; user clicks Finish-anyway to retry with confirmed=true.
        setErrorMsg(res.confirmation_message ?? "Stopping early — finish anyway?");
        return;
      }
      lastStoppedTaskIdRef.current = res.task_id;
      setStoppedSummary({
        minutes: Math.round(res.duration_minutes),
        delta: res.delta_minutes ?? null,
      });
      setMode("next-prompt");
      setErrorMsg(null);
      // Reset for next session.
      setReflection(3);
      qc.invalidateQueries({ queryKey: ["stopwatch-status"] });
      qc.invalidateQueries({ queryKey: ["tasks"] });
      qc.invalidateQueries({ queryKey: ["tasks-range"] });
      qc.invalidateQueries({ queryKey: ["me"] });
    },
    onError: (e) => setErrorMsg(e.message ?? "Failed to stop"),
  });

  // When a session genuinely STOPS server-side (status flips active→
  // inactive while we're in 'reflection' mode), the onSuccess above
  // already moved us to 'next-prompt'. If the user dismisses the
  // prompt and another session starts via /today (or some external
  // path), the running view simply re-derives from status — no local
  // mode reset needed.

  // ─── Render branches ──────────────────────────────────────────────

  // Running view — server says we're active and not paused, AND we're
  // not in reflection-input mode (which renders the slider over the
  // running state during the brief stop transaction).
  const showRunning = isActive && !isPaused && mode !== "reflection";
  const showPaused = isActive && isPaused && mode !== "reflection";
  const showReflection = mode === "reflection" || (stopM.isPending && isActive);
  const showNextPrompt = mode === "next-prompt" && !isActive;
  const showIdle = !isActive && mode === "idle";

  return (
    <div className="terminal-panel relative flex flex-col items-center overflow-hidden px-5 py-6 sm:px-6 sm:py-7">
      {/* Eyebrow */}
      <div className="mb-3 font-display text-[10px] font-medium uppercase tracking-macro text-dust">
        <span className="opacity-50">[ </span>
        {showRunning
          ? "Focus session"
          : showPaused
            ? "Session paused"
            : showReflection
              ? "How was it?"
              : showNextPrompt
                ? "Session complete"
                : "Current focus session"}
        <span className="opacity-50"> ]</span>
      </div>

      {/* Active task title (above timer when running/paused/reflecting) */}
      {(showRunning || showPaused || showReflection) && status?.task_title && (
        <h2
          className="mb-2 line-clamp-2 max-w-md text-center text-lg font-semibold tracking-tight text-parchment"
          title={status.task_title}
        >
          {status.task_title}
        </h2>
      )}

      {/* Idle / next-prompt shows different headlines */}
      {showIdle && (
        <h2 className="mb-2 text-center text-lg font-semibold tracking-tight text-dust">
          {plannedTasks.length > 0
            ? "Pick what you're starting"
            : "Nothing planned yet"}
        </h2>
      )}
      {showNextPrompt && (
        <h2 className="mb-2 text-center text-lg font-semibold tracking-tight text-parchment">
          Start the next one?
        </h2>
      )}

      {/* Radial timer — always present when active or running, hidden
          when in idle picker mode + when in next-prompt for visual
          calm (stoppedSummary takes its place). */}
      {(showRunning || showPaused || showReflection) && (
        <div className="my-1">
          <RadialFocusTimer status={status} />
        </div>
      )}

      {/* Idle: task picker + readiness slider + Start button */}
      {showIdle && plannedTasks.length > 0 && (
        <div className="flex w-full max-w-md flex-col gap-4 px-1">
          {/* Picker */}
          <ul className="flex max-h-[180px] flex-col gap-1 overflow-y-auto rounded-sm border border-hairline bg-void/40 p-1">
            {plannedTasks.map((t) => {
              const selected = t.task_id === selectedTaskId;
              return (
                <li key={t.task_id}>
                  <button
                    type="button"
                    onClick={() => setSelectedTaskId(t.task_id)}
                    className={`flex min-h-[44px] w-full items-center gap-3 rounded-sm px-3 py-2 text-left transition-colors ${
                      selected
                        ? "bg-signal/15 text-parchment ring-1 ring-signal/40"
                        : "text-dust hover:bg-void-2/60 hover:text-parchment"
                    }`}
                  >
                    <span
                      aria-hidden
                      className={`inline-block h-2 w-2 shrink-0 rounded-full transition-colors ${
                        selected ? "bg-signal shadow-[0_0_8px_rgba(77,212,232,0.7)]" : "bg-dust-deep"
                      }`}
                    />
                    <span className="flex-1 truncate text-[12px]">{t.title}</span>
                    <span className="shrink-0 font-mono text-[10px] text-dust-deep">
                      {fmtTime(t.start)}
                      {t.planned_duration_minutes !== null
                        ? ` · ${t.planned_duration_minutes}m`
                        : ""}
                    </span>
                  </button>
                </li>
              );
            })}
          </ul>

          {/* Readiness slider */}
          <div className="flex flex-col gap-2">
            <div className="flex items-center justify-between font-display text-[10px] uppercase tracking-macro text-dust">
              <span>
                <span className="opacity-50">[ </span>
                Readiness
                <span className="opacity-50"> ]</span>
              </span>
              <span className="text-signal">{READINESS_LABELS[readiness - 1]}</span>
            </div>
            <input
              type="range"
              min={1}
              max={5}
              step={1}
              value={readiness}
              onChange={(e) => setReadiness(Number(e.target.value))}
              className="lyra-range h-2 w-full"
              aria-label="Pre-task readiness 1 to 5"
            />
            <div className="flex justify-between font-mono text-[9px] uppercase tracking-widest text-dust-deep">
              {[1, 2, 3, 4, 5].map((n) => (
                <span
                  key={n}
                  className={n === readiness ? "text-signal" : ""}
                >
                  {n}
                </span>
              ))}
            </div>
          </div>

          {/* Start button */}
          <button
            type="button"
            onClick={() =>
              selectedTaskId &&
              startM.mutate({ taskId: selectedTaskId, readiness })
            }
            disabled={!selectedTaskId || startM.isPending}
            className="inline-flex min-h-[48px] items-center justify-center gap-2 rounded-sm border border-signal/40 bg-signal/15 px-5 py-3 font-mono text-[12px] uppercase tracking-widest text-signal transition-colors hover:bg-signal/25 hover:text-signal-neon disabled:opacity-50"
          >
            {startM.isPending ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Play className="h-4 w-4" />
            )}
            Start session
          </button>
        </div>
      )}

      {/* Idle with no PLANNED tasks — point user at brain dump */}
      {showIdle && plannedTasks.length === 0 && (
        <div className="flex w-full flex-col items-center gap-3 px-2 text-center">
          <p className="text-xs text-dust">
            Brain-dump in the footer to add what you're working on.
          </p>
        </div>
      )}

      {/* Running: Pause + Stop */}
      {showRunning && (
        <div className="mt-5 flex w-full max-w-md items-center justify-center gap-3 px-1">
          <button
            type="button"
            onClick={() => pauseM.mutate()}
            disabled={pauseM.isPending}
            className="inline-flex min-h-[44px] flex-1 items-center justify-center gap-2 rounded-sm border border-hairline bg-void-2/40 px-4 py-3 font-mono text-[11px] uppercase tracking-widest text-dust transition-colors hover:border-ember/40 hover:text-ember disabled:opacity-50"
          >
            {pauseM.isPending ? (
              <Loader2 className="h-3.5 w-3.5 animate-spin" />
            ) : (
              <Pause className="h-3.5 w-3.5" />
            )}
            Pause
          </button>
          <button
            type="button"
            onClick={() => setMode("reflection")}
            className="inline-flex min-h-[44px] flex-1 items-center justify-center gap-2 rounded-sm border border-signal/40 bg-signal/15 px-4 py-3 font-mono text-[11px] uppercase tracking-widest text-signal transition-colors hover:bg-signal/25 hover:text-signal-neon"
          >
            <Square className="h-3.5 w-3.5" />
            Stop
          </button>
        </div>
      )}

      {/* Paused: Resume + Stop */}
      {showPaused && (
        <div className="mt-5 flex w-full max-w-md items-center justify-center gap-3 px-1">
          <button
            type="button"
            onClick={() => resumeM.mutate()}
            disabled={resumeM.isPending}
            className="inline-flex min-h-[44px] flex-1 items-center justify-center gap-2 rounded-sm border border-signal/40 bg-signal/15 px-4 py-3 font-mono text-[11px] uppercase tracking-widest text-signal transition-colors hover:bg-signal/25 hover:text-signal-neon disabled:opacity-50"
          >
            {resumeM.isPending ? (
              <Loader2 className="h-3.5 w-3.5 animate-spin" />
            ) : (
              <Play className="h-3.5 w-3.5" />
            )}
            Resume
          </button>
          <button
            type="button"
            onClick={() => setMode("reflection")}
            className="inline-flex min-h-[44px] flex-1 items-center justify-center gap-2 rounded-sm border border-hairline bg-void-2/40 px-4 py-3 font-mono text-[11px] uppercase tracking-widest text-dust transition-colors hover:border-signal/40 hover:text-parchment"
          >
            <Square className="h-3.5 w-3.5" />
            Stop
          </button>
        </div>
      )}

      {/* Reflection mode: slider + Finish */}
      {showReflection && (
        <div className="mt-5 flex w-full max-w-md flex-col gap-4 px-1">
          <div className="flex flex-col gap-2">
            <div className="flex items-center justify-between font-display text-[10px] uppercase tracking-macro text-dust">
              <span>
                <span className="opacity-50">[ </span>
                Reflection
                <span className="opacity-50"> ]</span>
              </span>
              <span className="text-signal">{READINESS_LABELS[reflection - 1]}</span>
            </div>
            <input
              type="range"
              min={1}
              max={5}
              step={1}
              value={reflection}
              onChange={(e) => setReflection(Number(e.target.value))}
              className="lyra-range h-2 w-full"
              aria-label="Post-task reflection 1 to 5"
            />
            <div className="flex justify-between font-mono text-[9px] uppercase tracking-widest text-dust-deep">
              {[1, 2, 3, 4, 5].map((n) => (
                <span key={n} className={n === reflection ? "text-signal" : ""}>
                  {n}
                </span>
              ))}
            </div>
          </div>
          <div className="flex items-center justify-center gap-3">
            <button
              type="button"
              onClick={() => setMode("idle")}
              disabled={stopM.isPending}
              className="inline-flex min-h-[44px] items-center justify-center gap-2 rounded-sm border border-hairline bg-void-2/40 px-4 py-3 font-mono text-[11px] uppercase tracking-widest text-dust transition-colors hover:border-signal/40 hover:text-parchment disabled:opacity-50"
            >
              Cancel
            </button>
            <button
              type="button"
              onClick={() =>
                stopM.mutate({
                  reflection,
                  // If we already saw requires_confirmation in errorMsg,
                  // resend with confirmed=true.
                  confirmed: errorMsg?.toLowerCase().includes("early") ? true : undefined,
                })
              }
              disabled={stopM.isPending}
              className="inline-flex min-h-[44px] flex-1 items-center justify-center gap-2 rounded-sm border border-signal/40 bg-signal/15 px-4 py-3 font-mono text-[11px] uppercase tracking-widest text-signal transition-colors hover:bg-signal/25 hover:text-signal-neon disabled:opacity-50"
            >
              {stopM.isPending && <Loader2 className="h-3.5 w-3.5 animate-spin" />}
              {errorMsg?.toLowerCase().includes("early") ? "Finish anyway" : "Finish"}
            </button>
          </div>
        </div>
      )}

      {/* Next-prompt: post-stop summary + suggestion */}
      {showNextPrompt && (
        <div className="flex w-full max-w-md flex-col items-center gap-4 px-1">
          {stoppedSummary && (
            <div className="flex items-baseline gap-3 text-center">
              <span className="font-display text-3xl font-semibold tabular-nums neon-cyan">
                {stoppedSummary.minutes}
                <span className="text-base text-signal/85">m</span>
              </span>
              <span className="font-mono text-[10px] uppercase tracking-widest text-dust-deep">
                protected focus
              </span>
              {stoppedSummary.delta !== null && (
                <span
                  className={`font-mono text-[10px] uppercase tracking-widest ${
                    stoppedSummary.delta <= 0 ? "text-signal" : "text-ember"
                  }`}
                >
                  {stoppedSummary.delta > 0 ? "+" : ""}
                  {stoppedSummary.delta}m vs plan
                </span>
              )}
            </div>
          )}

          {(() => {
            const next = plannedTasks.find(
              (t) => t.task_id !== lastStoppedTaskIdRef.current
            );
            if (!next) {
              return (
                <p className="text-center text-xs text-dust">
                  Nothing else on the plan. Brain-dump in the footer to add more.
                </p>
              );
            }
            return (
              <div className="flex w-full flex-col items-center gap-3 rounded-sm border border-hairline bg-void/40 p-3">
                <div className="text-center">
                  <div className="font-mono text-[9px] uppercase tracking-widest text-dust-deep">
                    Next up
                  </div>
                  <div className="mt-0.5 text-[13px] text-parchment">{next.title}</div>
                  <div className="font-mono text-[10px] text-dust-deep">
                    {fmtTime(next.start)}
                    {next.planned_duration_minutes
                      ? ` · ${next.planned_duration_minutes}m`
                      : ""}
                  </div>
                </div>
                <div className="flex w-full items-center gap-3">
                  <button
                    type="button"
                    onClick={() => {
                      setMode("idle");
                      setStoppedSummary(null);
                    }}
                    className="inline-flex min-h-[44px] flex-1 items-center justify-center gap-2 rounded-sm border border-hairline bg-void-2/40 px-3 py-2 font-mono text-[11px] uppercase tracking-widest text-dust hover:border-signal/40 hover:text-parchment"
                  >
                    Not now
                  </button>
                  <button
                    type="button"
                    onClick={() => {
                      setSelectedTaskId(next.task_id);
                      setStoppedSummary(null);
                      setMode("idle"); // surfaces the readiness path
                      // No auto-start — readiness needs human intent.
                    }}
                    className="inline-flex min-h-[44px] flex-1 items-center justify-center gap-2 rounded-sm border border-signal/40 bg-signal/15 px-3 py-2 font-mono text-[11px] uppercase tracking-widest text-signal hover:bg-signal/25 hover:text-signal-neon"
                  >
                    <Play className="h-3.5 w-3.5" />
                    Start
                  </button>
                </div>
              </div>
            );
          })()}
        </div>
      )}

      {/* Error surface — bottom of card, dismissible by clicking */}
      {errorMsg && (
        <button
          type="button"
          onClick={() => setErrorMsg(null)}
          className="mt-3 w-full max-w-md rounded-sm border border-ember/40 bg-ember/5 px-3 py-1.5 text-left text-[11px] text-ember"
        >
          {errorMsg} <span className="text-ember/60">· tap to dismiss</span>
        </button>
      )}
    </div>
  );
}
