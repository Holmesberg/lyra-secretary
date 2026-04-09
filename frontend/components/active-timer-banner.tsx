"use client";
import { useEffect, useState } from "react";
import type { StopwatchStatus } from "@/lib/tasks";

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
  const [tick, setTick] = useState(0);
  useEffect(() => {
    const id = setInterval(() => setTick((t) => t + 1), 1000);
    return () => clearInterval(id);
  }, []);

  if (!status.active || !status.start_time) return null;
  const elapsed = formatElapsed(
    status.start_time,
    !!status.paused,
    status.total_paused_minutes ?? 0
  );
  return (
    <div className="mb-6 flex items-center justify-between rounded-lg border border-green-500/30 bg-green-500/10 px-4 py-3">
      <div>
        <div className="text-[10px] uppercase tracking-wide text-green-300/80">
          Active {status.paused ? "(paused)" : "timer"}
        </div>
        <div className="mt-0.5 truncate text-sm font-medium text-white">
          {status.task_title || status.task_id}
        </div>
      </div>
      <div className="font-mono text-lg tabular-nums text-green-200" data-tick={tick}>
        {elapsed}
      </div>
    </div>
  );
}
