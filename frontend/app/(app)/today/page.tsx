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
  type StopwatchStatus,
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
  // Orphan warning: shown inside ActiveTimerBanner when the user
  // hovers/clicks a Start button on another task while paused. Dismiss
  // persists for the session (one dismissal = no more nagging).
  const [orphanWarnShown, setOrphanWarnShown] = useState(false);
  const [orphanWarnDismissed, setOrphanWarnDismissed] = useState(false);

  const removeToast = useCallback((id: string) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  }, []);

  const dismissOrphanWarn = useCallback(() => {
    setOrphanWarnDismissed(true);
    setOrphanWarnShown(false);
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
  // Apr 16 fix: exclude paused from "busy" so users can start another
  // task while their current one is paused. The backend's interruption
  // flow handles the handoff (clears Redis for the parent, sets
  // parent_task_id on the child). Phase 5 will replace the implicit
  // interruption with an explicit modal (see dogfood: Cannot start new
  // task while another is paused — Phase 5 design refinement).
  const timerBusy = !!status?.active && !status?.paused;

  const notifyPotentialStart = useCallback(() => {
    // Fires on hover/focus/click of a non-active task's Start button.
    // Only meaningful when a paused timer is present; otherwise the
    // start will be a clean start. Dismissed-by-user → no-op.
    if (status?.paused && !orphanWarnDismissed) {
      setOrphanWarnShown(true);
    }
  }, [status?.paused, orphanWarnDismissed]);

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
    // Optimistic flip — the API call is ~1.5s over the Supabase pooler,
    // so close the readiness modal and flip status immediately. Snapshot
    // for rollback if the server rejects (e.g., task already EXECUTING
    // in another tab). Mirrors the cancelQueries pattern in
    // active-timer-banner.tsx §applyPause.
    await qc.cancelQueries({ queryKey: ["stopwatch-status"] });
    const snapshot = qc.getQueryData<StopwatchStatus>(["stopwatch-status"]);
    qc.setQueryData<StopwatchStatus>(["stopwatch-status"], {
      active: true,
      task_id: task.task_id,
      task_title: task.title,
      paused: false,
      start_time: new Date().toISOString(),
      elapsed_minutes: 0,
      planned_duration_minutes: task.planned_duration_minutes ?? 0,
      total_paused_minutes: 0,
    });
    // Optimistic task-state flip — the task card flips from "PLANNED" to
    // "EXECUTING" immediately instead of waiting 1.4 s for refresh().
    qc.setQueryData<TaskRowType[]>(["tasks", viewedDate], (old) =>
      old?.map((t) =>
        t.task_id === task.task_id ? { ...t, state: "EXECUTING" } : t
      )
    );
    setReadinessFor(null);
    try {
      await startStopwatch(task.task_id, readiness);
      refresh();
    } catch (e: any) {
      if (snapshot !== undefined) {
        qc.setQueryData(["stopwatch-status"], snapshot);
      }
      qc.setQueryData<TaskRowType[]>(["tasks", viewedDate], (old) =>
        old?.map((t) =>
          t.task_id === task.task_id ? { ...t, state: "PLANNED" } : t
        )
      );
      setErrorMsg(e?.message ?? "Failed to start timer");
    }
  }

  async function handleStop(
    reflection: number,
    opts: { confirmed?: boolean; completionPct?: number } = {}
  ) {
    setErrorMsg(null);
    // Optimistic flip — same cancelQueries pattern as handleStart. Clears
    // the active banner + unlocks Start buttons on sibling tasks instantly.
    // If the backend responds with requires_confirmation (early-stop gate),
    // we roll back so the banner stays visible for the confirmation modal.
    await qc.cancelQueries({ queryKey: ["stopwatch-status"] });
    const snapshot = qc.getQueryData<StopwatchStatus>(["stopwatch-status"]);
    const stoppedTaskId = snapshot?.task_id;
    qc.setQueryData<StopwatchStatus>(["stopwatch-status"], { active: false });
    if (stoppedTaskId) {
      qc.setQueryData<TaskRowType[]>(["tasks", viewedDate], (old) =>
        old?.map((t) =>
          t.task_id === stoppedTaskId ? { ...t, state: "EXECUTED" } : t
        )
      );
    }
    try {
      const res: StopResponse = await stopStopwatch(reflection, {
        confirmed: opts.confirmed,
        task_completion_percentage: opts.completionPct,
      });
      if (res.requires_confirmation) {
        if (snapshot !== undefined) {
          qc.setQueryData(["stopwatch-status"], snapshot);
        }
        if (stoppedTaskId) {
          qc.setQueryData<TaskRowType[]>(["tasks", viewedDate], (old) =>
            old?.map((t) =>
              t.task_id === stoppedTaskId ? { ...t, state: "EXECUTING" } : t
            )
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
      if (snapshot !== undefined) {
        qc.setQueryData(["stopwatch-status"], snapshot);
      }
      if (stoppedTaskId) {
        qc.setQueryData<TaskRowType[]>(["tasks", viewedDate], (old) =>
          old?.map((t) =>
            t.task_id === stoppedTaskId ? { ...t, state: "EXECUTING" } : t
          )
        );
      }
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
      {status && (
        <ActiveTimerBanner
          status={status}
          showOrphanWarning={orphanWarnShown}
          onDismissOrphanWarning={dismissOrphanWarn}
        />
      )}

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
              onStartHover={
                t.task_id !== activeTaskId ? notifyPotentialStart : undefined
              }
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
