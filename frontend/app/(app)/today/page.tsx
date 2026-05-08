"use client";
import { Suspense, useCallback, useEffect, useRef, useState } from "react";
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
  getPendingNotifications,
  type TaskRow as TaskRowType,
  type StopResponse,
  type StopwatchStatus,
  type PausePredictionNotification,
  type ResumePredictionNotification,
  resumeStopwatch,
} from "@/lib/tasks";
import { useCurrentTime } from "@/lib/hooks/use-current-time";
import { TaskRow } from "@/components/task-row";
import { ActiveTimerBanner } from "@/components/active-timer-banner";
import { ReadinessModal } from "@/components/readiness-modal";
import { ReflectionModal } from "@/components/reflection-modal";
import { NewTaskModal } from "@/components/new-task-modal";
import { RetroactiveModal } from "@/components/retroactive-modal";
import { SelectionActionBar } from "@/components/selection-action-bar";
import { VoidModal } from "@/components/void-modal";
import { Toast } from "@/components/toast";
import { PausePredictionBanner } from "@/components/pause-prediction-banner";
import { ResumePredictionBanner } from "@/components/resume-prediction-banner";
import { DeadlineRow } from "@/components/deadline-row";
import { DeadlineModal } from "@/components/deadline-modal";
import { listDeadlines, type DeadlineResponse } from "@/lib/deadlines";
import { PauseConfirmChip } from "@/components/pause-confirm-chip";
import { listPendingConfirmations } from "@/lib/pause-predictions";
import { ExternalEventRow } from "@/components/external-event-row";
import {
  getCalendarEvents,
  type ExternalCalendarEvent,
} from "@/lib/calendar";

interface ToastEntry {
  id: string;
  message: string;
  viewId: string | null;
  lifespan: "auto" | "pin";
  detailHref?: string;
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

  const tasksQ = useQuery({
    queryKey: ["tasks", viewedDate],
    queryFn: () => queryTasks(viewedDate),
    // 2026-05-08 latency pass: /today remounts and quick nav were paying a
    // fresh tunnel round-trip for task data even when the cache was seconds
    // old. Mutations below still invalidate/refetch explicitly, so this only
    // suppresses redundant mount/focus fetches.
    staleTime: 5_000,
  });
  const statusQ = useQuery({
    queryKey: ["stopwatch-status"],
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
    queryKey: ["calendar-events-today", viewedDate],
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
    queryKey: ["deadlines"],
    queryFn: () => listDeadlines(),
    staleTime: 60_000,
  });

  const [editingDeadline, setEditingDeadline] = useState<DeadlineResponse | null>(null);

  const notifQ = useQuery({
    queryKey: ["notifications-pending"],
    queryFn: getPendingNotifications,
    staleTime: 10_000,
    refetchInterval: 30_000,
  });

