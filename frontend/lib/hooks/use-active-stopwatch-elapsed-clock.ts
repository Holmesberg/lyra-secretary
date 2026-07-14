"use client";

import {
  type Dispatch,
  type SetStateAction,
  useCallback,
  useEffect,
  useRef,
  useState,
} from "react";

import type { StopwatchStatus } from "@/lib/tasks";
import { getElapsedSeconds } from "@/lib/stopwatch-time";

function fmtTime(secs: number) {
  const safe = Math.max(0, Math.floor(secs));
  const h = Math.floor(safe / 3600);
  const m = Math.floor((safe % 3600) / 60);
  const s = safe % 60;
  const hh = h > 0 ? `${String(h).padStart(2, "0")}:` : "";
  return `${hh}${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}`;
}

interface ActiveStopwatchElapsedClockOptions {
  status: StopwatchStatus;
  localPaused: boolean;
  setLocalPaused: Dispatch<SetStateAction<boolean>>;
  busy: boolean;
  showReasonPicker: boolean;
}

// Display timing:
// - Prefer second-precision elapsed_seconds; fall back to elapsed_minutes * 60.
// - While running, display = anchor.sec + (now - anchor.ts).
// - Polls can advance the local display, but never rewind it.
// - Pause freezes the value the user saw.
// - Resume rebases from the frozen display instead of minute-truncated server truth.
export function useActiveStopwatchElapsedClock({
  status,
  localPaused,
  setLocalPaused,
  busy,
  showReasonPicker,
}: ActiveStopwatchElapsedClockOptions) {
  const [tick, setTick] = useState(0);
  const initialSec = getElapsedSeconds(status);
  const [anchor, setAnchor] = useState<{ sec: number; ts: number }>(() => ({
    sec: initialSec,
    ts: Date.now(),
  }));
  const [frozenSec, setFrozenSec] = useState<number | null>(
    status.paused ? initialSec : null
  );
  const prevPausedRef = useRef<boolean>(!!status.paused);
  const lastDisplayedRef = useRef<number>(initialSec);
  const [pauseBaseSec, setPauseBaseSec] = useState(
    (status.total_paused_minutes ?? 0) * 60
  );
  const pauseStartRef = useRef<number | null>(
    status.paused
      ? Date.now() - (status.current_pause_seconds ?? 0) * 1000
      : null
  );
  const prevTaskIdRef = useRef(status.task_id);

  const markPauseStarted = useCallback(() => {
    pauseStartRef.current = Date.now();
  }, []);

  const markResumeStarted = useCallback(() => {
    pauseStartRef.current = null;
  }, []);

  useEffect(() => {
    setPauseBaseSec((status.total_paused_minutes ?? 0) * 60);
  }, [status.total_paused_minutes]);

  useEffect(() => {
    if (!busy && localPaused !== !!status.paused) {
      setLocalPaused(!!status.paused);
      if (!status.paused) {
        pauseStartRef.current = null;
        setFrozenSec(null);
      } else {
        pauseStartRef.current =
          pauseStartRef.current ??
          (Date.now() - (status.current_pause_seconds ?? 0) * 1000);
      }
    }
  }, [
    status.paused,
    status.current_pause_seconds,
    busy,
    localPaused,
    setLocalPaused,
  ]);

  useEffect(() => {
    if (status.task_id === prevTaskIdRef.current) return;
    prevTaskIdRef.current = status.task_id;
    const sec = getElapsedSeconds(status);
    setLocalPaused(!!status.paused);
    setAnchor({ sec, ts: Date.now() });
    setFrozenSec(status.paused ? sec : null);
    prevPausedRef.current = !!status.paused;
    lastDisplayedRef.current = sec;
    setPauseBaseSec((status.total_paused_minutes ?? 0) * 60);
    pauseStartRef.current = status.paused
      ? Date.now() - (status.current_pause_seconds ?? 0) * 1000
      : null;
  }, [
    status,
    status.task_id,
    status.paused,
    status.total_paused_minutes,
    status.current_pause_seconds,
    setLocalPaused,
  ]);

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
  }, [localPaused, frozenSec]);

  useEffect(() => {
    if (localPaused) return;
    const serverSec = getElapsedSeconds(status);
    const localSec = anchor.sec + Math.floor((Date.now() - anchor.ts) / 1000);
    if (serverSec > localSec) {
      setAnchor({ sec: serverSec, ts: Date.now() });
    }
  }, [
    status,
    status.elapsed_minutes,
    status.elapsed_seconds,
    localPaused,
    anchor.sec,
    anchor.ts,
  ]);

  useEffect(() => {
    if (showReasonPicker && !localPaused) return;
    const id = setInterval(() => setTick((value) => value + 1), 1000);
    return () => clearInterval(id);
  }, [showReasonPicker, localPaused]);

  let elapsed: string;
  if (localPaused) {
    const currentPauseSec = pauseStartRef.current
      ? Math.floor((Date.now() - pauseStartRef.current) / 1000)
      : 0;
    elapsed = `paused · ${fmtTime(Math.floor(pauseBaseSec + currentPauseSec))}`;
  } else {
    const activeSec =
      frozenSec !== null
        ? frozenSec
        : anchor.sec + Math.floor((Date.now() - anchor.ts) / 1000);
    lastDisplayedRef.current = activeSec;
    elapsed = fmtTime(activeSec);
  }

  return {
    elapsed,
    tick,
    markPauseStarted,
    markResumeStarted,
  };
}
