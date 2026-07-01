"use client";

import Link from "next/link";
import { useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Check, Clock, ExternalLink, RotateCcw, X } from "lucide-react";
import { ReflectionModal } from "@/components/reflection-modal";
import {
  getStopwatchStatus,
  markAbandoned,
  markDone,
  resolveStalePause,
  resumeStopwatch,
  type ScopeOutcome,
  switchStopwatch,
  type StopwatchStatus,
  type TaskRow,
} from "@/lib/tasks";
import { invalidatePulseReentryCaches, queryKeys } from "@/lib/query-keys";

interface PulseReentryQueueProps {
  tasks: TaskRow[];
}

type ReentryCandidate =
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
      canMarkDone: boolean;
      canDrop: boolean;
      priority: number;
    };

function localDateKeyFromIso(iso: string | null | undefined): string {
  const d = iso ? new Date(iso) : new Date();
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
}

function todayKey(): string {
  return localDateKeyFromIso(new Date().toISOString());
}

function formatMinutes(minutes: number | null | undefined): string {
  const rounded = Math.max(0, Math.round(minutes ?? 0));
  if (rounded >= 60) {
    const h = Math.floor(rounded / 60);
    const m = rounded % 60;
    return `${h}h${m ? ` ${m}m` : ""}`;
  }
  return `${rounded}m`;
}

const STALE_PAUSE_THRESHOLD_MINUTES = 72 * 60;

function pausedAgeDetail(pausedMinutes: number): string {
  if (pausedMinutes >= STALE_PAUSE_THRESHOLD_MINUTES) {
    return `Parked for ${formatMinutes(pausedMinutes)}. Resolve what happened.`;
  }
  if (pausedMinutes >= 24 * 60) {
    return `Open thread from earlier. Parked for ${formatMinutes(pausedMinutes)}.`;
  }
  if (pausedMinutes >= 2 * 60) {
    return `Parked for ${formatMinutes(pausedMinutes)}. Pick up, reschedule, or leave parked.`;
  }
  return `Paused for ${formatMinutes(pausedMinutes)}. Pick it back up?`;
}

function missedDetail(task: TaskRow): string {
  const planned = task.planned_duration_minutes
    ? `${task.planned_duration_minutes}m block`
    : "planned block";
  const bound = task.deadline_title ? ` linked to ${task.deadline_title}` : "";
  return `${planned}${bound} passed without an active session.`;
}

function looksLikeStaleRecoveryRejection(message: string): boolean {
  return [
    "current state:",
    "already has execution data",
    "Only overdue tasks",
    "Cannot mark a voided task done",
    "Task not found",
  ].some((needle) => message.includes(needle));
}

function buildCandidates(
  tasks: TaskRow[],
  status: StopwatchStatus | undefined,
  dismissed: Set<string>
): ReentryCandidate[] {
  const now = Date.now();
  const candidates: ReentryCandidate[] = [];

  if (status?.active && status.paused && status.task_id && status.task_title) {
    const pausedMinutes = Math.max(0, (status.current_pause_seconds ?? 0) / 60);
    const dateHref = `/today?date=${todayKey()}`;
    const id = `paused:${status.task_id}`;
    if (!dismissed.has(id)) {
      candidates.push({
        kind: "paused",
        id,
        title: status.task_title,
        taskId: status.task_id,
        sessionId: status.session_id ?? "",
        activeMinutes: status.elapsed_minutes ?? 0,
        plannedMinutes: status.planned_duration_minutes ?? null,
        pausedMinutes,
        detail: pausedAgeDetail(pausedMinutes),
        dateHref,
        action:
          pausedMinutes >= STALE_PAUSE_THRESHOLD_MINUTES
            ? "resolve_stale"
            : "resume_current",
        priority: 0,
      });
    }
  }

  for (const paused of status?.paused_others ?? []) {
    const id = `paused:${paused.task_id}`;
    if (dismissed.has(id)) continue;
    candidates.push({
      kind: "paused",
      id,
      title: paused.title,
      taskId: paused.task_id,
      sessionId: paused.session_id,
      activeMinutes: paused.elapsed_minutes ?? 0,
      plannedMinutes: paused.planned_duration_minutes ?? null,
      pausedMinutes: paused.paused_minutes,
      detail: pausedAgeDetail(paused.paused_minutes),
      dateHref: `/today?date=${todayKey()}`,
      action:
        paused.paused_minutes >= STALE_PAUSE_THRESHOLD_MINUTES
          ? "resolve_stale"
          : "switch_paused",
      priority: 2 + paused.paused_minutes / 10_000,
    });
  }

  for (const task of tasks) {
    if (task.voided_at || task.state === "DELETED") continue;
    const endMs = task.end ? new Date(task.end).getTime() : null;
    const autoSkipped =
      task.state === "SKIPPED" &&
      (task.initiation_status === "abandoned" ||
        task.initiation_status === "auto_abandoned") &&
      task.executed_duration_minutes == null;
    const overduePlanned =
      task.state === "PLANNED" && endMs !== null && endMs < now;
    if (!autoSkipped && !overduePlanned) continue;

    const id = `missed:${task.task_id}`;
    if (dismissed.has(id)) continue;
    const startMs = task.start ? new Date(task.start).getTime() : endMs ?? 0;
    candidates.push({
      kind: "missed",
      id,
      title: task.title,
      taskId: task.task_id,
      detail: missedDetail(task),
      dateHref: `/today?date=${localDateKeyFromIso(task.start ?? task.end)}`,
      canMarkDone: !!endMs && endMs < now,
      canDrop: overduePlanned,
      priority: autoSkipped ? 20 - startMs / 1_000_000_000_000 : 10 - startMs / 1_000_000_000_000,
    });
  }

  return candidates
    .sort((a, b) => a.priority - b.priority)
    .slice(0, 3);
}

