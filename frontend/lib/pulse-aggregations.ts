/**
 * Client-side aggregations for the /pulse v2 dashboard.
 *
 * Computes time-series + bucket aggregates from the raw task rows the
 * existing /v1/tasks/query endpoint already returns. Keeps the backend
 * untouched — no new endpoints, no schema changes.
 *
 * Performance note: typical alpha user has < 100 tasks/week, so even
 * naive O(n) iterations are sub-millisecond. If we ever hit 1k+/week
 * we'd push these aggregations into a backend analytics endpoint.
 */
import type { TaskRow } from "@/lib/tasks";

export interface DailyPoint {
  date: string; // YYYY-MM-DD
  label: string; // short display label, e.g. "Mon"
  minutes: number;
  count: number;
}

const DAY_LABELS = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];

function pad2(n: number): string {
  return n.toString().padStart(2, "0");
}

function dateKey(d: Date): string {
  return `${d.getFullYear()}-${pad2(d.getMonth() + 1)}-${pad2(d.getDate())}`;
}

/**
 * Sum executed_duration_minutes by day across the last `days` days
 * (inclusive of today). Returns the series ordered oldest-first so
 * Tremor renders left-to-right chronologically.
 */
export function focusMinutesByDay(
  tasks: TaskRow[],
  days: number = 7
): DailyPoint[] {
  const out: DailyPoint[] = [];
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  const dayMs = 24 * 60 * 60 * 1000;

  // Pre-bucket by date for one O(n) pass over tasks.
  const byDate = new Map<string, { minutes: number; count: number }>();
  for (const t of tasks) {
    if (t.voided_at) continue;
    if (t.state !== "EXECUTED") continue;
    if (!t.executed_end) continue;
    const end = new Date(t.executed_end);
    end.setHours(0, 0, 0, 0);
    const key = dateKey(end);
    const slot = byDate.get(key) ?? { minutes: 0, count: 0 };
    slot.minutes += Math.max(0, t.executed_duration_minutes ?? 0);
    slot.count += 1;
    byDate.set(key, slot);
  }

  for (let i = days - 1; i >= 0; i--) {
    const d = new Date(today.getTime() - i * dayMs);
    const key = dateKey(d);
    const slot = byDate.get(key) ?? { minutes: 0, count: 0 };
    out.push({
      date: key,
      label: DAY_LABELS[d.getDay()],
      minutes: Math.round(slot.minutes),
      count: slot.count,
    });
  }
  return out;
}

/**
 * Total focus minutes today (executed_duration_minutes summed over
 * today's EXECUTED tasks). Convenience for the greeting status pill.
 */
export function focusMinutesToday(tasks: TaskRow[]): number {
  const today = dateKey(new Date());
  let total = 0;
  for (const t of tasks) {
    if (t.voided_at || t.state !== "EXECUTED" || !t.executed_end) continue;
    const k = dateKey(new Date(t.executed_end));
    if (k === today) total += Math.max(0, t.executed_duration_minutes ?? 0);
  }
  return Math.round(total);
}

/**
 * Wins today — count of EXECUTED tasks today that finished early
 * (signed_discrepancy <= 0 == finished within or before planned).
 * Falls back to count of EXECUTED if signed_discrepancy null.
 */
export function winsToday(tasks: TaskRow[]): number {
  const today = dateKey(new Date());
  let wins = 0;
  for (const t of tasks) {
    if (t.voided_at || t.state !== "EXECUTED" || !t.executed_end) continue;
    const k = dateKey(new Date(t.executed_end));
    if (k !== today) continue;
    // A "win" = finished within the planned window (delta_minutes <= 0
    // means did not overrun). Null delta defaults to a win — better
    // to overcount on alpha than to undercount and feel discouraging.
    if ((t.duration_delta_minutes ?? 0) <= 0) wins += 1;
  }
  return wins;
}

/**
 * "Longest free planned slot today" — used by the system-insight
 * card. Looks at PLANNED + EXECUTING tasks today, finds the longest
 * uncovered window between now and end of day. Returns null if no
 * gaps. Approximate, not a calendar-conflict-aware solver.
 */
export function nextFreeBlock(
  tasks: TaskRow[]
): { startISO: string; endISO: string; minutes: number } | null {
  const now = new Date();
  const eod = new Date(now);
  eod.setHours(23, 59, 0, 0);
  const upcoming = tasks
    .filter(
      (t) =>
        !t.voided_at &&
        (t.state === "PLANNED" || t.state === "EXECUTING") &&
        t.start &&
        t.end
    )
    .map((t) => ({
      start: new Date(t.start as string),
      end: new Date(t.end as string),
    }))
    .filter((b) => b.end.getTime() > now.getTime())
    .sort((a, b) => a.start.getTime() - b.start.getTime());

  // Build the merged "busy" intervals from now → eod.
  const busy: { start: Date; end: Date }[] = [];
  for (const b of upcoming) {
    const start = b.start.getTime() < now.getTime() ? now : b.start;
    if (busy.length === 0) {
      busy.push({ start, end: b.end });
      continue;
    }
    const last = busy[busy.length - 1];
    if (start.getTime() <= last.end.getTime()) {
      if (b.end.getTime() > last.end.getTime()) last.end = b.end;
    } else {
      busy.push({ start, end: b.end });
    }
  }

  // Gaps between busy intervals (and before first / after last) within
  // [now, eod]. Find the longest.
  let best: { start: Date; end: Date; minutes: number } | null = null;
  let cursor = now;
  for (const b of busy) {
    if (b.start.getTime() > cursor.getTime()) {
      const gap = (b.start.getTime() - cursor.getTime()) / 60000;
      if (!best || gap > best.minutes) {
        best = { start: cursor, end: b.start, minutes: Math.floor(gap) };
      }
    }
    cursor = new Date(Math.max(cursor.getTime(), b.end.getTime()));
  }
  if (cursor.getTime() < eod.getTime()) {
    const gap = (eod.getTime() - cursor.getTime()) / 60000;
    if (!best || gap > best.minutes) {
      best = { start: cursor, end: eod, minutes: Math.floor(gap) };
    }
  }
  if (!best || best.minutes < 15) return null; // too short to call a "block"
  return {
    startISO: best.start.toISOString(),
    endISO: best.end.toISOString(),
    minutes: best.minutes,
  };
}
