"use client";
/**
 * PulseHero — at-a-glance stat readouts for /pulse.
 *
 * Six cells in a 3x2 grid. Mono digits, font-display Chakra Petch hero
 * numbers, neon-cyan glow on calm stats, neon-ember on overdue. Reads
 * as a CRT readout panel, not a SaaS stat card.
 *
 * Each cell has the same anatomy: hero number + bracketed eyebrow label.
 * Inactive/zero cells dim their numbers but keep the label so the grid
 * structure stays legible.
 */
import type { DeadlineResponse } from "@/lib/deadlines";
import type { TaskRow } from "@/lib/tasks";

export interface PulseHeroProps {
  tasks: TaskRow[];
  deadlines: DeadlineResponse[];
  /** Total EXECUTED non-voided sessions across all time, from /me. Powers
   *  the "milestones" cell so the hero acknowledges long-term momentum
   *  even on a slow day. */
  executedSessionCount: number;
}

function pad2(n: number): string {
  return n.toString().padStart(2, "0");
}

function topCourseCode(tasks: TaskRow[], deadlines: DeadlineResponse[]): string | null {
  // Mode of category_hint across today's tasks + ALL active deadlines.
  // Surfaces the user's most-loaded course at a glance — Moodle imports
  // populate `category_hint` with the course code (CSE281, ABC101, …).
  const counts = new Map<string, number>();
  const bump = (key: string | null | undefined) => {
    if (!key) return;
    counts.set(key, (counts.get(key) ?? 0) + 1);
  };
  for (const t of tasks) bump(t.category);
  for (const d of deadlines) {
    if (d.voided_at) continue;
    if (d.state === "active" || d.state === "planned") bump(d.category_hint);
  }
  let top: string | null = null;
  let topN = 0;
  for (const [k, n] of counts) {
    if (n > topN) {
      top = k;
      topN = n;
    }
  }
  return top;
}

export function PulseHero({ tasks, deadlines, executedSessionCount }: PulseHeroProps) {
  const nowMs = Date.now();
  const planned = tasks.filter((t) => t.state === "PLANNED" && !t.voided_at).length;
  const executing = tasks.filter(
    (t) => (t.state === "EXECUTING" || t.state === "PAUSED") && !t.voided_at
  ).length;
  const executedToday = tasks.filter((t) => t.state === "EXECUTED" && !t.voided_at);
  const focusMinutes = executedToday.reduce(
    (s, t) => s + Math.max(0, t.executed_duration_minutes ?? 0),
    0
  );
  const overdue = deadlines.filter((d) => {
    if (d.voided_at) return false;
    if (d.state === "missed") return true;
    if (d.state === "planned" || d.state === "active") {
      return new Date(d.due_at_utc).getTime() < nowMs;
    }
    return false;
  }).length;
  const topCourse = topCourseCode(tasks, deadlines);

  const cells: Cell[] = [
    { label: "Planned", value: pad2(planned), tone: planned > 0 ? "signal" : "dust" },
    {
      label: "In flight",
      value: pad2(executing),
      tone: executing > 0 ? "signal-neon" : "dust",
    },
    {
      label: "Done today",
      value: pad2(executedToday.length),
      tone: executedToday.length > 0 ? "signal" : "dust",
    },
    {
      label: "Focus today",
      value: focusMinutes >= 60 ? `${Math.floor(focusMinutes / 60)}h${pad2(focusMinutes % 60)}` : `${focusMinutes}m`,
      tone: focusMinutes > 0 ? "signal" : "dust",
      mono: true,
    },
    {
      label: "Overdue",
      value: pad2(overdue),
      tone: overdue > 0 ? "ember" : "dust",
    },
    {
      label: topCourse ? "Top course" : "Sessions",
      value: topCourse ?? executedSessionCount.toString().padStart(3, "0"),
      tone: "dust-signal",
      mono: !topCourse,
    },
  ];

  return (
    <div className="terminal-panel grid grid-cols-3 gap-px overflow-hidden bg-hairline">
      {cells.map((c, i) => (
        <HeroCell key={i} cell={c} />
      ))}
    </div>
  );
}

interface Cell {
  label: string;
  value: string;
  tone: "signal" | "signal-neon" | "ember" | "dust" | "dust-signal";
  /** When true, force tabular-nums + mono for fixed-width digit display. */
  mono?: boolean;
}

function HeroCell({ cell }: { cell: Cell }) {
  const valueColor =
    cell.tone === "ember"
      ? "neon-ember"
      : cell.tone === "signal-neon"
        ? "neon-cyan"
        : cell.tone === "signal"
          ? "text-signal"
          : cell.tone === "dust-signal"
            ? "text-parchment"
            : "text-dust-deep";
  const labelColor =
    cell.tone === "ember"
      ? "text-ember/75"
      : cell.tone === "dust"
        ? "text-dust-deep"
        : "text-dust";
  return (
    <div className="flex flex-col gap-2 bg-void-2/70 px-5 py-4">
      <div
        className={`font-display text-[2.4rem] font-semibold leading-none tabular-nums ${valueColor}`}
        style={{ letterSpacing: "-0.02em" }}
      >
        {cell.value}
      </div>
      <div
        className={`font-display text-[10px] font-medium uppercase tracking-macro ${labelColor}`}
      >
        <span className="opacity-50">[ </span>
        {cell.label}
        <span className="opacity-50"> ]</span>
      </div>
    </div>
  );
}
