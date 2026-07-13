"use client";
/**
 * PulseFocusCard — inline timer command surface (revised 2026-04-30).
 *
 * Operator preference revision: "revert the current focus session to
 * the timer, was much more cooler." → the radial timer is the visual
 * hero in EVERY state (including idle, where it shows dimmed 00:00),
 * and the task picker / readiness / reflection chrome lives BELOW it
 * compactly. The previous A1 ship hid the timer in idle and let the
 * picker dominate the card; that wasn't the vibe.
 *
 * Operator-narrowed action set still applies (no Switch button). Pause uses
 * the canonical reason vocabulary so route choice cannot silently alter
 * measurement truth. The interactivity from the
 * inline shipped as A1 stays — just visually subordinated to the
 * timer-as-hero composition.
 *
 * State machine:
 *   - mode='idle' (default): timer dimmed at 00:00 + compact
 *     picker/readiness/start chrome below (or "nothing planned" hint)
 *   - mode='reflection' (after Stop): timer still showing the final
 *     elapsed + reflection slider + Finish below
 *   - mode='next-prompt' (after Finish): summary card replaces picker
 *
 * Active session UI (running, paused) derives from the server
 * stopwatch-status query — local mode doesn't switch.
 *
 * Bugs fixed in this revision (caught via ultrathink pass):
 *   1. requires_confirmation handling no longer string-matches
 *      `errorMsg.includes("early")` — uses a typed boolean state flag
 *      `requiresConfirm`. Less fragile, works regardless of what
 *      copy the backend's `confirmation_message` returns.
 *   2. Orphan reflection mode — if another tab stops the session
 *      while we're in mode='reflection', server status flips
 *      inactive but our local mode stays. Without cleanup, user
 *      hits Finish on a non-existent session → 4xx error. useEffect
 *      now resets mode→'idle' when status flips inactive while in
 *      reflection AND no in-flight stop mutation.
 */
