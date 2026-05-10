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

export function ExecutionCorrectionDialog({ task, onClose, onSaved }: Props) {
  const observedDuration = task?.executed_duration_minutes ?? null;
  const effectiveDuration =
    task?.effective_executed_duration_minutes ?? observedDuration;
  const [duration, setDuration] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setDuration(effectiveDuration != null ? String(effectiveDuration) : "");
    setError(null);
    setSubmitting(false);
  }, [effectiveDuration, task?.task_id]);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    if (!task || observedDuration == null) return;
    const next = Number(duration);
    if (!Number.isInteger(next) || next < 1) {
      setError("Use a whole number of minutes.");
      return;
    }
    if (next >= observedDuration) {
      setError("The corrected duration must be shorter than the observed timer.");
      return;
    }
    setSubmitting(true);
    setError(null);
    try {
      await correctExecutionDuration(task.task_id, {
        corrected_duration_minutes: next,
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

  return (
    <Dialog open={!!task} onOpenChange={(open) => !open && onClose()}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{task.title}</DialogTitle>
          <DialogDescription>
            executed - timer correction
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
            Actual duration
            <Input
              className="mt-1"
              type="number"
              min={1}
              max={observedDuration ? observedDuration - 1 : undefined}
              value={duration}
              onChange={(e) => setDuration(e.target.value)}
            />
          </label>
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
