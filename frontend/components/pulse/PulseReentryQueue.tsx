"use client";

import Link from "next/link";
import { useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Check, Clock, ExternalLink, RotateCcw, X } from "lucide-react";
import {
  getStopwatchStatus,
  markAbandoned,
  markDone,
  resumeStopwatch,
  switchStopwatch,
  type StopwatchStatus,
  type TaskRow,
} from "@/lib/tasks";

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
      dateHref: string;
      action: "resume_current" | "switch_paused";
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

function missedDetail(task: TaskRow): string {
  const planned = task.planned_duration_minutes
    ? `${task.planned_duration_minutes}m block`
    : "planned block";
  const bound = task.deadline_title ? ` linked to ${task.deadline_title}` : "";
  return `${planned}${bound} passed without an active session.`;
}

function buildCandidates(
  tasks: TaskRow[],
  status: StopwatchStatus | undefined,
  dismissed: Set<string>
): ReentryCandidate[] {
  const now = Date.now();
  const candidates: ReentryCandidate[] = [];

  if (status?.active && status.paused && status.task_id && status.task_title) {
    const pausedFor = formatMinutes(
      Math.max(0, (status.current_pause_seconds ?? 0) / 60)
    );
    const dateHref = `/today?date=${todayKey()}`;
    const id = `paused:${status.task_id}`;
    if (!dismissed.has(id)) {
      candidates.push({
        kind: "paused",
        id,
        title: status.task_title,
        taskId: status.task_id,
        detail:
          pausedFor === "0m"
            ? "Paused now. Pick it back up or leave it parked."
            : `Paused for ${pausedFor}. Pick it back up or leave it parked.`,
        dateHref,
        action: "resume_current",
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
      detail: `Parked for ${formatMinutes(paused.paused_minutes)} during an interruption chain.`,
      dateHref: `/today?date=${todayKey()}`,
      action: "switch_paused",
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

  const statusQ = useQuery<StopwatchStatus>({
    queryKey: ["stopwatch-status"],
    queryFn: getStopwatchStatus,
    refetchInterval: 10_000,
    refetchOnWindowFocus: true,
  });

  const candidates = useMemo(
    () => buildCandidates(tasks, statusQ.data, dismissed),
    [tasks, statusQ.data, dismissed]
  );

  const refresh = () => {
    qc.invalidateQueries({ queryKey: ["stopwatch-status"] });
    qc.invalidateQueries({ queryKey: ["tasks"] });
    qc.invalidateQueries({ queryKey: ["tasks-range"] });
    qc.invalidateQueries({ queryKey: ["pressure-map"] });
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

  const doneM = useMutation({
    mutationFn: (taskId: string) => markDone(taskId),
    onSuccess: () => {
      setError(null);
      refresh();
    },
    onError: (e: Error) => setError(e.message ?? "Failed to mark done"),
  });

  const dropM = useMutation({
    mutationFn: (taskId: string) =>
      markAbandoned(taskId, "reentry_recovery_drop_from_pulse"),
    onSuccess: () => {
      setError(null);
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
                  disabled={resumeM.isPending}
                  onClick={() => resumeM.mutate(candidate)}
                  className="rounded-sm border border-signal/40 bg-signal/10 px-2 py-1 font-mono text-[10px] uppercase tracking-widest text-signal transition-colors hover:bg-signal/20 disabled:opacity-50"
                >
                  Pick it back up
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
    </section>
  );
}
