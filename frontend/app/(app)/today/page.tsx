"use client";
import { Suspense, useCallback, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useSearchParams, useRouter } from "next/navigation";
import { format, addDays, subDays, isSameDay } from "date-fns";
import { Plus, ChevronLeft, ChevronRight } from "lucide-react";
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
import { Toast } from "@/components/toast";

interface ToastEntry {
  id: string;
  message: string;
  viewId: string | null;
  lifespan: "auto" | "pin";
}

function localDateKey(d: Date) {
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
}

function parseDate(s: string): Date {
  const [y, m, d] = s.split("-").map(Number);
  return new Date(y, m - 1, d);
}

/** Inner component that reads search params (requires Suspense boundary). */
function TodayInner() {
  const qc = useQueryClient();
  const router = useRouter();
  const searchParams = useSearchParams();
  const now = useCurrentTime();
  const today = localDateKey(now);

  // Viewed date: from URL ?date= or default to today
  const dateParam = searchParams.get("date");
  const viewedDate = dateParam && /^\d{4}-\d{2}-\d{2}$/.test(dateParam) ? dateParam : today;
  const viewedDateObj = parseDate(viewedDate);
  const isToday = viewedDate === today;
  const isPast = viewedDateObj < parseDate(today) && !isToday;

  function navigateTo(dateStr: string) {
    const params = new URLSearchParams(searchParams.toString());
    if (dateStr === today) {
      params.delete("date");
    } else {
      params.set("date", dateStr);
    }
    const qs = params.toString();
    router.push(qs ? `/today?${qs}` : "/today");
  }

  const tasksQ = useQuery({
    queryKey: ["tasks", viewedDate],
    queryFn: () => queryTasks(viewedDate),
  });
  const statusQ = useQuery({
    queryKey: ["stopwatch-status"],
    queryFn: getStopwatchStatus,
  });

  const nextDateStr = localDateKey(addDays(viewedDateObj, 1));

  // Next-day gate: always allowed UNLESS viewing today and tomorrow has no planned tasks.
  // Use a separate query key prefix to avoid collisions with the main tasks query.
  const tomorrowQ = useQuery({
    queryKey: ["next-day-check", nextDateStr],
    queryFn: () => queryTasks(nextDateStr),
    enabled: isToday,
    staleTime: 60_000,
  });
  const nextDayBlocked = isToday && tomorrowQ.isFetched &&
    !tomorrowQ.data?.some((t) => t.state === "PLANNED" && !t.voided_at);

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
  const [toasts, setToasts] = useState<ToastEntry[]>([]);

  const removeToast = useCallback((id: string) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  }, []);

  function pushToast(message: string, viewId: string | null, lifespan: "auto" | "pin") {
    const id =
      typeof crypto !== "undefined" && "randomUUID" in crypto
        ? crypto.randomUUID()
        : `toast-${Date.now()}-${Math.random().toString(36).slice(2)}`;
    setToasts((prev) => [...prev, { id, message, viewId, lifespan }]);
  }

  const refresh = () => {
    qc.invalidateQueries({ queryKey: ["tasks", viewedDate] });
    qc.invalidateQueries({ queryKey: ["tasks", nextDateStr] });
    qc.invalidateQueries({ queryKey: ["stopwatch-status"] });
  };

  const status = statusQ.data;
  const activeTaskId = status?.active ? status.task_id : undefined;
  const timerBusy = !!status?.active;

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
        return;
      }
      setReflectionOpen(false);
      setEarlyStop(null);
      if (res.paused_parent) {
        setInfoMsg(
          `${res.paused_parent.title} is still paused (${res.paused_parent.paused_minutes} min). Resume when ready.`
        );
      }
      // LYR-098: surface retention signals as toasts per
      // notification_patterns.md §Toast. micro_mirror auto-dismisses
      // in 8s; calibration_nudge is pinned until dismissed since the
      // reference-class summary needs dwell time to read.
      if (res.micro_mirror) {
        pushToast(res.micro_mirror, res.micro_mirror_view_id ?? null, "auto");
      }
      if (res.calibration_nudge) {
        pushToast(res.calibration_nudge, res.calibration_nudge_view_id ?? null, "pin");
      }
      refresh();
    } catch (e: any) {
      setErrorMsg(e?.message ?? "Failed to stop timer");
    }
  }

  function handleInterruptionCreated(taskId: string, taskTitle: string) {
    refresh();
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
      discrepancy_score: null,
      signed_discrepancy: null,
      initiation_delay_minutes: null,
      total_paused_minutes: 0,
      pause_count: 0,
      task_completion_percentage: null,
      voided_reason: null,
      notion_page_id: null,
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

  const prevDateStr = localDateKey(subDays(viewedDateObj, 1));

  return (
    <div>
      <div className="mb-6 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <button
            onClick={() => navigateTo(prevDateStr)}
            className="rounded p-1 text-white/50 hover:bg-white/10 hover:text-white"
            aria-label="Previous day"
          >
            <ChevronLeft className="h-5 w-5" />
          </button>
          <div>
            <h1 className="text-2xl font-semibold">
              {format(viewedDateObj, "EEEE, MMMM d")}
            </h1>
            {!isToday && (
              <button
                onClick={() => navigateTo(today)}
                className="text-xs text-blue-400 hover:text-blue-300"
              >
                Back to today
              </button>
            )}
          </div>
          <button
            onClick={() => !nextDayBlocked && navigateTo(nextDateStr)}
            disabled={nextDayBlocked}
            className={`rounded p-1 ${
              !nextDayBlocked
                ? "text-white/50 hover:bg-white/10 hover:text-white"
                : "cursor-not-allowed text-white/15"
            }`}
            aria-label={!nextDayBlocked ? "Next day" : "No tasks planned tomorrow"}
            title={!nextDayBlocked ? "Next day" : "No tasks planned tomorrow"}
          >
            <ChevronRight className="h-5 w-5" />
          </button>
        </div>
        <Button onClick={() => setNewTaskOpen(true)}>
          <Plus className="mr-1 h-4 w-4" />
          New task
        </Button>
      </div>

      {/* Active timer banner: always visible regardless of viewed date */}
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
        <div className="text-sm text-white/50">Loading tasks…</div>
      )}

      {tasksQ.data && tasksQ.data.length === 0 && (
        <div className="rounded-lg border border-dashed border-white/10 p-10 text-center text-sm text-white/50">
          {isPast ? "No tasks recorded for this day." : "Nothing scheduled yet. Create your first task."}
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
              disableStart={isPast || (timerBusy && t.task_id !== activeTaskId)}
              onStart={(task) => setReadinessFor(task)}
              onStop={() => setReflectionOpen(true)}
              onSkip={isPast ? undefined : handleSkip}
              onDelete={isPast ? undefined : handleDelete}
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

      {/* LYR-098 toast stack — bottom-right, fixed, pointer-events-none
          container so clicks fall through except on the toast surfaces
          themselves (which re-enable pointer events). */}
      <div className="pointer-events-none fixed bottom-4 right-4 z-50 flex flex-col gap-2">
        {toasts.map((t) => (
          <Toast
            key={t.id}
            id={t.id}
            message={t.message}
            viewId={t.viewId}
            lifespan={t.lifespan}
            onDismiss={removeToast}
          />
        ))}
      </div>
    </div>
  );
}

/** Page wrapper with Suspense boundary for useSearchParams. */
export default function TodayPage() {
  return (
    <Suspense fallback={<div className="text-sm text-white/50">Loading…</div>}>
      <TodayInner />
    </Suspense>
  );
}
