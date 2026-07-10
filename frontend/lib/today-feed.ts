import { format } from "date-fns";
import type { ExternalCalendarEvent } from "@/lib/calendar";
import type { DeadlineResponse } from "@/lib/deadlines";
import type { TaskRow } from "@/lib/tasks";

export interface TodayDueDeadline {
  deadline: DeadlineResponse;
  overdue: boolean;
}

export type TodayFeedItem =
  | { kind: "task"; task: TaskRow }
  | { kind: "external"; event: ExternalCalendarEvent }
  | { kind: "deadline"; deadline: DeadlineResponse; overdue: boolean };

export function localDateKey(d: Date) {
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
}

export function parseDateKey(s: string): Date {
  const [y, m, d] = s.split("-").map(Number);
  return new Date(y, m - 1, d);
}

function todayTaskSortKey(t: TaskRow): number {
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

export function buildTodayDueDeadlines({
  deadlines,
  viewedDate,
  today,
  nowMs,
}: {
  deadlines: DeadlineResponse[] | null | undefined;
  viewedDate: string;
  today: string;
  nowMs: number;
}): TodayDueDeadline[] {
  const isViewingToday = viewedDate === today;
  return (deadlines ?? []).flatMap((d) => {
    if (d.voided_at) return [];
    const due = new Date(d.due_at_utc);
    const dueLocalKey = format(due, "yyyy-MM-dd");
    // OVERDUE definition unifies two paths:
    //   (a) post-sweep: sweep_missed_deadlines transitioned the row to missed.
    //   (b) pre-sweep: planned/active row is past due before the sweep runs.
    // Both paths pin to /today until the user handles the deadline.
    const isOverdue =
      d.state === "missed" ||
      ((d.state === "planned" || d.state === "active") &&
        due.getTime() < nowMs);

    // Show on the deadline's actual due day. The action-prompt OVERDUE pill
    // only fires on today's view; past/future browsing stays historical.
    if (dueLocalKey === viewedDate) {
      return [{ deadline: d, overdue: isViewingToday && isOverdue }];
    }
    // Pin overdue items to today so missed obligations cannot silently vanish
    // after the hourly sweep flips them to missed.
    if (isViewingToday && isOverdue) {
      return [{ deadline: d, overdue: true }];
    }
    return [];
  });
}

export function buildTodayFeed({
  tasks,
  events,
  dueDeadlines,
  nowMs,
}: {
  tasks: TaskRow[] | null | undefined;
  events: ExternalCalendarEvent[];
  dueDeadlines: TodayDueDeadline[];
  nowMs: number;
}): { top: TodayFeedItem[]; bottom: TodayFeedItem[] } {
  if (!tasks) return { top: [], bottom: [] };
  const visible = tasks.filter((t) => !t.voided_at);
  const plannedTasks = visible.filter((t) => t.state === "PLANNED");
  const restTasks = visible.filter((t) => t.state !== "PLANNED");
  const gcalFuture = events.filter((e) => new Date(e.end).getTime() > nowMs);
  const gcalPast = events.filter((e) => new Date(e.end).getTime() <= nowMs);

  const topItems: TodayFeedItem[] = [
    ...plannedTasks.map((t): TodayFeedItem => ({ kind: "task", task: t })),
    ...gcalFuture.map((e): TodayFeedItem => ({ kind: "external", event: e })),
    // Deadlines always live in the top bucket: pending-action items, even
    // when overdue, not "what already happened" rows.
    ...dueDeadlines.map(
      (x): TodayFeedItem => ({
        kind: "deadline",
        deadline: x.deadline,
        overdue: x.overdue,
      }),
    ),
  ].sort((a, b) => {
    const at =
      a.kind === "task"
        ? todayTaskSortKey(a.task)
        : a.kind === "external"
          ? new Date(a.event.start).getTime()
          : new Date(a.deadline.due_at_utc).getTime();
    const bt =
      b.kind === "task"
        ? todayTaskSortKey(b.task)
        : b.kind === "external"
          ? new Date(b.event.start).getTime()
          : new Date(b.deadline.due_at_utc).getTime();
    return at - bt;
  });

  const bottomItems: TodayFeedItem[] = [
    ...restTasks.map((t): TodayFeedItem => ({ kind: "task", task: t })),
    ...gcalPast.map((e): TodayFeedItem => ({ kind: "external", event: e })),
  ].sort((a, b) => {
    const at =
      a.kind === "task"
        ? todayTaskSortKey(a.task)
        : a.kind === "external"
          ? new Date(a.event.end).getTime()
          : new Date(a.deadline.due_at_utc).getTime();
    const bt =
      b.kind === "task"
        ? todayTaskSortKey(b.task)
        : b.kind === "external"
          ? new Date(b.event.end).getTime()
          : new Date(b.deadline.due_at_utc).getTime();
    return bt - at;
  });

  return { top: topItems, bottom: bottomItems };
}
