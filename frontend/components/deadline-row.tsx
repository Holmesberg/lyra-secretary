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
 *
 * 2026-05-01 addition: inline "Mark done" button on non-terminal
 * deadlines. Operator pain point with Moodle-imported overdue
 * items — they complete in Moodle but LyraOS has no way to know
 * (iCal feeds carry due dates, not submission status). Inline
 * one-click finish replaces the previous 4-click path through the
 * edit modal. Click bubbling stopped so it doesn't open the modal.
 */
import { useState } from "react";
import { format } from "date-fns";
import { Check, Flag, Loader2 } from "lucide-react";
import { cn } from "@/lib/utils";
import { getCategoryColor } from "@/lib/categories";
import { updateDeadline, type DeadlineResponse } from "@/lib/deadlines";

interface Props {
  deadline: DeadlineResponse;
  /** True when the deadline's due_at_utc has passed but state is still
   *  active/planned. Renders an "overdue" pill so the operator notices. */
  overdue?: boolean;
  onEdit: (deadline: DeadlineResponse) => void;
  /** Fires after a successful inline state change (mark-done). Page-level
   *  owner refetches /v1/deadlines so the row updates. */
  onChanged?: () => void;
}

export function DeadlineRow({ deadline, overdue, onEdit, onChanged }: Props) {
  const due = deadline.due_at_utc ? new Date(deadline.due_at_utc) : null;
  const timeStr = due ? format(due, "h:mm a") : "—";
  const catColor = getCategoryColor(deadline.category_hint);
  const stateLabel = overdue ? "OVERDUE" : deadline.state.toUpperCase();
  const [marking, setMarking] = useState(false);
  const canMarkDone =
    deadline.state === "planned" ||
    deadline.state === "active" ||
    deadline.state === "missed";

  async function handleMarkDone(e: React.MouseEvent) {
    e.stopPropagation();
    if (marking) return;
    setMarking(true);
    try {
      await updateDeadline(deadline.deadline_id, { state: "completed" });
      onChanged?.();
    } catch {
      // Surface failure non-blockingly — operator will notice the row
      // didn't transition + can retry via the edit modal.
      setMarking(false);
    }
  }

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
      {deadline.external_source?.startsWith("moodle") && (
        <span
          title="Imported from Moodle"
          className="rounded border border-ember/30 bg-ember/10 px-2 py-0.5 text-[10px] uppercase tracking-wide text-ember"
        >
          Moodle
        </span>
      )}
      {overdue ? (
        // Live status readout, not a tag. Pulsing dot + bracketed
        // cyber-display label = system alert vibe.
        <span
          className="inline-flex items-center gap-1.5 font-display text-[10px] font-semibold uppercase tracking-macro text-ember"
          style={{ ["--dot-color" as string]: "#FF8A3D" }}
        >
          <span aria-hidden className="status-dot" />
          <span>
            <span className="opacity-50">[ </span>
            OVERDUE
            <span className="opacity-50"> ]</span>
          </span>
        </span>
      ) : (
        <span
          className={cn(
            "rounded border px-2 py-0.5 text-[10px] uppercase tracking-wide",
            deadline.state === "active"
              ? "border-signal/40 bg-signal/10 text-signal"
              : "border-hairline bg-void-2 text-dust"
          )}
        >
          {stateLabel}
        </span>
      )}
      {/* Inline mark-done. Surfaces on planned/active/missed deadlines so
          the operator can one-click finish a Moodle assignment they
          submitted out-of-band. (Moodle iCal feeds carry due dates,
          NOT submission status — LyraOS has no other way to know.) */}
      {canMarkDone && (
        <button
          type="button"
          onClick={handleMarkDone}
          disabled={marking}
          title="Mark this deadline as completed"
          className="inline-flex items-center gap-1 rounded-sm border border-signal/40 bg-signal/5 px-2 py-0.5 text-[10px] uppercase tracking-widest text-signal transition-colors hover:bg-signal/15 disabled:opacity-40"
        >
          {marking ? (
            <Loader2 className="h-3 w-3 animate-spin" />
          ) : (
            <Check className="h-3 w-3" />
          )}
          <span>{marking ? "saving" : "done"}</span>
        </button>
      )}
    </div>
  );
}
