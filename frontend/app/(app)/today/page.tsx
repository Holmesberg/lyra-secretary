"use client";
import { useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { format } from "date-fns";
import { Plus } from "lucide-react";
import {
  queryTasks,
  getStopwatchStatus,
  startStopwatch,
  stopStopwatch,
  markAbandoned,
  deleteTask,
  voidTask,
  type TaskRow as TaskRowType,
  type StopResponse,
} from "@/lib/tasks";
import { useCurrentTime } from "@/lib/hooks/use-current-time";
import { Button } from "@/components/ui/button";
import { TaskRow } from "@/components/task-row";
import { ActiveTimerBanner } from "@/components/active-timer-banner";
import { ReadinessModal } from "@/components/readiness-modal";
import { ReflectionModal } from "@/components/reflection-modal";
import { NewTaskModal } from "@/components/new-task-modal";
import { SelectionActionBar } from "@/components/selection-action-bar";
import { VoidModal } from "@/components/void-modal";

function localDateKey(d: Date) {
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
}

export default function TodayPage() {
  const qc = useQueryClient();
  const now = useCurrentTime();
  const date = localDateKey(now);

  const tasksQ = useQuery({
    queryKey: ["tasks", date],
    queryFn: () => queryTasks(date),
  });
  const statusQ = useQuery({
    queryKey: ["stopwatch-status"],
    queryFn: getStopwatchStatus,
  });

  const [newTaskOpen, setNewTaskOpen] = useState(false);
  const [readinessFor, setReadinessFor] = useState<TaskRowType | null>(null);
  const [reflectionOpen, setReflectionOpen] = useState(false);
  const [earlyStop, setEarlyStop] = useState<{
    elapsed: number;
    planned: number;
    message: string;
  } | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [infoMsg, setInfoMsg] = useState<string | null>(null);
  const [editingTask, setEditingTask] = useState<TaskRowType | null>(null);
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [voidModalOpen, setVoidModalOpen] = useState(false);

  const refresh = () => {
    qc.invalidateQueries({ queryKey: ["tasks", date] });
    qc.invalidateQueries({ queryKey: ["stopwatch-status"] });
  };

  const status = statusQ.data;
  const activeTaskId = status?.active ? status.task_id : undefined;
  const timerBusy = !!status?.active;

  // Phase 3.2: sort by execution-time axis, not by state group. Key:
  //   EXECUTED  → executed_end  (when it actually finished)
  //   SKIPPED   → executed_end or planned_start
  //   EXECUTING → executed_start or planned_start
  //   PAUSED    → executed_start or planned_start
  //   PLANNED   → planned_start
  // This is Notion-like: planned_start is a placeholder that the real
  // execution time overrides once the task runs. Avoids the visible row
  // reshuffling that my earlier state-grouped sort caused on pause/resume.
  function sortKey(t: TaskRowType): number {
    const parse = (s: string | null) => (s ? new Date(s).getTime() : null);
    const pStart = parse(t.start);
    const eStart = parse(t.executed_start);
    const eEnd = parse(t.executed_end);
    switch (t.state) {
      case "EXECUTED":
        return eEnd ?? eStart ?? pStart ?? 0;
      case "SKIPPED":
        return eEnd ?? pStart ?? 0;
      case "EXECUTING":
      case "PAUSED":
        return eStart ?? pStart ?? 0;
      case "PLANNED":
      default:
        return pStart ?? 0;
    }
  }
  // PLANNED rows sort ascending (next-up first, earliest at top) so the
  // operator's attention anchors to the task they should start next.
  // Everything else stays descending (most-recently-touched first)
  // because for EXECUTED/SKIPPED the relevant question is "what did I
  // just finish," not "what's the oldest thing on record." Partition
  // rather than one mixed comparator — mixed comparators aren't
  // transitive when a stale PLANNED row has a past planned_start.
  const sortedTasks = tasksQ.data
    ? (() => {
        const visible = tasksQ.data.filter((t) => !t.voided_at);
        const planned = visible
          .filter((t) => t.state === "PLANNED")
          .sort((a, b) => sortKey(a) - sortKey(b));
        const rest = visible
          .filter((t) => t.state !== "PLANNED")
          .sort((a, b) => sortKey(b) - sortKey(a));
        return [...planned, ...rest];
      })()
    : [];

  async function handleStart(task: TaskRowType, readiness: number) {
    setErrorMsg(null);
    try {
      await startStopwatch(task.task_id, readiness);
      setReadinessFor(null);
      refresh();
    } catch (e: any) {
      setErrorMsg(e?.message ?? "Failed to start timer");
    }
  }

  async function handleStop(
    reflection: number,
    opts: { confirmed?: boolean; completionPct?: number } = {}
  ) {
    setErrorMsg(null);
    try {
      const res: StopResponse = await stopStopwatch(reflection, {
        confirmed: opts.confirmed,
        task_completion_percentage: opts.completionPct,
      });
      if (res.requires_confirmation) {
        setEarlyStop({
          elapsed: res.duration_minutes,
          planned: res.planned_duration_minutes,
          message: res.confirmation_message ?? "Early stop",
        });
        return; // keep modal open, now in early-stop mode
      }
      setReflectionOpen(false);
      setEarlyStop(null);
      if (res.paused_parent) {
        setInfoMsg(
          `${res.paused_parent.title} is still paused (${res.paused_parent.paused_minutes} min). Resume when ready.`
        );
      }
      refresh();
    } catch (e: any) {
      setErrorMsg(e?.message ?? "Failed to stop timer");
    }
  }

  function handleInterruptionCreated(taskId: string, taskTitle: string) {
    refresh();
    // Open readiness modal for the newly created interruption task.
    // Build a minimal TaskRowType — only task_id and title are used by
    // ReadinessModal and handleStart.
    setReadinessFor({
      task_id: taskId,
      title: taskTitle,
      start: null,
      end: null,
      state: "PLANNED",
      category: null,
      initiation_status: null,
      session_index_in_day: 0,
      pre_task_readiness: null,
      post_task_reflection: null,
      planned_duration_minutes: null,
      executed_duration_minutes: null,
      duration_delta_minutes: null,
      executed_start: null,
      executed_end: null,
      voided_at: null,
    });
  }

  async function handleSkip(task: TaskRowType) {
    const isLive = task.state === "EXECUTING" || task.state === "PAUSED";
    const msg = isLive
      ? "Stop and skip this task? Your progress will be saved as data."
      : "Skip this task?";
    if (!window.confirm(msg)) return;
    setErrorMsg(null);
    try {
      await markAbandoned(task.task_id, isLive ? "abandoned mid-session from Today view" : "user_skipped from Today view");
      refresh();
    } catch (e: any) {
      setErrorMsg(e?.message ?? "Failed to skip task");
    }
  }

  async function handleDelete(task: TaskRowType) {
    if (!window.confirm("Delete this task? Cancelled plans are recorded as a behavioral signal.")) return;
    setErrorMsg(null);
    try {
      await deleteTask(task.task_id);
      refresh();
    } catch (e: any) {
      setErrorMsg(e?.message ?? "Failed to delete task");
    }
  }

  function toggleSelect(taskId: string) {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (next.has(taskId)) next.delete(taskId);
      else next.add(taskId);
      return next;
    });
  }

  function clearSelection() {
    setSelectedIds(new Set());
  }

  async function handleBulkVoid(reason: string, detail?: string) {
    const ids = Array.from(selectedIds);
    await Promise.all(ids.map((id) => voidTask(id, reason, detail)));
    clearSelection();
    setVoidModalOpen(false);
    refresh();
  }

  return (
    <div>
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold">Today</h1>
          <p className="text-xs text-white/50">
            {format(new Date(), "EEEE, MMMM d")}
          </p>
        </div>
        <Button onClick={() => setNewTaskOpen(true)} disabled={timerBusy && false}>
          <Plus className="mr-1 h-4 w-4" />
          New task
        </Button>
      </div>

      {status && <ActiveTimerBanner status={status} />}

      {errorMsg && (
        <div className="mb-4 rounded border border-red-500/30 bg-red-500/10 p-3 text-xs text-red-200">
          {errorMsg}
        </div>
      )}

      {infoMsg && (
        <div className="mb-4 flex items-center justify-between rounded border border-yellow-500/30 bg-yellow-500/10 p-3 text-xs text-yellow-200">
          <span>{infoMsg}</span>
          <button onClick={() => setInfoMsg(null)} className="ml-2 text-white/40 hover:text-white/70">&times;</button>
        </div>
      )}

      {tasksQ.isLoading && (
        <div className="text-sm text-white/50">Loading today's tasks…</div>
      )}

      {tasksQ.data && tasksQ.data.length === 0 && (
        <div className="rounded-lg border border-dashed border-white/10 p-10 text-center text-sm text-white/50">
          Nothing scheduled yet. Create your first task.
        </div>
      )}

      <SelectionActionBar
        count={selectedIds.size}
        onVoid={() => setVoidModalOpen(true)}
        onCancel={clearSelection}
      />

      {sortedTasks.length > 0 && (
        <div className="flex flex-col gap-2">
          {sortedTasks.map((t) => (
            <TaskRow
              key={t.task_id}
              task={t}
              disableStart={timerBusy && t.task_id !== activeTaskId}
              onStart={(task) => setReadinessFor(task)}
              onStop={() => setReflectionOpen(true)}
              onSkip={handleSkip}
              onDelete={handleDelete}
              onEdit={(task) => setEditingTask(task)}
              selected={selectedIds.has(t.task_id)}
              showCheckbox={selectedIds.size > 0}
              onToggleSelect={toggleSelect}
            />
          ))}
        </div>
      )}

      {readinessFor && (
        <ReadinessModal
          open={!!readinessFor}
          taskTitle={readinessFor.title}
          onCancel={() => setReadinessFor(null)}
          onConfirm={(r) => handleStart(readinessFor, r)}
        />
      )}

      <ReflectionModal
        open={reflectionOpen}
        taskTitle={status?.task_title ?? ""}
        earlyStop={earlyStop}
        onCancel={() => {
          setReflectionOpen(false);
          setEarlyStop(null);
        }}
        onConfirm={(r, opts) => handleStop(r, { confirmed: opts?.confirmed, completionPct: opts?.completionPct })}
      />

      <NewTaskModal
        open={newTaskOpen || !!editingTask}
        onClose={() => { setNewTaskOpen(false); setEditingTask(null); }}
        onCreated={refresh}
        onInterruptionCreated={handleInterruptionCreated}
        editingTask={editingTask}
      />

      <VoidModal
        open={voidModalOpen}
        taskCount={selectedIds.size}
        onConfirm={handleBulkVoid}
        onCancel={() => setVoidModalOpen(false)}
      />
    </div>
  );
}
