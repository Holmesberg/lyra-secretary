"use client";

import { FormEvent, useEffect, useState } from "react";
import { format } from "date-fns";
import type { TaskRow } from "@/lib/tasks";
import { correctExecutionDuration } from "@/lib/tasks";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";

interface Props {
  task: TaskRow | null;
  onClose: () => void;
  onSaved: () => void;
}

function fmt(iso: string | null) {
  return iso ? format(new Date(iso), "EEE, MMM d - h:mm a") : "--";
}

function toDatetimeLocal(iso: string | null) {
  if (!iso) return "";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "";
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(
    d.getHours()
  )}:${pad(d.getMinutes())}`;
}

function minutesBetween(startIso: string | null, endValue: string | null) {
  if (!startIso || !endValue) return null;
  const start = new Date(startIso).getTime();
  const end = new Date(endValue).getTime();
  if (!Number.isFinite(start) || !Number.isFinite(end) || end <= start) return null;
  return Math.max(0, Math.round((end - start) / 60000));
}

export function ExecutionCorrectionDialog({ task, onClose, onSaved }: Props) {
  const observedDuration = task?.executed_duration_minutes ?? null;
  const effectiveDuration =
    task?.effective_executed_duration_minutes ?? observedDuration;
  const isRetroactiveReport = task?.initiation_status === "retroactive";
  const [endTime, setEndTime] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setEndTime(toDatetimeLocal(task?.effective_executed_end ?? task?.executed_end ?? null));
    setError(null);
    setSubmitting(false);
  }, [task?.effective_executed_end, task?.executed_end, task?.task_id]);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    if (!task || observedDuration == null || !task.executed_start || !task.executed_end) return;
    if (!endTime) {
      setError("Choose the actual stop time.");
      return;
    }
    const correctedEnd = new Date(endTime);
    const observedEnd = new Date(task.executed_end);
    const observedStart = new Date(task.executed_start);
    if (
      Number.isNaN(correctedEnd.getTime()) ||
      Number.isNaN(observedEnd.getTime()) ||
      Number.isNaN(observedStart.getTime())
    ) {
      setError("Choose a valid end time.");
      return;
    }
    if (correctedEnd <= observedStart) {
      setError("The actual end must be after the start time.");
      return;
    }
    if (!isRetroactiveReport && correctedEnd >= observedEnd) {
      setError("The actual end must be earlier than the timer stop.");
      return;
    }
    const currentDisplayedEnd = new Date(
      task.effective_executed_end ?? task.executed_end
    );
    if (
      isRetroactiveReport &&
      !Number.isNaN(currentDisplayedEnd.getTime()) &&
      correctedEnd.getTime() === currentDisplayedEnd.getTime()
    ) {
      setError("Choose a different reported end time.");
      return;
    }
    setSubmitting(true);
    setError(null);
    try {
      await correctExecutionDuration(task.task_id, {
        corrected_end_time: correctedEnd.toISOString(),
        reason: "forgot_to_stop_timer",
      });
      onSaved();
      onClose();
    } catch (err: any) {
      setError(err?.message ?? "Could not save correction.");
    } finally {
      setSubmitting(false);
    }
  }

  if (!task) return null;

  const corrected = task.execution_duration_provenance === "retroactive";
  const delta = task.effective_duration_delta_minutes ?? task.duration_delta_minutes;
  const observedWallMinutes = minutesBetween(task.executed_start, task.executed_end);
  const observedPausedMinutes =
    observedWallMinutes != null && observedDuration != null
      ? Math.max(0, observedWallMinutes - observedDuration)
      : 0;
  const correctedWallMinutes = minutesBetween(task.executed_start, endTime);
  const correctedActiveMinutes =
    correctedWallMinutes != null
      ? Math.max(0, correctedWallMinutes - observedPausedMinutes)
      : null;

  return (
    <Dialog open={!!task} onOpenChange={(open) => !open && onClose()}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{task.title}</DialogTitle>
          <DialogDescription>
            {isRetroactiveReport
              ? "executed - reported time correction"
              : "executed - timer correction"}
          </DialogDescription>
        </DialogHeader>

        <dl className="grid grid-cols-[auto_1fr] gap-x-4 gap-y-2 text-xs">
          <dt className="text-dust">Observed</dt>
          <dd className="text-parchment">
            {observedDuration ?? "--"} min - {fmt(task.executed_start)} -&gt; {fmt(task.executed_end)}
          </dd>
          <dt className="text-dust">Displayed</dt>
          <dd className="text-parchment">
            {effectiveDuration ?? "--"} min
            {delta !== null && (
              <span className="ml-2 text-dust-deep">
                (delta {delta > 0 ? "+" : ""}
                {delta})
              </span>
            )}
            {corrected && <span className="ml-2 text-signal">retroactive</span>}
          </dd>
        </dl>

        <form onSubmit={onSubmit} className="space-y-3">
          <label className="block text-xs text-dust">
            Actual end time
            <Input
              className="mt-1"
              type="datetime-local"
              value={endTime}
              onChange={(e) => setEndTime(e.target.value)}
            />
          </label>
          <p className="text-xs text-dust-deep">
            Lyra will derive the active duration
            {correctedActiveMinutes != null && correctedActiveMinutes > 0
              ? `: ${Math.round(correctedActiveMinutes)} min`
              : " from start -> end"}
            .
          </p>
          {error && (
            <p className="rounded-sm border border-ember/40 bg-ember/5 px-3 py-2 text-xs text-ember">
              {error}
            </p>
          )}
          <DialogFooter>
            <Button type="button" variant="ghost" onClick={onClose}>
              Close
            </Button>
            <Button type="submit" disabled={submitting || observedDuration == null}>
              {submitting ? "Saving..." : "Save correction"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
