"use client";
/**
 * PulseDeadlinesV2 — right rail deadlines panel for /pulse v2.
 *
 * Reference-image vocabulary: top section is OVERDUE in ember (when
 * present), below it the next 5 upcoming deadlines. Each row shows
 * the days-out delta + due date + "Moodle" badge if external_source.
 * Tighter than the v1 DeadlinesPulse — fits the right rail.
 */
import Link from "next/link";
import { format } from "date-fns";
import {
  computeOverdueDeadlines,
  type DeadlineResponse,
} from "@/lib/deadlines";

const SEVEN_DAYS_MS = 7 * 24 * 60 * 60 * 1000;

export interface PulseDeadlinesV2Props {
  deadlines: DeadlineResponse[];
}

function fmtDelta(iso: string, nowMs: number): string {
  const dueMs = new Date(iso).getTime();
  const deltaMin = Math.round((dueMs - nowMs) / 60000);
  if (deltaMin < 0) {
    const ago = Math.abs(deltaMin);
    if (ago < 60) return `${ago}m late`;
    const hours = Math.floor(ago / 60);
    if (hours < 24) return `${hours}h late`;
    return `${Math.floor(hours / 24)}d late`;
  }
  if (deltaMin < 60) return `in ${deltaMin}m`;
  const hours = Math.floor(deltaMin / 60);
  if (hours < 24) return `in ${hours}h`;
  return `in ${Math.floor(hours / 24)}d`;
}

function fmtDue(iso: string): string {
  try {
    return format(new Date(iso), "MMM d · HH:mm");
  } catch {
    return iso;
  }
}

export function PulseDeadlinesV2({ deadlines }: PulseDeadlinesV2Props) {
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
      return due >= nowMs && due - nowMs <= SEVEN_DAYS_MS * 4;
    })
    .sort(
      (a, b) =>
        new Date(a.due_at_utc).getTime() - new Date(b.due_at_utc).getTime()
    );

  const showCount = Math.max(0, 6 - Math.min(overdue.length, 3));

  return (
    <div className="terminal-panel flex h-full flex-col">
      <div className="flex items-center justify-between border-b border-hairline px-5 py-3.5">
        <div className="font-display text-[10px] font-medium uppercase tracking-macro text-dust">
          <span className="opacity-50">[ </span>
          Deadlines
          <span className="opacity-50"> ]</span>
        </div>
        <Link
          href="/deadlines"
          className="font-mono text-[10px] uppercase tracking-widest text-dust-deep transition-colors hover:text-signal"
        >
          All →
        </Link>
      </div>
      <div className="flex-1 overflow-y-auto">
        {overdue.length > 0 && (
          <div className="alert-bar-ember relative bg-ember/5 px-5 py-3">
            <div className="mb-2 flex items-baseline justify-between">
              <div className="flex items-center gap-2">
                <span
                  aria-hidden
                  className="status-dot"
                  style={{ ["--dot-color" as string]: "#FF8A3D" }}
                />
                <div className="font-display text-[10px] font-semibold uppercase tracking-macro text-ember">
                  <span className="opacity-50">[ </span>
                  Overdue
                  <span className="opacity-50"> ]</span>
                </div>
              </div>
              <span className="font-display text-xs tabular-nums text-ember/85">
                {overdue.length.toString().padStart(2, "0")}
              </span>
            </div>
            <ul className="flex flex-col gap-2">
              {overdue.slice(0, 3).map((d) => (
                <li key={d.deadline_id} className="flex items-baseline gap-2">
                  <div className="min-w-0 flex-1">
                    <div className="truncate text-[12px] text-parchment">
                      {d.title}
                    </div>
                    <div className="font-mono text-[10px] text-ember/75">
                      {fmtDelta(d.due_at_utc, nowMs)} · {fmtDue(d.due_at_utc)}
                    </div>
                  </div>
                  {d.external_source?.startsWith("moodle") && (
                    <span className="shrink-0 rounded border border-ember/30 px-1.5 py-px text-[8px] uppercase tracking-widest text-ember/85">
                      Moodle
                    </span>
                  )}
                </li>
              ))}
              {overdue.length > 3 && (
                <li className="font-mono text-[10px] uppercase tracking-widest text-ember/65">
                  +{overdue.length - 3} more overdue
                </li>
              )}
            </ul>
          </div>
        )}
        {upcoming.length === 0 && overdue.length === 0 ? (
          <div className="px-5 py-10 text-center text-[11px] text-dust-deep">
            No deadlines yet.
            <br />
            <Link
              href="/settings"
              className="text-signal underline-offset-2 hover:underline"
            >
              Connect Moodle
            </Link>{" "}
            to import them.
          </div>
        ) : upcoming.length === 0 ? null : (
          <ul className="flex flex-col">
            {upcoming.slice(0, showCount).map((d) => (
              <li
                key={d.deadline_id}
                className="flex items-baseline gap-2.5 border-b border-hairline px-5 py-2.5 last:border-b-0 hover:bg-void-2/50"
              >
                <span
                  aria-hidden
                  className="mt-1.5 inline-block h-1.5 w-1.5 shrink-0 rounded-full bg-signal/60"
                />
                <div className="min-w-0 flex-1 leading-tight">
                  <div className="truncate text-[12px] text-parchment">
                    {d.title}
                  </div>
                  <div className="font-mono text-[9px] uppercase tracking-widest text-dust-deep">
                    {fmtDelta(d.due_at_utc, nowMs)}
                    {d.category_hint ? ` · ${d.category_hint}` : ""} ·{" "}
                    {fmtDue(d.due_at_utc)}
                  </div>
                </div>
                {d.external_source?.startsWith("moodle") && (
                  <span className="shrink-0 rounded border border-signal/25 px-1.5 py-px text-[8px] uppercase tracking-widest text-signal/75">
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
