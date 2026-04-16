"use client";
// Install Temporal on globalThis BEFORE any Schedule-X import. Schedule-X's
// bundle has ~124 bare `Temporal.PlainDate` / `Temporal.ZonedDateTime`
// references and declares `temporal-polyfill` as a peerDependency, leaving
// the global install to the consumer. Without this side-effect import,
// `globalThis.Temporal` is undefined AND — critically — any Temporal
// instances we create with our own `import { Temporal } from "temporal-polyfill"`
// live in a different realm than whatever Schedule-X resolves at runtime, so
// its `instanceof Temporal.PlainDate` check fails and throws the misleading
// "[Schedule-X error]: selectedDate must have the format YYYY-MM-DD" message.
// The global import MUST precede every @schedule-x/* import below because
// Schedule-X touches Temporal during its own module initialization.
import "temporal-polyfill/global";
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
  getStopwatchStatus,
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

// TIMEZONE CONTRACT (Apr 11 2026, single-timezone alpha):
// Backend sends and accepts naked Cairo-local ISO strings
// ("2026-04-05T06:00:00"). Frontend treats them as wall-clock times in
// Africa/Cairo. When alpha proves retention and we add a second timezone,
// this contract changes to UTC-with-Z over the wire and per-user timezone
// conversion at display. See dogfood_findings_living.md P3 architecture
// entry for the deferred refactor.
//
// DO NOT "fix" this by adding a Z suffix or calling .toInstant() on the
// wire — backend and frontend must stay symmetric. The refactor is one
// commit that changes API serializer + frontend parser + user.timezone
// field together, not a piecemeal edit to this file.
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

// Backend returns Cairo-local naive ISO per project rule ("2026-04-05T06:00:00"
// — no Z, no offset). Parse as PlainDateTime (wall-clock, zoneless) and
// attach the Cairo zone to produce a ZonedDateTime. Single-timezone alpha
// — multi-timezone refactor deferred until post-retention. When that
// ships, this function changes alongside the API serializer in the same
// commit. See TIMEZONE CONTRACT above.
function toZdt(iso: string): Temporal.ZonedDateTime {
  return Temporal.PlainDateTime.from(iso).toZonedDateTime(TIMEZONE);
}

function taskToEvent(
  task: TaskRowType,
  liveStart?: Temporal.ZonedDateTime | null,
  liveEnd?: Temporal.ZonedDateTime | null,
): CalendarEventExternal | null {
  if (!task.start || !task.end) return null;
  const isImmutable =
    task.state === "EXECUTED" ||
    task.state === "SKIPPED" ||
    task.state === "EXECUTING" ||
    task.state === "PAUSED";

  // Calendar truth (Apr 16 2026) — three contracts, one render function:
  //
  //   1. EXECUTING (active and not paused): block = status.start_time →
  //      Temporal.Now. Grows on every 10 s stopwatch-status poll. Block
  //      start MUST come from status.start_time (passed as liveStart)
  //      because task.executed_start_utc is only written at stop time,
  //      not during execution — reading it here returns null and
  //      silently falls through to the planned block, which was the
  //      original bug in this feature.
  //
  //   2. EXECUTED with actual times populated: block = task.executed_start
  //      → task.executed_end. Shows what actually happened, not the
  //      plan. Retroactive logs land here too (they populate both
  //      executed_start_utc and executed_end_utc).
  //
  //   3. Everything else — PLANNED (intent), SKIPPED (unfulfilled
  //      intent), PAUSED (deliberately out of scope in this pass),
  //      EXECUTING that doesn't match status.task_id, EXECUTED missing
  //      either executed time — falls back to planned start/end. The
  //      pause-periods-rendered-inside-the-block feature is a separate
  //      follow-up that requires a new pause_event fetch.
  const isLiveActive =
    liveStart != null && liveEnd != null && task.state === "EXECUTING";
  const isHistorical =
    task.state === "EXECUTED" &&
    !!task.executed_start &&
    !!task.executed_end;

  let start: Temporal.ZonedDateTime;
  let end: Temporal.ZonedDateTime;
  if (isLiveActive) {
    start = liveStart;
    end = liveEnd;
  } else if (isHistorical) {
    start = toZdt(task.executed_start as string);
    end = toZdt(task.executed_end as string);
  } else {
    start = toZdt(task.start);
    end = toZdt(task.end);
  }

  return {
    id: task.task_id,
    title: task.title,
    start,
    end,
    calendarId: calendarIdForState(task.state),
    _options: {
      // Drag and resize only make sense for PLANNED rows — once a
      // task is live or done, its timeline is a historical record.
      disableDND: isImmutable,
      disableResize: isImmutable,
    },
    // Keep a flag so downstream (e.g., a custom event template) can
    // style the live-growing block distinctly from static EXECUTED
    // or PLANNED blocks.
    _isLive: isLiveActive,
    // Stash the full task row so onEventClick can find it without
    // hitting the cache again.
    _task: task,
  } as CalendarEventExternal & { _task: TaskRowType };
}

