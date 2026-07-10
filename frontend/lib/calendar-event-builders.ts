import { Temporal } from "temporal-polyfill";
import type { TaskRow } from "./tasks";

export const CALENDAR_TIMEZONE = "Africa/Cairo";

export type CalendarQueryRange = {
  from: string;
  to: string;
};

export type ScheduleRange = {
  start: Temporal.ZonedDateTime;
  end: Temporal.ZonedDateTime;
};

export function initialCalendarQueryRange(): CalendarQueryRange {
  const today = Temporal.Now.plainDateISO(CALENDAR_TIMEZONE);
  const weekStart = today.subtract({ days: today.dayOfWeek - 1 });
  return {
    from: weekStart.toString(),
    to: weekStart.add({ days: 6 }).toString(),
  };
}

export function calendarRangeToQueryRange(range: ScheduleRange): CalendarQueryRange {
  return {
    from: range.start.toPlainDate().toString(),
    to: range.end.toPlainDate().toString(),
  };
}

export function calendarIdForState(state: TaskRow["state"]): string {
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

export function toZdt(iso: string): Temporal.ZonedDateTime {
  return Temporal.PlainDateTime.from(iso).toZonedDateTime(CALENDAR_TIMEZONE);
}

export function deadlineToZdt(iso: string): Temporal.ZonedDateTime {
  return Temporal.Instant.from(iso).toZonedDateTimeISO(CALENDAR_TIMEZONE);
}
