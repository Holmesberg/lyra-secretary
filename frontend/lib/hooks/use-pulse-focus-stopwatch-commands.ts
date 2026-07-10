"use client";

import {
  useEffect,
  useRef,
  type Dispatch,
  type MutableRefObject,
  type SetStateAction,
} from "react";
import { useMutation } from "@tanstack/react-query";

import { useTimerCommandInvalidation } from "@/lib/hooks/use-timer-command-invalidation";
import { announceUndoAvailable } from "@/lib/undo";
import { QUICK_PAUSE_REASON } from "@/lib/stopwatch-pause-reasons";
import {
  pauseStopwatch,
  resumeStopwatch,
  startStopwatch,
  stopStopwatch,
  type ScopeOutcome,
  type StartStopwatchResponse,
  type StopResponse,
} from "@/lib/tasks";

export type PulseFocusMode = "idle" | "reflection" | "next-prompt";

interface StoppedSummary {
  minutes: number;
  delta: number | null;
}

interface PulseFocusStopwatchCommandOptions {
  setMode: Dispatch<SetStateAction<PulseFocusMode>>;
  setRequiresConfirm: Dispatch<SetStateAction<boolean>>;
  setReadiness: Dispatch<SetStateAction<number>>;
  setReflection: Dispatch<SetStateAction<number | null>>;
  setCompletionPct: Dispatch<SetStateAction<string>>;
  setScopeOutcome: Dispatch<SetStateAction<ScopeOutcome | null>>;
  setStoppedSummary: Dispatch<SetStateAction<StoppedSummary | null>>;
  setErrorMsg: Dispatch<SetStateAction<string | null>>;
  setInfoMsg: Dispatch<SetStateAction<string | null>>;
  lastStoppedTaskIdRef: MutableRefObject<string | null>;
}

export function usePulseFocusStopwatchCommands({
  setMode,
  setRequiresConfirm,
  setReadiness,
  setReflection,
  setCompletionPct,
  setScopeOutcome,
  setStoppedSummary,
  setErrorMsg,
  setInfoMsg,
  lastStoppedTaskIdRef,
}: PulseFocusStopwatchCommandOptions) {
  const refreshTimerSurfaces = useTimerCommandInvalidation();

  const startM = useMutation<
    StartStopwatchResponse,
    Error,
    { taskId: string; readiness: number }
  >({
    mutationFn: ({ taskId, readiness }) => startStopwatch(taskId, readiness),
    onSuccess: (res) => {
      setMode("idle");
      setErrorMsg(null);
      setReadiness(3);
      announceUndoAvailable("Timer started.");
      if (res.is_future_task && res.planned_start) {
        try {
          const planned = new Date(res.planned_start);
          const minutesEarly = Math.max(
            0,
            Math.round((planned.getTime() - Date.now()) / 60000),
          );
          const timeLabel = planned.toLocaleTimeString([], {
            hour: "numeric",
            minute: "2-digit",
          });
          const msg = `Heads up: this was scheduled for ${timeLabel}; you started ${minutesEarly} min early. The session will record from now.`;
          setInfoMsg(msg);
          setTimeout(() => {
            setInfoMsg((prev) => (prev === msg ? null : prev));
          }, 5000);
        } catch {
          setInfoMsg(
            "Heads up: this was scheduled later. The session will record from now.",
          );
        }
      } else {
        setInfoMsg(null);
      }
      refreshTimerSurfaces();
    },
    onError: (e) => setErrorMsg(e.message ?? "Failed to start"),
  });

  const pauseM = useMutation<unknown, Error, void>({
    mutationFn: () => pauseStopwatch(QUICK_PAUSE_REASON),
    onSuccess: () => refreshTimerSurfaces(),
    onError: (e) => setErrorMsg(e.message ?? "Failed to pause"),
  });

  const resumeM = useMutation<unknown, Error, void>({
    mutationFn: () => resumeStopwatch(),
    onSuccess: () => refreshTimerSurfaces(),
    onError: (e) => setErrorMsg(e.message ?? "Failed to resume"),
  });

  const stopM = useMutation<
    StopResponse,
    Error,
    {
      reflection: number;
      confirmed?: boolean;
      completionPct?: number;
      scopeOutcome?: ScopeOutcome;
    }
  >({
    mutationFn: ({ reflection, confirmed, completionPct, scopeOutcome }) =>
      stopStopwatch(reflection, {
        confirmed,
        task_completion_percentage: completionPct,
        scope_outcome: scopeOutcome,
      }),
    onSuccess: (res) => {
      if (res.requires_confirmation) {
        setRequiresConfirm(true);
        setErrorMsg(res.confirmation_message ?? "Stopping early — finish anyway?");
        return;
      }
      lastStoppedTaskIdRef.current = res.task_id;
      setStoppedSummary({
        minutes: Math.round(res.duration_minutes),
        delta: res.delta_minutes ?? null,
      });
      setMode("next-prompt");
      setRequiresConfirm(false);
      setErrorMsg(null);
      setInfoMsg(null);
      setReflection(null);
      setCompletionPct("");
      setScopeOutcome(null);
      refreshTimerSurfaces();
    },
    onError: (e) => setErrorMsg(e.message ?? "Failed to stop"),
  });

  const stopPendingRef = useRef(stopM.isPending);
  useEffect(() => {
    stopPendingRef.current = stopM.isPending;
  }, [stopM.isPending]);

  return {
    startM,
    pauseM,
    resumeM,
    stopM,
    stopPendingRef,
  };
}