// Inverse of toZdt — Schedule-X hands us ZonedDateTime after drag/resize;
// emit naked Cairo-local PlainDateTime ISO ("2026-04-05T06:00:00") so the
// backend round-trip is symmetric. See TIMEZONE CONTRACT above. DO NOT
// replace with toInstant()/toString() — that produces a Z-suffixed UTC
// string the backend will interpret as UTC, shifting every drag by the
// Cairo offset.
function zdtToIso(zdt: Temporal.ZonedDateTime | Temporal.PlainDate): string {
  // Lyra events are always timed; PlainDate only appears for all-day
  // views, which we don't use. Defensive narrow so a future all-day
  // experiment doesn't silently corrupt reschedule payloads.
  if (!(zdt instanceof Temporal.ZonedDateTime)) {
    throw new Error(
      "zdtToIso: unexpected PlainDate — Lyra events are always timed"
    );
  }
  return zdt.toPlainDateTime().toString();
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

  // Stopwatch status poll — drives the live EXECUTING block. Inherits the
  // global 10 s refetchInterval from providers.tsx. When the operator is
  // actively timing a task, `statusQ.data` reports task_id + active/paused
  // flags; the events memo below uses that to render the active block
  // from actual_start → now, growing on every poll. `dataUpdatedAt` is
  // included as a memo dep so the end-time recomputes every poll tick
  // even when status payload is byte-identical (elapsed minute hasn't
  // crossed yet) — without that dep the block would only grow on
  // minute boundaries, not on every 10 s poll.
  const statusQ = useQuery({
    queryKey: ["stopwatch-status"],
    queryFn: getStopwatchStatus,
  });

  const [editingTask, setEditingTask] = useState<TaskRowType | null>(null);
  const [detailsTask, setDetailsTask] = useState<TaskRowType | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const events = useMemo(() => {
    if (!tasksQ.data) return [];
    const status = statusQ.data;
    // liveStart/liveEnd are non-null ONLY when the operator has an
    // EXECUTING task running (active + not paused). Computed once here
    // and passed per-task — taskToEvent applies them only to the task
    // whose id matches status.task_id.
    //
    // liveStart comes from status.start_time (the stopwatch-session
    // start, Cairo-local ISO string from to_local()), NOT from
    // task.executed_start — the latter is null while a task is still
    // EXECUTING (see stopwatch_manager.complete_task: executed_start_utc
    // is only written at stop time). Reading task.executed_start in the
    // live path was the bug that made the first iteration of this
    // feature silently render planned times.
    const activeId =
      status?.active && !status?.paused ? status?.task_id : undefined;
    const liveStart =
      activeId && status?.start_time ? toZdt(status.start_time) : null;
    const liveEnd = activeId
      ? Temporal.Now.zonedDateTimeISO(TIMEZONE)
      : null;
    return tasksQ.data
      .filter((t) => !t.voided_at)
      .map((t) => {
        const isActive = t.task_id === activeId;
        return taskToEvent(
          t,
          isActive ? liveStart : null,
          isActive ? liveEnd : null,
        );
      })
      .filter((e): e is CalendarEventExternal => e !== null);
    // dataUpdatedAt changes on every poll, guaranteeing a fresh
    // Temporal.Now on each refresh cycle. Without this dep the block
    // would only grow when the status payload shape differs — but
    // elapsed_minutes is int, so two polls 10 s apart often return
    // identical data by-value.
  }, [
    tasksQ.data,
    statusQ.data?.active,
    statusQ.data?.task_id,
    statusQ.data?.paused,
    statusQ.data?.start_time,
    statusQ.dataUpdatedAt,
  ]);

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
  const dragAndDropService = useMemo(() => {
    const plugin = createDragAndDropPlugin(15);
    // Schedule-X 4.4.0 release coordination bug: @schedule-x/calendar@4.4.0
    // renamed the dragAndDrop plugin method contract from
    // createTimeGridDragHandler / createDateGridDragHandler /
    // createMonthGridDragHandler → startTimeGridDrag / startDateGridDrag /
    // startMonthGridDrag at core.cjs.js:1578, 2280, 6178. But
    // @schedule-x/drag-and-drop@3.7.3 is the LATEST published version on
    // npm (verified: `npm view @schedule-x/drag-and-drop versions` tops out
    // at 3.7.3, no 4.x line exists yet) and still exposes only the v3 names
    // at core.cjs.js:1116, 1136, 1139. Without this shim, dragging any event
    // throws `TypeError: $app.config.plugins.dragAndDrop.startTimeGridDrag is
    // not a function` at first mousedown.
    //
    // Signatures are byte-identical — confirmed by reading both packages'
    // sources end-to-end: both accept the same `{$app, eventCoordinates,
    // eventCopy, updateCopy}` dependency object + optional dayBoundaries
    // positional arg, and both new up the same `*DragHandlerImpl` class
    // whose constructor is the actual side-effect (binds mousemove/mouseup/
    // touch listeners to document). Return value is discarded by the caller
    // in both versions, so aliasing the old methods under the new names is
    // semantically indistinguishable from a real plugin 4.x release.
    //
    // Resize does NOT have this mismatch: calendar 4.4.0 still calls
    // `plugins.resize.createTimeGridEventResizer(...)` at core.cjs.js:1643,
    // matching resize 3.7.3's exposed name. Pure coincidence of incomplete
    // rename — only drag was renamed in the 4.x refactor. Do not add a
    // "matching" resize shim; it would be dead code.
    //
    // TODO(remove): When @schedule-x/drag-and-drop@4.x publishes on npm
    // with the renamed methods, delete this shim block, bump the dep,
    // verify drag still works.
    const p = plugin as unknown as {
      createTimeGridDragHandler: (...args: unknown[]) => unknown;
      createDateGridDragHandler: (...args: unknown[]) => unknown;
      createMonthGridDragHandler: (...args: unknown[]) => unknown;
      startTimeGridDrag?: (...args: unknown[]) => unknown;
      startDateGridDrag?: (...args: unknown[]) => unknown;
      startMonthGridDrag?: (...args: unknown[]) => unknown;
    };
    p.startTimeGridDrag = p.createTimeGridDragHandler.bind(plugin);
    p.startDateGridDrag = p.createDateGridDragHandler.bind(plugin);
    p.startMonthGridDrag = p.createMonthGridDragHandler.bind(plugin);
    return plugin;
  }, []);
  const resizeService = useMemo(() => createResizePlugin(15), []);

  const calendar = useNextCalendarApp(
    {
      views: [createViewWeek(), createViewDay(), createViewMonthGrid()],
      defaultView: "week",
      events: [],
      calendars: STATE_CALENDARS,
      isDark: true,
      timezone: TIMEZONE,
      // Schedule-X default (eventOverlap: true) cascades overlapping events
      // at horizontal offsets but extends each to the right edge — titles
      // obscured by neighbors. false makes them split into equal sub-columns,
      // matching Google/Outlook/Apple convention. Trade-off: 5+ concurrent
      // events in one slot get unreadably narrow. v4.4.0 has no
      // collapse/truncate option. See dogfood_findings_living.md P3 for the
      // polish item.
      weekOptions: {
        eventOverlap: false,
      },
      // `selectedDate` must be a `Temporal.PlainDate` instance, NOT a string —
      // Schedule-X runs `config.selectedDate instanceof Temporal.PlainDate`
      // and throws "[Schedule-X error]: selectedDate must have the format
      // YYYY-MM-DD" on failure. The error message is misleading: it does not
      // check string format, it checks nominal class identity. A plain
      // "yyyy-MM-dd" string fails this check. A Temporal.PlainDate from the
      // WRONG realm also fails this check — which is why the global import
      // on line 1 is load-bearing: it guarantees Schedule-X's bundle and our
      // local `import { Temporal } from "temporal-polyfill"` resolve to the
      // same Temporal class.
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

      {/*
        Schedule-X 4.x renders the 24-hour time grid as a single tall
        static element (~1200–1500px) and does NOT own its own internal
        scroll context for it — contrary to what I initially assumed
        when I wrote the 720px + overflow-hidden wrapper. Empirical
        proof from operator's DevTools session (Apr 11 2026): at 100%
        zoom only midnight → ~7 AM was visible with no scroll
        affordance; at 50% zoom the full 24-hour grid fit into the
        same box, confirming events render at correct positions but
        are clipped by the wrapper's overflow mode.
        Correct setup: wrapper owns the scroll. Viewport-relative
        height fills the available space (220px buffer ≈ AppLayout
        header ~64px + page title + subtitle + top/bottom padding —
        tune if future layout changes clip or add whitespace), and
        overflow-y-auto gives the user a vertical scrollbar for
        hours below the fold. Schedule-X's sticky day-header row
        anchors to the nearest scroll ancestor, which is now this
        wrapper, so the header stays put while the hour rows scroll
        underneath it.
        DO NOT revert to overflow-hidden on this wrapper — doing so
        silently re-clips the grid. If you need to remove the border
        or rounding, keep `overflow-y-auto` in place.
      */}
      <div className="sx-react-calendar-wrapper h-[calc(100vh-220px)] overflow-y-auto rounded-lg border border-white/10">
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
