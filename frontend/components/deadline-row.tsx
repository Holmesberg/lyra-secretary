"use client";
/**
 * DeadlineRow — renders a deadline as a task-like row in /today's feed.
 *
 * Mirrors `TaskRow` shape (time slot, title, optional category badge,
 * state pill) but stripped of timer affordances: no Start, no Stop, no
 * skip/delete inline. The whole row is click-to-edit (opens
 * DeadlineModal in edit mode), matching the PLANNED-task click idiom in
 * task-row.tsx.
 *
 * Tone is deliberately calmer than a PLANNED task: hairline border,
 * dust text. A deadline is a marker, not an executable. The category
 * badge reuses `getCategoryColor` so user-customs match the rest of
 * the app.
 */
import { format } from "date-fns";
import { Flag } from "lucide-react";
import { cn } from "@/lib/utils";
import { getCategoryColor } from "@/lib/categories";
import type { DeadlineResponse } from "@/lib/deadlines";

interface Props {
  deadline: DeadlineResponse;
  /** True when the deadline's due_at_utc has passed but state is still
   *  active/planned. Renders an "overdue" pill so the operator notices. */
  overdue?: boolean;
  onEdit: (deadline: DeadlineResponse) => void;
}

export function DeadlineRow({ deadline, overdue, onEdit }: Props) {
  const due = deadline.due_at_utc ? new Date(deadline.due_at_utc) : null;
  const timeStr = due ? format(due, "h:mm a") : "—";
  const catColor = getCategoryColor(deadline.category_hint);
  const stateLabel = overdue ? "OVERDUE" : deadline.state.toUpperCase();

  return (
    <div
      className={cn(
        "group flex items-center gap-4 rounded-sm border bg-void-2/30 px-4 py-3 transition-colors cursor-pointer",
        overdue
          ? "border-ember/40 hover:border-ember/60"
          : "border-hairline hover:border-dust/60"
      )}
      onClick={() => onEdit(deadline)}
      title="Click to edit deadline"
    >
      <div
        className={cn(
          "w-28 font-mono text-xs",
          overdue ? "text-ember" : "text-dust"
        )}
      >
        {timeStr}
      </div>
      <div className="flex shrink-0 items-center gap-1.5 text-dust">
        <Flag className="h-3.5 w-3.5" />
        <span className="font-mono text-[10px] uppercase tracking-widest">
          deadline
        </span>
      </div>
      <div className="min-w-0 flex-1">
        <div className="truncate text-sm text-parchment">{deadline.title}</div>
        {deadline.description && (
          <div className="truncate text-[11px] text-dust-deep">
            {deadline.description}
          </div>
        )}
      </div>
      {deadline.category_hint && catColor && (
        <span
          className={cn(
            "rounded border px-2 py-0.5 text-[10px] uppercase tracking-wide",
            catColor
          )}
        >
          {deadline.category_hint.replace("_", " ")}
        </span>
      )}
      {deadline.external_source === "moodle_ics" && (
        <span
          title="Imported from Moodle"
          className="rounded border border-ember/30 bg-ember/10 px-2 py-0.5 text-[10px] uppercase tracking-wide text-ember"
        >
          Moodle
        </span>
      )}
      <span
        className={cn(
          "rounded border px-2 py-0.5 text-[10px] uppercase tracking-wide",
          overdue
            ? "border-ember/40 bg-ember/10 text-ember"
            : deadline.state === "active"
              ? "border-signal/40 bg-signal/10 text-signal"
              : "border-hairline bg-void-2 text-dust"
        )}
      >
        {stateLabel}
      </span>
    </div>
  );
}
