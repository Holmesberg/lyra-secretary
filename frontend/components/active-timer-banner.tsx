"use client";
import { useEffect, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { Pause, Play } from "lucide-react";
import {
  pauseStopwatch,
  resumeStopwatch,
  type StopwatchStatus,
} from "@/lib/tasks";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

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

  useEffect(() => {
    if (status.paused) return; // freeze clock when paused
    const id = setInterval(() => setTick((t) => t + 1), 1000);
    return () => clearInterval(id);
  }, [status.paused]);

  if (!status.active || !status.start_time) return null;
  const paused = !!status.paused;
  const elapsed = formatElapsed(
    status.start_time,
    paused,
    status.total_paused_minutes ?? 0
  );

  async function toggle() {
    setErr(null);
    setBusy(true);
    // Snapshot for rollback before we optimistically mutate.
    const snapshot = qc.getQueryData<StopwatchStatus>(["stopwatch-status"]);
    // Optimistic flip so the banner doesn't wait for the 10 s poll.
    qc.setQueryData<StopwatchStatus>(["stopwatch-status"], (old) =>
      old ? { ...old, paused: !paused } : old
    );
    try {
      if (paused) await resumeStopwatch();
      else await pauseStopwatch();
      // Authoritative refetch so total_paused_minutes is accurate.
      qc.invalidateQueries({ queryKey: ["stopwatch-status"] });
    } catch (e) {
      // Rollback on failure.
      if (snapshot !== undefined) {
        qc.setQueryData(["stopwatch-status"], snapshot);
      }
      setErr(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
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
        <Button
          variant="outline"
          size="sm"
          onClick={toggle}
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
      </div>
    </div>
  );
}
