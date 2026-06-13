"use client";
/**
 * PulseTodaysPlanV2 — left column compact today's plan for /pulse v2.
 *
 * Tighter than TodayPulse v1: fewer columns, thinner rows, hides the
 * category to give the title room. Status pills follow the same
 * bracketed Chakra Petch + status-dot vocabulary as the rest of the
 * dashboard.
 */
import Link from "next/link";
import { format } from "date-fns";
import type { TaskRow } from "@/lib/tasks";

export interface PulseTodaysPlanV2Props {
  tasks: TaskRow[];
}

const STATE_TONE: Record<
  string,
  { dot: string; label: string; pill: string }
> = {
  PLANNED: { dot: "#4DD4E8", label: "Planned", pill: "text-signal" },
  EXECUTING: { dot: "#00E5FF", label: "Now", pill: "neon-cyan" },
  PAUSED: { dot: "#F5A96A", label: "Paused", pill: "text-ember" },
  EXECUTED: { dot: "#4A5168", label: "Done", pill: "text-dust-deep" },
  SKIPPED: { dot: "#4A5168", label: "Skipped", pill: "text-dust-deep" },
};

function fmtTime(iso: string | null): string {
  if (!iso) return "—";
  try {
    return format(new Date(iso), "HH:mm");
  } catch {
    return "—";
  }
}

export function PulseTodaysPlanV2({ tasks }: PulseTodaysPlanV2Props) {
  const visible = tasks
    .filter((t) => !t.voided_at && t.state !== "DELETED")
    .sort((a, b) => {
      const ax = a.start ? new Date(a.start).getTime() : Infinity;
      const bx = b.start ? new Date(b.start).getTime() : Infinity;
      return ax - bx;
    });

  return (
    <div className="terminal-panel flex h-full flex-col">
      <div className="flex items-center justify-between border-b border-hairline px-5 py-3.5">
        <div className="font-display text-[10px] font-medium uppercase tracking-macro text-dust">
          <span className="opacity-50">[ </span>
          Today's plan
          <span className="opacity-50"> ]</span>
        </div>
        <Link
          href="/today"
          className="font-mono text-[10px] uppercase tracking-widest text-dust-deep transition-colors hover:text-signal"
        >
          Open →
        </Link>
      </div>
      {visible.length === 0 ? (
        <div className="flex-1 px-5 py-10 text-center text-xs text-dust-deep">
          Nothing on the day yet.
          <br />
          <Link
            href="/pulse#quick-capture"
            className="text-signal underline-offset-2 hover:underline"
          >
            Brain dump
          </Link>{" "}
          to add the first.
        </div>
      ) : (
        <ul className="flex flex-col">
          {visible.slice(0, 8).map((t) => {
            const tone = STATE_TONE[t.state] ?? STATE_TONE.PLANNED;
            const dim = t.state === "EXECUTED" || t.state === "SKIPPED";
            return (
              <li
                key={t.task_id}
                className="group flex items-baseline gap-2.5 border-b border-hairline px-5 py-2.5 last:border-b-0 hover:bg-void-2/50"
              >
                <span
                  aria-hidden
                  className="status-dot mt-1 shrink-0"
                  style={{ ["--dot-color" as string]: tone.dot }}
                />
                <div className="min-w-0 flex-1 leading-tight">
                  <div
                    className={`truncate text-[12px] ${
                      dim
                        ? "text-dust line-through decoration-dust-deep/60"
                        : "text-parchment"
                    }`}
                    title={t.title}
                  >
                    {t.title}
                  </div>
                  <div className="font-mono text-[9px] uppercase tracking-widest text-dust-deep">
                    {fmtTime(t.start)}
                    {t.planned_duration_minutes !== null &&
                      ` · ${t.planned_duration_minutes}m`}
                  </div>
                </div>
                <span
                  className={`font-display text-[8px] font-medium uppercase tracking-macro ${tone.pill}`}
                >
                  <span className="opacity-50">[</span>
                  {tone.label}
                  <span className="opacity-50">]</span>
                </span>
              </li>
            );
          })}
          {visible.length > 8 && (
            <li className="border-t border-hairline px-5 py-2.5 text-center font-mono text-[10px] uppercase tracking-widest text-dust-deep">
              +{visible.length - 8} more on{" "}
              <Link
                href="/today"
                className="text-signal underline-offset-2 hover:underline"
              >
                /today
              </Link>
            </li>
          )}
        </ul>
      )}
    </div>
  );
}