export function PulseReentryQueue({ tasks }: PulseReentryQueueProps) {
  const qc = useQueryClient();
  const [dismissed, setDismissed] = useState<Set<string>>(new Set());
  const [error, setError] = useState<string | null>(null);
  const [resolving, setResolving] =
    useState<Extract<ReentryCandidate, { kind: "paused" }> | null>(null);

  const statusQ = useQuery<StopwatchStatus>({
    queryKey: queryKeys.stopwatchStatus,
    queryFn: getStopwatchStatus,
    refetchInterval: 10_000,
    refetchOnWindowFocus: true,
  });

  const candidates = useMemo(
    () => buildCandidates(tasks, statusQ.data, dismissed),
    [tasks, statusQ.data, dismissed]
  );

  const refresh = () => {
    void invalidatePulseReentryCaches(qc);
  };

  const resumeM = useMutation({
    mutationFn: (candidate: Extract<ReentryCandidate, { kind: "paused" }>) =>
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
      candidate: Extract<ReentryCandidate, { kind: "paused" }>;
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
    mutationFn: (taskId: string) => markDone(taskId),
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
    mutationFn: (taskId: string) =>
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

  if (candidates.length === 0) {
    return null;
  }

  return (
    <section
      aria-label="Re-entry queue"
      className="terminal-panel border-signal/25 bg-signal/[0.025] px-4 py-3"
    >
      <div className="mb-2 flex items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          <RotateCcw className="h-3.5 w-3.5 text-signal" />
          <div className="font-display text-[10px] font-medium uppercase tracking-macro text-dust">
            <span className="opacity-50">[ </span>
            Re-entry
            <span className="opacity-50"> ]</span>
          </div>
        </div>
        <Link
          href="/today"
          className="font-mono text-[10px] uppercase tracking-widest text-dust-deep transition-colors hover:text-signal"
        >
          Today →
        </Link>
      </div>

      <div className="grid gap-2 lg:grid-cols-3">
        {candidates.map((candidate) => (
          <div
            key={candidate.id}
            className="rounded-sm border border-hairline bg-void/45 px-3 py-2"
          >
            <div className="mb-1.5 flex items-start justify-between gap-2">
              <div className="min-w-0">
                <div className="flex items-center gap-1.5 font-mono text-[9px] uppercase tracking-widest text-signal">
                  <Clock className="h-3 w-3" />
                  {candidate.kind === "paused" ? "Paused work" : "Missed plan"}
                </div>
                <div className="mt-0.5 truncate text-[13px] font-medium text-parchment">
                  {candidate.title}
                </div>
              </div>
              <button
                type="button"
                aria-label="Hide re-entry item"
                className="shrink-0 text-dust-deep transition-colors hover:text-parchment"
                onClick={() =>
                  setDismissed((prev) => {
                    const next = new Set(prev);
                    next.add(candidate.id);
                    return next;
                  })
                }
              >
                <X className="h-3.5 w-3.5" />
              </button>
            </div>
            <p className="min-h-[32px] text-[11px] leading-snug text-dust">
              {candidate.detail}
            </p>
            <div className="mt-2 flex flex-wrap gap-1.5">
              {candidate.kind === "paused" ? (
                <button
                  type="button"
                  disabled={resumeM.isPending || resolveM.isPending}
                  onClick={() =>
                    candidate.action === "resolve_stale"
                      ? setResolving(candidate)
                      : resumeM.mutate(candidate)
                  }
                  className="rounded-sm border border-signal/40 bg-signal/10 px-2 py-1 font-mono text-[10px] uppercase tracking-widest text-signal transition-colors hover:bg-signal/20 disabled:opacity-50"
                >
                  {candidate.action === "resolve_stale"
                    ? "Resolve session"
                    : "Pick it back up"}
                </button>
              ) : (
                <>
                  {candidate.canMarkDone && (
                    <button
                      type="button"
                      disabled={doneM.isPending}
                      onClick={() => doneM.mutate(candidate.taskId)}
                      className="inline-flex items-center gap-1 rounded-sm border border-signal/35 bg-signal/10 px-2 py-1 font-mono text-[10px] uppercase tracking-widest text-signal transition-colors hover:bg-signal/20 disabled:opacity-50"
                    >
                      <Check className="h-3 w-3" />
                      Done
                    </button>
                  )}
                  {candidate.canDrop ? (
                    <button
                      type="button"
                      disabled={dropM.isPending}
                      onClick={() => dropM.mutate(candidate.taskId)}
                      className="rounded-sm border border-hairline bg-void-2/50 px-2 py-1 font-mono text-[10px] uppercase tracking-widest text-dust transition-colors hover:border-ember/40 hover:text-ember disabled:opacity-50"
                    >
                      Drop
                    </button>
                  ) : (
                    <button
                      type="button"
                      onClick={() =>
                        setDismissed((prev) => {
                          const next = new Set(prev);
                          next.add(candidate.id);
                          return next;
                        })
                      }
                      className="rounded-sm border border-hairline bg-void-2/50 px-2 py-1 font-mono text-[10px] uppercase tracking-widest text-dust transition-colors hover:border-signal/35 hover:text-parchment"
                    >
                      Hide
                    </button>
                  )}
                </>
              )}
              <Link
                href={candidate.dateHref}
                className="inline-flex items-center gap-1 rounded-sm border border-hairline bg-void-2/50 px-2 py-1 font-mono text-[10px] uppercase tracking-widest text-dust transition-colors hover:border-signal/35 hover:text-parchment"
              >
                Open
                <ExternalLink className="h-3 w-3" />
              </Link>
            </div>
          </div>
        ))}
      </div>
      {error && (
        <button
          type="button"
          onClick={() => setError(null)}
          className="mt-2 w-full rounded-sm border border-ember/40 bg-ember/5 px-3 py-1.5 text-left text-[11px] text-ember"
        >
          {error} <span className="text-ember/60">· tap to dismiss</span>
        </button>
      )}
      {resolving && (
        <ReflectionModal
          open
          taskTitle={resolving.title}
          completionRequired
          scopeRequired
          confirmLabel="Resolve session"
          description={
            <>
              Resolve parked session for{" "}
              <span className="text-parchment">{resolving.title}</span>.
            </>
          }
          contextNote={
            <div className="space-y-1">
              <div>Active work: {formatMinutes(resolving.activeMinutes)}.</div>
              <div>
                Planned:{" "}
                {resolving.plannedMinutes
                  ? formatMinutes(resolving.plannedMinutes)
                  : "not recorded"}.
              </div>
              <div>Paused: {formatMinutes(resolving.pausedMinutes)}.</div>
              <div>Lyra will close the session at the time you paused it.</div>
            </div>
          }
          onCancel={() => setResolving(null)}
          onConfirm={async (rating, opts) => {
            if (
              opts?.completionPct === undefined ||
              opts?.scopeOutcome === undefined
            ) {
              setError("Completion and scope are required to resolve this session.");
              return;
            }
            await resolveM.mutateAsync({
              candidate: resolving,
              rating,
              completionPct: opts.completionPct,
              scopeOutcome: opts.scopeOutcome,
            });
          }}
        />
      )}
    </section>
  );
}
