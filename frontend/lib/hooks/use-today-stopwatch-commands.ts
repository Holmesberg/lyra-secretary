"use client";

import { useCallback, type Dispatch, type SetStateAction } from "react";
import {
  useQueryClient,
  type QueryKey,
} from "@tanstack/react-query";

import { queryKeys } from "@/lib/query-keys";
import {
  presentStopwatchStopOutputs,
  type PushStopwatchStopOutputToast,
} from "@/lib/stopwatch-stop-outputs";
import { announceUndoAvailable } from "@/lib/undo";
import {
  startStopwatch,
  stopStopwatch,
  type StopResponse,
  type StopwatchStatus,
  type TaskRow as TaskRowType,
} from "@/lib/tasks";

export interface TodayEarlyStopState {
  elapsed: number;
  planned: number;
  message: string;
}

interface TodayStopwatchCommandOptions {
  tasksDayKey: QueryKey;
  refresh: () => void;
  setErrorMsg: Dispatch<SetStateAction<string | null>>;
  setReadinessFor: Dispatch<SetStateAction<TaskRowType | null>>;
  setReadinessInterruptionType: Dispatch<SetStateAction<string | null>>;
  setReflectionOpen: Dispatch<SetStateAction<boolean>>;
  setEarlyStop: Dispatch<SetStateAction<TodayEarlyStopState | null>>;
  setInfoMsg: Dispatch<SetStateAction<string | null>>;
  pushToast: PushStopwatchStopOutputToast;
}

export function useTodayStopwatchCommands({
  tasksDayKey,
  refresh,
  setErrorMsg,
  setReadinessFor,
  setReadinessInterruptionType,
  setReflectionOpen,
  setEarlyStop,
  setInfoMsg,
  pushToast,
}: TodayStopwatchCommandOptions) {
  const qc = useQueryClient();

  const handleStart = useCallback(
    async (
      task: TaskRowType,
      readiness: number,
      interruptionType?: string | null,
    ) => {
      setErrorMsg(null);
      await qc.cancelQueries({ queryKey: queryKeys.stopwatchStatus });
      const snapshot = qc.getQueryData<StopwatchStatus>(
        queryKeys.stopwatchStatus,
      );
      const interruptedTaskId =
        interruptionType && snapshot?.active ? snapshot.task_id : undefined;
      qc.setQueryData<StopwatchStatus>(queryKeys.stopwatchStatus, {
        active: true,
        task_id: task.task_id,
        task_title: task.title,
        paused: false,
        start_time: new Date().toISOString(),
        elapsed_minutes: 0,
        planned_duration_minutes: task.planned_duration_minutes ?? 0,
        total_paused_minutes: 0,
      });
      qc.setQueryData<TaskRowType[]>(tasksDayKey, (old) =>
        old?.map((t) => {
          if (t.task_id === task.task_id) return { ...t, state: "EXECUTING" };
          if (interruptedTaskId && t.task_id === interruptedTaskId) {
            return { ...t, state: "PAUSED" };
          }
          return t;
        }),
      );
      setReadinessFor(null);
      setReadinessInterruptionType(null);
      try {
        const startResp = await startStopwatch(
          task.task_id,
          readiness,
          interruptionType,
        );
        announceUndoAvailable("Timer started.");
        if (startResp.is_future_task && startResp.planned_start) {
          try {
            const planned = new Date(startResp.planned_start);
            const minutesEarly = Math.max(
              0,
              Math.round((planned.getTime() - Date.now()) / 60000),
            );
            const timeLabel = planned.toLocaleTimeString([], {
              hour: "numeric",
              minute: "2-digit",
            });
            setErrorMsg(
              `Heads up — this was scheduled for ${timeLabel}, you started ${minutesEarly} min early. The session will record from now.`,
            );
            setTimeout(() => setErrorMsg((prev) =>
              prev?.startsWith("Heads up — this was scheduled") ? null : prev
            ), 5000);
          } catch {
            // Bad provider/date data should not break timer start.
          }
        }
        refresh();
      } catch (e: unknown) {
        if (snapshot !== undefined) {
          qc.setQueryData(queryKeys.stopwatchStatus, snapshot);
        }
        qc.setQueryData<TaskRowType[]>(tasksDayKey, (old) =>
          old?.map((t) => {
            if (t.task_id === task.task_id) return { ...t, state: "PLANNED" };
            if (interruptedTaskId && t.task_id === interruptedTaskId) {
              return { ...t, state: "EXECUTING" };
            }
            return t;
          }),
        );
        setErrorMsg(e instanceof Error ? e.message : "Failed to start timer");
      }
    },
    [
      qc,
      tasksDayKey,
      refresh,
      setErrorMsg,
      setReadinessFor,
      setReadinessInterruptionType,
    ],
  );

  const handleStop = useCallback(
    async (
      reflection: number,
      opts: {
        confirmed?: boolean;
        completionPct?: number;
        scopeOutcome?: string;
      } = {},
    ) => {
      setErrorMsg(null);
      await qc.cancelQueries({ queryKey: queryKeys.stopwatchStatus });
      const snapshot = qc.getQueryData<StopwatchStatus>(
        queryKeys.stopwatchStatus,
      );
      const stoppedTaskId = snapshot?.task_id;
      qc.setQueryData<StopwatchStatus>(queryKeys.stopwatchStatus, {
        active: false,
      });
      if (stoppedTaskId) {
        qc.setQueryData<TaskRowType[]>(tasksDayKey, (old) =>
          old?.map((t) =>
            t.task_id === stoppedTaskId ? { ...t, state: "EXECUTED" } : t
          ),
        );
      }
      try {
        const res: StopResponse = await stopStopwatch(reflection, {
          confirmed: opts.confirmed,
          task_completion_percentage: opts.completionPct,
          scope_outcome: opts.scopeOutcome,
        });
        if (res.requires_confirmation) {
          if (snapshot !== undefined) {
            qc.setQueryData(queryKeys.stopwatchStatus, snapshot);
          }
          if (stoppedTaskId) {
            qc.setQueryData<TaskRowType[]>(tasksDayKey, (old) =>
              old?.map((t) =>
                t.task_id === stoppedTaskId ? { ...t, state: "EXECUTING" } : t
              ),
            );
          }
          setEarlyStop({
            elapsed: res.duration_minutes,
            planned: res.planned_duration_minutes,
            message: res.confirmation_message ?? "Early stop",
          });
          return;
        }
        setReflectionOpen(false);
        setEarlyStop(null);
        if (res.paused_parent) {
          setInfoMsg(
            `${res.paused_parent.title} is still paused (${res.paused_parent.paused_minutes} min). Resume when ready.`,
          );
        }
        presentStopwatchStopOutputs(res, pushToast);
        refresh();
      } catch (e: unknown) {
        if (snapshot !== undefined) {
          qc.setQueryData(queryKeys.stopwatchStatus, snapshot);
        }
        if (stoppedTaskId) {
          qc.setQueryData<TaskRowType[]>(tasksDayKey, (old) =>
            old?.map((t) =>
              t.task_id === stoppedTaskId ? { ...t, state: "EXECUTING" } : t
            ),
          );
        }
        setErrorMsg(e instanceof Error ? e.message : "Failed to stop timer");
      }
    },
    [
      qc,
      tasksDayKey,
      refresh,
      setErrorMsg,
      setReflectionOpen,
      setEarlyStop,
      setInfoMsg,
      pushToast,
    ],
  );

  return {
    handleStart,
    handleStop,
  };
}
