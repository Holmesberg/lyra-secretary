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
import { createTask } from "@/lib/tasks";

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

interface Props {
  open: boolean;
  onClose: () => void;
  onCreated: () => void;
}

export function NewTaskModal({ open, onClose, onCreated }: Props) {
  const [title, setTitle] = useState("");
  const [start, setStart] = useState(defaultStart());
  const [duration, setDuration] = useState(30);
  const [category, setCategory] = useState<Category>("work");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function submit() {
    setError(null);
    setSubmitting(true);
    try {
      const startDate = new Date(start);
      const endDate = new Date(startDate.getTime() + duration * 60_000);
      const res = await createTask({
        title: title.trim(),
        start: startDate.toISOString(),
        end: endDate.toISOString(),
        category,
      });
      if (!res.created) {
        if (res.conflicts.length > 0) {
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
      setTitle("");
      setDuration(30);
      setStart(defaultStart());
      onCreated();
      onClose();
    } catch (e: any) {
      setError(e?.message ?? "Failed to create task");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <Dialog open={open} onOpenChange={(o) => !o && onClose()}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>New task</DialogTitle>
          <DialogDescription>
            Set the plan. You can always reschedule later.
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

          {error && (
            <div className="rounded border border-red-500/30 bg-red-500/10 p-2 text-xs text-red-200">
              {error}
            </div>
          )}
        </div>

        <DialogFooter>
          <Button variant="ghost" onClick={onClose} disabled={submitting}>
            Cancel
          </Button>
          <Button
            onClick={submit}
            disabled={submitting || !title.trim()}
          >
            Create
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
