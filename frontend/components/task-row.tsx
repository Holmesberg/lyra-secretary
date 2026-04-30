"use client";
import { format } from "date-fns";
import { Play, Square, Ban, Trash2 } from "lucide-react";
import type { TaskRow as TaskRowType } from "@/lib/tasks";
import { getCategoryColor, STATE_STYLES } from "@/lib/categories";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { LlmEnrichmentChip } from "@/components/llm-enrichment-chip";


interface Props {
  task: TaskRowType;
  disableStart: boolean;
  onStart: (task: TaskRowType) => void;
  onStop: () => void;
  onSkip?: (task: TaskRowType) => void;
  onDelete?: (task: TaskRowType) => void;
  onEdit?: (task: TaskRowType) => void;
  selected?: boolean;
  showCheckbox?: boolean;
  onToggleSelect?: (taskId: string) => void;
  // Fires when user hovers or clicks this row's Start button. Page-level
  // owner uses this to surface a contextual orphan-warning when a paused
  // timer is present (see ActiveTimerBanner orphan-warning prop).
  onStartHover?: () => void;
  // Fires after the LLM enrichment chip has confirmed/rejected a binding.
  // Page-level owner refetches /tasks/query so the chip stops rendering.
  onLlmChipChanged?: () => void;
}

// Research layer: readiness X → focus Y ±Nmin
// Typography kept subordinate to title (text-[11px] white/40).
function ResearchLayer({ task }: { task: TaskRowType }) {
  const { state, pre_task_readiness, post_task_reflection, duration_delta_minutes } = task;

  if (state === "SKIPPED") {
    return <span className="font-mono text-[11px] text-dust-deep">—</span>;
  }
  if (state === "PLANNED") return null;

  if (state === "EXECUTING" || state === "PAUSED") {
    if (pre_task_readiness == null) return null;
    return (
      <span className="font-mono text-[11px] text-dust">
        ready {pre_task_readiness} →
      </span>
    );
  }

  // EXECUTED
  if (pre_task_readiness == null && post_task_reflection == null) return null;
  const delta = duration_delta_minutes;
  const deltaStr =
    delta == null
      ? ""
      : delta === 0
      ? " ±0min"
      : delta > 0
      ? ` −${delta}min`
      : ` +${Math.abs(delta)}min`;
  return (
    <span className="font-mono text-[11px] text-dust">
      {pre_task_readiness ?? "?"} → {post_task_reflection ?? "?"}
      {deltaStr}
    </span>
  );
}

export function TaskRow({
  task, disableStart, onStart, onStop, onSkip, onDelete, onEdit,
  selected, showCheckbox, onToggleSelect, onStartHover, onLlmChipChanged,
}: Props) {
  // P1-1: 12-hour format.
  const start = task.start ? format(new Date(task.start), "h:mm a") : "—";
  const end = task.end ? format(new Date(task.end), "h:mm a") : "—";
  const cat = task.category as string | null;
  const catColor = getCategoryColor(cat);
  const state = task.state;
  const isLive = state === "EXECUTING" || state === "PAUSED";
  const isTerminal = state === "EXECUTED" || state === "SKIPPED";

  return (
    <div
      className={cn(
        "group flex items-center gap-2 rounded-sm border border-hairline bg-void-2/40 px-2.5 py-2 transition-colors sm:gap-4 sm:px-4 sm:py-3",
        selected && "border-signal/40 bg-signal/5",
        isLive && !selected && "border-signal/30 bg-signal/[0.03]"
      )}
    >
      {onToggleSelect && (
        <input
          type="checkbox"
          checked={!!selected}
          onChange={() => onToggleSelect(task.task_id)}
          className={cn(
            "h-3.5 w-3.5 shrink-0 cursor-pointer accent-[#4dd4e8]",
            showCheckbox ? "opacity-100" : "opacity-0 group-hover:opacity-100"
          )}
          onClick={(e) => e.stopPropagation()}
        />
      )}
      <div className="w-28 font-mono text-xs text-dust">
        {start}–{end}
      </div>
      <div
        className={cn("min-w-0 flex-1", state === "PLANNED" && onEdit && "cursor-pointer")}
        onClick={() => state === "PLANNED" && onEdit?.(task)}
      >
        <div className="truncate text-sm text-parchment">{task.title}</div>
        {/* LLM enrichment chip — magic-for-alpha W1, 2026-04-28.
            Only renders when llm_parse_status is 'enriched' AND the user
            hasn't already taken ownership of the binding. Self-suppresses
            otherwise. Stops the row's PLANNED-edit click from bubbling so
            chip clicks don't open the edit modal. */}
        {state === "PLANNED" && (
          <div onClick={(e) => e.stopPropagation()} className="mt-1.5">
            <LlmEnrichmentChip task={task} onChanged={onLlmChipChanged} />
          </div>
        )}
      </div>
      <ResearchLayer task={task} />
      {cat && catColor && (
        <span
          className={cn(
            "rounded border px-2 py-0.5 text-[10px] uppercase tracking-wide",
            catColor
          )}
        >
          {cat.replace("_", " ")}
        </span>
      )}
      <span
        className={cn(
          "rounded border px-2 py-0.5 text-[10px] uppercase tracking-wide",
          STATE_STYLES[state] || STATE_STYLES.PLANNED
        )}
      >
        {state}
      </span>
      <div className="flex items-center gap-1">
        {state === "PLANNED" && (
          <>
            <Button
              size="sm"
              variant="secondary"
              onMouseEnter={onStartHover}
              onFocus={onStartHover}
              onClick={() => { onStartHover?.(); onStart(task); }}
              disabled={disableStart}
              title={disableStart ? "Another timer is active" : "Start timer"}
            >
              <Play className="h-3.5 w-3.5" />
            </Button>
            {onSkip && (
              <Button
                size="sm"
                variant="ghost"
                onClick={() => onSkip(task)}
                title="Mark skipped"
              >
                <Ban className="h-3.5 w-3.5" />
              </Button>
            )}
            {onDelete && (
              <Button
                size="sm"
                variant="ghost"
                onClick={() => onDelete(task)}
                title="Delete task"
                className="text-dust-deep hover:text-ember"
              >
                <Trash2 className="h-3.5 w-3.5" />
              </Button>
            )}
          </>
        )}
        {isLive && (
          <>
            <Button size="sm" variant="secondary" onClick={onStop} title="Stop timer">
              <Square className="h-3.5 w-3.5" />
            </Button>
            {onSkip && (
              <Button
                size="sm"
                variant="ghost"
                onClick={() => onSkip(task)}
                title="Stop and skip"
              >
                <Ban className="h-3.5 w-3.5" />
              </Button>
            )}
          </>
        )}
        {isTerminal && <div className="w-8" />}
      </div>
    </div>
  );
}
