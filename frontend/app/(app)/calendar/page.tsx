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
  queryTasksRange,
  rescheduleTask,
  getStopwatchStatus,
  type TaskRow as TaskRowType,
} from "@/lib/tasks";
import {
  getCalendarEvents,
  type ExternalCalendarEvent,
} from "@/lib/calendar";
import { NewTaskModal } from "@/components/new-task-modal";
import { ExecutionCorrectionDialog } from "@/components/execution-correction-dialog";
import { DeadlineModal } from "@/components/deadline-modal";
import { listDeadlines, type DeadlineResponse } from "@/lib/deadlines";
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

// Five state-colored calendars — mapped to the brand palette so calendar
// blocks and /today's state badges carry the same visual vocabulary:
// EXECUTING signal, PAUSED ember, PLANNED/EXECUTED dust ramp, SKIPPED
// dust-deep. Schedule-X's main/container/onContainer triad: main is the
// block's accent stripe, container is its background fill, onContainer
// is the title text color on that fill. Values hand-picked to stay in
// the brand family — signal / ember / dust / dust-deep from
// tailwind.config.ts are the `main` hues; container + onContainer are
// darker / lighter brand-family shades rather than Tailwind colors.
const STATE_CALENDARS: Record<string, CalendarType> = {
  planned: {
    colorName: "planned",
    label: "Planned",
    darkColors: {
      main: "#8A92A3", // dust
      container: "#141B2A", // ink (brand)
      onContainer: "#F0EFEA", // parchment
    },
  },
  executing: {
    colorName: "executing",
    label: "Executing",
    darkColors: {
      main: "#4DD4E8", // signal
      container: "#0F3845", // signal-shadow
      onContainer: "#E0F7FA", // signal-washed
    },
  },
  paused: {
    colorName: "paused",
    label: "Paused",
    darkColors: {
      main: "#F5A96A", // ember
      container: "#3D2914", // ember-shadow
      onContainer: "#FDE8D3", // ember-washed
    },
  },
  executed: {
    colorName: "executed",
    label: "Executed",
    darkColors: {
      main: "#6B7280", // dust-muted (completed/past, greyed)
      container: "#1F2937", // void-deep
      onContainer: "#E5E7EB", // dust-light
    },
  },
  skipped: {
    colorName: "skipped",
    label: "Skipped",
    darkColors: {
      main: "#4A5168", // dust-deep
      container: "#1F2230", // void-deep
      onContainer: "#9CA3AF", // dust-mid
    },
  },
  // Google Calendar read-only import (Path B, 2026-04-21). Rendered
  // as muted grey background blocks — distinct from every Lyra state
  // so the user can't confuse "my tracked plan" with "my external
  // commitment." Events carry disableDND + disableResize via
  // _options so Schedule-X doesn't offer interaction handles.
  google_external: {
    colorName: "google_external",
    label: "Google Calendar",
    darkColors: {
      main: "#6B7280", // muted grey (same ramp as EXECUTED)
      container: "#111827", // darker void, sinks behind Lyra blocks
      onContainer: "#9CA3AF", // dust-mid — readable but not attention-grabbing
    },
  },
  // Loop 11 deadline mechanism (April 2026). Rendered with a warm
  // ember-leaning hue so a deadline reads as a flag, not a task.
  // disableDND + disableResize via _options on each event — the
  // operator should not be able to silently drag a deadline off its
  // actual day from the calendar surface; due-date changes go through
  // the DeadlineModal instead.
  deadlines: {
    colorName: "deadlines",
    label: "Deadlines",
    darkColors: {
      main: "#E8A04D", // warm amber, distinct from PAUSED ember (which is task-state)
      container: "#2D2417",
      onContainer: "#FDE8D3",
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

// Deadlines deliberately violate the TIMEZONE CONTRACT for tasks: the
// DeadlineResponse schema serializes due_at_utc with an explicit UTC
// offset ("2026-05-15T15:00:00+00:00") so the browser-local list view
// renders correctly. Schedule-X expects a Cairo-zoned time, so convert
// from Instant → ZonedDateTime in the user's tz here. Do NOT call
// `toZdt(...)` on a deadline ISO; PlainDateTime.from rejects offsets
// and throws.
function deadlineToZdt(iso: string): Temporal.ZonedDateTime {
  return Temporal.Instant.from(iso).toZonedDateTimeISO(TIMEZONE);
}

function eventDateString(event: CalendarEventExternal): string | null {
  const start = event.start as unknown as {
    toPlainDate?: () => { toString: () => string };
    toString?: () => string;
  };
  if (typeof start?.toPlainDate === "function") {
    return start.toPlainDate().toString();
  }
  if (typeof start?.toString === "function") {
    return start.toString().slice(0, 10);
  }
  return null;
}

function isLyraTaskEvent(event: CalendarEventExternal): boolean {
  const id = String(event.id);
  return !id.startsWith("gcal-") && !id.startsWith("deadline-");
}

function eventIdSelector(eventId: string): string {
  const escaped = eventId.replace(/\\/g, "\\\\").replace(/"/g, '\\"');
  return `[data-event-id="${escaped}"]`;
}

function scrollElementIntoCalendarViewport(
  viewport: HTMLDivElement,
  element: HTMLElement,
) {
  const viewportRect = viewport.getBoundingClientRect();
  const elementRect = element.getBoundingClientRect();
  const targetTop =
    viewport.scrollTop +
    (elementRect.top - viewportRect.top) -
    Math.max(96, viewport.clientHeight * 0.24);

  viewport.scrollTo({
    top: Math.max(0, targetTop),
    behavior: "auto",
  });
}

function scrollCalendarViewportToNow(viewport: HTMLDivElement) {
  const now = Temporal.Now.zonedDateTimeISO(TIMEZONE);
  const startHour = 6;
  const endHour = 23;
  const minutesFromStart = Math.max(
    0,
    Math.min((endHour - startHour) * 60, (now.hour - startHour) * 60 + now.minute),
  );
  const ratio = minutesFromStart / ((endHour - startHour) * 60);
  const targetTop = viewport.scrollHeight * ratio - viewport.clientHeight * 0.35;

  viewport.scrollTo({
    top: Math.max(0, targetTop),
    behavior: "auto",
  });
}

type CalendarQueryRange = {
  from: string;
  to: string;
};

type ScheduleRange = {
  start: Temporal.ZonedDateTime;
  end: Temporal.ZonedDateTime;
};

function initialCalendarQueryRange(): CalendarQueryRange {
  const today = Temporal.Now.plainDateISO(TIMEZONE);
  const weekStart = today.subtract({ days: today.dayOfWeek - 1 });
  return {
    from: weekStart.toString(),
    to: weekStart.add({ days: 6 }).toString(),
  };
}

function calendarRangeToQueryRange(range: ScheduleRange): CalendarQueryRange {
  return {
    from: range.start.toPlainDate().toString(),
    to: range.end.toPlainDate().toString(),
  };
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
  const [visibleRange, setVisibleRange] = useState<CalendarQueryRange>(() =>
    initialCalendarQueryRange(),
  );
  // Fetch the range Schedule-X is actually showing. A fixed "near today"
  // window made old weeks look task-empty while all-range deadlines still
  // appeared, which was both confusing and false.
  const tasksQ = useQuery({
    queryKey: ["tasks-range", visibleRange.from, visibleRange.to],
    queryFn: async () => {
      const res = await queryTasksRange(visibleRange.from, visibleRange.to);
      return res.tasks.filter((t) => t.state !== "DELETED");
    },
    staleTime: 60_000,
  });

  // Google Calendar read-only events. Same visible range as the task query so
  // external events render alongside Lyra tasks across the operator's
  // scrollable view. 60s staleTime matches the backend Redis TTL, so
  // switching views feels instant but Lyra picks up newly-added GCal
  // events within ~1 minute. Connected=false (no refresh_token yet)
  // returns empty events gracefully — no error toast, UI simply shows
  // Lyra tasks alone.
  const calendarEventsQ = useQuery({
    queryKey: ["calendar-events", visibleRange.from, visibleRange.to],
    queryFn: () =>
      getCalendarEvents({
        dateFrom: visibleRange.from,
        dateTo: visibleRange.to,
      }),
    staleTime: 60_000,
    refetchInterval: 60_000,
  });

  // Stopwatch status poll — drives the live EXECUTING block. When the
  // operator is actively timing a task, `statusQ.data` reports task_id + active/paused
  // flags; the events memo below uses that to render the active block
  // from actual_start → now, growing on every poll. `dataUpdatedAt` is
  // included as a memo dep so the end-time recomputes every poll tick
  // even when status payload is byte-identical (elapsed minute hasn't
  // crossed yet) — without that dep the block would only grow on
  // minute boundaries, not on every 10 s poll.
  const statusQ = useQuery({
    queryKey: ["stopwatch-status"],
    queryFn: getStopwatchStatus,
    refetchInterval: 10_000,
  });

  const [editingTask, setEditingTask] = useState<TaskRowType | null>(null);
  const [detailsTask, setDetailsTask] = useState<TaskRowType | null>(null);
  const [correctionTask, setCorrectionTask] = useState<TaskRowType | null>(null);
  const [editingDeadline, setEditingDeadline] = useState<DeadlineResponse | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  // View-toggle state — drives the explicit Day/Week/Month button bar
  // we render above the calendar, since Schedule-X v4 conditionally
  // mounts its own selector items only when the dropdown is open
  // (the prior CSS-flatten attempt was dead because the items list
  // wasn't in the DOM to style). 2026-04-30 mobile-fix recovery.
  const [currentView, setCurrentView] = useState<"day" | "week" | "month-grid">("week");
  const calendarViewportRef = useRef<HTMLDivElement | null>(null);
  const autoScrolledKeyRef = useRef<string | null>(null);

  // Deadlines render as Schedule-X events on their actual due day.
  // No state filter — completed/missed/skipped deadlines also surface
  // (their state pill is reflected in the event title via the icon),
  // so the calendar reads as the historical record of every deadline.
  // Voided deadlines are excluded by default per the list endpoint.
  const deadlinesQ = useQuery({
    queryKey: ["deadlines"],
    queryFn: () => listDeadlines(),
    staleTime: 60_000,
    refetchInterval: 60_000,
  });

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
    const lyraEvents = tasksQ.data
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

    // Merge in Google Calendar events as read-only background blocks.
    // calendarId="google_external" picks up the muted grey scheme
    // registered in STATE_CALENDARS; _options disables DND/resize so
    // Schedule-X treats them as immutable alongside EXECUTED/SKIPPED
    // Lyra tasks. id-prefixed with `gcal-` so onEventClick can
    // distinguish external events from Lyra task ids (Lyra uses
    // UUIDs, external uses gcal-<google_event_id>). Hyphen — not
    // colon — because Schedule-X uses document.querySelector on the
    // event id, and `:` is a CSS pseudo-class delimiter that breaks
    // selector parsing (2026-04-21 crash: "Event id gcal:... is not
    // a valid id"). Google event ids are base32 + underscore +
    // hyphen per their docs, all CSS-ident-safe with the letter
    // prefix.
    const gcalEvents: CalendarEventExternal[] = (
      calendarEventsQ.data?.events ?? []
    ).map((e: ExternalCalendarEvent) => ({
      id: `gcal-${e.id}`,
      title: e.title,
      start: toZdt(e.start),
      end: toZdt(e.end),
      calendarId: "google_external",
      _options: {
        disableDND: true,
        disableResize: true,
      },
    }) as CalendarEventExternal);

    // Deadlines appear on their actual due day. Each is a 1-hour
    // block ending at due_at — the title carries a flag emoji so the
    // ember calendar color + the prefix together read as "deadline."
    // Both DND and resize disabled: editing a deadline's due time
    // should go through the modal, not silent calendar drag (the
    // modal also runs the planned→active transition + state buttons).
    const deadlineEvents: CalendarEventExternal[] = (
      deadlinesQ.data?.deadlines ?? []
    ).map((d) => {
      const end = deadlineToZdt(d.due_at_utc);
      const start = end.subtract({ minutes: 60 });
      return {
        id: `deadline-${d.deadline_id}`,
        title: `⚑ ${d.title}`,
        start,
        end,
        calendarId: "deadlines",
        _options: {
          disableDND: true,
          disableResize: true,
        },
      } as CalendarEventExternal;
    });

    return [...lyraEvents, ...gcalEvents, ...deadlineEvents];
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
    calendarEventsQ.data,
    deadlinesQ.data,
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

  // Same trick for deadlines — onEventClick reads fresh rows without
  // closing over a stale snapshot.
  const deadlinesRef = useRef<DeadlineResponse[] | undefined>(undefined);
  useEffect(() => {
    deadlinesRef.current = deadlinesQ.data?.deadlines;
  }, [deadlinesQ.data]);

  function findDeadline(id: string): DeadlineResponse | undefined {
    if (!id.startsWith("deadline-")) return undefined;
    const did = id.slice("deadline-".length);
    return deadlinesRef.current?.find((d) => d.deadline_id === did);
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
      // Crop the visible day to 06:00–23:00 (operator-active hours).
      // Schedule-X default is 00:00–24:00 — on mobile this means the
      // top of the visible grid is midnight, and the operator has to
      // scroll a long way to reach their actual tasks. Cropping shows
      // ~17 productive hours instead of 24, which fits ~2x more of the
      // day in viewport at the same zoom level.
      // 2026-04-30 mobile-density fix per operator screenshot review.
      dayBoundaries: { start: "06:00", end: "23:00" },
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
        onRangeUpdate(range) {
          const nextRange = calendarRangeToQueryRange(range);
          autoScrolledKeyRef.current = null;
          setVisibleRange((prev) =>
            prev.from === nextRange.from && prev.to === nextRange.to
              ? prev
              : nextRange,
          );
        },
        onEventClick(evt) {
          const idStr = String(evt.id);
          // Branch on prefix: deadlines open the DeadlineModal in
          // edit mode; tasks fall through to the existing flow.
          // External GCal events (id `gcal-...`) reach this same
          // handler but are no-ops: findTask returns undefined and
          // we early-return.
          if (idStr.startsWith("deadline-")) {
            const dl = findDeadline(idStr);
            if (dl) setEditingDeadline(dl);
            return;
          }
          const task = findTask(idStr);
          if (!task) return;
          if (task.state === "PLANNED") {
            setEditingTask(task);
          } else if (task.state === "EXECUTED") {
            setCorrectionTask(task);
          } else {
            setDetailsTask(task);
          }
        },
        async onBeforeEventUpdateAsync(_oldEvent, newEvent) {
          // Deadlines have disableDND/disableResize so this callback
          // shouldn't fire for them — guard anyway in case Schedule-X
          // surfaces a drag-attempt for a brief moment.
          if (String(newEvent.id).startsWith("deadline-")) return false;
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

  // Schedule-X starts the time-grid at the top of the day-boundary window.
  // With 06:00-23:00 cropped into a fixed-height internal scroll viewport,
  // afternoon/evening work can be correctly rendered but below the fold,
  // making the calendar look empty. After events mount, land the viewport on
  // the active task first when it is visible, then the first Lyra task in the
  // viewed range, then current time.
  useEffect(() => {
    if (!calendar || currentView === "month-grid") return;
    const viewport = calendarViewportRef.current;
    if (!viewport || tasksQ.isLoading) return;

    const activeId =
      statusQ.data?.active && statusQ.data.task_id
        ? String(statusQ.data.task_id)
        : null;
    const activeEvent = activeId
      ? events.find((event) => String(event.id) === activeId)
      : undefined;
    const today = Temporal.Now.plainDateISO(TIMEZONE).toString();
    const firstTodayTask = events.find(
      (event) => isLyraTaskEvent(event) && eventDateString(event) === today,
    );
    const firstVisibleTask = events.find(isLyraTaskEvent);
    const firstVisibleEvent = events[0];
    const targetId = activeEvent
      ? String(activeEvent.id)
      : firstTodayTask
        ? String(firstTodayTask.id)
        : firstVisibleTask
          ? String(firstVisibleTask.id)
          : firstVisibleEvent
            ? String(firstVisibleEvent.id)
            : null;
    const scrollKey = `${currentView}:${visibleRange.from}:${visibleRange.to}:${targetId ?? "now"}:${events.length}`;
    if (autoScrolledKeyRef.current === scrollKey) return;

    const timeoutId = window.setTimeout(() => {
      let didScrollToEvent = false;
      if (targetId) {
        const element = viewport.querySelector(
          eventIdSelector(targetId),
        ) as HTMLElement | null;
        if (element) {
          scrollElementIntoCalendarViewport(viewport, element);
          didScrollToEvent = true;
        }
      }
      if (!didScrollToEvent) {
        scrollCalendarViewportToNow(viewport);
      }
      autoScrolledKeyRef.current = scrollKey;
    }, 120);

    return () => window.clearTimeout(timeoutId);
  }, [
    calendar,
    currentView,
    events,
    statusQ.data?.active,
    statusQ.data?.task_id,
    tasksQ.isLoading,
    visibleRange.from,
    visibleRange.to,
  ]);

  return (
    <div>
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight text-parchment">
            Calendar
          </h1>
          <p className="mt-1 text-xs text-dust">
            Drag planned tasks to reschedule. Click to edit.
          </p>
        </div>
      </div>

      {errorMsg && (
        <div className="mb-4 flex items-center justify-between rounded-sm border border-ember/40 bg-ember/5 p-3 text-xs text-ember">
          <span>{errorMsg}</span>
          <button
            onClick={() => setErrorMsg(null)}
            className="ml-2 text-dust-deep transition-colors hover:text-parchment"
          >
            &times;
          </button>
        </div>
      )}

      {tasksQ.isLoading && (
        <div className="text-sm text-dust">Loading calendar…</div>
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
      {/* View-toggle pill bar — explicit JSX so the buttons are
          always rendered (Schedule-X v4's built-in selector
          conditionally mounts items only when the dropdown is open,
          so a CSS-flatten approach can't show them inline). The
          buttons drive Schedule-X's calendarState.setView via the
          $app handle, which is marked private but is the only stable
          public API surface for programmatic view switching in v4.x. */}
      {calendar && (
        <div className="mb-3 flex flex-wrap gap-1">
          {(
            [
              { id: "day", label: "Day" },
              { id: "week", label: "Week" },
              { id: "month-grid", label: "Month" },
            ] as const
          ).map((opt) => {
            const isActive = currentView === opt.id;
            return (
              <button
                key={opt.id}
                type="button"
                onClick={() => {
                  autoScrolledKeyRef.current = null;
                  setCurrentView(opt.id);
                  // Schedule-X internal API — public surface in v5 per
                  // their roadmap; until then we reach into $app.
                  const c = calendar as unknown as {
                    $app: {
                      calendarState: { setView: (n: string, d: unknown) => void };
                      datePickerState: { selectedDate: { value: unknown } };
                    };
                  };
                  c.$app.calendarState.setView(
                    opt.id,
                    c.$app.datePickerState.selectedDate.value,
                  );
                }}
                className={`rounded-sm border px-3 py-1.5 font-mono text-[11px] uppercase tracking-widest transition-colors ${
                  isActive
                    ? "border-signal/60 bg-signal/15 text-signal shadow-[0_0_8px_rgba(0,229,255,0.2)]"
                    : "border-hairline-signal/30 bg-void-2/60 text-dust hover:bg-signal/10 hover:text-parchment"
                }`}
              >
                {opt.label}
              </button>
            );
          })}
        </div>
      )}
      <div
        ref={calendarViewportRef}
        className="sx-react-calendar-wrapper h-[calc(100vh-220px)] overflow-y-auto rounded-sm border border-hairline-signal/30"
      >
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

      <ExecutionCorrectionDialog
        task={correctionTask}
        onClose={() => setCorrectionTask(null)}
        onSaved={refreshAll}
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
          <dt className="text-dust">State</dt>
          <dd className="text-parchment">{task.state.toLowerCase()}</dd>
          <dt className="text-dust">Planned</dt>
          <dd className="text-parchment">
            {fmt(task.start)} → {fmt(task.end)}
          </dd>
          {task.executed_start && (
            <>
              <dt className="text-dust">Executed</dt>
              <dd className="text-parchment">
                {fmt(task.executed_start)} → {fmt(task.executed_end)}
              </dd>
            </>
          )}
          {task.planned_duration_minutes !== null && (
            <>
              <dt className="text-dust">Planned duration</dt>
              <dd className="text-parchment">
                {task.planned_duration_minutes} min
              </dd>
            </>
          )}
          {task.executed_duration_minutes !== null && (
            <>
              <dt className="text-dust">Actual duration</dt>
              <dd className="text-parchment">
                {task.executed_duration_minutes} min
                {task.duration_delta_minutes !== null && (
                  <span className="ml-2 text-dust-deep">
                    (Δ {task.duration_delta_minutes > 0 ? "+" : ""}
                    {task.duration_delta_minutes})
                  </span>
                )}
              </dd>
            </>
          )}
          {task.pre_task_readiness !== null && (
            <>
              <dt className="text-dust">Readiness</dt>
              <dd className="text-parchment">
                {task.pre_task_readiness}/5
              </dd>
            </>
          )}
          {task.post_task_reflection !== null && (
            <>
              <dt className="text-dust">Focus</dt>
              <dd className="text-parchment">
                {task.post_task_reflection}/5
              </dd>
            </>
          )}
          {task.category && (
            <>
              <dt className="text-dust">Category</dt>
              <dd className="text-parchment">{task.category}</dd>
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
