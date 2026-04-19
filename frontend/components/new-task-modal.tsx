"use client";
import { useEffect, useRef, useState } from "react";
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
import { CATEGORIES } from "@/lib/categories";
import { useCurrentTime } from "@/lib/hooks/use-current-time";
import {
  createTask,
  rescheduleTask,
  lookupBiasFactor,
  type TaskRow,
  type BiasFactorCell,
} from "@/lib/tasks";

function formatLocal(d: Date) {
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(
    d.getHours()
  )}:${pad(d.getMinutes())}`;
}

/** Round up to the next 5-minute boundary. 2:06 → 2:10; 2:58 → 3:00. */
function defaultStart(from: Date = new Date()) {
  const d = new Date(from);
  const mins = d.getMinutes();
  const next5 = Math.ceil(mins / 5) * 5;
  if (next5 >= 60) {
    d.setHours(d.getHours() + 1, 0, 0, 0);
  } else {
    d.setMinutes(next5, 0, 0);
  }
  return formatLocal(d);
}

/**
 * Default start for a specific target date — preserves the user's current
 * clock time (rounded up to next 5 min) but swaps the calendar day to the
 * `targetDateStr` (YYYY-MM-DD). Used when the operator clicks "+ New task"
 * while viewing a future day in /today — the start defaults to that day
 * at "now"-ish rather than literal today.
 */
function defaultStartForDate(targetDateStr: string, now: Date = new Date()) {
  const [y, m, d] = targetDateStr.split("-").map(Number);
  const base = new Date(y, m - 1, d, now.getHours(), now.getMinutes(), 0, 0);
  const mins = base.getMinutes();
  const next5 = Math.ceil(mins / 5) * 5;
  if (next5 >= 60) {
    base.setHours(base.getHours() + 1, 0, 0, 0);
  } else {
    base.setMinutes(next5, 0, 0);
  }
  return formatLocal(base);
}

function addMinutes(localStr: string, mins: number): string {
  const d = new Date(localStr);
  d.setMinutes(d.getMinutes() + mins);
  return formatLocal(d);
}

function diffMinutes(startStr: string, endStr: string): number {
  return Math.round((new Date(endStr).getTime() - new Date(startStr).getTime()) / 60_000);
}

function timeOfDay(localStr: string): string {
  const h = new Date(localStr).getHours();
  if (h >= 5 && h < 12) return "morning";
  if (h >= 12 && h < 17) return "afternoon";
  if (h >= 17 && h < 21) return "evening";
  return "night";
}

function roundTo5(n: number): number {
  return Math.round(n / 5) * 5 || 5;
}

interface PausedConflict {
  taskId: string;
  title: string;
  blockingTitles: string[];
}

interface SoftConflict {
  reasons: string[];
  overlapTitles: string[];
  executingTitles: string[];
  duplicateTitle: string | null;
}

interface Props {
  open: boolean;
  onClose: () => void;
  onCreated: () => void;
  onInterruptionCreated?: (taskId: string, taskTitle: string) => void;
  editingTask?: TaskRow | null;
  /** Day the operator is viewing in /today — default start defaults to this
     day at the current clock time (rounded to 5 min). Format YYYY-MM-DD.
     Omit for "use today". */
  defaultDate?: string;
}

export function NewTaskModal({ open, onClose, onCreated, onInterruptionCreated, editingTask, defaultDate }: Props) {
  const isEdit = !!editingTask;
  const now = useCurrentTime();

  const [title, setTitle] = useState("");
  const titleInputRef = useRef<HTMLInputElement>(null);
  const [start, setStart] = useState(() => defaultStart());
  const [end, setEnd] = useState(() => defaultStart());
  // Default 0h 0m — user must explicitly pick a duration before Create
  // enables (`canSubmit` already requires totalMinutes > 0).
  const [durHours, setDurHours] = useState(0);
  const [durMinutes, setDurMinutes] = useState(0);
  // Category: picker mode uses the fixed taxonomy; "custom" mode reveals
  // a text input for a user-created name. The Apr 4–15 experiment window
  // has closed, so operator-created categories are research-safe going
  // forward (fresh buckets start at n=0 until data accrues for
  // bias_factor analysis).
  const [category, setCategory] = useState<string>("work");
  const [categoryMode, setCategoryMode] = useState<"picker" | "custom">(
    "picker"
  );
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [pausedConflict, setPausedConflict] = useState<PausedConflict | null>(null);
  const [softConflict, setSoftConflict] = useState<SoftConflict | null>(null);
  const [lastEditId, setLastEditId] = useState<string | null>(null);
  const [description, setDescription] = useState("");
  const [showDescription, setShowDescription] = useState(false);
  const [nudgeSource, setNudgeSource] = useState<"personal" | "research" | null>(null);
  const [calibrationNudge, setCalibrationNudge] = useState<{
    cell: BiasFactorCell;
    suggestedMin: number;
  } | null>(null);

  // Fetch bias_factor when category or start time changes (debounced).
  useEffect(() => {
    if (!open || isEdit) { setCalibrationNudge(null); return; }
    const tod = timeOfDay(start);
    const planned = durHours * 60 + durMinutes;
    const abortCtl = new AbortController();
    const timer = setTimeout(() => {
      lookupBiasFactor(category, tod, planned || 30)
        .then((res) => {
          if (abortCtl.signal.aborted) return;
          const isResearch = res.source === "research";
          const threshold = isResearch ? 1.20 : 1.25;
          if (res.cell && res.cell.bias_factor >= threshold) {
            setCalibrationNudge({
              cell: res.cell,
              suggestedMin: roundTo5(planned * res.cell.bias_factor),
            });
            setNudgeSource(isResearch ? "research" : "personal");
          } else {
            setCalibrationNudge(null);
            setNudgeSource(null);
          }
        })
        .catch(() => { if (!abortCtl.signal.aborted) { setCalibrationNudge(null); setNudgeSource(null); } });
    }, 400);
    return () => { clearTimeout(timer); abortCtl.abort(); };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open, category, start, durHours, durMinutes, isEdit]);

  const totalMinutes = durHours * 60 + durMinutes;
  const endBeforeStart = diffMinutes(start, end) <= 0;
  const canSubmit = !submitting && title.trim().length > 0 && !endBeforeStart && totalMinutes > 0;

  // Fresh defaults every time modal opens for a new task.
  // Using `open` as only dep intentionally — the 60s `now` tick must
  // not clobber in-progress typing.
  // eslint-disable-next-line react-hooks/exhaustive-deps
  useEffect(() => {
    if (open && !editingTask) {
      const s = defaultDate ? defaultStartForDate(defaultDate, now) : defaultStart(now);
      setStart(s);
      setEnd(s);
      setDurHours(0);
      setDurMinutes(0);
      setTitle("");
      setCategory("work");
      setCategoryMode("picker");
      setDescription("");
      setShowDescription(false);
      setError(null);
      setPausedConflict(null);
      setLastEditId(null);
    }
  }, [open, editingTask]);

  // When opening in edit mode, select all of the title text so the operator
  // can retype instantly. rAF avoids racing the input mount + autoFocus.
  useEffect(() => {
    if (open && editingTask) {
      const raf = requestAnimationFrame(() => {
        titleInputRef.current?.select();
      });
      return () => cancelAnimationFrame(raf);
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
    const editCat = editingTask.category || "work";
    setCategory(editCat);
    // If the editing task has a custom (non-taxonomy) category, open the
    // custom input pre-filled so the operator can edit it directly.
    setCategoryMode(
      (CATEGORIES as readonly string[]).includes(editCat) ? "picker" : "custom"
    );
    setError(null);
    setPausedConflict(null);
    setSoftConflict(null);
    setLastEditId(editingTask.task_id);
  }

  function resetForm() {
    const s = defaultDate ? defaultStartForDate(defaultDate, now) : defaultStart(now);
    setTitle("");
    setStart(s);
    setEnd(s);
    setDurHours(0);
    setDurMinutes(0);
    setCategory("work");
    setCategoryMode("picker");
    setDescription("");
    setShowDescription(false);
    setError(null);
    setPausedConflict(null);
    setSoftConflict(null);
    setCalibrationNudge(null);
    setNudgeSource(null);
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
        description: description.trim() || undefined,
      });
      // Debug aid (Apr 16): dogfood diagnostic for severity-render
      // bug. If operator sees the wrong UI (red when expecting yellow
      // or vice versa), the response shape is logged so we can
      // verify severity + gate_ids match expectations.
      if (!res.created) {
        // eslint-disable-next-line no-console
        console.debug("[create] conflict response:", res);
      }
      if (!res.created) {
        if (res.conflicts.length > 0) {
          const paused = res.conflicts.filter((c) => c.state === "PAUSED");
          const startingSoon = new Date(start).getTime() - Date.now() < 5 * 60_000;
          if (paused.length > 0 && onInterruptionCreated && startingSoon) {
            setPausedConflict({
              taskId: paused[0].task_id,
              title: paused[0].title,
              blockingTitles: res.conflicts
                .filter((c) => c.state !== "PAUSED")
                .map((c) => c.title),
            });
            return;
          }
          if (res.severity === "soft" || res.severity === "hard") {
            const executing = res.conflicts
              .filter((c) => c.gate_id === "executing_overlap" || c.gate_id === "active_overlap")
              .map((c) => c.title);
            const overlaps = res.conflicts
              .filter((c) => c.gate_id === "planned_overlap")
              .map((c) => c.title);
            const dups = res.conflicts
              .filter((c) => c.gate_id === "duplicate_title")
              .map((c) => c.title);
            setSoftConflict({
              reasons: res.soft_reasons ?? [],
              overlapTitles: overlaps,
              executingTitles: executing,
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
              ref={titleInputRef}
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="What needs doing"
              autoFocus
              onFocus={(e) => { if (isEdit) e.currentTarget.select(); }}
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
            {categoryMode === "picker" ? (
              <select
                id="category"
                value={category}
                onChange={(e) => {
                  if (e.target.value === "__CREATE_NEW__") {
                    setCategoryMode("custom");
                    setCategory("");
                  } else {
                    setCategory(e.target.value);
                  }
                }}
                className="h-9 rounded-md border border-white/15 bg-transparent px-3 text-sm"
              >
                {CATEGORIES.map((c) => (
                  <option key={c} value={c} className="bg-[#0a0a0a]">
                    {c.replace("_", " ")}
                  </option>
                ))}
                <option
                  value="__CREATE_NEW__"
                  className="bg-[#0a0a0a] text-blue-300"
                >
                  + Create a new category…
                </option>
              </select>
            ) : (
              <div className="flex items-center gap-2">
                <Input
                  id="category"
                  value={category}
                  onChange={(e) => setCategory(e.target.value)}
                  placeholder="e.g. research, admin, side_project"
                  autoComplete="off"
                  autoFocus
                />
                <button
                  type="button"
                  className="whitespace-nowrap text-xs text-white/50 hover:text-white"
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
              <p className="text-[11px] text-white/40">
                New categories start with no history — their patterns accrue
                as you log.
              </p>
            )}
          </div>

          {!isEdit && (
            <div className="flex flex-col gap-1.5">
              {!showDescription ? (
                <button
                  type="button"
                  className="flex items-center gap-1 text-xs text-white/40 hover:text-white/60"
                  onClick={() => setShowDescription(true)}
                >
                  <span>Add details</span>
                  <span className="text-[10px]">▾</span>
                </button>
              ) : (
                <>
                  <Label htmlFor="description">What does this involve? <span className="text-white/30 font-normal">(optional)</span></Label>
                  <textarea
                    id="description"
                    value={description}
                    onChange={(e) => setDescription(e.target.value)}
                    placeholder="- Step one&#10;- Step two&#10;- Step three"
                    rows={3}
                    className="rounded-md border border-white/15 bg-transparent px-3 py-2 text-sm text-white/70 placeholder:text-white/20 resize-none"
                  />
                  {(() => {
                    const items = description.split("\n").filter((l) => /^\s*[-*•]\s|^\s*\d+[.)]\s/.test(l));
                    const planned = durHours * 60 + durMinutes;
                    if (items.length >= 2 && planned > 0) {
                      const perItem = Math.round((planned / items.length) * 10) / 10;
                      return (
                        <span className="text-[11px] text-white/30">
                          {items.length} items, ~{perItem} min each based on your estimate
                        </span>
                      );
                    }
                    return null;
                  })()}
                </>
              )}
            </div>
          )}

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
              {softConflict.executingTitles.length > 0 && (
                <div>
                  Timer running on{" "}
                  <span className="font-medium text-white">
                    {softConflict.executingTitles.join(", ")}
                  </span>
                  .
                </div>
              )}
              {softConflict.overlapTitles.length > 0 && (
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
              <div className="mt-1 text-white/60">Create as planned anyway?</div>
            </div>
          )}

          {calibrationNudge && !softConflict && !pausedConflict && !error && (
            <div className="rounded-md border border-blue-500/30 bg-blue-500/10 p-3 text-xs text-blue-200">
              <div>
                {nudgeSource === "research" ? (
                  <>
                    Research on <span className="font-medium text-white">{calibrationNudge.cell.category}</span> tasks
                    shows people underestimate by <span className="font-medium text-white">{Math.round((calibrationNudge.cell.bias_factor - 1) * 100)}%</span>.
                    {" "}Your estimate: {durHours * 60 + durMinutes} min.
                    {calibrationNudge.cell.citation && (
                      <span className="block mt-0.5 text-[10px] text-blue-300/50">{calibrationNudge.cell.citation}</span>
                    )}
                  </>
                ) : (
                  <>
                    {calibrationNudge.cell.sessions < 10 ? "Early data" : "Your data"}
                    {" "}({calibrationNudge.cell.sessions} sessions): <span className="font-medium text-white">{calibrationNudge.cell.category}</span> tasks
                    {calibrationNudge.cell.time_of_day !== "all" && (
                      <> in the <span className="font-medium text-white">{calibrationNudge.cell.time_of_day}</span></>
                    )}
                    {" "}run <span className="font-medium text-white">{Math.round((calibrationNudge.cell.bias_factor - 1) * 100)}%</span> over plan.
                  </>
                )}
                {" "}Adjust to {calibrationNudge.suggestedMin} min?
              </div>
              <div className="mt-2 flex gap-2">
                <button
                  type="button"
                  className="rounded bg-blue-500/20 px-2 py-1 text-[11px] font-medium text-blue-100 hover:bg-blue-500/30"
                  onClick={() => {
                    const newMin = calibrationNudge.suggestedMin;
                    setDurHours(Math.floor(newMin / 60));
                    setDurMinutes(newMin % 60);
                    setEnd(addMinutes(start, newMin));
                    setCalibrationNudge(null);
                  }}
                >
                  Use {calibrationNudge.suggestedMin} min
                </button>
                <button
                  type="button"
                  className="rounded bg-white/5 px-2 py-1 text-[11px] text-white/60 hover:bg-white/10"
                  onClick={() => setCalibrationNudge(null)}
                >
                  Keep {durHours * 60 + durMinutes} min
                </button>
              </div>
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
