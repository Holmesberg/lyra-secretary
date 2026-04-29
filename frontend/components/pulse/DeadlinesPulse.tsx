"use client";
/**
 * DeadlinesPulse — overdue + next-up deadlines for /pulse right rail.
 *
 * Two stacked sections inside one panel:
 *   1. OVERDUE — wrapped in terminal-panel-ember + alert-bar-ember
 *      (the polish vocabulary established earlier today). Sorted
 *      most-recent-due first.
 *   2. Coming up — next 7 days of active/planned deadlines, dust tone.
 *
 * Reuses computeOverdueDeadlines() from lib/deadlines.ts so the
 * overdue semantics match /today exactly (post-sweep missed +
 * pre-sweep planned/active+past). Each row shows the LMS "Moodle"
 * badge when external_source==='moodle_ics' so the user can see at
 * a glance what's coming from the school feed vs what they typed.
 */
import Link from "next/link";
import { format } from "date-fns";
import {
  computeOverdueDeadlines,
  type DeadlineResponse,
} from "@/lib/deadlines";

const SEVEN_DAYS_MS = 7 * 24 * 60 * 60 * 1000;

export interface DeadlinesPulseProps {
  deadlines: DeadlineResponse[];
}

function fmtDue(iso: string): string {
  try {
    const d = new Date(iso);
    return format(d, "EEE MMM d · HH:mm");
  } catch {
    return iso;
  }
}

function fmtDelta(iso: string, nowMs: number): string {
  const dueMs = new Date(iso).getTime();
  const deltaMin = Math.round((dueMs - nowMs) / 60000);
  if (deltaMin < 0) {
    const ago = Math.abs(deltaMin);
    if (ago < 60) return `${ago}m ago`;
    const hours = Math.floor(ago / 60);
    if (hours < 24) return `${hours}h ago`;
    return `${Math.floor(hours / 24)}d ago`;
  }
  if (deltaMin < 60) return `in ${deltaMin}m`;
  const hours = Math.floor(deltaMin / 60);
  if (hours < 24) return `in ${hours}h`;
  return `in ${Math.floor(hours / 24)}d`;
}

export function DeadlinesPulse({ deadlines }: DeadlinesPulseProps) {
  const nowMs = Date.now();
  const overdue = computeOverdueDeadlines(deadlines, { nowMs })
    .map((x) => x.deadline)
    .sort(
      (a, b) =>
        new Date(b.due_at_utc).getTime() - new Date(a.due_at_utc).getTime()
    );
  const overdueIds = new Set(overdue.map((d) => d.deadline_id));
  const upcoming = deadlines
    .filter((d) => {
      if (d.voided_at) return false;
      if (overdueIds.has(d.deadline_id)) return false;
      if (d.state !== "active" && d.state !== "planned") return false;
      const due = new Date(d.due_at_utc).getTime();
      return due >= nowMs && due - nowMs <= SEVEN_DAYS_MS;
    })
    .sort(
      (a, b) =>
        new Date(a.due_at_utc).getTime() - new Date(b.due_at_utc).getTime()
    )
    .slice(0, 5);

  return (
    <div className="flex flex-col gap-4">
      {overdue.length > 0 && (
        <div className="terminal-panel-ember alert-bar-ember p-4">
          <div className="mb-3 flex items-baseline justify-between">
            <div className="flex items-center gap-2">
              <span
                aria-hidden
                className="status-dot"
                style={{ ["--dot-color" as string]: "#FF8A3D" }}
              />
              <div className="font-display text-[11px] font-semibold uppercase tracking-macro text-ember">
                <span className="opacity-50">[ </span>
                Overdue
                <span className="opacity-50"> ]</span>
              </div>
            </div>
            <span className="font-display text-xs tabular-nums text-ember/80">
              {overdue.length.toString().padStart(2, "0")}
            </span>
          </div>
          <ul className="flex flex-col gap-2">
            {overdue.slice(0, 4).map((d) => (
              <li key={d.deadline_id} className="flex items-baseline gap-2">
                <div className="min-w-0 flex-1">
                  <div className="truncate text-xs text-parchment">
                    {d.title}
                  </div>
                  <div className="font-mono text-[10px] text-ember/70">
                    {fmtDelta(d.due_at_utc, nowMs)} · {fmtDue(d.due_at_utc)}
                  </div>
                </div>
                {d.external_source === "moodle_ics" && (
                  <span className="shrink-0 rounded border border-ember/30 px-1.5 py-px text-[9px] uppercase tracking-widest text-ember/80">
                    Moodle
                  </span>
                )}
              </li>
            ))}
            {overdue.length > 4 && (
              <li className="font-mono text-[10px] uppercase tracking-widest text-ember/60">
                +{overdue.length - 4} more on{" "}
                <Link
                  href="/deadlines"
                  className="underline-offset-2 hover:underline"
                >
                  /deadlines
                </Link>
              </li>
            )}
          </ul>
        </div>
      )}

      <div className="terminal-panel p-4">
        <div className="mb-3 flex items-baseline justify-between">
          <div className="font-display text-[11px] font-medium uppercase tracking-macro text-dust">
            <span className="text-signal/70">{">>"}</span>{" "}
            <span className="ml-1">Coming up · 7d</span>
          </div>
          <Link
            href="/deadlines"
            className="font-mono text-[10px] uppercase tracking-widest text-dust-deep hover:text-signal"
          >
            All →
          </Link>
        </div>
        {upcoming.length === 0 ? (
          <div className="py-3 text-center text-[11px] text-dust-deep">
            Nothing in the next 7 days.
          </div>
        ) : (
          <ul className="flex flex-col gap-2.5">
            {upcoming.map((d) => (
              <li key={d.deadline_id} className="flex items-baseline gap-2">
                <span
                  aria-hidden
                  className="mt-1 inline-block h-1.5 w-1.5 shrink-0 rounded-full bg-signal/60"
                />
                <div className="min-w-0 flex-1">
                  <div className="truncate text-xs text-parchment">
                    {d.title}
                  </div>
                  <div className="font-mono text-[10px] text-dust">
                    {fmtDelta(d.due_at_utc, nowMs)} ·{" "}
                    {d.category_hint && (
                      <span className="text-dust-deep">
                        {d.category_hint} ·{" "}
                      </span>
                    )}
                    {fmtDue(d.due_at_utc)}
                  </div>
                </div>
                {d.external_source === "moodle_ics" && (
                  <span className="shrink-0 rounded border border-signal/30 px-1.5 py-px text-[9px] uppercase tracking-widest text-signal/70">
                    Moodle
                  </span>
                )}
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}
