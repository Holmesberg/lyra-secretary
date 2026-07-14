import type { PausedOther, StopwatchStatus, TaskState } from "./tasks";
import { getElapsedSeconds } from "./stopwatch-time";

export function markStopwatchStatusPaused(
  old: StopwatchStatus | undefined,
): StopwatchStatus | undefined {
  return old ? { ...old, paused: true } : old;
}

export function markStopwatchStatusResumed(
  old: StopwatchStatus | undefined,
): StopwatchStatus | undefined {
  return old ? { ...old, paused: false } : old;
}

export function updateTaskStatesInQueryData(
  old: unknown,
  updates: Array<{ taskId: string | null | undefined; state: TaskState }>,
): unknown {
  if (!Array.isArray(old)) return old;

  return old.map((task: Record<string, unknown>) => {
    for (const update of updates) {
      if (update.taskId && task.task_id === update.taskId) {
        return { ...task, state: update.state };
      }
    }
    return task;
  });
}

export function buildOptimisticSwitchStatus(
  old: StopwatchStatus | undefined,
  target: PausedOther,
  source: {
    taskId: string | null | undefined;
    title: string | null | undefined;
    sessionId: string | null | undefined;
  },
): StopwatchStatus {
  const remainingOthers = (old?.paused_others ?? []).filter(
    (other) => other.task_id !== target.task_id,
  );
  const pausedOthers =
    source.taskId && source.title && source.sessionId
      ? [
          {
            task_id: source.taskId,
            title: source.title,
            session_id: source.sessionId,
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
    start_time: target.start_time ?? old?.start_time ?? new Date().toISOString(),
    paused_others: pausedOthers,
  } as StopwatchStatus;
}
