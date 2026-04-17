"use client";
import { useEffect, useRef, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { Pause, Play, X } from "lucide-react";
import {
  pauseStopwatch,
  resumeStopwatch,
  type StopwatchStatus,
} from "@/lib/tasks";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

// Matches backend PAUSE_REASONS enum in
// backend/app/schemas/stopwatch.py:58. Keep in sync.
const PAUSE_REASON_OPTIONS: Array<{ value: string; label: string }> = [
  { value: "mental_fatigue", label: "Mental fatigue" },
  { value: "distraction", label: "Distraction" },
  { value: "task_difficulty", label: "Task difficulty" },
  { value: "external_interruption", label: "External interruption" },
  { value: "intentional_break", label: "Intentional break" },
  { value: "prayer", label: "Prayer" },
];

// Silent default on click-outside was removed Apr 16 — pause_reason is
// a structural invariant (research-relevant field per do_not_add.md
// §Hardcoded default values and rules_vs_agency.md §Structural
// Invariants). Click-outside now just dismisses the picker; the user
// must explicitly pick a reason to pause.

// Display timing — the old formula `now - start - total_paused_minutes`
// ignored in-progress pauses (total_paused_minutes only accumulates
// after a resume fires, so the active pause isn't in it), which made
// the clock visibly jump forward on every 10 s poll while paused and
// snap back on resume when the delta finally landed. Current approach:
//   • Maintain a local {sec, ts} anchor with sub-minute precision.
//   • While running, display = anchor.sec + (now − anchor.ts)/1000.
//   • On each poll, advance anchor to server `elapsed_minutes` only if
//     server > local (polls never rewind — server truncates to int min).
//   • On pause → freeze current display as `frozenSec`.
//   • On resume → rebase anchor to `frozenSec` so the clock continues
//     from where the user saw it paused, not from minute-truncated
//     server truth (which would backward-jump the sub-minute remainder).
function fmtTime(secs: number) {
  const safe = Math.max(0, Math.floor(secs));
  const h = Math.floor(safe / 3600);
  const m = Math.floor((safe % 3600) / 60);
  const s = safe % 60;
  const hh = h > 0 ? `${String(h).padStart(2, "0")}:` : "";
  return `${hh}${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}`;
}

interface Props {
  status: StopwatchStatus;
  showOrphanWarning?: boolean;
  onDismissOrphanWarning?: () => void;
  requestPause?: boolean;
  onRequestPauseHandled?: () => void;
}

export function ActiveTimerBanner({ status, showOrphanWarning, onDismissOrphanWarning, requestPause, onRequestPauseHandled }: Props) {
  const qc = useQueryClient();
  const [tick, setTick] = useState(0);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const [showReasonPicker, setShowReasonPicker] = useState(false);
  const pickerRef = useRef<HTMLDivElement | null>(null);

  // Local pause state, decoupled from React Query poll cycle. Changed
  // ONLY by applyPause/doResume (immediate, no network wait) and on
  // mount (from status prop). This prevents the stale-poll race where
  // refetchInterval fires during the 1.4 s mutation and overwrites
  // the optimistic flip, causing a visible pause↔unpause flicker.
  const [localPaused, setLocalPaused] = useState(!!status.paused);

  const [anchor, setAnchor] = useState<{ sec: number; ts: number }>(() => ({
    sec: (status.elapsed_minutes ?? 0) * 60,
    ts: Date.now(),
  }));
  const [frozenSec, setFrozenSec] = useState<number | null>(
    status.paused ? (status.elapsed_minutes ?? 0) * 60 : null
  );
  const prevPausedRef = useRef<boolean>(!!status.paused);
  const lastDisplayedRef = useRef<number>((status.elapsed_minutes ?? 0) * 60);

  // Pause counter: cumulative pause seconds. pauseBaseSec = completed
  // pauses from server; pauseStartRef = when the current pause began
  // (local capture, not from server). Display = base + (now - start).
  const [pauseBaseSec, setPauseBaseSec] = useState(
    (status.total_paused_minutes ?? 0) * 60
  );
  const pauseStartRef = useRef<number | null>(
    status.paused ? Date.now() : null
  );

  // Sync pause base from server polls.
  useEffect(() => {
    setPauseBaseSec((status.total_paused_minutes ?? 0) * 60);
  }, [status.total_paused_minutes]);

  // Safety sync: if localPaused disagrees with server AND no mutation is
  // in-flight, reconcile to server truth. Catches any edge case where
  // localPaused gets stuck (e.g., task switch via interruption, React
  // effect ordering, etc.). The !busy guard prevents stale polls from
  // overwriting optimistic state during a 1.4s mutation.
  useEffect(() => {
    if (!busy && localPaused !== !!status.paused) {
      setLocalPaused(!!status.paused);
      if (!status.paused) {
        pauseStartRef.current = null;
        setFrozenSec(null);
      } else {
        pauseStartRef.current = pauseStartRef.current ?? Date.now();
      }
    }
  }, [status.paused, busy, localPaused]);

  // Per-session reset: when the active task changes (new start, interruption,
  // etc.), all local timer state must reset to match the new task. Without
  // this, the previous task's pause counter / frozen display leaks into the
  // new session's banner.
  const prevTaskIdRef = useRef(status.task_id);
  useEffect(() => {
    if (status.task_id === prevTaskIdRef.current) return;
    prevTaskIdRef.current = status.task_id;
    setLocalPaused(!!status.paused);
    setAnchor({ sec: (status.elapsed_minutes ?? 0) * 60, ts: Date.now() });
    setFrozenSec(status.paused ? (status.elapsed_minutes ?? 0) * 60 : null);
    prevPausedRef.current = !!status.paused;
    lastDisplayedRef.current = (status.elapsed_minutes ?? 0) * 60;
    setPauseBaseSec((status.total_paused_minutes ?? 0) * 60);
    pauseStartRef.current = status.paused ? Date.now() : null;
  }, [status.task_id, status.paused, status.elapsed_minutes, status.total_paused_minutes]);

  // Pause-transition effect — freezes on pause, rebases anchor on resume.
  // Uses lastDisplayedRef (the value the user SAW on screen) to avoid a
  // forward-snap when frozenSec would otherwise recompute from anchor+now
  // (which includes time that elapsed while the reason picker was open).
  useEffect(() => {
    const wasPaused = prevPausedRef.current;
    const isPaused = localPaused;
    if (!wasPaused && isPaused) {
      setFrozenSec(lastDisplayedRef.current);
    } else if (wasPaused && !isPaused) {
      if (frozenSec !== null) {
        setAnchor({ sec: frozenSec, ts: Date.now() });
      }
      setFrozenSec(null);
    }
    prevPausedRef.current = isPaused;
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [localPaused]);

  // Server catch-up — advance to server `elapsed_minutes` only if it
  // passes the local tick. Strict `>` so polls never rewind the display.
  useEffect(() => {
    if (localPaused) return;
    const serverSec = (status.elapsed_minutes ?? 0) * 60;
    const localSec = anchor.sec + Math.floor((Date.now() - anchor.ts) / 1000);
    if (serverSec > localSec) {
      setAnchor({ sec: serverSec, ts: Date.now() });
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [status.elapsed_minutes]);

  // 1-Hz local tick — always runs unless the reason picker is open
  // (pre-freeze: timer appears to stop the moment the user clicks
  // Pause). While paused, the tick drives the pause counter instead
  // of the active counter.
  useEffect(() => {
    if (showReasonPicker && !localPaused) return;
    const id = setInterval(() => setTick((t) => t + 1), 1000);
    return () => clearInterval(id);
  }, [showReasonPicker, localPaused]);

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
      setShowReasonPicker(true);
      onRequestPauseHandled?.();
    }
  }, [requestPause, localPaused, onRequestPauseHandled]);

  if (!status.active || !status.start_time) return null;
  const paused = localPaused;

  let elapsed: string;
  if (paused) {
    // Pause counter: cumulative pause time
    const currentPauseSec = pauseStartRef.current
      ? Math.floor((Date.now() - pauseStartRef.current) / 1000)
      : 0;
    elapsed = `paused · ${fmtTime(Math.floor(pauseBaseSec + currentPauseSec))}`;
  } else {
    // Active counter: cumulative active work time
    const activeSec = frozenSec !== null
      ? frozenSec
      : anchor.sec + Math.floor((Date.now() - anchor.ts) / 1000);
    lastDisplayedRef.current = activeSec;
    elapsed = fmtTime(activeSec);
  }

  async function applyPause(reason: string | undefined) {
    setShowReasonPicker(false);
    setErr(null);
    setLocalPaused(true);
    pauseStartRef.current = Date.now();
    setBusy(true);
    // Cancel any in-flight stopwatch-status poll so it can't return
    // stale (pre-pause) data AFTER our optimistic flip and overwrite
    // it. Without this, the 10 s refetchInterval can fire mid-request
    // and the response wins the race against our setQueryData,
    // producing a visible "snap-back to unpaused for ~1 s" flicker.
    await qc.cancelQueries({ queryKey: ["stopwatch-status"] });
    // Snapshot for rollback before we optimistically mutate.
    const snapshot = qc.getQueryData<StopwatchStatus>(["stopwatch-status"]);
    qc.setQueryData<StopwatchStatus>(["stopwatch-status"], (old) =>
      old ? { ...old, paused: true } : old
    );
    // Optimistic task-state flip — task card shows PAUSED instantly instead
    // of waiting for the 10s tasks poll to return the new state.
    qc.setQueriesData({ queryKey: ["tasks"] }, (old: unknown) =>
      Array.isArray(old)
        ? old.map((t: Record<string, unknown>) =>
            t.task_id === status.task_id ? { ...t, state: "PAUSED" } : t
          )
        : old
    );
    try {
      await pauseStopwatch(reason);
      qc.invalidateQueries({ queryKey: ["stopwatch-status"] });
      qc.invalidateQueries({ queryKey: ["tasks"] });
    } catch (e) {
      setLocalPaused(false);
      if (snapshot !== undefined) {
        qc.setQueryData(["stopwatch-status"], snapshot);
      }
      qc.setQueriesData({ queryKey: ["tasks"] }, (old: unknown) =>
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
    pauseStartRef.current = null;
    setBusy(true);
    await qc.cancelQueries({ queryKey: ["stopwatch-status"] });
    const snapshot = qc.getQueryData<StopwatchStatus>(["stopwatch-status"]);
    qc.setQueryData<StopwatchStatus>(["stopwatch-status"], (old) =>
      old ? { ...old, paused: false } : old
    );
    qc.setQueriesData({ queryKey: ["tasks"] }, (old: unknown) =>
      Array.isArray(old)
        ? old.map((t: Record<string, unknown>) =>
            t.task_id === status.task_id ? { ...t, state: "EXECUTING" } : t
          )
        : old
    );
    try {
      await resumeStopwatch();
      qc.invalidateQueries({ queryKey: ["stopwatch-status"] });
      qc.invalidateQueries({ queryKey: ["tasks"] });
    } catch (e) {
      setLocalPaused(true);
      pauseStartRef.current = Date.now();
      if (snapshot !== undefined) {
        qc.setQueryData(["stopwatch-status"], snapshot);
      }
      qc.setQueriesData({ queryKey: ["tasks"] }, (old: unknown) =>
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
    <div
      className={cn(
        "mb-6 rounded-lg border px-4 py-3",
        paused
          ? "border-yellow-500/30 bg-yellow-500/10"
          : "border-green-500/30 bg-green-500/10"
      )}
    >
      <div className="flex items-center justify-between">
        <div className="min-w-0">
          <div
            className={cn(
              "text-[10px] uppercase tracking-wide",
              paused ? "text-yellow-300/80" : "text-green-300/80"
            )}
          >
            {paused ? "Paused" : "Active timer"}
          </div>
          <div className="mt-0.5 truncate text-sm font-medium text-white">
            {status.task_title || status.task_id}
          </div>
          {err && <div className="mt-1 text-[11px] text-red-300">{err}</div>}
        </div>
        <div className="flex items-center gap-3">
        <div
          className={cn(
            "font-mono text-lg tabular-nums",
            paused ? "text-yellow-200" : "text-green-200"
          )}
          data-tick={tick}
        >
          {elapsed}
        </div>
        <div className="relative">
          <Button
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
              className="absolute right-0 top-full z-50 mt-2 w-48 overflow-hidden rounded-md border border-white/15 bg-[#0a0a0a] shadow-lg"
              role="menu"
            >
              <div className="border-b border-white/10 px-3 py-1.5 text-[10px] uppercase tracking-wide text-white/50">
                Reason
              </div>
              {PAUSE_REASON_OPTIONS.map((opt) => (
                <button
                  key={opt.value}
                  type="button"
                  role="menuitem"
                  onClick={() => applyPause(opt.value)}
                  className="block w-full px-3 py-2 text-left text-xs text-white/90 hover:bg-white/10"
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
        <div className="mt-2 flex items-start justify-between gap-2 border-t border-yellow-500/20 pt-2 text-[11px] text-yellow-200/80">
          <span>
            <span className="font-medium text-white">{status.task_title}</span>{" "}
            will remain paused in the background when you start another task.
            Resume it from this banner, or it auto-closes after 12 hours.
          </span>
          <button
            type="button"
            onClick={onDismissOrphanWarning}
            aria-label="Dismiss"
            className="shrink-0 text-white/40 transition-colors hover:text-white/70"
          >
            <X className="h-3.5 w-3.5" />
          </button>
        </div>
      )}
    </div>
  );
}
