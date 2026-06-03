"use client";

import { useEffect, useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Link2, X } from "lucide-react";

import { listDeadlines } from "@/lib/deadlines";
import {
  updateTaskDeadlineBinding,
  type TaskRow,
} from "@/lib/tasks";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { cn } from "@/lib/utils";

interface Props {
  task: TaskRow | null;
  open: boolean;
  onClose: () => void;
  onSaved: () => void;
}

function formatDue(iso: string) {
  return new Date(iso).toLocaleString(undefined, {
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  });
}

export function DeadlineBindingDialog({ task, open, onClose, onSaved }: Props) {
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const deadlinesQ = useQuery({
    queryKey: ["deadlines", "binding-correction"],
    queryFn: () => listDeadlines(),
    enabled: open,
  });

  const deadlines = useMemo(
    () =>
      (deadlinesQ.data?.deadlines ?? []).filter(
        (deadline) => !deadline.voided_at
      ),
    [deadlinesQ.data?.deadlines]
  );

  useEffect(() => {
    if (!open) return;
    setSelectedId(task?.deadline_id ?? null);
    setError(null);
  }, [open, task?.deadline_id]);

  if (!task) return null;

  async function saveBinding(clear = false) {
    if (!task) return;
    setSaving(true);
    setError(null);
    try {
      await updateTaskDeadlineBinding(task.task_id, {
        deadline_id: clear ? null : selectedId,
        clear_deadline: clear,
      });
      onSaved();
      onClose();
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Could not update binding");
    } finally {
      setSaving(false);
    }
  }

  const currentChanged = selectedId !== (task.deadline_id ?? null);
  const canSave = selectedId !== null && currentChanged && !saving;
  const canClear = task.deadline_id !== null && !saving;

  return (
    <Dialog open={open} onOpenChange={(nextOpen) => !nextOpen && onClose()}>
      <DialogContent className="max-w-lg">
        <DialogHeader>
          <DialogTitle>Change linked deadline</DialogTitle>
          <DialogDescription>
            This corrects task context only. It will not change planned time,
            execution time, or calibration metrics.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-3">
          <div className="rounded-sm border border-hairline bg-void-2/50 p-3">
            <div className="text-sm text-parchment">{task.title}</div>
            <div className="mt-1 font-mono text-[10px] uppercase tracking-widest text-dust-deep">
              {task.state.toLowerCase()} metadata correction
            </div>
            {task.deadline_title && (
              <div className="mt-2 flex items-center gap-1.5 text-xs text-signal">
                <Link2 className="h-3 w-3" />
                <span>Currently linked to {task.deadline_title}</span>
              </div>
            )}
          </div>

          <div className="max-h-72 space-y-1 overflow-y-auto">
            {deadlinesQ.isLoading ? (
              <div className="text-xs text-dust-deep">Loading deadlines...</div>
            ) : deadlines.length === 0 ? (
              <div className="text-xs text-dust-deep">
                No deadlines available.
              </div>
            ) : (
              deadlines.map((deadline) => {
                const selected = selectedId === deadline.deadline_id;
                return (
                  <button
                    key={deadline.deadline_id}
                    type="button"
                    onClick={() => setSelectedId(deadline.deadline_id)}
                    className={cn(
                      "flex w-full items-center justify-between gap-3 rounded-sm border px-3 py-2 text-left transition-colors",
                      selected
                        ? "border-signal/60 bg-signal/10 text-parchment"
                        : "border-hairline bg-void-2/40 text-dust hover:border-signal/40 hover:text-parchment"
                    )}
                  >
                    <span className="min-w-0">
                      <span className="block truncate text-sm">
                        {deadline.title}
                      </span>
                      <span className="font-mono text-[10px] uppercase tracking-widest text-dust-deep">
                        {deadline.state}
                      </span>
                    </span>
                    <span className="shrink-0 font-mono text-[11px] text-dust-deep">
                      {formatDue(deadline.due_at_utc)}
                    </span>
                  </button>
                );
              })
            )}
          </div>

          {error && (
            <div className="rounded-sm border border-ember/40 bg-ember/10 px-3 py-2 text-xs text-ember">
              {error}
            </div>
          )}
        </div>

        <DialogFooter className="gap-2 sm:gap-0">
          {canClear && (
            <Button
              type="button"
              variant="ghost"
              onClick={() => saveBinding(true)}
              disabled={saving}
              className="mr-auto text-dust-deep hover:text-ember"
            >
              <X className="mr-1 h-3.5 w-3.5" />
              Clear link
            </Button>
          )}
          <Button type="button" variant="ghost" onClick={onClose} disabled={saving}>
            Cancel
          </Button>
          <Button type="button" onClick={() => saveBinding(false)} disabled={!canSave}>
            Save link
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
