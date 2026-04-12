"use client";
import { useEffect, useRef, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { Pause, Play } from "lucide-react";
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

// Fallback when the user opens the picker and clicks outside without
// choosing — most commonly they got pulled into something, so
// external_interruption is the least-wrong assumption.
const PAUSE_REASON_DEFAULT = "external_interruption";

function formatElapsed(start: string, paused: boolean, totalPaused: number) {
  const startMs = new Date(start).getTime();
  const now = Date.now();
  const activeMs = now - startMs - totalPaused * 60_000;
  const secs = Math.max(0, Math.floor(activeMs / 1000));
  const h = Math.floor(secs / 3600);
  const m = Math.floor((secs % 3600) / 60);
  const s = secs % 60;
  const hh = h > 0 ? `${String(h).padStart(2, "0")}:` : "";
  return `${hh}${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}${
    paused ? " · paused" : ""
  }`;
}

export function ActiveTimerBanner({ status }: { status: StopwatchStatus }) {
  const qc = useQueryClient();
  const [tick, setTick] = useState(0);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const [showReasonPicker, setShowReasonPicker] = useState(false);
  const pickerRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    if (status.paused) return; // freeze clock when paused
    const id = setInterval(() => setTick((t) => t + 1), 1000);
    return () => clearInterval(id);
  }, [status.paused]);

  // Click-outside listener for pause reason picker.
  // MUST be declared before the early return below to
  // satisfy React's Rules of Hooks. When status.active
  // flips false, the early return path renders fewer
  // hooks than the active path — any hook below the
  // return causes "Rendered fewer hooks than expected"
  // crash on the transition. The internal showReasonPicker
  // guard makes this effect a no-op when the banner is
  // hidden anyway. (Bug introduced f3af1df, fixed today.)
  useEffect(() => {
    if (!showReasonPicker) return;
    function onDown(e: PointerEvent) {
      if (
        pickerRef.current &&
        !pickerRef.current.contains(e.target as Node)
      ) {
        applyPause(PAUSE_REASON_DEFAULT);
      }
    }
    document.addEventListener("pointerdown", onDown);
    return () => document.removeEventListener("pointerdown", onDown);
    // applyPause is stable enough for this lifecycle; we only want
    // to re-bind when the picker opens/closes.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [showReasonPicker]);

  if (!status.active || !status.start_time) return null;
  const paused = !!status.paused;
  const elapsed = formatElapsed(
    status.start_time,
    paused,
    status.total_paused_minutes ?? 0
  );

  async function applyPause(reason: string | undefined) {
    setShowReasonPicker(false);
    setErr(null);
    setBusy(true);
    // Snapshot for rollback before we optimistically mutate.
    const snapshot = qc.getQueryData<StopwatchStatus>(["stopwatch-status"]);
    // Optimistic flip so the banner doesn't wait for the 10 s poll.
    qc.setQueryData<StopwatchStatus>(["stopwatch-status"], (old) =>
      old ? { ...old, paused: true } : old
    );
    try {
      await pauseStopwatch(reason);
      qc.invalidateQueries({ queryKey: ["stopwatch-status"] });
    } catch (e) {
      if (snapshot !== undefined) {
        qc.setQueryData(["stopwatch-status"], snapshot);
      }
      setErr(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  }

  async function doResume() {
    setErr(null);
    setBusy(true);
    const snapshot = qc.getQueryData<StopwatchStatus>(["stopwatch-status"]);
    qc.setQueryData<StopwatchStatus>(["stopwatch-status"], (old) =>
      old ? { ...old, paused: false } : old
    );
    try {
      await resumeStopwatch();
      qc.invalidateQueries({ queryKey: ["stopwatch-status"] });
    } catch (e) {
      if (snapshot !== undefined) {
        qc.setQueryData(["stopwatch-status"], snapshot);
      }
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
        "mb-6 flex items-center justify-between rounded-lg border px-4 py-3",
        paused
          ? "border-yellow-500/30 bg-yellow-500/10"
          : "border-green-500/30 bg-green-500/10"
      )}
    >
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
  );
}
