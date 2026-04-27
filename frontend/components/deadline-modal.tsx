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
import { cn } from "@/lib/utils";
import { CategorySelect } from "@/components/category-select";
import {
  type DeadlineResponse,
  type DeadlineUpdateRequest,
  createDeadline,
  updateDeadline,
} from "@/lib/deadlines";

type Mode = "create" | "edit";
// State actions surfaced inside the modal. Includes "planned" as a
// reopen target from terminal states (skipped / completed / missed) —
// shipped Apr 27 after operator misclicked Skip and lost the
// deadline. The button STAGES the change locally; nothing persists
// until the user clicks Save.
type StateButton = "completed" | "skipped" | "planned";

interface Props {
  open: boolean;
  mode: Mode;
  deadline?: DeadlineResponse | null; // required when mode = "edit"
  onClose: () => void;
  onSaved: (deadline: DeadlineResponse) => void;
}

function _isoToLocalInput(iso: string | null | undefined): string {
  // datetime-local needs YYYY-MM-DDTHH:mm in local time. Backend now
  // emits explicit UTC offsets (DeadlineResponse._serialize_utc), so
  // `new Date(iso)` correctly converts UTC → local before getHours().
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
  // Mirror NewTaskModal: dropdown for built-ins + custom-entry mode
  // when the user picks "+ Create a new category…".
  const [categoryMode, setCategoryMode] = useState<"picker" | "custom">("picker");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  // Staged state change. Apr 27 footgun: the prior version called the
  // API the moment the user clicked Skip/Complete, so a misclick was
  // unrecoverable through the UI. Now state buttons set this local
  // value and nothing reaches the server until Save.
  const [pendingState, setPendingState] = useState<StateButton | null>(null);

  useEffect(() => {
    if (!open) return;
    if (mode === "edit" && deadline) {
      setTitle(deadline.title);
      setDescription(deadline.description ?? "");
      setDueAt(_isoToLocalInput(deadline.due_at_utc));
      setCategoryHint(deadline.category_hint ?? "");
      // Free-text customs from prior tasks may not match a built-in;
      // if the existing hint isn't blank, default to picker mode and
      // let CategorySelect surface it under "Your categories".
      setCategoryMode("picker");
    } else {
      setTitle("");
      setDescription("");
      const tomorrow = new Date();
      tomorrow.setDate(tomorrow.getDate() + 7);
      tomorrow.setHours(17, 0, 0, 0);
      setDueAt(_isoToLocalInput(tomorrow.toISOString()));
      setCategoryHint("");
      setCategoryMode("picker");
    }
    setPendingState(null);
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
          // Persist staged state change at Save time, not at click time.
          ...(pendingState ? { state: pendingState } : {}),
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

  // State buttons: stage locally only — no API call here. The pending
  // transition surfaces as a pill above the Save button so the user
  // sees what's about to land. Cancel / close discards the staging.
  function stageState(next: StateButton) {
    setPendingState(next);
  }

  function clearStaging() {
    setPendingState(null);
  }

  // The buttons surfaced in the "Mark as" panel depend on the deadline's
  // current state. Active/planned deadlines can move forward (complete,
  // skip). Terminal-state deadlines (skipped, completed, missed) get
  // a reopen button — recovery from misclicks per the Apr 27 incident.
  const stateButtonOptions: StateButton[] = (() => {
    if (mode !== "edit" || !deadline) return [];
    switch (deadline.state) {
      case "planned":
      case "active":
        return ["completed", "skipped"];
      case "skipped":
      case "completed":
      case "missed":
        return ["planned"]; // reopen
      default:
        return [];
    }
  })();

  return (
    <Dialog open={open} onOpenChange={(o) => !o && onClose()}>
      <DialogContent
        onKeyDown={(e) => {
          // Enter submits — except inside textareas (where Enter inserts
          // a newline) and when modifier keys are held. Mirrors the
          // pattern used in reflection-modal, readiness-modal, etc.
          if (e.key !== "Enter") return;
          if (e.shiftKey || e.ctrlKey || e.metaKey || e.altKey) return;
          if ((e.target as HTMLElement).tagName === "TEXTAREA") return;
          if (!canSubmit) return;
          e.preventDefault();
          void handleSave();
        }}
      >
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

          <div className="flex flex-col gap-1 text-xs text-dust">
            <span>Category (optional)</span>
            {categoryMode === "picker" ? (
              <CategorySelect
                value={categoryHint || "work"}
                onChange={(val) => {
                  if (val === "__CREATE_NEW__") {
                    setCategoryMode("custom");
                    setCategoryHint("");
                  } else {
                    setCategoryHint(val);
                  }
                }}
              />
            ) : (
              <div className="flex items-center gap-2">
                <Input
                  value={categoryHint}
                  onChange={(e) => setCategoryHint(e.target.value)}
                  placeholder="e.g. research, admin, side_project"
                  autoComplete="off"
                  autoFocus
                />
                <button
                  type="button"
                  className="whitespace-nowrap text-xs text-dust transition-colors hover:text-parchment"
                  onClick={() => {
                    setCategoryMode("picker");
                    setCategoryHint("");
                  }}
                >
                  ← Back
                </button>
              </div>
            )}
          </div>

          {error && (
            <div className="rounded-sm border border-ember/40 bg-ember/5 p-3 text-xs text-ember">
              {error}
            </div>
          )}

          {stateButtonOptions.length > 0 && (
            <div className="flex flex-col gap-2 rounded-sm border border-hairline p-3">
              <span className="text-[11px] uppercase tracking-widest text-dust-deep">
                {deadline?.state === "planned" || deadline?.state === "active"
                  ? "Mark as"
                  : "Reopen"}
              </span>
              <div className="flex gap-2">
                {stateButtonOptions.map((opt) => {
                  const staged = pendingState === opt;
                  const tone =
                    opt === "completed"
                      ? "border-signal/40 bg-signal/10 hover:bg-signal/20 text-parchment"
                      : opt === "planned"
                        ? "border-signal/40 bg-signal/10 hover:bg-signal/20 text-parchment"
                        : "border-hairline bg-void-2 hover:border-dust hover:text-parchment text-dust";
                  const stagedTone =
                    "border-signal bg-signal/30 text-parchment";
                  return (
                    <button
                      key={opt}
                      type="button"
                      onClick={() => stageState(opt)}
                      disabled={submitting}
                      className={cn(
                        "flex-1 rounded-sm border px-3 py-1.5 text-xs transition-colors",
                        staged ? stagedTone : tone,
                        submitting && "opacity-50"
                      )}
                    >
                      {opt === "completed"
                        ? "Complete"
                        : opt === "skipped"
                          ? "Skip"
                          : "Reopen as planned"}
                    </button>
                  );
                })}
              </div>
              {pendingState && (
                <div className="flex items-center justify-between rounded-sm border border-signal/40 bg-signal/5 px-2 py-1 text-[11px] text-signal">
                  <span>
                    Will mark as{" "}
                    <span className="font-medium text-parchment">
                      {pendingState}
                    </span>{" "}
                    on save.
                  </span>
                  <button
                    type="button"
                    onClick={clearStaging}
                    className="text-dust-deep transition-colors hover:text-parchment"
                  >
                    undo
                  </button>
                </div>
              )}
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