  // Retroactive pause-confirmation chips. Backend applies all three
  // gates: user_response='no_response', fired_at within 24h, no
  // pause_event within ±10 min of predicted_at. We just render what
  // it returns, tracking local dismiss state for the session.
  const pauseConfirmQ = useQuery({
    queryKey: ["pause-predictions-pending-confirmation"],
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
      queryKey: ["pause-predictions-pending-confirmation"],
    });
  }
  const [dismissedFirings, setDismissedFirings] = useState<Set<string>>(new Set());
  const pausePrediction: PausePredictionNotification | null = (() => {
    for (const n of notifQ.data?.notifications ?? []) {
      if (n.type === "pause_prediction" && typeof n.firing_id === "string" && !dismissedFirings.has(n.firing_id)) {
        return n as unknown as PausePredictionNotification;
      }
    }
    return null;
  })();
  // W2 magic-for-alpha (alembic 038, 2026-04-28). Mirrors pause-prediction
  // selection above. Banner mounts when status?.paused === true and a
  // matching firing hasn't been dismissed.
  const resumePrediction: ResumePredictionNotification | null = (() => {
    for (const n of notifQ.data?.notifications ?? []) {
      if (n.type === "resume_prediction" && typeof n.firing_id === "string" && !dismissedFirings.has(n.firing_id)) {
        return n as unknown as ResumePredictionNotification;
      }
    }
    return null;
  })();

  const [newTaskOpen, setNewTaskOpen] = useState(false);
  const [retroOpen, setRetroOpen] = useState(false);
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
  const [requestPause, setRequestPause] = useState(false);
  // When set, ActiveTimerBanner skips the reason picker on pause and
  // applies this reason directly — one-tap pause from the prediction
  // banner's primary action (2026-04-22). Clears on handled.
  const [quickPauseReason, setQuickPauseReason] = useState<string | undefined>(undefined);
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

  function pushToast(
    message: string,
    viewId: string | null,
    lifespan: "auto" | "pin",
    detailHref?: string,
  ) {
    const id =
      typeof crypto !== "undefined" && "randomUUID" in crypto
        ? crypto.randomUUID()
        : `toast-${Date.now()}-${Math.random().toString(36).slice(2)}`;
    setToasts((prev) => [...prev, { id, message, viewId, lifespan, detailHref }]);
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

  // Unified /today feed — Lyra tasks + external GCal events interleaved
  // by time while preserving Lyra's existing two-bucket rhythm:
  //   top  — PLANNED Lyra tasks + FUTURE/ongoing GCal events, asc by start
  //   bottom — non-PLANNED Lyra tasks + PAST GCal events, desc by end
  //
  // Past-end GCal events sit alongside EXECUTED/SKIPPED so the operator
  // finds attendance controls where they expect "what-happened" items
  // to live. Future events sit with PLANNED so the day reads
  // chronologically forward.
  //
  // The sort produces a union-typed list the renderer branches on
  // (TaskRow vs ExternalEventRow) — keeps the two row types visually
  // distinct without duplicating the feed.
  type FeedItem =
    | { kind: "task"; task: TaskRowType }
    | { kind: "external"; event: ExternalCalendarEvent }
    | { kind: "deadline"; deadline: DeadlineResponse; overdue: boolean };

  const nowMs = now.getTime();
  const gcalEventsAll: ExternalCalendarEvent[] = calEventsQ.data?.events ?? [];

  // Filter deadlines for the viewed day. Browser-local date comparison —
  // matches the operator's mental model (Cairo-local since
  // USER_TIMEZONE=Africa/Cairo and the operator dogfoods from Cairo).
  // Voided deadlines are always excluded; state-based exclusion is left
  // to the badge rendering (so completed deadlines on a past day still
  // show with a "COMPLETED" pill for historical reference).
  const isViewingToday = viewedDate === today;
  const dueDeadlines = ((): { deadline: DeadlineResponse; overdue: boolean }[] => {
    const all = deadlinesQ.data?.deadlines ?? [];
    return all.flatMap((d) => {
      if (d.voided_at) return [];
      const due = new Date(d.due_at_utc);
      const dueLocalKey = format(due, "yyyy-MM-dd");
      // OVERDUE definition unifies two paths:
      //   (a) post-sweep: sweep_missed_deadlines transitioned the row to
      //       state='missed' (every 1h job in workers/scheduler.py).
      //   (b) pre-sweep: state still 'planned'/'active' but due_at has
      //       passed — the sweep just hasn't run yet (up to ~1h window).
      // Both paths render the loud OVERDUE pill + pin to /today until
      // the user explicitly handles them. Operator-flagged 2026-04-29:
      // missed academic deadlines are the highest-signal procrastination
      // data point and must be impossible to miss in the UI.
      const isOverdue =
        d.state === "missed" ||
        ((d.state === "planned" || d.state === "active") &&
          due.getTime() < nowMs);
      // Show on the deadline's actual due day (any past/future day the
      // operator views). The OVERDUE pill only fires on today-view —
      // browsing a past day where a deadline missed should show the
      // historical "MISSED" state, not the action-prompt "OVERDUE"
      // (which implies "act now" — false on a past-day view).
      if (dueLocalKey === viewedDate) {
        return [{ deadline: d, overdue: isViewingToday && isOverdue }];
      }
      // Pin overdue items to today so they stay visible until resolved.
      // Covers both the pre-sweep (planned/active+past) and post-sweep
      // (missed) cases — without this, a deadline that misses by >1h
      // (when sweep flips it to missed) silently disappears from /today.
      if (isViewingToday && isOverdue) {
        return [{ deadline: d, overdue: true }];
      }
      return [];
    });
  })();

  // Overdue aggregate for the top banner. Only surfaces on /today (don't
  // pollute past/future-day views with action prompts about today). LMS
  // breakout shows the "from your school" sub-count when imported rows
  // are present — academic stakes get explicit emphasis per operator
  // call 2026-04-29 evening.
  const overdueDeadlines = isViewingToday
    ? dueDeadlines.filter((x) => x.overdue)
    : [];
  const overdueCount = overdueDeadlines.length;
  const overdueFromLms = overdueDeadlines.filter(
    (x) => x.deadline.external_source === "moodle_ics"
  ).length;

  const feed = ((): { top: FeedItem[]; bottom: FeedItem[] } => {
    if (!tasksQ.data) return { top: [], bottom: [] };
    const visible = tasksQ.data.filter((t) => !t.voided_at);
    const plannedTasks = visible.filter((t) => t.state === "PLANNED");
    const restTasks = visible.filter((t) => t.state !== "PLANNED");
    const gcalFuture = gcalEventsAll.filter(
      (e) => new Date(e.end).getTime() > nowMs
    );
    const gcalPast = gcalEventsAll.filter(
      (e) => new Date(e.end).getTime() <= nowMs
    );

    const topItems: FeedItem[] = [
      ...plannedTasks.map(
        (t): FeedItem => ({ kind: "task", task: t })
      ),
      ...gcalFuture.map(
        (e): FeedItem => ({ kind: "external", event: e })
      ),
      // Deadlines always live in the top bucket — they are pending-action
      // items even when overdue, never "what already happened."
      ...dueDeadlines.map(
        (x): FeedItem => ({ kind: "deadline", deadline: x.deadline, overdue: x.overdue })
      ),
    ].sort((a, b) => {
      const at =
        a.kind === "task"
          ? sortKey(a.task)
          : a.kind === "external"
            ? new Date(a.event.start).getTime()
            : new Date(a.deadline.due_at_utc).getTime();
      const bt =
        b.kind === "task"
          ? sortKey(b.task)
          : b.kind === "external"
            ? new Date(b.event.start).getTime()
            : new Date(b.deadline.due_at_utc).getTime();
      return at - bt;
    });

    const bottomItems: FeedItem[] = [
      ...restTasks.map((t): FeedItem => ({ kind: "task", task: t })),
      ...gcalPast.map(
        (e): FeedItem => ({ kind: "external", event: e })
      ),
    ].sort((a, b) => {
      const at =
        a.kind === "task"
          ? sortKey(a.task)
          : a.kind === "external"
            ? new Date(a.event.end).getTime()
            : new Date(a.deadline.due_at_utc).getTime();
      const bt =
        b.kind === "task"
          ? sortKey(b.task)
          : b.kind === "external"
            ? new Date(b.event.end).getTime()
            : new Date(b.deadline.due_at_utc).getTime();
      return bt - at;
    });

    return { top: topItems, bottom: bottomItems };
  })();

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
      const startResp = await startStopwatch(task.task_id, readiness);
      // LYR-097 (2026-04-28): surface "started early" hint when backend
      // flags the task as future. Inline 4s toast — non-blocking,
      // visible-once acknowledgment so the user knows the session
      // timestamp diverges from the calendar slot.
      if (startResp.is_future_task && startResp.planned_start) {
        try {
          const planned = new Date(startResp.planned_start);
          const minutesEarly = Math.max(
            0,
            Math.round((planned.getTime() - Date.now()) / 60000)
          );
          const timeLabel = planned.toLocaleTimeString([], {
            hour: "numeric", minute: "2-digit",
          });
          setErrorMsg(
            `Heads up — this was scheduled for ${timeLabel}, you started ${minutesEarly} min early. The session will record from now.`
          );
          // Auto-clear so it doesn't hover indefinitely
          setTimeout(() => setErrorMsg((prev) =>
            prev?.startsWith("Heads up — this was scheduled") ? null : prev
          ), 5000);
        } catch {
          // Defensive — bad date string shouldn't break the start flow
        }
      }
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
    opts: { confirmed?: boolean; completionPct?: number; scopeOutcome?: string } = {}
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
        scope_outcome: opts.scopeOutcome,
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
      // LYR-110: both toasts now carry a "View details →" link to /insights.
      // micro_mirror had 95% dismissal at ~6s dwell across all users —
      // adding a deeper-engagement affordance tests whether absence-of-
      // affordance was the failure vs content-not-valuable.
      if (res.micro_mirror) {
        pushToast(res.micro_mirror, res.micro_mirror_view_id ?? null, "auto", "/insights");
      }
      if (res.calibration_nudge) {
        pushToast(res.calibration_nudge, res.calibration_nudge_view_id ?? null, "pin", "/insights");
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
    qc.setQueryData<TaskRowType[]>(["tasks", viewedDate], (old) =>
      old?.map((t) => t.task_id === task.task_id ? { ...t, state: "SKIPPED" } : t)
    );
    if (isLive) {
      qc.setQueryData<StopwatchStatus>(["stopwatch-status"], { active: false });
    }
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
    qc.setQueryData<TaskRowType[]>(["tasks", viewedDate], (old) =>
      old?.filter((t) => t.task_id !== task.task_id)
    );
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
    if (ids.length === 0) return;

    // Apr 26 perf fix: optimistic close + cache update. Operator complaint
    // was "modal closing takes forever" — root cause was awaiting N parallel
    // void network calls (~1s each over Cloudflare Tunnel + Supabase) before
    // closing the modal. Now we close the modal AND fade voided tasks from
    // the list instantly; mutations fire in background; on error we rollback
    // and surface via errorMsg.
    await qc.cancelQueries({ queryKey: ["tasks", viewedDate] });
    const snapshot = qc.getQueryData<TaskRowType[]>(["tasks", viewedDate]);
    const nowIso = new Date().toISOString();
    qc.setQueryData<TaskRowType[]>(["tasks", viewedDate], (old) =>
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
      qc.invalidateQueries({ queryKey: ["tasks", viewedDate] });
      qc.invalidateQueries({ queryKey: ["stopwatch-status"] });
    } catch (e) {
      // Rollback the optimistic mutation; surface error.
      if (snapshot !== undefined) {
        qc.setQueryData(["tasks", viewedDate], snapshot);
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
            onClick={() => setNewTaskOpen(true)}
            className="cyber-pill cyber-pill-compact cyber-pill-primary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-signal/70"
          >
            <Plus className="h-3.5 w-3.5" />
            New task
          </button>
          <button
            onClick={() => setRetroOpen(true)}
            className="font-mono text-[10px] uppercase tracking-widest text-dust transition-colors hover:text-parchment"
            title="Log a past session that wasn't tracked live"
          >
            Retroactive ↓
          </button>
        </div>
      </div>

      {/* VT-17 pause prediction banner (above active timer) */}
      {pausePrediction && status?.active && !status?.paused && (
        <PausePredictionBanner
          prediction={pausePrediction}
          onPauseNow={(quick) => {
            setDismissedFirings((s) => new Set(s).add(pausePrediction!.firing_id));
            setQuickPauseReason(quick ? "intentional_break" : undefined);
            setRequestPause(true);
          }}
          onDismissed={() =>
            setDismissedFirings((s) => new Set(s).add(pausePrediction!.firing_id))
          }
        />
      )}

      {/* W2 resume prediction banner (only when paused). Operator-locked
          2026-04-28: surfaces "you usually resume by now" or cold-start
          "Lyra hasn't seen enough yet" copy. Resume button hits
          /v1/stopwatch/resume; dismiss is local-state. */}
      {resumePrediction && status?.active && status?.paused && (
        <ResumePredictionBanner
          prediction={resumePrediction}
          onResume={async () => {
            setDismissedFirings((s) => new Set(s).add(resumePrediction!.firing_id));
            try {
              await resumeStopwatch();
              refresh();
            } catch (e: any) {
              setErrorMsg(e?.message ?? "Failed to resume");
            }
          }}
          onDismissed={() =>
            setDismissedFirings((s) => new Set(s).add(resumePrediction!.firing_id))
          }
        />
      )}

      {/* Active timer banner: always visible regardless of viewed date */}
      {status && (
        <ActiveTimerBanner
          status={status}
          showOrphanWarning={orphanWarnShown}
          onDismissOrphanWarning={dismissOrphanWarn}
          requestPause={requestPause}
          quickPauseReason={quickPauseReason}
          onRequestPauseHandled={clearRequestPause}
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
              {overdueCount === 1 ? "Overdue assignment" : "Overdue assignments"}
              <span className="opacity-50"> ]</span>
            </p>
            <p className="text-xs text-ember/85">
              {overdueFromLms > 0
                ? `${overdueFromLms} from your school${
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
                  disableStart={
                    isPast ||
                    (timerBusy && item.task.task_id !== activeTaskId)
                  }
                  onStart={(task) => setReadinessFor(task)}
                  onStartHover={
                    item.task.task_id !== activeTaskId
                      ? notifyPotentialStart
                      : undefined
                  }
                  onStop={() => setReflectionOpen(true)}
                  onSkip={isPast ? undefined : handleSkip}
                  onDelete={isPast ? undefined : handleDelete}
                  onEdit={(task) => setEditingTask(task)}
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
                    queryKey: ["calendar-events-today", viewedDate],
                  });
                }}
              />
            ) : (
              <DeadlineRow
                key={`deadline-${item.deadline.deadline_id}`}
                deadline={item.deadline}
                overdue={item.overdue}
                onEdit={(d) => setEditingDeadline(d)}
                onChanged={() => qc.invalidateQueries({ queryKey: ["deadlines"] })}
              />
            )
          )}
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
          qc.invalidateQueries({ queryKey: ["deadlines"] });
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
