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
import { cn } from "@/lib/utils";
import {
  type DeadlineResponse,
  type DeadlineUpdateRequest,
  createDeadline,
  updateDeadline,
} from "@/lib/deadlines";

type Mode = "create" | "edit";
type StateButton = "completed" | "skipped";

interface Props {
  open: boolean;
  mode: Mode;
  deadline?: DeadlineResponse | null; // required when mode = "edit"
  onClose: () => void;
  onSaved: (deadline: DeadlineResponse) => void;
}

function _isoToLocalInput(iso: string | null | undefined): string {
  // datetime-local needs YYYY-MM-DDTHH:mm in local time
  if (!iso) return "";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "";
  const pad = (n: number) => n.toString().padStart(2, "0");
  return (
    `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T` +
    `${pad(d.getHours())}:${pad(d.getMinutes())}`
  );
}

function _localInputToIso(local: string): string {
  return new Date(local).toISOString();
}

export function DeadlineModal({
  open,
  mode,
  deadline,
  onClose,
  onSaved,
}: Props) {
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [dueAt, setDueAt] = useState(""); // datetime-local string
  const [categoryHint, setCategoryHint] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!open) return;
    if (mode === "edit" && deadline) {
      setTitle(deadline.title);
      setDescription(deadline.description ?? "");
      setDueAt(_isoToLocalInput(deadline.due_at_utc));
      setCategoryHint(deadline.category_hint ?? "");
    } else {
      setTitle("");
      setDescription("");
      const tomorrow = new Date();
      tomorrow.setDate(tomorrow.getDate() + 7);
      tomorrow.setHours(17, 0, 0, 0);
      setDueAt(_isoToLocalInput(tomorrow.toISOString()));
      setCategoryHint("");
    }
    setError(null);
  }, [open, mode, deadline]);

  const canSubmit =
    !submitting && title.trim().length > 0 && dueAt.trim().length > 0;

  async function handleSave() {
    if (!canSubmit) return;
    setSubmitting(true);
    setError(null);
    try {
      let saved: DeadlineResponse;
      if (mode === "edit" && deadline) {
        const patch: DeadlineUpdateRequest = {
          title: title.trim(),
          description: description.trim() || undefined,
          due_at_utc: _localInputToIso(dueAt),
          category_hint: categoryHint.trim() || undefined,
        };
        saved = await updateDeadline(deadline.deadline_id, patch);
      } else {
        saved = await createDeadline({
          title: title.trim(),
          description: description.trim() || undefined,
          due_at_utc: _localInputToIso(dueAt),
          category_hint: categoryHint.trim() || undefined,
        });
      }
      onSaved(saved);
      onClose();
    } catch (e: any) {
      setError(e?.message ?? "Failed to save deadline");
    } finally {
      setSubmitting(false);
    }
  }

  async function handleStateTransition(next: StateButton) {
    if (!deadline) return;
    setSubmitting(true);
    setError(null);
    try {
      const saved = await updateDeadline(deadline.deadline_id, { state: next });
      onSaved(saved);
      onClose();
    } catch (e: any) {
      setError(e?.message ?? "Failed to update state");
    } finally {
      setSubmitting(false);
    }
  }

  const showStateButtons =
    mode === "edit" &&
    deadline &&
    (deadline.state === "planned" || deadline.state === "active");

  return (
    <Dialog open={open} onOpenChange={(o) => !o && onClose()}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>
            {mode === "edit" ? "Edit deadline" : "New deadline"}
          </DialogTitle>
          <DialogDescription>
            Tasks bind here automatically when titles overlap. You can also
            pick the binding explicitly when creating a task.
          </DialogDescription>
        </DialogHeader>

        <div className="flex flex-col gap-4 py-2">
          <label className="flex flex-col gap-1 text-xs text-dust">
            Title
            <input
              type="text"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="e.g. BCI hackathon submission"
              className="rounded-sm border border-hairline bg-void-2 px-3 py-2 text-sm text-parchment focus:border-signal/60 focus:outline-none"
              autoFocus={mode === "create"}
            />
          </label>

          <label className="flex flex-col gap-1 text-xs text-dust">
            Description (optional)
            <textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="What ships when this deadline lands?"
              rows={3}
              className="rounded-sm border border-hairline bg-void-2 px-3 py-2 text-sm text-parchment focus:border-signal/60 focus:outline-none"
            />
          </label>

          <label className="flex flex-col gap-1 text-xs text-dust">
            Due at
            <input
              type="datetime-local"
              value={dueAt}
              onChange={(e) => setDueAt(e.target.value)}
              className="rounded-sm border border-hairline bg-void-2 px-3 py-2 text-sm text-parchment focus:border-signal/60 focus:outline-none"
            />
          </label>

          <label className="flex flex-col gap-1 text-xs text-dust">
            Category hint (optional)
            <input
              type="text"
              value={categoryHint}
              onChange={(e) => setCategoryHint(e.target.value)}
              placeholder="e.g. academic, work"
              className="rounded-sm border border-hairline bg-void-2 px-3 py-2 text-sm text-parchment focus:border-signal/60 focus:outline-none"
            />
          </label>

          {error && (
            <div className="rounded-sm border border-ember/40 bg-ember/5 p-3 text-xs text-ember">
              {error}
            </div>
          )}

          {showStateButtons && (
            <div className="flex flex-col gap-2 rounded-sm border border-hairline p-3">
              <span className="text-[11px] uppercase tracking-widest text-dust-deep">
                Mark as
              </span>
              <div className="flex gap-2">
                <button
                  type="button"
                  onClick={() => handleStateTransition("completed")}
                  disabled={submitting}
                  className={cn(
                    "flex-1 rounded-sm border border-signal/40 bg-signal/10 px-3 py-1.5 text-xs text-parchment transition-colors hover:bg-signal/20",
                    submitting && "opacity-50"
                  )}
                >
                  Complete
                </button>
                <button
                  type="button"
                  onClick={() => handleStateTransition("skipped")}
                  disabled={submitting}
                  className={cn(
                    "flex-1 rounded-sm border border-hairline bg-void-2 px-3 py-1.5 text-xs text-dust transition-colors hover:border-dust hover:text-parchment",
                    submitting && "opacity-50"
                  )}
                >
                  Skip
                </button>
              </div>
            </div>
          )}
        </div>

        <DialogFooter>
          <Button variant="ghost" onClick={onClose} disabled={submitting}>
            Cancel
          </Button>
          <Button onClick={handleSave} disabled={!canSubmit}>
            {submitting ? "Saving…" : mode === "edit" ? "Save" : "Create"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
