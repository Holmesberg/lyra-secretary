"use client";
import { useEffect, useState } from "react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { CATEGORIES, type Category } from "@/lib/categories";
import { useCurrentTime } from "@/lib/hooks/use-current-time";
import { createTask, rescheduleTask, type TaskRow } from "@/lib/tasks";

function formatLocal(d: Date) {
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(
    d.getHours()
  )}:${pad(d.getMinutes())}`;
}

/** Round up to next 30-minute boundary. */
function defaultStart(from: Date = new Date()) {
  const d = new Date(from);
  const mins = d.getMinutes();
  const next30 = mins <= 0 ? 0 : mins <= 30 ? 30 : 60;
  d.setMinutes(next30, 0, 0);
  return formatLocal(d);
}

function addMinutes(localStr: string, mins: number): string {
  const d = new Date(localStr);
  d.setMinutes(d.getMinutes() + mins);
  return formatLocal(d);
}

function diffMinutes(startStr: string, endStr: string): number {
  return Math.round((new Date(endStr).getTime() - new Date(startStr).getTime()) / 60_000);
}

interface PausedConflict {
  taskId: string;
  title: string;
  blockingTitles: string[];
}

interface SoftConflict {
  // "overlap" + "duplicate_title" possible combinations from soft_reasons
  reasons: string[];
  overlapTitles: string[];
  duplicateTitle: string | null;
}

interface Props {
  open: boolean;
  onClose: () => void;
  onCreated: () => void;
  onInterruptionCreated?: (taskId: string, taskTitle: string) => void;
  editingTask?: TaskRow | null;
}

export function NewTaskModal({ open, onClose, onCreated, onInterruptionCreated, editingTask }: Props) {
  const isEdit = !!editingTask;
  const now = useCurrentTime();

  const [title, setTitle] = useState("");
  const [start, setStart] = useState(() => defaultStart());
  const [end, setEnd] = useState(() => addMinutes(defaultStart(), 30));
  const [durHours, setDurHours] = useState(0);
  const [durMinutes, setDurMinutes] = useState(30);
  const [category, setCategory] = useState<Category>("work");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [pausedConflict, setPausedConflict] = useState<PausedConflict | null>(null);
  const [softConflict, setSoftConflict] = useState<SoftConflict | null>(null);
  const [lastEditId, setLastEditId] = useState<string | null>(null);

  const totalMinutes = durHours * 60 + durMinutes;
  const endBeforeStart = diffMinutes(start, end) <= 0;
  const canSubmit = !submitting && title.trim().length > 0 && !endBeforeStart && totalMinutes > 0;

  // Fresh defaults every time modal opens for a new task.
  // Using `open` as only dep intentionally — the 60s `now` tick must
  // not clobber in-progress typing.
  // eslint-disable-next-line react-hooks/exhaustive-deps
  useEffect(() => {
    if (open && !editingTask) {
      const s = defaultStart(now);
      const e = addMinutes(s, 30);
      setStart(s);
      setEnd(e);
      setDurHours(0);
      setDurMinutes(30);
      setTitle("");
      setCategory("work");
      setError(null);
      setPausedConflict(null);
      setLastEditId(null);
    }
  }, [open, editingTask]);

  // Sync form fields when editingTask changes
  if (editingTask && editingTask.task_id !== lastEditId) {
    const startDate = editingTask.start ? new Date(editingTask.start) : new Date();
    const endDate = editingTask.end ? new Date(editingTask.end) : new Date();
    const dur = Math.max(0, Math.round((endDate.getTime() - startDate.getTime()) / 60_000));
    setTitle(editingTask.title);
    setStart(formatLocal(startDate));
    setEnd(formatLocal(endDate));
    setDurHours(Math.floor(dur / 60));
    setDurMinutes(dur % 60);
    setCategory((editingTask.category as Category) || "work");
    setError(null);
    setPausedConflict(null);
    setSoftConflict(null);
    setLastEditId(editingTask.task_id);
  }

  function resetForm() {
    const s = defaultStart(now);
    setTitle("");
    setStart(s);
    setEnd(addMinutes(s, 30));
    setDurHours(0);
    setDurMinutes(30);
    setCategory("work");
    setError(null);
    setPausedConflict(null);
    setSoftConflict(null);
    setLastEditId(null);
  }

  // --- Bidirectional binding helpers ---

  function handleStartChange(newStart: string) {
    // Preserve current duration, shift end
    const dur = durHours * 60 + durMinutes;
    setStart(newStart);
    setEnd(addMinutes(newStart, dur));
  }

  function handleEndChange(newEnd: string) {
    setEnd(newEnd);
    const mins = diffMinutes(start, newEnd);
    if (mins > 0) {
      setDurHours(Math.floor(mins / 60));
      setDurMinutes(mins % 60);
    }
  }

  function handleDurHoursChange(h: number) {
    const clamped = Math.max(0, h);
    setDurHours(clamped);
    setEnd(addMinutes(start, clamped * 60 + durMinutes));
  }

  function handleDurMinutesChange(m: number) {
    const clamped = Math.max(0, m);
    setDurMinutes(clamped);
    setEnd(addMinutes(start, durHours * 60 + clamped));
  }

  // --- Submit ---

  async function submit() {
    setError(null);
    setPausedConflict(null);
    setSoftConflict(null);
    setSubmitting(true);
    try {
      const startDate = new Date(start);
      const endDate = new Date(end);

      if (isEdit && editingTask) {
        await rescheduleTask({
          task_id: editingTask.task_id,
          new_start: startDate.toISOString(),
          new_end: endDate.toISOString(),
          title: title.trim(),
          category,
        });
        resetForm();
        onCreated();
        onClose();
        return;
      }

      const res = await createTask({
        title: title.trim(),
        start: startDate.toISOString(),
        end: endDate.toISOString(),
        category,
      });
      if (!res.created) {
        if (res.conflicts.length > 0) {
          const paused = res.conflicts.filter((c) => c.state === "PAUSED");
          const blocking = res.conflicts.filter((c) => c.state !== "PAUSED");
          if (paused.length > 0 && onInterruptionCreated) {
            setPausedConflict({
              taskId: paused[0].task_id,
              title: paused[0].title,
              blockingTitles: blocking.map((c) => c.title),
            });
            return;
          }
          // Path A (Apr 16): branch on severity. HARD = active-timer
          // overlap, no override. SOFT = planned overlap or duplicate
          // title, override-able.
          if (res.severity === "hard") {
            const titles = res.conflicts.map((c) => c.title).join(", ");
            setError(
              `Conflicts with active timer (${titles}). Stop the active timer first.`
            );
            return;
          }
          if (res.severity === "soft") {
            const overlaps = res.conflicts
              .filter((c) => c.gate_id === "planned_overlap")
              .map((c) => c.title);
            const dups = res.conflicts
              .filter((c) => c.gate_id === "duplicate_title")
              .map((c) => c.title);
            setSoftConflict({
              reasons: res.soft_reasons ?? [],
              overlapTitles: overlaps,
              duplicateTitle: dups[0] ?? null,
            });
            return;
          }
          // Fallback for older backends without severity field.
          setError(
            `Conflicts with: ${res.conflicts
              .map((c) => c.title)
              .join(", ")}. Adjust the time and try again.`
          );
          return;
        }
        setError("Task was not created.");
        return;
      }
      resetForm();
      onCreated();
      onClose();
    } catch (e: any) {
      setError(e?.message ?? "Failed to create task");
    } finally {
      setSubmitting(false);
    }
  }

  async function submitWithForce() {
    // Path A: soft-conflict override. Calls /v1/create with force=true.
    // Backend rejects HARD conflicts even with force, so a 200 with
    // created=false here means the conflict tightened mid-flight (e.g.,
    // a task transitioned to EXECUTING) — surface as a fresh warning.
    setError(null);
    setSubmitting(true);
    try {
      const startDate = new Date(start);
      const endDate = new Date(end);
      const res = await createTask({
        title: title.trim(),
        start: startDate.toISOString(),
        end: endDate.toISOString(),
        category,
        force: true,
      });
      if (!res.created) {
        setError(
          res.severity === "hard"
            ? "Override rejected — an active timer now overlaps. Stop it first."
            : "Override failed."
        );
        return;
      }
      resetForm();
      onCreated();
      onClose();
    } catch (e: any) {
      setError(e?.message ?? "Failed to create task");
    } finally {
      setSubmitting(false);
    }
  }

  async function submitAsInterruption() {
    setError(null);
    setSubmitting(true);
    try {
      const startDate = new Date(start);
      const endDate = new Date(end);
      const res = await createTask({
        title: title.trim(),
        start: startDate.toISOString(),
        end: endDate.toISOString(),
        category,
        force: true,
      });
      if (!res.created || !res.task_id) {
        setError("Failed to create interruption task.");
        return;
      }
      const createdTitle = title.trim();
      const createdId = res.task_id;
      resetForm();
      onClose();
      onInterruptionCreated?.(createdId, createdTitle);
    } catch (e: any) {
      setError(e?.message ?? "Failed to create interruption task");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <Dialog open={open} onOpenChange={(o) => { if (!o) { resetForm(); onClose(); } }}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{isEdit ? "Edit task" : "New task"}</DialogTitle>
          <DialogDescription>
            {isEdit ? "Update the plan for this task." : "Set the plan. You can always reschedule later."}
          </DialogDescription>
        </DialogHeader>

        <div className="flex flex-col gap-4">
          <div className="flex flex-col gap-1.5">
            <Label htmlFor="title">Title</Label>
            <Input
              id="title"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="What needs doing"
              autoFocus
            />
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div className="flex flex-col gap-1.5">
              <Label htmlFor="start">Start</Label>
              <Input
                id="start"
                type="datetime-local"
                value={start}
                onChange={(e) => handleStartChange(e.target.value)}
              />
            </div>
            <div className="flex flex-col gap-1.5">
              <Label htmlFor="end">End</Label>
              <Input
                id="end"
                type="datetime-local"
                value={end}
                onChange={(e) => handleEndChange(e.target.value)}
              />
            </div>
          </div>

          <div className="flex flex-col gap-1.5">
            <Label className="text-xs text-white/50">Duration</Label>
            <div className="flex items-center gap-2">
              <Input
                type="number"
                min={0}
                value={durHours}
                onChange={(e) => handleDurHoursChange(Number(e.target.value))}
                className="w-20 text-center text-sm text-white/70"
              />
              <span className="text-xs text-white/40">h</span>
              <Input
                type="number"
                min={0}
                value={durMinutes}
                onChange={(e) => handleDurMinutesChange(Number(e.target.value))}
                className="w-20 text-center text-sm text-white/70"
              />
              <span className="text-xs text-white/40">m</span>
            </div>
          </div>

          <div className="flex flex-col gap-1.5">
            <Label htmlFor="category">Category</Label>
            <select
              id="category"
              value={category}
              onChange={(e) => setCategory(e.target.value as Category)}
              className="h-9 rounded-md border border-white/15 bg-transparent px-3 text-sm"
            >
              {CATEGORIES.map((c) => (
                <option key={c} value={c} className="bg-[#0a0a0a]">
                  {c.replace("_", " ")}
                </option>
              ))}
            </select>
          </div>

          {endBeforeStart && (
            <div className="rounded border border-red-500/30 bg-red-500/10 p-2 text-xs text-red-200">
              End time must be after start
            </div>
          )}

          {pausedConflict && (
            <>
              <div className="rounded-md border border-yellow-500/30 bg-yellow-500/10 p-3 text-xs text-yellow-200">
                <span className="font-medium text-white">{pausedConflict.title}</span>{" "}
                is paused in this window.{" "}
                {pausedConflict.blockingTitles.length === 0 ? (
                  <>
                    Start{" "}
                    <span className="font-medium text-white">{title.trim()}</span>{" "}
                    as an interruption? It will be linked — you can resume{" "}
                    <span className="font-medium text-white">{pausedConflict.title}</span>{" "}
                    after.
                  </>
                ) : (
                  <>
                    To interrupt it, adjust the time to avoid the blocking conflict
                    {pausedConflict.blockingTitles.length > 1 ? "s" : ""} below.
                  </>
                )}
              </div>
              {pausedConflict.blockingTitles.length > 0 && (
                <div className="rounded border border-red-500/30 bg-red-500/10 p-2 text-xs text-red-200">
                  Also conflicts with: {pausedConflict.blockingTitles.join(", ")}
                </div>
              )}
            </>
          )}

          {softConflict && (
            <div className="rounded-md border border-yellow-500/30 bg-yellow-500/10 p-3 text-xs text-yellow-200">
              {softConflict.reasons.includes("overlap") && softConflict.overlapTitles.length > 0 && (
                <div>
                  Overlaps with{" "}
                  <span className="font-medium text-white">
                    {softConflict.overlapTitles.join(", ")}
                  </span>
                  .
                </div>
              )}
              {softConflict.reasons.includes("duplicate_title") && softConflict.duplicateTitle && (
                <div>
                  Already have{" "}
                  <span className="font-medium text-white">{softConflict.duplicateTitle}</span>{" "}
                  today.
                </div>
              )}
              <div className="mt-1 text-white/60">Create anyway?</div>
            </div>
          )}

          {error && (
            <div className="rounded border border-red-500/30 bg-red-500/10 p-2 text-xs text-red-200">
              {error}
            </div>
          )}
        </div>

        <DialogFooter>
          <Button variant="ghost" onClick={() => { resetForm(); onClose(); }} disabled={submitting}>
            Cancel
          </Button>
          {pausedConflict ? (
            <Button
              onClick={submitAsInterruption}
              disabled={submitting || pausedConflict.blockingTitles.length > 0}
            >
              Start as interruption
            </Button>
          ) : softConflict ? (
            <Button onClick={submitWithForce} disabled={submitting}>
              Create anyway
            </Button>
          ) : (
            <Button
              onClick={submit}
              disabled={!canSubmit}
            >
              {isEdit ? "Save" : "Create"}
            </Button>
          )}
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
