"use client";
import { Suspense, useCallback, useEffect, useRef, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useSearchParams, useRouter } from "next/navigation";
import { format, addDays, subDays, isSameDay } from "date-fns";
import { Plus, ChevronLeft, ChevronRight } from "lucide-react";
import {
  queryTasks,
  getStopwatchStatus,
  markAbandoned,
  markDone,
  deleteTask,
  voidTask,
  type TaskRow as TaskRowType,
  type StopwatchStatus,
} from "@/lib/tasks";
import { useCurrentTime } from "@/lib/hooks/use-current-time";
import {
  useTodayStopwatchCommands,
  type TodayEarlyStopState,
} from "@/lib/hooks/use-today-stopwatch-commands";
import { TaskRow } from "@/components/task-row";
import { ActiveTimerBanner } from "@/components/active-timer-banner";
import { ReadinessModal } from "@/components/readiness-modal";
import { ReflectionModal } from "@/components/reflection-modal";
import { NewTaskModal } from "@/components/new-task-modal";
import { RetroactiveModal } from "@/components/retroactive-modal";
import { ExecutionCorrectionDialog } from "@/components/execution-correction-dialog";
import { SelectionActionBar } from "@/components/selection-action-bar";
import { VoidModal } from "@/components/void-modal";
import { Toast } from "@/components/toast";
import { DeadlineRow } from "@/components/deadline-row";
import { DeadlineModal } from "@/components/deadline-modal";
import { DeadlineBindingDialog } from "@/components/deadline-binding-dialog";
import { listDeadlines, type DeadlineResponse } from "@/lib/deadlines";
import { PauseConfirmChip } from "@/components/pause-confirm-chip";
import { listPendingConfirmations } from "@/lib/pause-predictions";
import { ExternalEventRow } from "@/components/external-event-row";
import {
  getCalendarEvents,
  type ExternalCalendarEvent,
} from "@/lib/calendar";
import { ackExposureRender } from "@/lib/api";
import { announceUndoAvailable } from "@/lib/undo";
import {
  invalidateTodayTaskCommandSurfaces,
  queryKeys,
} from "@/lib/query-keys";
import {
  buildTodayDueDeadlines,
  buildTodayFeed,
  localDateKey,
  parseDateKey,
} from "@/lib/today-feed";
import type { PauseReason } from "@/lib/stopwatch-pause-reasons";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";

interface ToastEntry {
  id: string;
  message: string;
  viewId: string | null;
  exposureId?: string | null;
  surfaceId?: string | null;
  lifespan: "auto" | "pin";
  detailHref?: string;
}

