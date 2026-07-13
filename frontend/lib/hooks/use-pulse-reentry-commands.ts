"use client";

import {
  type Dispatch,
  type SetStateAction,
} from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";

import { invalidatePulseReentryCaches } from "@/lib/query-keys";
import {
  markAbandoned,
  markDone,
  resolveStalePause,
  resumeStopwatch,
  type ScopeOutcome,
  switchStopwatch,
  type TaskRow,
} from "@/lib/tasks";

export type PulseReentryCandidate =
  | {
      kind: "paused";
      id: string;
      title: string;
      detail: string;
      taskId: string;
      sessionId: string;
      activeMinutes: number;
      plannedMinutes: number | null;
      pausedMinutes: number;
      dateHref: string;
      rescheduleHref: string;
      action: "resume_current" | "switch_paused" | "resolve_stale";
      priority: number;
    }
  | {
      kind: "missed";
      id: string;
      title: string;
      detail: string;
      taskId: string;
      dateHref: string;
      rescheduleHref: string;
      canMarkDone: boolean;
      canDrop: boolean;
      priority: number;
    };

export type PulsePausedReentryCandidate = Extract<
  PulseReentryCandidate,
  { kind: "paused" }
>;

function looksLikeStaleRecoveryRejection(message: string): boolean {
  return [
    "current state:",
    "already has execution data",
    "Only overdue tasks",
    "Cannot mark a voided task done",
    "Task not found",
  ].some((needle) => message.includes(needle));
}

interface PulseReentryCommandOptions {
  setDismissed: Dispatch<SetStateAction<Set<string>>>;
  setError: Dispatch<SetStateAction<string | null>>;
  setResolving: Dispatch<SetStateAction<PulsePausedReentryCandidate | null>>;
}

export function usePulseReentryCommands({
  setDismissed,
  setError,
  setResolving,
}: PulseReentryCommandOptions) {
  const qc = useQueryClient();

  const refresh = () => {
    void invalidatePulseReentryCaches(qc);
  };

  const resumeM = useMutation({
    mutationFn: (candidate: PulsePausedReentryCandidate) =>
      candidate.action === "switch_paused"
        ? switchStopwatch(candidate.taskId)
        : resumeStopwatch(),
    onSuccess: () => {
      setError(null);
      refresh();
    },
    onError: (e: Error) => setError(e.message ?? "Failed to resume"),
  });

  const resolveM = useMutation({
    mutationFn: ({
      candidate,
      rating,
      completionPct,
      scopeOutcome,
    }: {
      candidate: PulsePausedReentryCandidate;
      rating: number;
      completionPct: number;
      scopeOutcome: ScopeOutcome;
    }) =>
      resolveStalePause(candidate.sessionId, {
        post_task_reflection: rating,
        task_completion_percentage: completionPct,
        scope_outcome: scopeOutcome,
      }),
    onSuccess: (_data, vars) => {
      setError(null);
      setResolving(null);
      setDismissed((prev) => {
        const next = new Set(prev);
        next.add(vars.candidate.id);
        return next;
      });
      refresh();
    },
    onError: (e: Error) => setError(e.message ?? "Failed to resolve session"),
  });

  const doneM = useMutation({
    mutationFn: (taskId: TaskRow["task_id"]) => markDone(taskId),
    onSuccess: (_data, taskId) => {
      setError(null);
      setDismissed((prev) => {
        const next = new Set(prev);
        next.add(`missed:${taskId}`);
        return next;
      });
      refresh();
    },
    onError: (e: Error, taskId) => {
      const message = e.message ?? "Failed to mark done";
      if (looksLikeStaleRecoveryRejection(message)) {
        setDismissed((prev) => {
          const next = new Set(prev);
          next.add(`missed:${taskId}`);
          return next;
        });
        setError(null);
        refresh();
        return;
      }
      setError(message);
    },
  });

  const dropM = useMutation({
    mutationFn: (taskId: TaskRow["task_id"]) =>
      markAbandoned(taskId, "reentry_recovery_drop_from_pulse"),
    onSuccess: (_data, taskId) => {
      setError(null);
      setDismissed((prev) => {
        const next = new Set(prev);
        next.add(`missed:${taskId}`);
        return next;
      });
      refresh();
    },
    onError: (e: Error) => setError(e.message ?? "Failed to drop from plan"),
  });

  return {
    resumeM,
    resolveM,
    doneM,
    dropM,
  };
}
