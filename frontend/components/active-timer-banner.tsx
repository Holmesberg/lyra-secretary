"use client";
import { useEffect, useRef, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { Pause, Play, X, ArrowLeftRight } from "lucide-react";
import {
  pauseStopwatch,
  resumeStopwatch,
  switchStopwatch,
  type StopwatchStatus,
  type PausedOther,
} from "@/lib/tasks";
import { Button } from "@/components/ui/button";
import { useActiveStopwatchElapsedClock } from "@/lib/hooks/use-active-stopwatch-elapsed-clock";
import { useTimerCommandInvalidation } from "@/lib/hooks/use-timer-command-invalidation";
import { cn } from "@/lib/utils";
import { queryKeys } from "@/lib/query-keys";
import { getElapsedSeconds } from "@/lib/stopwatch-time";
import {
  PAUSE_REASON_OPTIONS,
  type PauseReason,
} from "@/lib/stopwatch-pause-reasons";

// `task_switch` exposed to the user-facing picker on 2026-05-02 (operator
// request during Phase 2 system transition). Previously it was system-only,
// written by /v1/stopwatch/switch when the operator swapped between paused
// tasks. Surfacing it lets the user explicitly attribute pauses caused by
// switching contexts — a distinct primitive from "distraction" or
// "external_interruption" (it's user-driven and intentional, but breaks
// flow). Captured separately so context-switch-cost analysis can
// distinguish operator-initiated swaps from involuntary disruptions.

// Silent default on click-outside was removed Apr 16 — pause_reason is
// a structural invariant (research-relevant field per do_not_add.md
// §Hardcoded default values and rules_vs_agency.md §Structural
// Invariants). Click-outside now just dismisses the picker; the user
// must explicitly pick a reason to pause.

interface Props {
  status: StopwatchStatus;
  showOrphanWarning?: boolean;
  onDismissOrphanWarning?: () => void;
  requestPause?: boolean;
  // When set, skip the reason picker and apply pause immediately with
  // this reason. Used by the prediction-banner "Quick pause" action
  // (2026-04-22): operator mid-break shouldn't have to pick a reason.
  quickPauseReason?: PauseReason;
  onRequestPauseHandled?: () => void;
}

export function ActiveTimerBanner({ status, showOrphanWarning, onDismissOrphanWarning, requestPause, quickPauseReason, onRequestPauseHandled }: Props) {
  const qc = useQueryClient();
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const [showReasonPicker, setShowReasonPicker] = useState(false);
  const pickerRef = useRef<HTMLDivElement | null>(null);
  const refreshTimerSurfaces = useTimerCommandInvalidation();

  // Local pause state, decoupled from React Query poll cycle. Changed
  // ONLY by applyPause/doResume (immediate, no network wait) and on
  // mount (from status prop). This prevents the stale-poll race where
  // refetchInterval fires during the 1.4 s mutation and overwrites
  // the optimistic flip, causing a visible pause↔unpause flicker.
  const [localPaused, setLocalPaused] = useState(!!status.paused);

  const {
    elapsed,
    tick,
    markPauseStarted,
    markResumeStarted,
  } = useActiveStopwatchElapsedClock({
    status,
    localPaused,
    setLocalPaused,
    busy,
    showReasonPicker,
  });

  // Click-outside listener for pause reason picker.
  // MUST be declared before the early return below to satisfy React's
  // Rules of Hooks — when status.active flips false, the early return
  // renders fewer hooks than the active path. The internal
  // showReasonPicker guard makes this a no-op when the banner is
  // hidden. (Hook-order bug introduced f3af1df, fixed Apr 12.)
  //
  // Apr 16: click-outside no longer triggers a silent pause with a
  // default reason — that was a do_not_add.md §Hardcoded default
  // values violation (research-relevant field defaulted silently).
  // Now it just dismisses the picker; user must explicitly choose.
  useEffect(() => {
    if (!showReasonPicker) return;
    function onDown(e: PointerEvent) {
      if (
        pickerRef.current &&
        !pickerRef.current.contains(e.target as Node)
      ) {
        setShowReasonPicker(false);
      }
    }
    document.addEventListener("pointerdown", onDown);
    return () => document.removeEventListener("pointerdown", onDown);
  }, [showReasonPicker]);

  useEffect(() => {
    if (requestPause && !localPaused) {
      if (quickPauseReason) {
        // One-tap quick pause — skip the reason picker. Direct apply
        // with the supplied reason (typically "intentional_break" for
        // the VT-17 prediction-banner flow).
        void applyPause(quickPauseReason);
      } else {
        setShowReasonPicker(true);
      }
      onRequestPauseHandled?.();
    }
    // applyPause is defined below and closes over the latest qc/status;
    // intentionally excluded from deps to avoid a re-run loop when
    // status changes mid-pause.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [requestPause, localPaused, quickPauseReason, onRequestPauseHandled]);

  // Multi-tasking swap chips visibility: paused-with-open-session tasks
  // that the user can switch into. Render even when no active task —
  // user may have stopped the child and the parent is still paused-with-
  // open-session, resumable via switch.
  const pausedOthers = status.paused_others ?? [];
  const hasOthers = pausedOthers.length > 0;
  const hasActive = !!(status.active && status.start_time);

  if (!hasActive && !hasOthers) return null;

  if (!hasActive) {
    return (
      <PausedOthersPanel others={pausedOthers} />
    );
  }

  const paused = localPaused;

  async function applyPause(reason: PauseReason | undefined) {
    setShowReasonPicker(false);
    setErr(null);
    setLocalPaused(true);
    markPauseStarted();
    setBusy(true);
    // Cancel any in-flight stopwatch-status poll so it can't return
    // stale (pre-pause) data AFTER our optimistic flip and overwrite
    // it. Without this, the 10 s refetchInterval can fire mid-request
    // and the response wins the race against our setQueryData,
    // producing a visible "snap-back to unpaused for ~1 s" flicker.
    await qc.cancelQueries({ queryKey: queryKeys.stopwatchStatus });
    // Snapshot for rollback before we optimistically mutate.
    const snapshot = qc.getQueryData<StopwatchStatus>(queryKeys.stopwatchStatus);
    qc.setQueryData<StopwatchStatus>(queryKeys.stopwatchStatus, (old) =>
      old ? { ...old, paused: true } : old
    );
    // Optimistic task-state flip — task card shows PAUSED instantly instead
    // of waiting for the 10s tasks poll to return the new state.
    qc.setQueriesData({ queryKey: queryKeys.tasks }, (old: unknown) =>
      Array.isArray(old)
        ? old.map((t: Record<string, unknown>) =>
            t.task_id === status.task_id ? { ...t, state: "PAUSED" } : t
          )
        : old
    );
    try {
      await pauseStopwatch(reason);
      refreshTimerSurfaces();
    } catch (e) {
      setLocalPaused(false);
      if (snapshot !== undefined) {
        qc.setQueryData(queryKeys.stopwatchStatus, snapshot);
      }
      qc.setQueriesData({ queryKey: queryKeys.tasks }, (old: unknown) =>
        Array.isArray(old)
          ? old.map((t: Record<string, unknown>) =>
              t.task_id === status.task_id ? { ...t, state: "EXECUTING" } : t
            )
          : old
      );
      setErr(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  }

  async function doResume() {
    setErr(null);
    setLocalPaused(false);
    markResumeStarted();
    setBusy(true);
    await qc.cancelQueries({ queryKey: queryKeys.stopwatchStatus });
    const snapshot = qc.getQueryData<StopwatchStatus>(queryKeys.stopwatchStatus);
    qc.setQueryData<StopwatchStatus>(queryKeys.stopwatchStatus, (old) =>
      old ? { ...old, paused: false } : old
    );
    qc.setQueriesData({ queryKey: queryKeys.tasks }, (old: unknown) =>
      Array.isArray(old)
        ? old.map((t: Record<string, unknown>) =>
            t.task_id === status.task_id ? { ...t, state: "EXECUTING" } : t
          )
        : old
    );
    try {
      await resumeStopwatch();
      refreshTimerSurfaces();
    } catch (e) {
      setLocalPaused(true);
      markPauseStarted();
      if (snapshot !== undefined) {
        qc.setQueryData(queryKeys.stopwatchStatus, snapshot);
      }
      qc.setQueriesData({ queryKey: queryKeys.tasks }, (old: unknown) =>
        Array.isArray(old)
          ? old.map((t: Record<string, unknown>) =>
              t.task_id === status.task_id ? { ...t, state: "PAUSED" } : t
            )
          : old
      );
      setErr(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  }

  function onPauseButtonClick() {
    if (paused) {
      doResume();
    } else {
      setShowReasonPicker(true);
    }
  }

  return (
    <div className="terminal-panel mb-6 px-4 py-3">
      <div className="flex items-center justify-between">
        <div className="min-w-0">
          <div
            className={cn(
              "flex items-center gap-2 font-mono text-[10px] uppercase tracking-widest",
              paused ? "text-ember" : "text-signal"
            )}
          >
            <span
              className={cn(
                "h-1.5 w-1.5 rounded-full",
                paused
                  ? "bg-ember"
                  : "bg-signal motion-safe:animate-pulse-glow"
              )}
            />
            <span>{paused ? "Paused" : "Active timer"}</span>
          </div>
          <div className="mt-1 truncate text-sm font-medium text-parchment">
            {status.task_title || status.task_id}
          </div>
          {err && <div className="mt-1 text-[11px] text-ember">{err}</div>}
        </div>
        <div className="flex items-center gap-3">
          <div
            className={cn(
              "font-mono text-lg tabular-nums",
              paused ? "neon-ember" : "neon-cyan"
            )}
            data-tick={tick}
          >
            {elapsed}
          </div>
          <div className="relative">
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={onPauseButtonClick}
              disabled={busy}
              title={paused ? "Resume" : "Pause"}
            >
              {paused ? (
                <>
                  <Play className="mr-1 h-3.5 w-3.5" />
                  Resume
                </>
              ) : (
                <>
                  <Pause className="mr-1 h-3.5 w-3.5" />
                  Pause
                </>
              )}
            </Button>
            {showReasonPicker && !paused && (
              <div
                ref={pickerRef}
                className="absolute right-0 top-full z-50 mt-2 w-48 overflow-hidden rounded-sm border border-hairline-signal bg-void-2 shadow-lg"
                role="menu"
              >
                <div className="border-b border-hairline-signal/40 px-3 py-1.5 font-mono text-[10px] uppercase tracking-widest text-dust">
                  Reason
                </div>
                {PAUSE_REASON_OPTIONS.map((opt) => (
                  <button
                    key={opt.value}
                    type="button"
                    role="menuitem"
                    onClick={() => applyPause(opt.value)}
                    className="block w-full px-3 py-2 text-left text-xs text-parchment transition-colors hover:bg-signal/10 hover:text-signal"
                  >
                    {opt.label}
                  </button>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
      {paused && showOrphanWarning && (
        <div className="mt-2 flex items-start justify-between gap-2 border-t border-hairline-signal/40 pt-2 text-[11px] text-dust">
          <span>
            <span className="font-medium text-parchment">
              {status.task_title}
            </span>{" "}
            will remain paused in the background when you start another task.
            Resume it from this banner, or it auto-closes after 12 hours.
          </span>
          <button
            type="button"
            onClick={onDismissOrphanWarning}
            aria-label="Dismiss"
            className="shrink-0 text-dust-deep transition-colors hover:text-parchment"
          >
            <X className="h-3.5 w-3.5" />
          </button>
        </div>
      )}
      {hasOthers && (
        <PausedOthersChips others={pausedOthers} />
      )}
    </div>
  );
}


// ---------------------------------------------------------------------------
// Multi-tasking swap (Apr 25): chip row + standalone panel
// ---------------------------------------------------------------------------

function PausedOthersChips({ others }: { others: PausedOther[] }) {
  const qc = useQueryClient();
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const refreshTimerSurfaces = useTimerCommandInvalidation();

  // Optimistic swap: mirrors the pause/resume optimistic pattern. The
  // network call to /v1/stopwatch/switch typically takes 300-1000ms (DB
  // pause source + resume target + Redis swap); without optimistic
  // updates the UI hangs for that round-trip. With optimistic updates,
  // the banner flips identity instantly and the refetch reconciles
  // seconds later. On failure we rollback to the snapshot.
  async function handleSwitch(target: PausedOther) {
    setErr(null);
    setBusy(true);

    // Snapshot for rollback BEFORE we mutate anything.
    await qc.cancelQueries({ queryKey: queryKeys.stopwatchStatus });
    const statusSnapshot = qc.getQueryData<StopwatchStatus>(queryKeys.stopwatchStatus);
    const sourceTaskId = statusSnapshot?.task_id;
    const sourceTitle = statusSnapshot?.task_title;
    const sourceSessionId = statusSnapshot?.session_id;

    // Optimistic stopwatch-status: target becomes active, source (if any)
    // moves to paused_others. Use the target's server-computed elapsed +
    // start_time + total_paused so the banner anchors at the CORRECT
    // value instantly. Pre-fix used elapsed=0 + start=now, which made the
    // timer count up from 0:00 for the entire round-trip duration (the
    // operator saw 16 seconds of wrong-value over the Cloudflare Tunnel).
    qc.setQueryData<StopwatchStatus>(queryKeys.stopwatchStatus, (old) => {
      const remainingOthers = (old?.paused_others ?? []).filter(
        (o) => o.task_id !== target.task_id
      );
      // For the source we're demoting: copy what we know from snapshot
      // and approximate the chip fields (paused_minutes=0 since we just
      // paused it; elapsed and start carry forward).
      const newOthers =
        sourceTaskId && sourceTitle && sourceSessionId
          ? [
              {
                task_id: sourceTaskId,
                title: sourceTitle,
                session_id: sourceSessionId,
                paused_minutes: 0,
                elapsed_minutes: old?.elapsed_minutes ?? 0,
                elapsed_seconds: getElapsedSeconds(old),
                start_time: old?.start_time ?? null,
                total_paused_minutes: old?.total_paused_minutes ?? 0,
              },
              ...remainingOthers,
            ]
          : remainingOthers;
      return {
        ...(old ?? {}),
        active: true,
        task_id: target.task_id,
        task_title: target.title,
        session_id: target.session_id,
        paused: false,
        elapsed_minutes: target.elapsed_minutes,
        elapsed_seconds: getElapsedSeconds(target),
        total_paused_minutes: target.total_paused_minutes,
        start_time:
          target.start_time ?? old?.start_time ?? new Date().toISOString(),
        paused_others: newOthers,
      } as StopwatchStatus;
    });

    // Optimistic task list: target → EXECUTING, source → PAUSED.
    qc.setQueriesData({ queryKey: queryKeys.tasks }, (old: unknown) =>
      Array.isArray(old)
        ? old.map((t: Record<string, unknown>) => {
            if (t.task_id === target.task_id) return { ...t, state: "EXECUTING" };
            if (sourceTaskId && t.task_id === sourceTaskId)
              return { ...t, state: "PAUSED" };
            return t;
          })
        : old
    );

    try {
      await switchStopwatch(target.task_id);
      // Reconcile with truth — fast path because we already cancelled
      // pending queries above; this fires a fresh fetch.
      refreshTimerSurfaces();
    } catch (e) {
      // Rollback the optimistic mutations.
      if (statusSnapshot !== undefined) {
        qc.setQueryData(queryKeys.stopwatchStatus, statusSnapshot);
      }
      qc.setQueriesData({ queryKey: queryKeys.tasks }, (old: unknown) =>
        Array.isArray(old)
          ? old.map((t: Record<string, unknown>) => {
              if (t.task_id === target.task_id) return { ...t, state: "PAUSED" };
              if (sourceTaskId && t.task_id === sourceTaskId)
                return { ...t, state: "EXECUTING" };
              return t;
            })
          : old
      );
      setErr(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="mt-3 flex flex-wrap items-center gap-2 border-t border-hairline-signal/40 pt-2">
      <span className="font-mono text-[10px] uppercase tracking-widest text-dust">
        Other in-progress
      </span>
      {others.map((other) => (
        <button
          key={other.task_id}
          type="button"
          disabled={busy}
          onClick={() => handleSwitch(other)}
          className="inline-flex items-center gap-1.5 rounded-sm border border-hairline-signal/40 bg-void-2/40 px-2 py-1 text-[11px] text-dust transition-colors hover:border-signal/60 hover:bg-signal/10 hover:text-parchment disabled:opacity-50"
          title={`Switch to ${other.title} (paused ${other.paused_minutes}m)`}
        >
          <ArrowLeftRight className="h-3 w-3" />
          <span className="truncate max-w-[180px]">{other.title}</span>
          <span className="text-dust-deep">·{other.paused_minutes}m</span>
        </button>
      ))}
      {err && <span className="text-[11px] text-ember">{err}</span>}
    </div>
  );
}


function PausedOthersPanel({ others }: { others: PausedOther[] }) {
  // Standalone panel for the no-active case: user stopped the child but the
  // parent (or any other paused-with-open-session task) is still resumable.
  // Same chip surface as inside the active banner.
  return (
    <div className="terminal-panel mb-6 px-4 py-3">
      <div className="flex items-center gap-2 font-mono text-[10px] uppercase tracking-widest text-dust">
        <span className="h-1.5 w-1.5 rounded-full bg-ember" />
        <span>Paused tasks (resumable)</span>
      </div>
      <div className="mt-2">
        <PausedOthersChips others={others} />
      </div>
    </div>
  );
}
