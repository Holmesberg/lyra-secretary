"use client";
import { useState } from "react";
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
import { createTask, rescheduleTask, type TaskRow } from "@/lib/tasks";

function defaultStart() {
  const d = new Date();
  d.setMinutes(d.getMinutes() + 5 - (d.getMinutes() % 5));
  d.setSeconds(0);
  d.setMilliseconds(0);
  return formatLocal(d);
}

function formatLocal(d: Date) {
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(
    d.getHours()
  )}:${pad(d.getMinutes())}`;
}

interface PausedConflict {
  taskId: string;
  title: string;
  blockingTitles: string[];
}

interface Props {
  open: boolean;
  onClose: () => void;
  onCreated: () => void;
  onInterruptionCreated?: (taskId: string, taskTitle: string) => void;
  editingTask?: TaskRow | null;
}

function editDefaults(task: TaskRow) {
  const startDate = task.start ? new Date(task.start) : new Date();
  const endDate = task.end ? new Date(task.end) : new Date();
  const dur = Math.max(5, Math.round((endDate.getTime() - startDate.getTime()) / 60_000));
  return { start: formatLocal(startDate), duration: dur };
}

export function NewTaskModal({ open, onClose, onCreated, onInterruptionCreated, editingTask }: Props) {
  const isEdit = !!editingTask;
  const [title, setTitle] = useState("");
  const [start, setStart] = useState(defaultStart());
  const [duration, setDuration] = useState(30);
  const [category, setCategory] = useState<Category>("work");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [pausedConflict, setPausedConflict] = useState<PausedConflict | null>(null);
  const [lastEditId, setLastEditId] = useState<string | null>(null);

  // Sync form fields when editingTask changes
  if (editingTask && editingTask.task_id !== lastEditId) {
    const defs = editDefaults(editingTask);
    setTitle(editingTask.title);
    setStart(defs.start);
    setDuration(defs.duration);
    setCategory((editingTask.category as Category) || "work");
    setError(null);
    setPausedConflict(null);
    setLastEditId(editingTask.task_id);
  }

  function resetForm() {
    setTitle("");
    setDuration(30);
    setStart(defaultStart());
    setError(null);
    setPausedConflict(null);
    setLastEditId(null);
  }

  function buildDates() {
    const startDate = new Date(start);
    const endDate = new Date(startDate.getTime() + duration * 60_000);
    return { startDate, endDate };
  }

  async function submit() {
    setError(null);
    setPausedConflict(null);
    setSubmitting(true);
    try {
      const { startDate, endDate } = buildDates();

      // Edit mode: reschedule instead of create
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

  async function submitAsInterruption() {
    setError(null);
    setSubmitting(true);
    try {
      const { startDate, endDate } = buildDates();
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
    <Dialog open={open} onOpenChange={(o) => !o && onClose()}>
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
                onChange={(e) => setStart(e.target.value)}
              />
            </div>
            <div className="flex flex-col gap-1.5">
              <Label htmlFor="duration">Duration (min)</Label>
              <Input
                id="duration"
                type="number"
                min={5}
                step={5}
                value={duration}
                onChange={(e) => setDuration(Number(e.target.value))}
              />
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

          {error && (
            <div className="rounded border border-red-500/30 bg-red-500/10 p-2 text-xs text-red-200">
              {error}
            </div>
          )}
        </div>

        <DialogFooter>
          <Button variant="ghost" onClick={() => { setPausedConflict(null); onClose(); }} disabled={submitting}>
            Cancel
          </Button>
          {pausedConflict ? (
            <Button
              onClick={submitAsInterruption}
              disabled={submitting || pausedConflict.blockingTitles.length > 0}
            >
              Start as interruption
            </Button>
          ) : (
            <Button
              onClick={submit}
              disabled={submitting || !title.trim()}
            >
              {isEdit ? "Save" : "Create"}
            </Button>
          )}
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