function InterruptionStartDialog({
  open,
  taskTitle,
  activeTaskTitle,
  onCancel,
  onContinue,
}: {
  open: boolean;
  taskTitle: string;
  activeTaskTitle: string;
  onCancel: () => void;
  onContinue: () => void;
}) {
  return (
    <Dialog open={open} onOpenChange={(o) => !o && onCancel()}>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle>Start as interruption?</DialogTitle>
          <DialogDescription>
            This will pause <span className="text-parchment">{activeTaskTitle}</span> and
            start <span className="text-parchment">{taskTitle}</span>. You can resume the
            paused task later.
          </DialogDescription>
        </DialogHeader>
        <DialogFooter>
          <Button variant="ghost" onClick={onCancel}>
            Cancel
          </Button>
          <Button onClick={onContinue}>
            Start as interruption
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
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
  const viewedDateObj = parseDateKey(viewedDate);
  const isToday = viewedDate === today;
  const isPast = viewedDateObj < parseDateKey(today) && !isToday;

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

  // Apr 25 edge-case fix: midnight auto-advance.
  // Operator scenario: user is on /today (URL has explicit ?date=2026-04-25
  // because they navigated to it earlier OR they have a task spanning
  // midnight). At midnight the clock crosses; useCurrentTime's 60s tick
  // recomputes `today` to "2026-04-26" but the URL param keeps `viewedDate`
  // at "2026-04-25". Without this redirect, the user stays staring at
  // "Friday April 25" until they manually click "← back to today."
  //
  // Heuristic: only auto-advance if the URL's date param matched the
  // PREVIOUS "today." If the user is explicitly viewing some past or
  // future date (e.g. an archive day), don't surprise them by yanking
  // the calendar forward.
  const prevTodayRef = useRef(today);
  useEffect(() => {
    const prevToday = prevTodayRef.current;
    if (today !== prevToday && viewedDate === prevToday) {
      // Clock crossed midnight; user was on the day that just stopped
      // being today. Strip the date param so it defaults to the new today.
      navigateTo(today);
    }
    prevTodayRef.current = today;
    // navigateTo is stable enough; deps locked to today/viewedDate so
    // the effect runs whenever either ticks forward.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [today, viewedDate]);

  const tasksDayKey = queryKeys.tasksDay(viewedDate);
  const tasksQ = useQuery({
    queryKey: tasksDayKey,
    queryFn: () => queryTasks(viewedDate),
    // 2026-05-08 latency pass: /today remounts and quick nav were paying a
    // fresh tunnel round-trip for task data even when the cache was seconds
    // old. Mutations below still invalidate/refetch explicitly, so this only
    // suppresses redundant mount/focus fetches.
    staleTime: 5_000,
  });
  const statusQ = useQuery({
    queryKey: queryKeys.stopwatchStatus,
    queryFn: getStopwatchStatus,
  });

  const nextDateStr = localDateKey(addDays(viewedDateObj, 1));
  // Forward-nav is always enabled — the operator can open any future day
  // and plan tasks there. (Previously gated on whether tomorrow had any
  // PLANNED tasks, which made cold-start forward navigation impossible.)

  // External calendar events for the viewed day (Path B 2026-04-21).
  // Mirrors /calendar's fetch with a tighter window — just the one day
  // the user is looking at. 60s staleTime + refetchInterval keeps
  // "adding an event in Google Calendar → it appears here" near-instant.
  // Query key scoped to `viewedDate` so navigating days invalidates.
  const calEventsQ = useQuery({
    queryKey: queryKeys.calendarEventsToday(viewedDate),
    queryFn: () =>
      getCalendarEvents({
        dateFrom: viewedDate,
        dateTo: nextDateStr,
      }),
    staleTime: 60_000,
    refetchInterval: 60_000,
  });

  // Loop 11 follow-up: deadlines render on the day they're due, not as
  // a generic "upcoming" strip. Filter applied client-side because the
  // backend list endpoint accepts only one state filter and we want
  // {planned, active} together. Two inclusion rules:
  //   1. due_at_utc (browser-local) date matches viewedDate
  //   2. when viewedDate === today, ALSO include overdue planned/active
  //      deadlines (state ∈ {planned, active}, due < now) — pinned to
  //      today so the operator notices and marks complete or skips.
  const deadlinesQ = useQuery({
    queryKey: queryKeys.deadlines,
    queryFn: () => listDeadlines(),
    staleTime: 60_000,
  });

  const [editingDeadline, setEditingDeadline] = useState<DeadlineResponse | null>(null);

  // Retroactive pause-confirmation chips. Backend applies all three
  // gates: user_response='no_response', fired_at within 24h, no
  // pause_event within ±10 min of predicted_at. We just render what
  // it returns, tracking local dismiss state for the session.
  const pauseConfirmQ = useQuery({
    queryKey: queryKeys.pausePredictionsPendingConfirmation,
    queryFn: listPendingConfirmations,
    staleTime: 10_000,
    refetchInterval: 120_000,
  });
  const [dismissedConfirms, setDismissedConfirms] = useState<Set<string>>(new Set());

  // Partition firings into task-attached (rendered inline after
  // matching TaskRow) and standalone (no active_task_id OR task not
  // visible in current feed — rendered as a small banner above the
  // feed).
  const visibleTaskIds = new Set(
    (tasksQ.data ?? []).filter((t) => !t.voided_at).map((t) => t.task_id)
  );
  type PendingList = NonNullable<typeof pauseConfirmQ.data>["pending"];
  const pendingByTask = new Map<string, PendingList>();
  const pendingStandalone: PendingList = [];
  for (const p of pauseConfirmQ.data?.pending ?? []) {
    if (dismissedConfirms.has(p.firing_id)) continue;
    if (p.active_task_id && visibleTaskIds.has(p.active_task_id)) {
      const list = pendingByTask.get(p.active_task_id) ?? [];
      list.push(p);
      pendingByTask.set(p.active_task_id, list);
    } else {
      pendingStandalone.push(p);
    }
  }

  function onConfirmResolved(firingId: string) {
    setDismissedConfirms((s) => {
      const n = new Set(s);
      n.add(firingId);
      return n;
    });
    // Refetch so if the server still has other pending firings we
    // haven't interacted with, they stay in sync.
    qc.invalidateQueries({
      queryKey: queryKeys.pausePredictionsPendingConfirmation,
    });
  }
  const [newTaskOpen, setNewTaskOpen] = useState(false);
  const [retroOpen, setRetroOpen] = useState(false);
  const [readinessFor, setReadinessFor] = useState<TaskRowType | null>(null);
  const [interruptionStartFor, setInterruptionStartFor] = useState<TaskRowType | null>(null);
  const [readinessInterruptionType, setReadinessInterruptionType] = useState<string | null>(null);
  const [reflectionOpen, setReflectionOpen] = useState(false);
  const [earlyStop, setEarlyStop] = useState<TodayEarlyStopState | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [infoMsg, setInfoMsg] = useState<string | null>(null);
  const [editingTask, setEditingTask] = useState<TaskRowType | null>(null);
  const [correctionTask, setCorrectionTask] = useState<TaskRowType | null>(null);
  const [bindingTask, setBindingTask] = useState<TaskRowType | null>(null);
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [voidModalOpen, setVoidModalOpen] = useState(false);
  const [toasts, setToasts] = useState<ToastEntry[]>([]);
  // Orphan warning: shown inside ActiveTimerBanner when the user
  // hovers/clicks a Start button on another task while paused. Dismiss
  // persists for the session (one dismissal = no more nagging).
  const [orphanWarnShown, setOrphanWarnShown] = useState(false);
  const [orphanWarnDismissed, setOrphanWarnDismissed] = useState(false);
  const [requestPause, setRequestPause] = useState(false);
  // When set, ActiveTimerBanner skips the reason picker on pause and
  // applies this reason directly — one-tap pause from the prediction
  // banner's primary action (2026-04-22). Clears on handled.
  const [quickPauseReason, setQuickPauseReason] = useState<PauseReason | undefined>(undefined);
  const clearRequestPause = useCallback(() => {
    setRequestPause(false);
    setQuickPauseReason(undefined);
  }, []);

  const removeToast = useCallback((id: string) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  }, []);

  const dismissOrphanWarn = useCallback(() => {
    setOrphanWarnDismissed(true);
    setOrphanWarnShown(false);
  }, []);

  const pushToast = useCallback((
    message: string,
    viewId: string | null,
    lifespan: "auto" | "pin",
    detailHref?: string,
    exposureId?: string | null,
    surfaceId?: string | null,
  ) => {
    const id =
      typeof crypto !== "undefined" && "randomUUID" in crypto
        ? crypto.randomUUID()
        : `toast-${Date.now()}-${Math.random().toString(36).slice(2)}`;
    setToasts((prev) => [
      ...prev,
      { id, message, viewId, exposureId, surfaceId, lifespan, detailHref },
    ]);
  }, []);

  const refresh = () => {
    void invalidateTodayTaskCommandSurfaces(qc, viewedDate, nextDateStr);
  };

  const { handleStart, handleStop } = useTodayStopwatchCommands({
    tasksDayKey,
    refresh,
    setErrorMsg,
    setReadinessFor,
    setReadinessInterruptionType,
    setReflectionOpen,
    setEarlyStop,
    setInfoMsg,
    pushToast,
  });

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

  function requestTaskStart(task: TaskRowType) {
    setErrorMsg(null);
    if (timerBusy && activeTaskId && task.task_id !== activeTaskId) {
      setInterruptionStartFor(task);
      return;
    }
    setReadinessInterruptionType(null);
    setReadinessFor(task);
  }

  function continueInterruptionStart() {
    if (!interruptionStartFor) return;
    setReadinessInterruptionType("scheduled_override");
    setReadinessFor(interruptionStartFor);
    setInterruptionStartFor(null);
  }

  function cancelReadiness() {
    setReadinessFor(null);
    setReadinessInterruptionType(null);
  }

  // Unified /today feed — LyraOS tasks + external GCal events interleaved
  // by time while preserving LyraOS's existing two-bucket rhythm:
  //   top  — PLANNED LyraOS tasks + FUTURE/ongoing GCal events, asc by start
  //   bottom — non-PLANNED LyraOS tasks + PAST GCal events, desc by end
  //
  // Past-end GCal events sit alongside EXECUTED/SKIPPED so the operator
  // finds attendance controls where they expect "what-happened" items
  // to live. Future events sit with PLANNED so the day reads
  // chronologically forward.
  //
  // The sort produces a union-typed list the renderer branches on
  // (TaskRow vs ExternalEventRow) — keeps the two row types visually
  // distinct without duplicating the feed.
  const nowMs = now.getTime();
  const gcalEventsAll: ExternalCalendarEvent[] = calEventsQ.data?.events ?? [];

  // Filter deadlines for the viewed day. Browser-local date comparison —
  // matches the operator's mental model (Cairo-local since
  // USER_TIMEZONE=Africa/Cairo and the operator dogfoods from Cairo).
  // Voided deadlines are always excluded; state-based exclusion is left
  // to the badge rendering (so completed deadlines on a past day still
  // show with a "COMPLETED" pill for historical reference).
  const dueDeadlines = buildTodayDueDeadlines({
    deadlines: deadlinesQ.data?.deadlines,
    viewedDate,
    today,
    nowMs,
  });

  // Overdue aggregate for the top banner. Only surfaces on /today (don't
  // pollute past/future-day views with action prompts about today). LMS
  // breakout shows the connected-source sub-count when imported rows
  // are present, without implying one fixed obligation source.
  // call 2026-04-29 evening.
  const overdueDeadlines = isToday
    ? dueDeadlines.filter((x) => x.overdue)
    : [];
  const overdueCount = overdueDeadlines.length;
  const overdueFromLms = overdueDeadlines.filter(
    (x) => x.deadline.external_source?.startsWith("moodle")
  ).length;

  const feed = buildTodayFeed({
    tasks: tasksQ.data,
    events: gcalEventsAll,
    dueDeadlines,
    nowMs,
  });

  function handleInterruptionCreated(taskId: string, taskTitle: string) {
    refresh();
    setReadinessFor({
      task_id: taskId,
      title: taskTitle,
      start: null,
      end: null,
      state: "PLANNED",
      category: null,
      is_anchor: false,
      rct_arm: null,
      initiation_status: null,
      session_index_in_day: 0,
      pre_task_readiness: null,
      post_task_reflection: null,
      planned_duration_minutes: null,
      executed_duration_minutes: null,
      duration_delta_minutes: null,
      executed_start: null,
      executed_end: null,
      effective_executed_duration_minutes: null,
      effective_duration_delta_minutes: null,
      effective_executed_end: null,
      execution_duration_provenance: "observed",
      execution_correction_id: null,
      voided_at: null,
      discrepancy_score: null,
      signed_discrepancy: null,
      initiation_delay_minutes: null,
      total_paused_minutes: 0,
      pause_count: 0,
      task_completion_percentage: null,
      voided_reason: null,
      description: null,
      deadline_id: null,
      deadline_match_source: null,
      deadline_match_confidence: null,
      deadline_title: null,
      llm_parse_status: null,
      llm_inferred_deadline_id: null,
      llm_deadline_match_confidence: null,
      llm_deadline_candidates: null,
      llm_priority: null,
      llm_binding_rejected_at: null,
      llm_alternative_suggestion: null,
    });
  }

  async function handleSkip(task: TaskRowType) {
    const isLive = task.state === "EXECUTING" || task.state === "PAUSED";
    const msg = isLive
      ? "Stop and skip this task? Your progress will be saved as data."
      : "Skip this task?";
    if (!window.confirm(msg)) return;
    setErrorMsg(null);
    await qc.cancelQueries({ queryKey: tasksDayKey });
    await qc.cancelQueries({ queryKey: queryKeys.stopwatchStatus });
    const tasksSnapshot = qc.getQueryData<TaskRowType[]>(tasksDayKey);
    const statusSnapshot = qc.getQueryData<StopwatchStatus>(queryKeys.stopwatchStatus);
    qc.setQueryData<TaskRowType[]>(tasksDayKey, (old) =>
      old?.map((t) => t.task_id === task.task_id ? { ...t, state: "SKIPPED" } : t)
    );
    if (isLive) {
      qc.setQueryData<StopwatchStatus>(queryKeys.stopwatchStatus, { active: false });
    }
    try {
      await markAbandoned(task.task_id, isLive ? "abandoned mid-session from Today view" : "user_skipped from Today view");
      refresh();
    } catch (e: any) {
      if (tasksSnapshot !== undefined) {
        qc.setQueryData(tasksDayKey, tasksSnapshot);
      }
      if (statusSnapshot !== undefined) {
        qc.setQueryData(queryKeys.stopwatchStatus, statusSnapshot);
      }
      setErrorMsg(e?.message ?? "Failed to skip task");
    }
  }

  async function handleDone(task: TaskRowType) {
    setErrorMsg(null);
    await qc.cancelQueries({ queryKey: tasksDayKey });
    const snapshot = qc.getQueryData<TaskRowType[]>(tasksDayKey);
    const executedStart = task.start;
    const executedEnd = task.end;
    const planned = task.planned_duration_minutes;
    qc.setQueryData<TaskRowType[]>(tasksDayKey, (old) =>
      old?.map((t) =>
        t.task_id === task.task_id
          ? {
              ...t,
              state: "EXECUTED",
              initiation_status: "retroactive",
              executed_start: executedStart,
              executed_end: executedEnd,
              executed_duration_minutes: planned,
              duration_delta_minutes: planned != null ? 0 : t.duration_delta_minutes,
              effective_executed_duration_minutes: planned,
              effective_duration_delta_minutes: planned != null ? 0 : t.effective_duration_delta_minutes,
              effective_executed_end: executedEnd,
              execution_duration_provenance: "retroactive",
            }
          : t
      )
    );
    try {
      await markDone(task.task_id);
      refresh();
    } catch (e: any) {
      if (snapshot !== undefined) {
        qc.setQueryData(tasksDayKey, snapshot);
      }
      setErrorMsg(e?.message ?? "Failed to mark task done");
    }
  }

  async function handleDelete(task: TaskRowType) {
    if (!window.confirm("Delete this task? Cancelled plans are recorded as a behavioral signal.")) return;
    setErrorMsg(null);
    qc.setQueryData<TaskRowType[]>(tasksDayKey, (old) =>
      old?.filter((t) => t.task_id !== task.task_id)
    );
    try {
      await deleteTask(task.task_id);
      announceUndoAvailable("Task deleted.");
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
    if (ids.length === 0) return;

    // Apr 26 perf fix: optimistic close + cache update. Operator complaint
    // was "modal closing takes forever" — root cause was awaiting N parallel
    // void network calls (~1s each over Cloudflare Tunnel + Supabase) before
    // closing the modal. Now we close the modal AND fade voided tasks from
    // the list instantly; mutations fire in background; on error we rollback
    // and surface via errorMsg.
    await qc.cancelQueries({ queryKey: tasksDayKey });
    const snapshot = qc.getQueryData<TaskRowType[]>(tasksDayKey);
    const nowIso = new Date().toISOString();
    qc.setQueryData<TaskRowType[]>(tasksDayKey, (old) =>
      Array.isArray(old)
        ? old.map((t) =>
            ids.includes(t.task_id) ? { ...t, voided_at: nowIso } : t
          )
        : old
    );
    clearSelection();
    setVoidModalOpen(false);

    try {
      await Promise.all(ids.map((id) => voidTask(id, reason, detail)));
      qc.invalidateQueries({ queryKey: tasksDayKey });
      qc.invalidateQueries({ queryKey: queryKeys.stopwatchStatus });
    } catch (e) {
      // Rollback the optimistic mutation; surface error.
      if (snapshot !== undefined) {
        qc.setQueryData(tasksDayKey, snapshot);
      }
      setErrorMsg(
        `Void failed: ${e instanceof Error ? e.message : String(e)}`
      );
    }
  }

  const prevDateStr = localDateKey(subDays(viewedDateObj, 1));

  return (
    <div>
      <div className="mb-6 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <button
            onClick={() => navigateTo(prevDateStr)}
            className="rounded p-1 text-dust transition-colors hover:bg-signal/10 hover:text-signal"
            aria-label="Previous day"
          >
            <ChevronLeft className="h-5 w-5" />
          </button>
          <div>
            <h1 className="text-base font-semibold tracking-tight text-parchment sm:text-2xl">
              {format(viewedDateObj, "EEEE, MMMM d")}
            </h1>
            {!isToday && (
              <button
                onClick={() => navigateTo(today)}
                className="font-mono text-[10px] uppercase tracking-widest text-signal transition-colors hover:text-signal-neon"
              >
                ← back to today
              </button>
            )}
          </div>
          <button
            onClick={() => navigateTo(nextDateStr)}
            className="rounded p-1 text-dust transition-colors hover:bg-signal/10 hover:text-signal"
            aria-label="Next day"
            title="Next day"
          >
            <ChevronRight className="h-5 w-5" />
          </button>
        </div>
        <div className="flex flex-col items-end gap-1.5">
          <button
            data-testid="today-new-task"
            onClick={() => setNewTaskOpen(true)}
            className="cyber-pill cyber-pill-compact cyber-pill-primary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-signal/70"
          >
            <Plus className="h-3.5 w-3.5" />
            New task
          </button>
          <button
            data-testid="today-retroactive"
            onClick={() => setRetroOpen(true)}
            className="font-mono text-[10px] uppercase tracking-widest text-dust transition-colors hover:text-parchment"
            title="Log a past session that wasn't tracked live"
          >
            Retroactive ↓
          </button>
        </div>
      </div>

      {/* Active timer banner: always visible regardless of viewed date */}
      {status && (
        <ActiveTimerBanner
          status={status}
          showOrphanWarning={orphanWarnShown}
          onDismissOrphanWarning={dismissOrphanWarn}
          requestPause={requestPause}
          quickPauseReason={quickPauseReason}
          onRequestPauseHandled={clearRequestPause}
          onStop={() => setReflectionOpen(true)}
        />
      )}


      {errorMsg && (
        <div className="mb-4 rounded-sm border border-ember/40 bg-ember/5 p-3 text-xs text-ember">
          {errorMsg}
        </div>
      )}

      {overdueCount > 0 && (
        <div
          role="alert"
          className="terminal-panel-ember alert-bar-ember mb-4 flex items-stretch gap-3 px-3 py-2.5 sm:gap-5 sm:px-5 sm:py-4"
        >
          {/* Hero count — cyber-display digits, neon-ember glow.
              Reads as a system readout, not a counter chip.
              Mobile step-down: 2.75rem → 1.75rem so the alert
              consumes ~50% less vertical real estate on phones. */}
          <div className="flex shrink-0 items-center pl-1 sm:pl-2">
            <span
              aria-hidden
              className="font-display text-[1.75rem] font-semibold leading-none neon-ember tabular-nums sm:text-[2.75rem]"
            >
              {overdueCount.toString().padStart(2, "0")}
            </span>
          </div>
          {/* Vertical separator — anchors the readout structure. */}
          <div
            aria-hidden
            className="my-1 w-px shrink-0 bg-gradient-to-b from-transparent via-ember/40 to-transparent"
          />
          {/* Copy stack — bracketed eyebrow + warm body line. */}
          <div className="flex min-w-0 flex-1 flex-col justify-center gap-1.5">
            <p className="font-display text-[11px] font-medium uppercase tracking-macro text-ember">
              <span className="opacity-50">[ </span>
              {overdueCount === 1 ? "Overdue obligation" : "Overdue obligations"}
              <span className="opacity-50"> ]</span>
            </p>
            <p className="text-xs text-ember/85">
              {overdueFromLms > 0
                ? `${overdueFromLms} from connected sources${
                    overdueFromLms < overdueCount
                      ? `, ${overdueCount - overdueFromLms} other`
                      : ""
                  } — handle these first.`
                : "Past due — handle these first."}
            </p>
          </div>
        </div>
      )}

      {infoMsg && (
        <div className="mb-4 flex items-center justify-between rounded-sm border border-signal/40 bg-signal/5 p-3 text-xs text-signal">
          <span>{infoMsg}</span>
          <button
            onClick={() => setInfoMsg(null)}
            className="ml-2 text-dust-deep transition-colors hover:text-parchment"
          >
            &times;
          </button>
        </div>
      )}

      {tasksQ.isLoading && (
        <div className="text-sm text-dust">Loading tasks…</div>
      )}

      {tasksQ.data && tasksQ.data.length === 0 && dueDeadlines.length === 0 && (
        <div className="rounded-sm border border-dashed border-hairline p-10 text-center text-sm text-dust">
          {isPast ? "Nothing logged on this day." : "Nothing on the day yet. Add the first thing on your mind."}
        </div>
      )}

      <SelectionActionBar
        count={selectedIds.size}
        onVoid={() => setVoidModalOpen(true)}
        onCancel={clearSelection}
      />

      {/* Standalone pause-confirm chips — firings without a task in
          the current feed render here above the task list. */}
      {pendingStandalone.map((p) => (
        <PauseConfirmChip
          key={p.firing_id}
          prediction={p}
          variant="standalone"
          onResolved={onConfirmResolved}
        />
      ))}

      {(feed.top.length > 0 || feed.bottom.length > 0) && (
        <div className="flex flex-col gap-2">
          {[...feed.top, ...feed.bottom].map((item) =>
            item.kind === "task" ? (
              <div key={item.task.task_id} className="flex flex-col gap-1.5">
                <TaskRow
                  task={item.task}
                  disableStart={isPast}
                  startAsInterruption={timerBusy && item.task.task_id !== activeTaskId}
                  onStart={requestTaskStart}
                  onStartHover={
                    item.task.task_id !== activeTaskId
                      ? notifyPotentialStart
                      : undefined
                  }
                  onStop={() => setReflectionOpen(true)}
                  // Live rows must stay skippable even when the operator is
                  // viewing a past planned day. This is the crossed-circle
                  // PAUSED/EXECUTING recovery path; disabling it leaves a
                  // paused task trapped behind date navigation.
                  onSkip={
                    isPast &&
                    item.task.state !== "EXECUTING" &&
                    item.task.state !== "PAUSED"
                      ? undefined
                      : handleSkip
                  }
                  onDone={handleDone}
                  onDelete={isPast ? undefined : handleDelete}
                  onEdit={(task) => {
                    if (task.state === "EXECUTED") {
                      setCorrectionTask(task);
                    } else {
                      setEditingTask(task);
                    }
                  }}
                  onEditBinding={(task) => setBindingTask(task)}
                  selected={selectedIds.has(item.task.task_id)}
                  showCheckbox={selectedIds.size > 0}
                  onToggleSelect={toggleSelect}
                  onLlmChipChanged={refresh}
                />
                {/* Inline pause-confirm chips for this task. Rendered
                    under the row, visually attached via gap-1.5. */}
                {(pendingByTask.get(item.task.task_id) ?? []).map((p) => (
                  <PauseConfirmChip
                    key={p.firing_id}
                    prediction={p}
                    variant="inline"
                    onResolved={onConfirmResolved}
                  />
                ))}
              </div>
            ) : item.kind === "external" ? (
              <ExternalEventRow
                key={item.event.id}
                event={item.event}
                now={now}
                onMutated={() => {
                  qc.invalidateQueries({
                    queryKey: queryKeys.calendarEventsToday(viewedDate),
                  });
                }}
              />
            ) : (
              <DeadlineRow
                key={`deadline-${item.deadline.deadline_id}`}
                deadline={item.deadline}
                overdue={item.overdue}
                onEdit={(d) => setEditingDeadline(d)}
                onChanged={() =>
                  qc.invalidateQueries({ queryKey: queryKeys.deadlines })
                }
              />
            )
          )}
        </div>
      )}

      {interruptionStartFor && (
        <InterruptionStartDialog
          open={!!interruptionStartFor}
          taskTitle={interruptionStartFor.title}
          activeTaskTitle={status?.task_title ?? "the current task"}
          onCancel={() => setInterruptionStartFor(null)}
          onContinue={continueInterruptionStart}
        />
      )}

      {readinessFor && (
        <ReadinessModal
          open={!!readinessFor}
          taskTitle={readinessFor.title}
          onCancel={cancelReadiness}
          onConfirm={(r) => handleStart(readinessFor, r, readinessInterruptionType)}
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
        onConfirm={(r, opts) => handleStop(r, { confirmed: opts?.confirmed, completionPct: opts?.completionPct, scopeOutcome: opts?.scopeOutcome })}
      />

      <NewTaskModal
        open={newTaskOpen || !!editingTask}
        onClose={() => { setNewTaskOpen(false); setEditingTask(null); }}
        onCreated={refresh}
        onInterruptionCreated={handleInterruptionCreated}
        editingTask={editingTask}
        defaultDate={editingTask ? undefined : viewedDate}
      />

      <RetroactiveModal
        open={retroOpen}
        onClose={() => setRetroOpen(false)}
        onCreated={refresh}
        defaultDate={viewedDate}
      />

      <ExecutionCorrectionDialog
        task={correctionTask}
        onClose={() => setCorrectionTask(null)}
        onSaved={refresh}
      />

      <DeadlineBindingDialog
        task={bindingTask}
        open={!!bindingTask}
        onClose={() => setBindingTask(null)}
        onSaved={() => {
          qc.invalidateQueries({ queryKey: queryKeys.deadlines });
          refresh();
        }}
      />

      <VoidModal
        open={voidModalOpen}
        taskCount={selectedIds.size}
        onConfirm={handleBulkVoid}
        onCancel={() => setVoidModalOpen(false)}
      />

      <DeadlineModal
        open={!!editingDeadline}
        mode="edit"
        deadline={editingDeadline}
        onClose={() => setEditingDeadline(null)}
        onSaved={() => {
          qc.invalidateQueries({ queryKey: queryKeys.deadlines });
          setEditingDeadline(null);
        }}
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
            exposureId={t.exposureId}
            surfaceId={t.surfaceId}
            lifespan={t.lifespan}
            detailHref={t.detailHref}
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
    <Suspense fallback={<div className="text-sm text-dust">Loading…</div>}>
      <TodayInner />
    </Suspense>
  );
}
