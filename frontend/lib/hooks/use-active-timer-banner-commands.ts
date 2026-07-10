"use client";

import {
  type Dispatch,
  type SetStateAction,
  useCallback,
  useState,
} from "react";
import { useQueryClient } from "@tanstack/react-query";

import { useTimerCommandInvalidation } from "@/lib/hooks/use-timer-command-invalidation";
import { queryKeys } from "@/lib/query-keys";
import {
  buildOptimisticSwitchStatus,
  markStopwatchStatusPaused,
  markStopwatchStatusResumed,
  updateTaskStatesInQueryData,
} from "@/lib/stopwatch-optimistic";
import type { PauseReason } from "@/lib/stopwatch-pause-reasons";
import {
  pauseStopwatch,
  resumeStopwatch,
  switchStopwatch,
  type PausedOther,
  type StopwatchStatus,
} from "@/lib/tasks";

interface PauseResumeCommandOptions {
  status: StopwatchStatus;
  setLocalPaused: Dispatch<SetStateAction<boolean>>;
  setShowReasonPicker: Dispatch<SetStateAction<boolean>>;
  setBusy: Dispatch<SetStateAction<boolean>>;
  setErr: Dispatch<SetStateAction<string | null>>;
  markPauseStarted: () => void;
  markResumeStarted: () => void;
}

export function useActiveTimerPauseResumeCommands({
  status,
  setLocalPaused,
  setShowReasonPicker,
  setBusy,
  setErr,
  markPauseStarted,
  markResumeStarted,
}: PauseResumeCommandOptions) {
  const qc = useQueryClient();
  const refreshTimerSurfaces = useTimerCommandInvalidation();

  const applyPause = useCallback(
    async (reason: PauseReason | undefined) => {
      setShowReasonPicker(false);
      setErr(null);
      setLocalPaused(true);
      markPauseStarted();
      setBusy(true);
      // Cancel in-flight status polls so stale pre-pause responses cannot
      // overwrite the optimistic flip before the mutation resolves.
      await qc.cancelQueries({ queryKey: queryKeys.stopwatchStatus });
      const snapshot = qc.getQueryData<StopwatchStatus>(
        queryKeys.stopwatchStatus,
      );
      qc.setQueryData<StopwatchStatus>(
        queryKeys.stopwatchStatus,
        markStopwatchStatusPaused,
      );
      qc.setQueriesData({ queryKey: queryKeys.tasks }, (old: unknown) =>
        updateTaskStatesInQueryData(old, [
          { taskId: status.task_id, state: "PAUSED" },
        ]),
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
          updateTaskStatesInQueryData(old, [
            { taskId: status.task_id, state: "EXECUTING" },
          ]),
        );
        setErr(e instanceof Error ? e.message : String(e));
      } finally {
        setBusy(false);
      }
    },
    [
      markPauseStarted,
      qc,
      refreshTimerSurfaces,
      setLocalPaused,
      setShowReasonPicker,
      setBusy,
      setErr,
      status.task_id,
    ],
  );

  const doResume = useCallback(async () => {
    setErr(null);
    setLocalPaused(false);
    markResumeStarted();
    setBusy(true);
    await qc.cancelQueries({ queryKey: queryKeys.stopwatchStatus });
    const snapshot = qc.getQueryData<StopwatchStatus>(
      queryKeys.stopwatchStatus,
    );
    qc.setQueryData<StopwatchStatus>(
      queryKeys.stopwatchStatus,
      markStopwatchStatusResumed,
    );
    qc.setQueriesData({ queryKey: queryKeys.tasks }, (old: unknown) =>
      updateTaskStatesInQueryData(old, [
        { taskId: status.task_id, state: "EXECUTING" },
      ]),
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
        updateTaskStatesInQueryData(old, [
          { taskId: status.task_id, state: "PAUSED" },
        ]),
      );
      setErr(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  }, [
    markPauseStarted,
    markResumeStarted,
    qc,
    refreshTimerSurfaces,
    setBusy,
    setErr,
    setLocalPaused,
    status.task_id,
  ]);

  return {
    applyPause,
    doResume,
  };
}

export function usePausedOtherSwitchCommands() {
  const qc = useQueryClient();
  const refreshTimerSurfaces = useTimerCommandInvalidation();
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  const handleSwitch = useCallback(
    async (target: PausedOther) => {
      setErr(null);
      setBusy(true);

      await qc.cancelQueries({ queryKey: queryKeys.stopwatchStatus });
      const statusSnapshot = qc.getQueryData<StopwatchStatus>(
        queryKeys.stopwatchStatus,
      );
      const sourceTaskId = statusSnapshot?.task_id;
      const sourceTitle = statusSnapshot?.task_title;
      const sourceSessionId = statusSnapshot?.session_id;

      qc.setQueryData<StopwatchStatus>(queryKeys.stopwatchStatus, (old) =>
        buildOptimisticSwitchStatus(old, target, {
          taskId: sourceTaskId,
          title: sourceTitle,
          sessionId: sourceSessionId,
        }),
      );
      qc.setQueriesData({ queryKey: queryKeys.tasks }, (old: unknown) =>
        updateTaskStatesInQueryData(old, [
          { taskId: target.task_id, state: "EXECUTING" },
          { taskId: sourceTaskId, state: "PAUSED" },
        ]),
      );

      try {
        await switchStopwatch(target.task_id);
        refreshTimerSurfaces();
      } catch (e) {
        if (statusSnapshot !== undefined) {
          qc.setQueryData(queryKeys.stopwatchStatus, statusSnapshot);
        }
        qc.setQueriesData({ queryKey: queryKeys.tasks }, (old: unknown) =>
          updateTaskStatesInQueryData(old, [
            { taskId: target.task_id, state: "PAUSED" },
            { taskId: sourceTaskId, state: "EXECUTING" },
          ]),
        );
        setErr(e instanceof Error ? e.message : String(e));
      } finally {
        setBusy(false);
      }
    },
    [qc, refreshTimerSurfaces],
  );

  return {
    handleSwitch,
    busy,
    err,
  };
}
