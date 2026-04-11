"use client";
import "@schedule-x/theme-shadcn/dist/index.css";
import { useEffect, useMemo, useRef, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { format } from "date-fns";
import { Temporal } from "temporal-polyfill";
import { ScheduleXCalendar, useNextCalendarApp } from "@schedule-x/react";
import {
  createViewDay,
  createViewWeek,
  createViewMonthGrid,
  type CalendarEventExternal,
  type CalendarType,
} from "@schedule-x/calendar";
import { createEventsServicePlugin } from "@schedule-x/events-service";
import { createDragAndDropPlugin } from "@schedule-x/drag-and-drop";
import { createResizePlugin } from "@schedule-x/resize";
import {
  queryTasks,
  rescheduleTask,
  type TaskRow as TaskRowType,
} from "@/lib/tasks";
import { NewTaskModal } from "@/components/new-task-modal";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";

// All display lives in the user's timezone. Kept hardcoded to match
// backend USER_TIMEZONE default; if we ever go multi-tenant we'll
// thread this through session or a server endpoint.
const TIMEZONE = "Africa/Cairo";

// Five state-colored calendars — mirror the palette in task-row.tsx:11
// so rows and calendar events carry the same visual vocabulary.
// lightColors and darkColors use Schedule-X's main/container/onContainer
// triad; we tune darkColors since the app ships in dark mode.
const STATE_CALENDARS: Record<string, CalendarType> = {
  planned: {
    colorName: "planned",
    label: "Planned",
    darkColors: {
      main: "#9ca3af", // gray-400
      container: "#1f2937", // gray-800
      onContainer: "#e5e7eb", // gray-200
    },
  },
  executing: {
    colorName: "executing",
    label: "Executing",
    darkColors: {
      main: "#60a5fa", // blue-400
      container: "#1e3a8a", // blue-900
      onContainer: "#dbeafe", // blue-100
    },
  },
  paused: {
    colorName: "paused",
    label: "Paused",
    darkColors: {
      main: "#fbbf24", // amber-400
      container: "#78350f", // amber-900
      onContainer: "#fef3c7", // amber-100
    },
  },
  executed: {
    colorName: "executed",
    label: "Executed",
    darkColors: {
      main: "#4ade80", // green-400
      container: "#14532d", // green-900
      onContainer: "#dcfce7", // green-100
    },
  },
  skipped: {
    colorName: "skipped",
    label: "Skipped",
    darkColors: {
      main: "#f87171", // red-400
      container: "#7f1d1d", // red-900
      onContainer: "#fee2e2", // red-100
    },
  },
};

function calendarIdForState(state: TaskRowType["state"]): string {
  switch (state) {
    case "EXECUTING":
      return "executing";
    case "PAUSED":
      return "paused";
    case "EXECUTED":
      return "executed";
    case "SKIPPED":
      return "skipped";
    case "PLANNED":
    default:
      return "planned";
  }
}

// ISO-with-offset/Z → ZonedDateTime in the user's timezone. Using
// Instant.from then toZonedDateTimeISO is the bulletproof route: it
// parses any ISO variant the backend emits and only *then* attaches the
// zone. Appending "[Africa/Cairo]" directly to the raw ISO string
// rejects when the string contains both an offset AND the bracketed
// zone under certain polyfill versions, so avoid that shortcut.
function toZdt(iso: string): Temporal.ZonedDateTime {
  return Temporal.Instant.from(iso).toZonedDateTimeISO(TIMEZONE);
}

function taskToEvent(task: TaskRowType): CalendarEventExternal | null {
  if (!task.start || !task.end) return null;
  const isImmutable =
    task.state === "EXECUTED" ||
    task.state === "SKIPPED" ||
    task.state === "EXECUTING" ||
    task.state === "PAUSED";
  return {
    id: task.task_id,
    title: task.title,
    start: toZdt(task.start),
    end: toZdt(task.end),
    calendarId: calendarIdForState(task.state),
    _options: {
      // Drag and resize only make sense for PLANNED rows — once a
      // task is live or done, its timeline is a historical record.
      disableDND: isImmutable,
      disableResize: isImmutable,
    },
    // Stash the full task row so onEventClick can find it without
    // hitting the cache again.
    _task: task,
  } as CalendarEventExternal & { _task: TaskRowType };
}

// Convert a ZonedDateTime back to an ISO string that the backend can
// parse. Schedule-X hands us ZonedDateTime instances after drag/resize.
function zdtToIso(zdt: Temporal.ZonedDateTime | Temporal.PlainDate): string {
  // Narrow — after a drag/resize on a timed event we always get
  // ZonedDateTime; PlainDate would come from all-day views we don't use.
  if ("toInstant" in zdt) {
    return zdt.toInstant().toString();
  }
  // Fallback for PlainDate: treat as midnight in TIMEZONE.
  return (zdt as Temporal.PlainDate)
    .toZonedDateTime(TIMEZONE)
    .toInstant()
    .toString();
}

export default function CalendarPage() {
  const qc = useQueryClient();
  // Pull a wide window so the calendar has something to render across
  // day/week/month navigation. Pivot 14 days before today and pull 62
  // days forward: covers two weeks of history + ~6 weeks ahead, which
  // is enough for month-view scrolling without yet another round trip.
  // Cached under a distinct key so this bulk fetch doesn't collide
  // with Today view's single-day query.
  const pivot = useMemo(() => {
    const d = new Date();
    d.setDate(d.getDate() - 14);
    return d;
  }, []);
  const pivotKey = format(pivot, "yyyy-MM-dd");
  const RANGE_DAYS = 62;

  const tasksQ = useQuery({
    queryKey: ["tasks-range", pivotKey, RANGE_DAYS],
    queryFn: () => queryTasks(pivotKey, RANGE_DAYS),
  });

  const [editingTask, setEditingTask] = useState<TaskRowType | null>(null);
  const [detailsTask, setDetailsTask] = useState<TaskRowType | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const events = useMemo(() => {
    if (!tasksQ.data) return [];
    return tasksQ.data
      .filter((t) => !t.voided_at)
      .map(taskToEvent)
      .filter((e): e is CalendarEventExternal => e !== null);
  }, [tasksQ.data]);

  // `useNextCalendarApp` initializes the calendar ONCE on mount and the
  // callbacks inside its config close over whatever state existed at
  // that moment. That means a direct `tasksQ.data.find(...)` lookup
  // inside `onEventClick` or `onBeforeEventUpdateAsync` would read the
  // first-render snapshot forever. Stash the latest data in a ref that
  // the callbacks read through so they always see fresh rows.
  const tasksRef = useRef<TaskRowType[] | undefined>(undefined);
  useEffect(() => {
    tasksRef.current = tasksQ.data;
  }, [tasksQ.data]);

  function findTask(id: string | number): TaskRowType | undefined {
    const idStr = String(id);
    return tasksRef.current?.find((t) => t.task_id === idStr);
  }

  // Refresh both cache keys on any calendar-driven mutation so the
  // Today view (`["tasks", date]`) and the Calendar view
  // (`["tasks-range", pivot, days]`) stay in lock-step without either
  // side knowing about the other's key shape.
  function refreshAll() {
    qc.invalidateQueries({
      predicate: (q) =>
        q.queryKey[0] === "tasks" || q.queryKey[0] === "tasks-range",
    });
  }

  // Toast-style auto-dismiss for the drag/resize rejection banner —
  // a PLANNED-only constraint should feel ephemeral, not linger until
  // the user manually dismisses. 4s is long enough to read, short
  // enough to not stack on repeated drag attempts.
  useEffect(() => {
    if (!errorMsg) return;
    const id = setTimeout(() => setErrorMsg(null), 4000);
    return () => clearTimeout(id);
  }, [errorMsg]);

  const eventsService = useMemo(() => createEventsServicePlugin(), []);
  const dragAndDropService = useMemo(() => createDragAndDropPlugin(15), []);
  const resizeService = useMemo(() => createResizePlugin(15), []);

  const calendar = useNextCalendarApp(
    {
      views: [createViewWeek(), createViewDay(), createViewMonthGrid()],
      defaultView: "week",
      events: [],
      calendars: STATE_CALENDARS,
      isDark: true,
      timezone: TIMEZONE,
      selectedDate: Temporal.Now.plainDateISO(TIMEZONE),
      callbacks: {
        onEventClick(evt) {
          const task = findTask(evt.id);
          if (!task) return;
          if (task.state === "PLANNED") {
            setEditingTask(task);
          } else {
            setDetailsTask(task);
          }
        },
        async onBeforeEventUpdateAsync(_oldEvent, newEvent) {
          const task = findTask(newEvent.id);
          if (!task) return false;
          if (task.state !== "PLANNED") {
            setErrorMsg(`Cannot modify ${task.state.toLowerCase()} tasks`);
            return false;
          }
          try {
            await rescheduleTask({
              task_id: task.task_id,
              new_start: zdtToIso(newEvent.start),
              new_end: zdtToIso(newEvent.end),
            });
            refreshAll();
            setErrorMsg(null);
            return true;
          } catch (e) {
            setErrorMsg(
              e instanceof Error ? e.message : "Failed to reschedule task"
            );
            return false;
          }
        },
      },
    },
    [eventsService, dragAndDropService, resizeService]
  );

  // Sync the events service with the latest query result. useNextCalendarApp
  // takes an initial `events` array but we want live updates as tasks
  // change in the cache.
  useEffect(() => {
    if (!calendar) return;
    eventsService.set(events);
  }, [calendar, events, eventsService]);

  return (
    <div>
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold">Calendar</h1>
          <p className="text-xs text-white/50">
            Drag planned tasks to reschedule. Click to edit.
          </p>
        </div>
      </div>

      {errorMsg && (
        <div className="mb-4 flex items-center justify-between rounded border border-red-500/30 bg-red-500/10 p-3 text-xs text-red-200">
          <span>{errorMsg}</span>
          <button
            onClick={() => setErrorMsg(null)}
            className="ml-2 text-white/40 hover:text-white/70"
          >
            &times;
          </button>
        </div>
      )}

      {tasksQ.isLoading && (
        <div className="text-sm text-white/50">Loading calendar…</div>
      )}

      <div className="sx-react-calendar-wrapper h-[720px] overflow-hidden rounded-lg border border-white/10">
        {calendar && <ScheduleXCalendar calendarApp={calendar} />}
      </div>

      {editingTask && (
        <NewTaskModal
          open={!!editingTask}
          onClose={() => setEditingTask(null)}
          onCreated={refreshAll}
          editingTask={editingTask}
        />
      )}

      <TaskDetailsDialog
        task={detailsTask}
        onClose={() => setDetailsTask(null)}
      />
    </div>
  );
}

// Read-only details popover for non-PLANNED tasks. Executed / skipped /
// live rows are immutable from the calendar — this dialog is a dead-end
// peek rather than an edit surface.
function TaskDetailsDialog({
  task,
  onClose,
}: {
  task: TaskRowType | null;
  onClose: () => void;
}) {
  if (!task) return null;
  const fmt = (iso: string | null) =>
    iso ? format(new Date(iso), "EEE, MMM d · HH:mm") : "—";
  return (
    <Dialog open={!!task} onOpenChange={(o) => !o && onClose()}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{task.title}</DialogTitle>
          <DialogDescription>
            {task.state.toLowerCase()} · read-only
          </DialogDescription>
        </DialogHeader>
        <dl className="grid grid-cols-[auto_1fr] gap-x-4 gap-y-2 text-xs">
          <dt className="text-white/50">State</dt>
          <dd className="text-white/90">{task.state.toLowerCase()}</dd>
          <dt className="text-white/50">Planned</dt>
          <dd className="text-white/90">
            {fmt(task.start)} → {fmt(task.end)}
          </dd>
          {task.executed_start && (
            <>
              <dt className="text-white/50">Executed</dt>
              <dd className="text-white/90">
                {fmt(task.executed_start)} → {fmt(task.executed_end)}
              </dd>
            </>
          )}
          {task.planned_duration_minutes !== null && (
            <>
              <dt className="text-white/50">Planned duration</dt>
              <dd className="text-white/90">
                {task.planned_duration_minutes} min
              </dd>
            </>
          )}
          {task.executed_duration_minutes !== null && (
            <>
              <dt className="text-white/50">Actual duration</dt>
              <dd className="text-white/90">
                {task.executed_duration_minutes} min
                {task.duration_delta_minutes !== null && (
                  <span className="ml-2 text-white/40">
                    (Δ {task.duration_delta_minutes > 0 ? "+" : ""}
                    {task.duration_delta_minutes})
                  </span>
                )}
              </dd>
            </>
          )}
          {task.pre_task_readiness !== null && (
            <>
              <dt className="text-white/50">Readiness</dt>
              <dd className="text-white/90">
                {task.pre_task_readiness}/5
              </dd>
            </>
          )}
          {task.post_task_reflection !== null && (
            <>
              <dt className="text-white/50">Focus</dt>
              <dd className="text-white/90">
                {task.post_task_reflection}/5
              </dd>
            </>
          )}
          {task.category && (
            <>
              <dt className="text-white/50">Category</dt>
              <dd className="text-white/90">{task.category}</dd>
            </>
          )}
        </dl>
        <DialogFooter>
          <Button variant="ghost" onClick={onClose}>
            Close
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
