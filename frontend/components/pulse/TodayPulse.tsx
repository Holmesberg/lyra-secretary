"use client";
/**
 * TodayPulse — compact today's-schedule panel for /pulse.
 *
 * Renders today's tasks as dense readout rows. Bypasses the heavy
 * TaskRow component (which carries the full /today action surface:
 * start, stop, skip, delete, LLM chips, pause-confirm chips, etc.) —
 * /pulse is a glance surface, not a control surface. Tap a row → jump
 * to /today scrolled to it.
 *
 * State pills mirror the Neural Noir vocabulary the OVERDUE polish
 * established: bracketed Chakra Petch labels, status dots, restrained
 * single-color treatment per row.
 */
import Link from "next/link";
import { format } from "date-fns";
import type { TaskRow } from "@/lib/tasks";

export interface TodayPulseProps {
  tasks: TaskRow[];
}

const STATE_TONE: Record<
  string,
  { dot: string; label: string; pill: string }
> = {
  PLANNED: {
    dot: "#4DD4E8",
    label: "Planned",
    pill: "text-signal",
  },
  EXECUTING: {
    dot: "#00E5FF",
    label: "In flight",
    pill: "neon-cyan",
  },
  PAUSED: {
    dot: "#F5A96A",
    label: "Paused",
    pill: "text-ember",
  },
  EXECUTED: {
    dot: "#4A5168",
    label: "Done",
    pill: "text-dust-deep",
  },
  SKIPPED: {
    dot: "#4A5168",
    label: "Skipped",
    pill: "text-dust-deep",
  },
};

function fmtTime(iso: string | null): string {
  if (!iso) return "—";
  try {
    return format(new Date(iso), "HH:mm");
  } catch {
    return "—";
  }
}

export function TodayPulse({ tasks }: TodayPulseProps) {
  const visible = tasks
    .filter((t) => !t.voided_at && t.state !== "DELETED")
    .sort((a, b) => {
      const ax = a.start ? new Date(a.start).getTime() : Infinity;
      const bx = b.start ? new Date(b.start).getTime() : Infinity;
      return ax - bx;
    });

  return (
    <div className="terminal-panel flex flex-col">
      <div className="flex items-center justify-between border-b border-hairline px-5 py-3">
        <div className="font-display text-[11px] font-medium uppercase tracking-macro text-dust">
          <span className="text-signal/70">{">>"}</span>{" "}
          <span className="ml-1">Today</span>{" "}
          <span className="ml-1 text-dust-deep">({visible.length})</span>
        </div>
        <Link
          href="/today"
          className="font-mono text-[10px] uppercase tracking-widest text-dust-deep transition-colors hover:text-signal"
        >
          Open →
        </Link>
      </div>
      {visible.length === 0 ? (
        <div className="px-5 py-10 text-center text-xs text-dust-deep">
          Nothing on the day yet.
          <br />
          <Link
            href="/today"
            className="text-signal underline-offset-2 hover:underline"
          >
            Brain dump on Today
          </Link>{" "}
          to add the first thing.
        </div>
      ) : (
        <ul className="flex flex-col">
          {visible.map((t) => {
            const tone = STATE_TONE[t.state] ?? STATE_TONE.PLANNED;
            const dim = t.state === "EXECUTED" || t.state === "SKIPPED";
            return (
              <li
                key={t.task_id}
                className="group flex items-center gap-3 border-b border-hairline px-5 py-2.5 last:border-b-0 hover:bg-void-2/50"
              >
                <div className="font-mono text-[11px] tabular-nums text-dust">
                  {fmtTime(t.start)}
                </div>
                <span
                  aria-hidden
                  className="status-dot shrink-0"
                  style={{ ["--dot-color" as string]: tone.dot }}
                />
                <div
                  className={`min-w-0 flex-1 truncate text-xs ${
                    dim ? "text-dust line-through decoration-dust-deep/60" : "text-parchment"
                  }`}
                  title={t.title}
                >
                  {t.title}
                </div>
                {t.category && (
                  <span className="hidden font-mono text-[9px] uppercase tracking-widest text-dust-deep sm:inline">
                    {t.category}
                  </span>
                )}
                <span
                  className={`font-display text-[9px] font-medium uppercase tracking-macro ${tone.pill}`}
                >
                  <span className="opacity-50">[</span>
                  {tone.label}
                  <span className="opacity-50">]</span>
                </span>
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}
