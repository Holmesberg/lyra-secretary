"use client";
import { format } from "date-fns";
import { Play, Square, Ban } from "lucide-react";
import type { TaskRow as TaskRowType } from "@/lib/tasks";
import { CATEGORY_COLORS, type Category } from "@/lib/categories";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

const STATE_STYLES: Record<string, string> = {
  PLANNED: "bg-white/10 text-white/70 border-white/15",
  EXECUTING: "bg-green-500/20 text-green-300 border-green-500/30",
  PAUSED: "bg-yellow-500/20 text-yellow-300 border-yellow-500/30",
  EXECUTED: "bg-blue-500/20 text-blue-300 border-blue-500/30",
  SKIPPED: "bg-red-500/15 text-red-300 border-red-500/25",
};

interface Props {
  task: TaskRowType;
  disableStart: boolean;
  onStart: (task: TaskRowType) => void;
  onStop: () => void;
  onSkip: (task: TaskRowType) => void;
}

export function TaskRow({ task, disableStart, onStart, onStop, onSkip }: Props) {
  const start = task.start ? format(new Date(task.start), "HH:mm") : "—";
  const end = task.end ? format(new Date(task.end), "HH:mm") : "—";
  const cat = task.category as Category | null;
  const state = task.state;
  const isLive = state === "EXECUTING" || state === "PAUSED";
  const isTerminal = state === "EXECUTED" || state === "SKIPPED";

  return (
    <div className="flex items-center gap-4 rounded-md border border-white/5 bg-white/[0.02] px-4 py-3">
      <div className="w-20 font-mono text-xs text-white/50">
        {start}–{end}
      </div>
      <div className="flex-1 truncate">
        <div className="truncate text-sm">{task.title}</div>
      </div>
      {cat && CATEGORY_COLORS[cat] && (
        <span
          className={cn(
            "rounded border px-2 py-0.5 text-[10px] uppercase tracking-wide",
            CATEGORY_COLORS[cat]
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
              onClick={() => onStart(task)}
              disabled={disableStart}
              title={disableStart ? "Another timer is active" : "Start timer"}
            >
              <Play className="h-3.5 w-3.5" />
            </Button>
            <Button
              size="sm"
              variant="ghost"
              onClick={() => onSkip(task)}
              title="Mark skipped"
            >
              <Ban className="h-3.5 w-3.5" />
            </Button>
          </>
        )}
        {isLive && (
          <Button size="sm" variant="secondary" onClick={onStop} title="Stop timer">
            <Square className="h-3.5 w-3.5" />
          </Button>
        )}
        {isTerminal && <div className="w-8" />}
      </div>
    </div>
  );
}