import { useCallback, useEffect, useRef, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { AlertTriangle, Loader2, Pause, Play, RefreshCw, Square } from "lucide-react";
import { Toast } from "@/components/toast";
import {
  getStopwatchStatus,
  type ScopeOutcome,
  type StopwatchStatus,
  type TaskRow,
} from "@/lib/tasks";
import { RadialFocusTimer } from "@/components/pulse/RadialFocusTimer";
import { queryKeys } from "@/lib/query-keys";
import type { StopwatchStopOutputToast } from "@/lib/stopwatch-stop-outputs";
import { PAUSE_REASON_OPTIONS } from "@/lib/stopwatch-pause-reasons";
import {
  usePulseFocusStopwatchCommands,
  type PulseFocusMode,
} from "@/lib/hooks/use-pulse-focus-stopwatch-commands";

export interface PulseFocusCardProps {
  todaysTasks: TaskRow[];
}

interface PulseToastEntry extends StopwatchStopOutputToast {
  id: string;
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

// "Drained" was audit-flagged 2026-04-30 (CAUTION) as identity-cementing
// when used post-task as the reflection label too — picking it after
// finishing a session reads as "the work drained me." Swapped for "Tired,"
// which is universally accepted as a transient state not a trait. Same
// scale used for pre-task readiness + post-task reflection so the swap
// applies to both surfaces. Established 5-point energy scales (Karolinska,
// Stanford) use state words, not identity words — this aligns with that.
const READINESS_LABELS = ["Tired", "Low", "Steady", "Sharp", "Peak"];

const SCOPE_OPTIONS: { value: ScopeOutcome; label: string }[] = [
  { value: "stuck_to_plan", label: "Plan" },
  { value: "expanded", label: "Expanded" },
  { value: "reduced", label: "Reduced" },
];

export function PulseFocusCard({ todaysTasks }: PulseFocusCardProps) {
  const statusQ = useQuery<StopwatchStatus>({
    queryKey: queryKeys.stopwatchStatus,
    queryFn: getStopwatchStatus,
    refetchInterval: 5_000,
    refetchOnWindowFocus: true,
  });

  const status = statusQ.data;
  const isActive = !!status?.active;
  const isPaused = !!status?.paused;

  const [mode, setMode] = useState<PulseFocusMode>("idle");
  // Typed flag for the early-stop confirmation gate. Replaces the
  // fragile `errorMsg.includes("early")` heuristic in A1's first cut.
  const [requiresConfirm, setRequiresConfirm] = useState(false);

  const plannedTasks = todaysTasks
    .filter((t) => t.state === "PLANNED" && !t.voided_at)
    .sort((a, b) => {
      const ax = a.start ? new Date(a.start).getTime() : Infinity;
      const bx = b.start ? new Date(b.start).getTime() : Infinity;
      return ax - bx;
    });

  const [selectedTaskId, setSelectedTaskId] = useState<string | null>(null);

  useEffect(() => {
    if (selectedTaskId && plannedTasks.some((t) => t.task_id === selectedTaskId)) {
      return;
    }
    setSelectedTaskId(plannedTasks[0]?.task_id ?? null);
  }, [plannedTasks, selectedTaskId]);

  const [readiness, setReadiness] = useState<number>(3);
  const [reflection, setReflection] = useState<number | null>(null);
  const [completionPct, setCompletionPct] = useState("");
  const [scopeOutcome, setScopeOutcome] = useState<ScopeOutcome | null>(null);
  const [stoppedSummary, setStoppedSummary] = useState<{
    minutes: number;
    delta: number | null;
  } | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [infoMsg, setInfoMsg] = useState<string | null>(null);
  const [showPauseReasons, setShowPauseReasons] = useState(false);
  const [toasts, setToasts] = useState<PulseToastEntry[]>([]);
  const lastStoppedTaskIdRef = useRef<string | null>(null);

  const removeToast = useCallback((id: string) => {
    setToasts((previous) => previous.filter((toast) => toast.id !== id));
  }, []);

  const pushToast = useCallback((
    message: string,
    viewId: string | null,
    lifespan: "auto" | "pin",
    detailHref = "/insights",
    exposureId: string | null = null,
    surfaceId: string | null = null,
  ) => {
    if (
      surfaceId !== "stopwatch.micro_mirror"
      && surfaceId !== "stopwatch.calibration_nudge"
    ) {
      return;
    }
    const id =
      typeof crypto !== "undefined" && "randomUUID" in crypto
        ? crypto.randomUUID()
        : `toast-${Date.now()}-${Math.random().toString(36).slice(2)}`;
    setToasts((previous) => [
      ...previous,
      {
        id,
        message,
        viewId,
        lifespan,
        detailHref,
        exposureId,
        surfaceId,
      },
    ]);
  }, []);

  function beginReflection() {
    setShowPauseReasons(false);
    setCompletionPct("");
    setScopeOutcome(null);
    setMode("reflection");
  }

  function parsedCompletionPct(): number | undefined {
    if (completionPct.trim() === "") return undefined;
    const parsed = Number(completionPct);
    if (!Number.isFinite(parsed)) return undefined;
    return Math.max(0, Math.min(100, Math.round(parsed)));
  }

  const { startM, pauseM, resumeM, stopM, stopPendingRef } =
    usePulseFocusStopwatchCommands({
      setMode,
      setRequiresConfirm,
      setReadiness,
      setReflection,
      setCompletionPct,
      setScopeOutcome,
      setStoppedSummary,
      setErrorMsg,
      setInfoMsg,
      pushToast,
      lastStoppedTaskIdRef,
    });

  // Bug fix #2 (ultrathink): if status flips inactive while we're
  // in reflection mode (e.g. another tab stopped the session), reset
  // local mode so Finish doesn't 4xx on a non-existent session.
  useEffect(() => {
    if (mode === "reflection" && !isActive && !stopPendingRef.current) {
      setMode("idle");
      setRequiresConfirm(false);
      setErrorMsg(null);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isActive, mode]);

  // Render branches
  const showRunning = isActive && !isPaused && mode !== "reflection";
  const showPaused = isActive && isPaused && mode !== "reflection";
  const showReflection = mode === "reflection" || (stopM.isPending && isActive);
  const showNextPrompt = mode === "next-prompt" && !isActive;
  const showIdle = !isActive && mode === "idle";

  useEffect(() => {
    if (!showRunning) {
      setShowPauseReasons(false);
    }
  }, [showRunning]);

  // Eyebrow copy
  const eyebrow = showRunning
    ? "Focus session"
    : showPaused
      ? "Session paused"
      : showReflection
        ? "How was it?"
        : showNextPrompt
          ? "Session complete"
          : "Current focus session";

  // Title above timer
  const title =
    showRunning || showPaused || showReflection
      ? status?.task_title ?? null
      : showNextPrompt
        ? "Start the next one?"
        : plannedTasks.length > 0
          ? "Ready when you are"
          : "Ready when you are";

  if (statusQ.isError) {
    return (
      <div
        data-testid="pulse-focus-status-unavailable"
        role="status"
        className="terminal-panel flex min-h-[320px] flex-col items-center justify-center gap-4 px-6 py-8 text-center"
      >
        <AlertTriangle className="h-6 w-6 text-ember" aria-hidden />
        <div>
          <div className="font-display text-[10px] uppercase tracking-macro text-ember">
            [ Focus unavailable ]
          </div>
          <p className="mt-2 max-w-xs text-sm text-parchment">
            The live timer did not load, so Pulse will not guess its state.
          </p>
        </div>
        <button
          data-testid="pulse-focus-status-retry"
          type="button"
          onClick={() => void statusQ.refetch()}
          disabled={statusQ.isFetching}
          className="inline-flex min-h-[40px] items-center justify-center gap-2 border border-ember/40 px-3 font-mono text-[10px] uppercase tracking-widest text-ember transition-colors hover:bg-ember/10 disabled:opacity-50"
        >
          <RefreshCw className={`h-3.5 w-3.5 ${statusQ.isFetching ? "animate-spin" : ""}`} />
          Retry timer
        </button>
      </div>
    );
  }

  return (
    <>
      <div
      data-testid="pulse-focus-card"
      className="terminal-panel relative flex flex-col items-center overflow-hidden px-5 py-6 sm:px-6 sm:py-7"
    >
      {/* Eyebrow */}
      <div className="mb-3 font-display text-[10px] font-medium uppercase tracking-macro text-dust">
        <span className="opacity-50">[ </span>
        {eyebrow}
        <span className="opacity-50"> ]</span>
      </div>

      {/* Title — task title (active) or "Ready when you are" (idle) */}
      {title && (
        <h2
          className={`mb-3 line-clamp-2 max-w-md text-center text-lg font-semibold tracking-tight ${
            showIdle && !status?.task_title ? "text-dust" : "text-parchment"
          }`}
          title={title}
        >
          {title}
        </h2>
      )}

      {/* RADIAL TIMER — visual hero in EVERY state.
          - Idle: status undefined or active=false → dimmed 00:00
          - Active: live ticking
          - Paused: frozen, ember tone (handled inside RadialFocusTimer)
          - Reflection: shows final elapsed
          - Next-prompt: hidden (replaced by stop summary) */}
      {!showNextPrompt && (
        <div className="my-1">
          <RadialFocusTimer status={status} />
        </div>
      )}

      {/* IDLE — compact picker + readiness + Start, BELOW the timer. */}
      {showIdle && plannedTasks.length > 0 && (
        <div className="mt-5 flex w-full max-w-md flex-col gap-3 px-1">
          {/* Compact picker — caps at 120px scrollable */}
          <ul className="flex max-h-[120px] flex-col gap-1 overflow-y-auto rounded-sm border border-hairline bg-void/40 p-1">
            {plannedTasks.map((t) => {
              const selected = t.task_id === selectedTaskId;
              return (
                <li key={t.task_id}>
                  <button
                    data-testid="focus-task-option"
                    data-task-id={t.task_id}
                    data-task-title={t.title}
                    type="button"
                    onClick={() => setSelectedTaskId(t.task_id)}
                    className={`flex min-h-[40px] w-full items-center gap-2.5 rounded-sm px-2.5 py-1.5 text-left transition-colors ${
                      selected
                        ? "bg-signal/15 text-parchment ring-1 ring-signal/40"
                        : "text-dust hover:bg-void-2/60 hover:text-parchment"
                    }`}
                  >
                    <span
                      aria-hidden
                      className={`inline-block h-1.5 w-1.5 shrink-0 rounded-full transition-colors ${
                        selected
                          ? "bg-signal shadow-[0_0_8px_rgba(77,212,232,0.7)]"
                          : "bg-dust-deep"
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

          {/* Readiness — single inline row to keep it compact */}
          <div className="flex items-center gap-3">
            <span className="font-display text-[9px] uppercase tracking-macro text-dust-deep shrink-0">
              READY
            </span>
            <input
              type="range"
              min={1}
              max={5}
              step={1}
              value={readiness}
              onChange={(e) => setReadiness(Number(e.target.value))}
              className="lyraos-range h-2 flex-1"
              aria-label="Pre-task readiness 1 to 5"
            />
            <span className="shrink-0 font-mono text-[10px] uppercase tracking-widest text-signal min-w-[52px] text-right">
              {READINESS_LABELS[readiness - 1]}
            </span>
          </div>

          <button
            data-testid="focus-start-session"
            type="button"
            onClick={() =>
              selectedTaskId && startM.mutate({ taskId: selectedTaskId, readiness })
            }
            disabled={!selectedTaskId || startM.isPending}
            className="inline-flex min-h-[44px] items-center justify-center gap-2 rounded-sm border border-signal/40 bg-signal/15 px-5 py-2.5 font-mono text-[11px] uppercase tracking-widest text-signal transition-colors hover:bg-signal/25 hover:text-signal-neon disabled:opacity-50"
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

      {/* IDLE — no PLANNED tasks. Calmer empty state under the timer. */}
      {showIdle && plannedTasks.length === 0 && (
        <p className="mt-4 max-w-xs text-center text-xs text-dust">
          Nothing planned yet. Use quick capture above to add what you're
          working on.
        </p>
      )}

      {/* RUNNING — Pause + Stop */}
      {showRunning && (
        <div className="mt-5 flex w-full max-w-md flex-col gap-3 px-1">
          <div className="flex items-center justify-center gap-3">
            <button
              data-testid="focus-pause"
              type="button"
              onClick={() => setShowPauseReasons((visible) => !visible)}
              disabled={pauseM.isPending}
              aria-expanded={showPauseReasons}
              aria-controls="focus-pause-reasons"
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
              data-testid="focus-stop"
              type="button"
              onClick={beginReflection}
              className="inline-flex min-h-[44px] flex-1 items-center justify-center gap-2 rounded-sm border border-signal/40 bg-signal/15 px-4 py-3 font-mono text-[11px] uppercase tracking-widest text-signal transition-colors hover:bg-signal/25 hover:text-signal-neon"
            >
              <Square className="h-3.5 w-3.5" />
              Stop
            </button>
          </div>
          {showPauseReasons && (
            <div
              id="focus-pause-reasons"
              data-testid="focus-pause-reasons"
              className="rounded-sm border border-hairline bg-void/45 p-2"
            >
              <div className="mb-2 font-display text-[9px] uppercase tracking-macro text-dust-deep">
                Why are you pausing?
              </div>
              <div className="grid grid-cols-1 gap-1.5 sm:grid-cols-2">
                {PAUSE_REASON_OPTIONS.map((option) => (
                  <button
                    key={option.value}
                    data-testid={`focus-pause-reason-${option.value}`}
                    type="button"
                    onClick={() =>
                      pauseM.mutate(option.value, {
                        onSuccess: () => setShowPauseReasons(false),
                      })
                    }
                    disabled={pauseM.isPending}
                    className="min-h-[40px] rounded-sm border border-hairline px-3 py-2 text-left text-xs text-parchment transition-colors hover:border-ember/45 hover:bg-ember/5 hover:text-ember disabled:opacity-50"
                  >
                    {option.label}
                  </button>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* PAUSED — Resume + Stop */}
      {showPaused && (
        <div className="mt-5 flex w-full max-w-md items-center justify-center gap-3 px-1">
          <button
            data-testid="focus-resume"
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
            data-testid="focus-stop"
            type="button"
            onClick={beginReflection}
            className="inline-flex min-h-[44px] flex-1 items-center justify-center gap-2 rounded-sm border border-hairline bg-void-2/40 px-4 py-3 font-mono text-[11px] uppercase tracking-widest text-dust transition-colors hover:border-signal/40 hover:text-parchment"
          >
            <Square className="h-3.5 w-3.5" />
            Stop
          </button>
        </div>
      )}

      {/* REFLECTION — slider + Finish, below the timer */}
      {showReflection && (
        <div className="mt-4 flex w-full max-w-md flex-col gap-3 px-1">
          <div className="flex items-center gap-3">
            <span className="font-display text-[9px] uppercase tracking-macro text-dust-deep shrink-0">
              FELT
            </span>
            <input
              type="range"
              min={1}
              max={5}
              step={1}
              value={reflection ?? 3}
              onChange={(e) => setReflection(Number(e.target.value))}
              className="lyraos-range h-2 flex-1"
              aria-label="Post-task reflection 1 to 5"
            />
            <span className="shrink-0 font-mono text-[10px] uppercase tracking-widest text-signal min-w-[52px] text-right">
              {reflection === null ? "Choose" : READINESS_LABELS[reflection - 1]}
            </span>
          </div>
          <div className="grid gap-2 sm:grid-cols-[minmax(0,1fr)_minmax(0,1.35fr)]">
            <label className="flex min-h-[38px] items-center gap-2 rounded-sm border border-hairline bg-void/35 px-2.5 text-xs text-dust">
              <span className="shrink-0 font-display text-[9px] uppercase tracking-macro text-dust-deep">
                Done %
              </span>
              <input
                data-testid="focus-completion"
                type="text"
                inputMode="numeric"
                pattern="[0-9]*"
                placeholder="0-100"
                value={completionPct}
                onChange={(e) => {
                  const raw = e.target.value.replace(/[^0-9]/g, "");
                  if (raw === "") {
                    setCompletionPct("");
                    return;
                  }
                  setCompletionPct(String(Math.min(100, parseInt(raw, 10))));
                }}
                className="min-w-0 flex-1 bg-transparent text-right font-mono text-xs text-parchment outline-none placeholder:text-dust-deep"
              />
            </label>
            <div className="flex min-h-[38px] items-center gap-1.5 rounded-sm border border-hairline bg-void/35 px-2">
              <span className="shrink-0 font-display text-[9px] uppercase tracking-macro text-dust-deep">
                Scope
              </span>
              <div className="flex min-w-0 flex-1 items-center justify-end gap-1">
                {SCOPE_OPTIONS.map((option) => (
                  <button
                    data-testid={`focus-scope-${option.value}`}
                    key={option.value}
                    type="button"
                    onClick={() =>
                      setScopeOutcome((prev) =>
                        prev === option.value ? null : option.value
                      )
                    }
                    className={`min-h-7 rounded-sm border px-2 font-mono text-[9px] uppercase tracking-widest transition-colors ${
                      scopeOutcome === option.value
                        ? "border-signal/60 bg-signal/10 text-signal"
                        : "border-hairline text-dust-deep hover:border-signal/40 hover:text-parchment"
                    }`}
                  >
                    {option.label}
                  </button>
                ))}
              </div>
            </div>
          </div>
          <div className="flex items-center justify-center gap-3">
            <button
              data-testid="focus-cancel-reflection"
              type="button"
              onClick={() => {
                setMode("idle");
                setRequiresConfirm(false);
                setErrorMsg(null);
                setCompletionPct("");
                setScopeOutcome(null);
              }}
              disabled={stopM.isPending}
              className="inline-flex min-h-[44px] items-center justify-center gap-2 rounded-sm border border-hairline bg-void-2/40 px-4 py-3 font-mono text-[11px] uppercase tracking-widest text-dust transition-colors hover:border-signal/40 hover:text-parchment disabled:opacity-50"
            >
              Cancel
            </button>
            <button
              data-testid="focus-finish"
              type="button"
              onClick={() =>
                reflection !== null &&
                stopM.mutate({
                  reflection,
                  confirmed: requiresConfirm ? true : undefined,
                  completionPct: parsedCompletionPct(),
                  scopeOutcome: scopeOutcome ?? undefined,
                })
              }
              disabled={stopM.isPending || reflection === null}
              className="inline-flex min-h-[44px] flex-1 items-center justify-center gap-2 rounded-sm border border-signal/40 bg-signal/15 px-4 py-3 font-mono text-[11px] uppercase tracking-widest text-signal transition-colors hover:bg-signal/25 hover:text-signal-neon disabled:opacity-50"
            >
              {stopM.isPending && <Loader2 className="h-3.5 w-3.5 animate-spin" />}
              {requiresConfirm ? "Finish anyway" : "Finish"}
            </button>
          </div>
        </div>
      )}

      {/* NEXT-PROMPT — replaces the timer with a summary card. */}
      {showNextPrompt && (
        <div className="my-2 flex w-full max-w-md flex-col items-center gap-4 px-1">
          {stoppedSummary && (
            <div className="flex flex-col items-center gap-1 text-center">
              <div className="flex items-baseline gap-2">
                <span className="font-display text-5xl font-semibold tabular-nums neon-cyan">
                  {stoppedSummary.minutes}
                  <span className="text-xl text-signal/85">m</span>
                </span>
              </div>
              <div className="font-display text-[10px] uppercase tracking-macro text-dust">
                <span className="opacity-50">[ </span>
                Protected focus
                <span className="opacity-50"> ]</span>
              </div>
              {stoppedSummary.delta !== null && (
                <div
                  className={`font-mono text-[10px] uppercase tracking-widest ${
                    stoppedSummary.delta <= 0 ? "text-signal" : "text-ember"
                  }`}
                >
                  {stoppedSummary.delta > 0 ? "+" : ""}
                  {stoppedSummary.delta}m vs plan
                </div>
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
                  Nothing else on the plan. Use quick capture above for more.
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
                      setMode("idle");
                    }}
                    className="inline-flex min-h-[44px] flex-1 items-center justify-center gap-2 rounded-sm border border-signal/40 bg-signal/15 px-3 py-2 font-mono text-[11px] uppercase tracking-widest text-signal hover:bg-signal/25 hover:text-signal-neon"
                  >
                    <Play className="h-3.5 w-3.5" />
                    Pick this
                  </button>
                </div>
              </div>
            );
          })()}
        </div>
      )}

      {/* Error surface — bottom of card, dismissible by tap */}
      {errorMsg && (
        <button
          type="button"
          onClick={() => {
            setErrorMsg(null);
            setRequiresConfirm(false);
          }}
          className="mt-3 w-full max-w-md rounded-sm border border-ember/40 bg-ember/5 px-3 py-1.5 text-left text-[11px] text-ember"
        >
          {errorMsg} <span className="text-ember/60">· tap to dismiss</span>
        </button>
      )}
      {infoMsg && !errorMsg && (
        <button
          type="button"
          onClick={() => setInfoMsg(null)}
          className="mt-3 w-full max-w-md rounded-sm border border-signal/35 bg-signal/5 px-3 py-1.5 text-left text-[11px] text-signal"
        >
          {infoMsg} <span className="text-signal/60">· tap to dismiss</span>
        </button>
      )}
      </div>
      <div className="pointer-events-none fixed bottom-4 right-4 z-50 flex flex-col gap-2">
        {toasts.map((toast) => (
          <Toast
            key={toast.id}
            id={toast.id}
            message={toast.message}
            viewId={toast.viewId}
            exposureId={toast.exposureId}
            surfaceId={toast.surfaceId}
            lifespan={toast.lifespan}
            detailHref={toast.detailHref}
            onDismiss={removeToast}
          />
        ))}
      </div>
    </>
  );
}
