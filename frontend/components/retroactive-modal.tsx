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
import { createRetroactive, type UnplannedReason } from "@/lib/tasks";
import { CATEGORIES } from "@/lib/categories";

function formatLocal(d: Date) {
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(
    d.getDate()
  )}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

const REASONS: { value: UnplannedReason; label: string; hint: string }[] = [
  {
    value: "forgot_to_log",
    label: "I forgot to log it",
    hint: "Did the work, never hit Start.",
  },
  {
    value: "unexpected_task",
    label: "Unexpected task came up",
    hint: "Wasn't on the plan this morning.",
  },
  {
    value: "spontaneous_decision",
    label: "Spontaneous decision",
    hint: "Felt like doing it, didn't plan ahead.",
  },
  {
    value: "planning_friction",
    label: "Planning was too much friction",
    hint: "Skipped the planning step on purpose.",
  },
];

type Step = "reason" | "log";

interface Props {
  open: boolean;
  onClose: () => void;
  onCreated: () => void;
  /** YYYY-MM-DD. Defaults the modal's date pickers to this day. */
  defaultDate?: string;
}

/**
 * Two-step retroactive logging. Step 1 asks WHY the session wasn't logged
 * in real time (preserves unplanned_reason for research stratification).
 * Step 2 collects the minimum fields to construct a valid
 * /v1/stopwatch/retroactive POST.
 */
export function RetroactiveModal({
  open,
  onClose,
  onCreated,
  defaultDate,
}: Props) {
  const [step, setStep] = useState<Step>("reason");
  const [reason, setReason] = useState<UnplannedReason | null>(null);

  const [title, setTitle] = useState("");
  const [start, setStart] = useState("");
  const [end, setEnd] = useState("");
  // Category: required field per research integrity — without a category
  // the session can't be placed in a bias_factor cell. Reuses the exact
  // picker/custom UI pattern from new-task-modal.
  const [category, setCategory] = useState<string>("work");
  const [categoryMode, setCategoryMode] = useState<"picker" | "custom">(
    "picker"
  );
  // Completion % is captured for operator's own recall / future analytics.
  // Not sent to the backend in this pass — the retroactive endpoint doesn't
  // accept task_completion_percentage. See TODO in handleSubmit.
  const [completionPct, setCompletionPct] = useState<number>(100);
  const [reflection, setReflection] = useState<number>(3);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Reset everything when modal opens.
  useEffect(() => {
    if (!open) return;
    setStep("reason");
    setReason(null);
    setTitle("");
    setCategory("work");
    setCategoryMode("picker");
    setCompletionPct(100);
    setReflection(3);
    setError(null);
    setSubmitting(false);

    // Seed start/end from defaultDate (or today) at a workday-reasonable
    // time. End defaults to 30 min after start as a common-case guess;
    // operator adjusts both.
    const base = new Date();
    if (defaultDate) {
      const [y, m, d] = defaultDate.split("-").map(Number);
      base.setFullYear(y, m - 1, d);
    }
    base.setHours(9, 0, 0, 0);
    const s = new Date(base);
    const e = new Date(base);
    e.setMinutes(e.getMinutes() + 30);
    setStart(formatLocal(s));
    setEnd(formatLocal(e));
  }, [open, defaultDate]);

  const canSubmit =
    !submitting &&
    title.trim().length > 0 &&
    category.trim().length > 0 &&
    !!start &&
    !!end &&
    new Date(end).getTime() > new Date(start).getTime() &&
    !!reason;

  async function handleSubmit() {
    if (!canSubmit || !reason) return;
    setError(null);
    setSubmitting(true);
    try {
      await createRetroactive({
        title: title.trim(),
        start_time: new Date(start).toISOString(),
        end_time: new Date(end).toISOString(),
        post_task_reflection: reflection,
        total_paused_minutes: 0,
        unplanned_reason: reason,
        category: category.trim(),
      });
      // TODO(completion_pct): the retroactive endpoint doesn't currently
      // accept task_completion_percentage. To round-trip the UI slider,
      // either (a) extend the endpoint, or (b) POST to a new
      // /v1/tasks/{id}/completion updater right after create. For now the
      // slider is informational only.
      onCreated();
      onClose();
    } catch (e: any) {
      setError(e?.message ?? "Failed to log retroactive session");
    } finally {
      setSubmitting(false);
    }
  }

  const prettyReason = reason
    ? REASONS.find((r) => r.value === reason)?.label
    : "—";

  return (
    <Dialog
      open={open}
      onOpenChange={(o) => {
        if (!o) onClose();
      }}
    >
      <DialogContent>
        {step === "reason" ? (
          <>
            <DialogHeader>
              <DialogTitle>Log past session</DialogTitle>
              <DialogDescription>
                First — why didn&apos;t this get logged in real time? This
                becomes part of the record so patterns over time stay
                honest.
              </DialogDescription>
            </DialogHeader>

            <div className="flex flex-col gap-2">
              {REASONS.map((r) => (
                <button
                  key={r.value}
                  type="button"
                  onClick={() => setReason(r.value)}
                  className={`rounded-md border px-4 py-3 text-left transition-colors ${
                    reason === r.value
                      ? "border-signal/60 bg-signal/10"
                      : "border-hairline hover:border-signal/40 hover:bg-signal/[0.03]"
                  }`}
                >
                  <div className="text-sm font-medium text-parchment">
                    {r.label}
                  </div>
                  <div className="mt-0.5 text-xs text-dust">{r.hint}</div>
                </button>
              ))}
            </div>

            <DialogFooter>
              <Button variant="ghost" onClick={onClose}>
                Cancel
              </Button>
              <Button
                onClick={() => setStep("log")}
                disabled={!reason}
              >
                Continue →
              </Button>
            </DialogFooter>
          </>
        ) : (
          <>
            <DialogHeader>
              <DialogTitle>Log what happened</DialogTitle>
              <DialogDescription>
                Reason:{" "}
                <span className="text-parchment">{prettyReason}</span>
              </DialogDescription>
            </DialogHeader>

            <div className="flex flex-col gap-4">
              <div className="flex flex-col gap-1.5">
                <Label htmlFor="retro-title">Title</Label>
                <Input
                  id="retro-title"
                  value={title}
                  onChange={(e) => setTitle(e.target.value)}
                  placeholder="What did you do"
                  autoFocus
                />
              </div>

              {/* Category picker — exact same UI pattern as new-task-modal.
                 Required field: bias_factor analytics can't place a session
                 in a cell without a category, so no fallback default. */}
              <div className="flex flex-col gap-1.5">
                <Label htmlFor="retro-category">Category</Label>
                {categoryMode === "picker" ? (
                  <select
                    id="retro-category"
                    value={category}
                    onChange={(e) => {
                      if (e.target.value === "__CREATE_NEW__") {
                        setCategoryMode("custom");
                        setCategory("");
                      } else {
                        setCategory(e.target.value);
                      }
                    }}
                    className="h-9 rounded-sm border border-hairline-signal/30 bg-transparent px-3 text-sm text-parchment"
                  >
                    {CATEGORIES.map((c) => (
                      <option key={c} value={c} className="bg-void">
                        {c.replace("_", " ")}
                      </option>
                    ))}
                    <option
                      value="__CREATE_NEW__"
                      className="bg-void text-signal"
                    >
                      + Create a new category…
                    </option>
                  </select>
                ) : (
                  <div className="flex items-center gap-2">
                    <Input
                      id="retro-category"
                      value={category}
                      onChange={(e) => setCategory(e.target.value)}
                      placeholder="e.g. research, admin, side_project"
                      autoComplete="off"
                      autoFocus
                    />
                    <button
                      type="button"
                      className="whitespace-nowrap text-xs text-dust transition-colors hover:text-parchment"
                      onClick={() => {
                        setCategoryMode("picker");
                        setCategory("work");
                      }}
                    >
                      ← Back
                    </button>
                  </div>
                )}
                {categoryMode === "custom" && (
                  <p className="text-[11px] text-dust-deep">
                    New categories start with no history — their patterns
                    accrue as you log.
                  </p>
                )}
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div className="flex flex-col gap-1.5">
                  <Label htmlFor="retro-start">Started</Label>
                  <Input
                    id="retro-start"
                    type="datetime-local"
                    value={start}
                    onChange={(e) => setStart(e.target.value)}
                  />
                </div>
                <div className="flex flex-col gap-1.5">
                  <Label htmlFor="retro-end">Ended</Label>
                  <Input
                    id="retro-end"
                    type="datetime-local"
                    value={end}
                    onChange={(e) => setEnd(e.target.value)}
                  />
                </div>
              </div>

              <div className="flex flex-col gap-1.5">
                <Label htmlFor="retro-completion">
                  Scope / completion{" "}
                  <span className="font-normal text-dust-deep">
                    ({completionPct}%)
                  </span>
                </Label>
                <input
                  id="retro-completion"
                  type="range"
                  min={0}
                  max={100}
                  step={5}
                  value={completionPct}
                  onChange={(e) => setCompletionPct(Number(e.target.value))}
                  className="accent-[#4dd4e8]"
                />
                <div className="flex justify-between text-[10px] uppercase tracking-widest text-dust-deep">
                  <span>0%</span>
                  <span>50%</span>
                  <span>100%</span>
                </div>
              </div>

              <div className="flex flex-col gap-1.5">
                <Label htmlFor="retro-reflection">
                  Focus quality{" "}
                  <span className="font-normal text-dust-deep">
                    (1 = poor, 5 = excellent)
                  </span>
                </Label>
                <div className="flex gap-1.5">
                  {[1, 2, 3, 4, 5].map((n) => (
                    <button
                      key={n}
                      type="button"
                      onClick={() => setReflection(n)}
                      className={`h-9 flex-1 rounded-sm border text-sm transition-colors ${
                        reflection === n
                          ? "border-signal/60 bg-signal/10 text-parchment"
                          : "border-hairline text-dust hover:border-signal/40 hover:text-parchment"
                      }`}
                    >
                      {n}
                    </button>
                  ))}
                </div>
              </div>

              {error && (
                <div className="rounded-sm border border-ember/40 bg-ember/5 p-2 text-xs text-ember">
                  {error}
                </div>
              )}
            </div>

            <DialogFooter>
              <Button variant="ghost" onClick={() => setStep("reason")}>
                ← Back
              </Button>
              <Button onClick={handleSubmit} disabled={!canSubmit}>
                {submitting ? "Logging…" : "Log session"}
              </Button>
            </DialogFooter>
          </>
        )}
      </DialogContent>
    </Dialog>
  );
}
