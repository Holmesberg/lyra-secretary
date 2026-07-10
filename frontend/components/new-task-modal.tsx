"use client";
import { useEffect, useLayoutEffect, useRef, useState } from "react";
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
import { useCurrentTime } from "@/lib/hooks/use-current-time";
import {
  rescheduleTask,
  type TaskRow,
} from "@/lib/tasks";
import { useNewTaskTimeControls } from "@/lib/hooks/use-new-task-time-controls";
import { useNewTaskCategoryControls } from "@/lib/hooks/use-new-task-category-controls";
import { useNewTaskDescriptionControls } from "@/lib/hooks/use-new-task-description-controls";
import { CategorySelect } from "@/components/category-select";
import { DeadlinePickerSlot } from "@/components/deadline-picker-slot";
import { CalibrationNudgeCard } from "@/components/calibration-nudge-card";
import {
  nudgeDecisionFromCalibration,
  type NudgeDecisionData,
} from "@/lib/creation-nudge";
import {
  useNewTaskSubmitController,
  type NewTaskSubmitDraft,
  type PausedConflict,
  type SoftConflict,
} from "@/components/use-new-task-submit-controller";
import { useNewTaskDeadlineControls } from "@/components/use-new-task-deadline-controls";
import { useCreationNudgeExposure } from "@/lib/hooks/use-creation-nudge-exposure";
import { useCreationNudgeLookup } from "@/components/use-creation-nudge-lookup";

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
  // Default 0h 0m — user must explicitly pick a duration before Create
  // enables (`canSubmit` already requires totalMinutes > 0).
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [pausedConflict, setPausedConflict] = useState<PausedConflict | null>(null);
  const [softConflict, setSoftConflict] = useState<SoftConflict | null>(null);
  const [lastEditId, setLastEditId] = useState<string | null>(null);
  // Once the user decides on the calibration nudge — accept the
  // suggested duration OR dismiss — suppress further fetches for the
  // rest of this modal session. Prevents the re-suggestion loop the
  // operator flagged 2026-04-21: clicking "Use X min" changes the
  // duration, which re-runs the bias_factor lookup with the new
  // planned value, which finds a *new* suggestion, which pops up a
  // second time. One decision per modal open. Reset on modal re-open
  // (see the `if (open && !editingTask)` effect below).
  const [nudgeDecisionMade, setNudgeDecisionMade] = useState(false);
  // Loop 1 calibration_nudge outcome log: capture the user's decision +
  // the four numeric inputs that produced the suggestion. Travels with
  // the createTask payload so the backend writes a calibration_nudge_event
  // row in the same transaction. Null when no nudge fired this session.
  const [nudgeDecisionData, setNudgeDecisionData] =
    useState<NudgeDecisionData | null>(null);
  const [editScheduleTouched, setEditScheduleTouched] = useState(false);

  const {
    category,
    categoryMode,
    resetCategory,
    loadCategory,
    handleCategorySelect,
    handleCustomCategoryChange,
    returnToCategoryPicker,
  } = useNewTaskCategoryControls();

  const {
    start,
    end,
    durHours,
    durMinutes,
    totalMinutes,
    endBeforeStart,
    suggestAmPmSwap,
    suggestPushStartToFuture,
    resetTimeDefaults,
    loadTimeRange,
    handleStartChange,
    handleEndChange,
    handleDurHoursChange,
    handleDurMinutesChange,
    applyDurationMinutes,
    applyAmPmSwap,
    applyPushStartToFuture,
  } = useNewTaskTimeControls({
    defaultDate,
    now,
    onEditScheduleChanged: markEditScheduleChanged,
  });

  const {
    description,
    showDescription,
    checklistEstimate,
    resetDescription,
    loadDescription,
    showDescriptionField,
    handleDescriptionChange,
  } = useNewTaskDescriptionControls(totalMinutes);

  // Loop 11 Phase K — deadline picker. `deadlineId` carries the user's
  // explicit choice (or the confirmed parser suggestion). `parserSuggestion`
  // is the read-only Pass 2 preview surfaced as a soft suggestion above the
  // submit button. They live in separate slices so dismissing the suggestion
  // doesn't clobber an already-confirmed picker choice.
  const {
    deadlineId,
    parserSuggestion,
    showDeadlinePicker,
    resetDeadline,
    loadDeadline,
    confirmSuggestion,
    dismissSuggestion,
    clearBinding,
    togglePicker,
    pickDeadline,
  } = useNewTaskDeadlineControls({
    open,
    isEdit,
    title,
    description,
  });
  const {
    calibrationNudge,
    nudgeSource,
    clearCreationNudge,
  } = useCreationNudgeLookup({
    open,
    category,
    start,
    end,
    durHours,
    durMinutes,
    isEdit,
    editScheduleTouched,
    nudgeDecisionMade,
  });

  const canSubmit = !submitting && title.trim().length > 0 && !endBeforeStart && totalMinutes > 0;
  const { ackVisibleCreationNudge } = useCreationNudgeExposure({
    nudge: calibrationNudge,
    source: nudgeSource,
    plannedMinutes: totalMinutes,
  });

  // AM/PM-swap recovery. Native <input type="datetime-local"> keeps
  // whichever period was last rendered; if the user types "1:45" meaning
  // PM after typing "11:45 AM" for the start, end silently lands 10h
  // before start on the same calendar day. Offer a one-tap +12h shift
  // as a fix.
  //
  // Strict inequality (negDiffMin < 0, not <= 0): when end EQUALS start
  // (diff=0) the user has zero duration, not an AM/PM slip. Dogfood
  // 2026-04-21 screenshot showed the old `>` guard (which flipped to
  // false for diff=0) suggesting "Did you mean 9:25 AM?" for start=end=
  // 9:25 PM — misleading because shifting 9:25 PM by +12h lands on the
  // NEXT day's 9:25 AM, and the time-only display hid the date change.
  // Same-day check on the shifted result catches any cross-midnight
  // shift defensively.
  // Past-start recovery. Distinct concern from AM/PM swap: user typed a
  // start time that's already passed (e.g., it's 9:23 PM and they set
  // start to 9:20 PM by accident, or the modal's `defaultStart` round-
  // up has gone stale because the user spent >5 min filling out the
  // form). Offer to bump start to the next 5-min mark in the future.
  // Fires alongside (not instead of) the AM/PM banner when both apply
  // — they're independent fixes. Only fires when start is strictly in
  // the past; the 60s useCurrentTime tick means the suggestion
  // naturally appears after the user lingers past the original
  // round-up mark.
  // Fresh defaults every time modal opens for a new task.
  // Using `open` as only dep intentionally — the 60s `now` tick must
  // not clobber in-progress typing.
  // eslint-disable-next-line react-hooks/exhaustive-deps
  useEffect(() => {
    if (open && !editingTask) {
      resetTimeDefaults();
      setTitle("");
      resetCategory();
      resetDescription();
      setError(null);
      setPausedConflict(null);
      setNudgeDecisionMade(false);
      setNudgeDecisionData(null);
      setEditScheduleTouched(false);
      resetDeadline();
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

  // Sync form fields when editingTask changes.
  useLayoutEffect(() => {
    if (!editingTask || editingTask.task_id === lastEditId) {
      return;
    }
    const startDate = editingTask.start ? new Date(editingTask.start) : new Date();
    const endDate = editingTask.end ? new Date(editingTask.end) : new Date();
    setTitle(editingTask.title);
    loadTimeRange(startDate, endDate);
    loadCategory(editingTask.category);
    // Edit-modal parity (2026-04-28): load description + deadline_id
    // from the task. Without this, opening edit + saving would silently
    // wipe both fields — DATA LOSS bug.
    loadDescription(editingTask.description);
    loadDeadline(editingTask.deadline_id);
    setError(null);
    setPausedConflict(null);
    setSoftConflict(null);
    clearCreationNudge();
    setNudgeDecisionMade(false);
    setNudgeDecisionData(null);
    setEditScheduleTouched(false);
    setLastEditId(editingTask.task_id);
  }, [
    clearCreationNudge,
    editingTask,
    lastEditId,
    loadCategory,
    loadDeadline,
    loadDescription,
    loadTimeRange,
  ]);

  function resetForm() {
    resetTimeDefaults();
    setTitle("");
    resetCategory();
    resetDescription();
    setError(null);
    setPausedConflict(null);
    setSoftConflict(null);
    clearCreationNudge();
    setNudgeDecisionMade(false);
    setNudgeDecisionData(null);
    setEditScheduleTouched(false);
    resetDeadline();
    setLastEditId(null);
  }

  const createDraft = (): NewTaskSubmitDraft => ({
    title,
    start,
    end,
    category,
    description,
    deadlineId,
    nudgeDecisionData,
  });

  const submitController = useNewTaskSubmitController({
    open,
    onReset: resetForm,
    onCreated,
    onClose,
    onInterruptionCreated,
  });

  // --- Edit schedule touch helper ---

  function markEditScheduleChanged() {
    if (!isEdit) return;
    setEditScheduleTouched(true);
    setNudgeDecisionMade(false);
    setNudgeDecisionData(null);
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
        const clearDeadline =
          Boolean(editingTask.deadline_id) && deadlineId === null;
        await rescheduleTask({
          task_id: editingTask.task_id,
          new_start: startDate.toISOString(),
          new_end: endDate.toISOString(),
          title: title.trim(),
          category,
          // Edit-modal parity (2026-04-28): description + deadline_id
          // now editable. Backend resets llm_parse_status='pending' on
          // description change so the chip refreshes.
          description: description.trim() || undefined,
          deadline_id: deadlineId ?? undefined,
          clear_deadline: clearDeadline,
        });
        resetForm();
        onCreated();
        onClose();
        return;
      }

      const res = await submitController.submit(createDraft());
      // Debug aid (Apr 16): dogfood diagnostic for severity-render
      // bug. If operator sees the wrong UI (red when expecting yellow
      // or vice versa), the response shape is logged so we can
      // verify severity + gate_ids match expectations.
      if (res.kind !== "created") {
        // eslint-disable-next-line no-console
        console.debug("[create] conflict response:", res);
      }
      if (res.kind === "pausedConflict") {
        setPausedConflict(res.conflict);
        return;
      }
      if (res.kind === "softConflict") {
        setSoftConflict(res.conflict);
        return;
      }
      if (res.kind === "error") {
        setError(res.message);
        return;
      }
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
    // a task transitioned to EXECUTING) - surface as a fresh warning.
    setError(null);
    setSubmitting(true);
    try {
      const res = await submitController.submitWithForce(createDraft());
      if (res.kind === "error") {
        setError(res.message);
        return;
      }
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
      const res = await submitController.submitAsInterruption(createDraft());
      if (res.kind === "error") {
        setError(res.message);
        return;
      }
    } catch (e: any) {
      setError(e?.message ?? "Failed to create interruption task");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <Dialog open={open} onOpenChange={(o) => { if (!o) { resetForm(); onClose(); } }}>
      <DialogContent
        data-testid="new-task-modal"
        onKeyDown={(e) => {
          if (e.key !== "Enter") return;
          if (e.shiftKey || e.ctrlKey || e.metaKey || e.altKey) return;
          if ((e.target as HTMLElement).tagName === "TEXTAREA") return;
          if (submitting) return;
          // Mirror DialogFooter button-selection logic so Enter triggers
          // whichever primary action is currently visible.
          if (pausedConflict) {
            if (pausedConflict.blockingTitles.length === 0) {
              e.preventDefault();
              submitAsInterruption();
            }
            return;
          }
          if (softConflict) {
            e.preventDefault();
            submitWithForce();
            return;
          }
          if (canSubmit) {
            e.preventDefault();
            submit();
          }
        }}
      >
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
              data-testid="new-task-title"
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
                data-testid="new-task-start"
                id="start"
                type="datetime-local"
                value={start}
                onChange={(e) => handleStartChange(e.target.value)}
              />
              {suggestPushStartToFuture && !isEdit && (
                <p className="text-[11px] text-ember/80">
                  Start is in the past —{" "}
                  <button
                    type="button"
                    onClick={applyPushStartToFuture}
                    className="text-signal underline-offset-2 transition-colors hover:text-signal-neon hover:underline"
                  >
                    push to{" "}
                    {new Date(suggestPushStartToFuture).toLocaleTimeString([], {
                      hour: "numeric",
                      minute: "2-digit",
                      hour12: true,
                    })}
                  </button>
                </p>
              )}
            </div>
            <div className="flex flex-col gap-1.5">
              <Label htmlFor="end">End</Label>
              <Input
                data-testid="new-task-end"
                id="end"
                type="datetime-local"
                value={end}
                onChange={(e) => handleEndChange(e.target.value)}
              />
            </div>
          </div>

          <div className="flex flex-col gap-1.5">
            <Label className="text-xs text-dust">Duration</Label>
            <div className="flex items-center gap-2">
              <Input
                data-testid="new-task-duration-hours"
                type="number"
                min={0}
                value={durHours}
                onChange={(e) => handleDurHoursChange(Number(e.target.value))}
                className="w-20 text-center text-sm text-parchment"
              />
              <span className="text-xs text-dust-deep">h</span>
              <Input
                data-testid="new-task-duration-minutes"
                type="number"
                min={0}
                value={durMinutes}
                onChange={(e) => handleDurMinutesChange(Number(e.target.value))}
                className="w-20 text-center text-sm text-parchment"
              />
              <span className="text-xs text-dust-deep">m</span>
            </div>
          </div>

          <div className="flex flex-col gap-1.5">
            <Label htmlFor="category">Category</Label>
            {categoryMode === "picker" ? (
              <CategorySelect
                value={category}
                onChange={handleCategorySelect}
              />
            ) : (
              <div className="flex items-center gap-2">
                <Input
                  data-testid="new-task-category-custom"
                  id="category"
                  value={category}
                  onChange={(e) => handleCustomCategoryChange(e.target.value)}
                  placeholder="e.g. research, admin, side_project"
                  autoComplete="off"
                  autoFocus
                />
                <button
                  data-testid="new-task-category-back"
                  type="button"
                  className="whitespace-nowrap text-xs text-dust transition-colors hover:text-parchment"
                  onClick={returnToCategoryPicker}
                >
                  ← Back
                </button>
              </div>
            )}
            {categoryMode === "custom" && (
              <p className="text-[11px] text-dust-deep">
                New categories start with no history — their patterns accrue
                as you log.
              </p>
            )}
          </div>

          {/* Edit-modal parity (2026-04-28): description was previously
              gated to create-only. Now editable on edit too — the
              reschedule endpoint resets llm_parse_status='pending' on
              change so the chip refreshes. */}
          <div className="flex flex-col gap-1.5">
            {!showDescription ? (
              <button
                type="button"
                className="flex items-center gap-1 text-xs text-dust-deep transition-colors hover:text-dust"
                onClick={showDescriptionField}
              >
                <span>{isEdit ? "Edit details" : "Add details"}</span>
                <span className="text-[10px]">▾</span>
              </button>
            ) : (
              <>
                <Label htmlFor="description">What does this involve? <span className="text-dust-deep font-normal">(optional)</span></Label>
                <textarea
                  data-testid="new-task-description"
                  id="description"
                  value={description}
                  onChange={(e) => handleDescriptionChange(e.target.value)}
                  placeholder="- Step one&#10;- Step two&#10;- Step three"
                  rows={3}
                  className="rounded-sm border border-hairline-signal/30 bg-transparent px-3 py-2 text-sm text-parchment placeholder:text-dust-deep resize-none"
                />
                {checklistEstimate && (
                  <span className="text-[11px] text-dust-deep">
                    {checklistEstimate.itemCount} items, ~{checklistEstimate.perItemMinutes} min each based on your estimate
                  </span>
                )}
              </>
            )}
          </div>

          {endBeforeStart && (
            <div className="rounded-sm border border-ember/40 bg-ember/5 p-3 text-xs text-ember">
              <div className="font-medium">End time must be after start.</div>
              {suggestAmPmSwap && (
                <button
                  type="button"
                  onClick={applyAmPmSwap}
                  className="mt-1.5 inline-flex items-center gap-1 text-signal underline-offset-2 transition-colors hover:text-signal-neon hover:underline"
                >
                  Did you mean{" "}
                  {new Date(suggestAmPmSwap).toLocaleTimeString([], {
                    hour: "numeric",
                    minute: "2-digit",
                    hour12: true,
                  })}
                  ? — tap to fix
                </button>
              )}
            </div>
          )}

          {pausedConflict && (
            <>
              <div className="rounded-md border border-ember/40 bg-ember/5 p-3 text-xs text-ember">
                <span className="font-medium text-parchment">{pausedConflict.title}</span>{" "}
                is paused in this window.{" "}
                {pausedConflict.blockingTitles.length === 0 ? (
                  <>
                    Start{" "}
                    <span className="font-medium text-parchment">{title.trim()}</span>{" "}
                    as an interruption? It will be linked — you can resume{" "}
                    <span className="font-medium text-parchment">{pausedConflict.title}</span>{" "}
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
                <div className="rounded border border-ember/40 bg-ember/5 p-2 text-xs text-ember">
                  Also conflicts with: {pausedConflict.blockingTitles.join(", ")}
                </div>
              )}
            </>
          )}

          {softConflict && (
            <div className="rounded-md border border-ember/40 bg-ember/5 p-3 text-xs text-ember">
              {softConflict.executingTitles.length > 0 && (
                <div>
                  Timer running on{" "}
                  <span className="font-medium text-parchment">
                    {softConflict.executingTitles.join(", ")}
                  </span>
                  .
                </div>
              )}
              {softConflict.overlapTitles.length > 0 && (
                <div>
                  Overlaps with{" "}
                  <span className="font-medium text-parchment">
                    {softConflict.overlapTitles.join(", ")}
                  </span>
                  .
                </div>
              )}
              {softConflict.reasons.includes("duplicate_title") && softConflict.duplicateTitle && (
                <div>
                  Already have{" "}
                  <span className="font-medium text-parchment">{softConflict.duplicateTitle}</span>{" "}
                  today.
                </div>
              )}
              <div className="mt-1 text-dust">Create as planned anyway?</div>
            </div>
          )}

          {/* Loop 11 Phase K — deadline picker.
              Three modes:
                1. deadlineId set → show "Bound to X" with a clear button
                2. parserSuggestion present (and no manual choice) → soft suggestion
                3. neither → "+ pick deadline" link (opens manual picker)
              Edit-modal parity (2026-04-28): rendered in edit mode too.
              parserSuggestion is suppressed in edit (only fires on first
              create via parser preview), but the manual picker stays
              available so users can rebind. */}
          {!softConflict && !pausedConflict && !error && (
            <DeadlinePickerSlot
              deadlineId={deadlineId}
              suggestion={isEdit ? null : parserSuggestion}
              showPicker={showDeadlinePicker}
              onConfirmSuggestion={confirmSuggestion}
              onDismissSuggestion={dismissSuggestion}
              onClearBinding={clearBinding}
              onTogglePicker={togglePicker}
              onPick={pickDeadline}
            />
          )}

          {calibrationNudge && !softConflict && !pausedConflict && !error && (
            <CalibrationNudgeCard
              nudge={calibrationNudge}
              source={nudgeSource}
              plannedMinutes={durHours * 60 + durMinutes}
              onUseSuggested={() => {
                const newMin = calibrationNudge.suggestedMin;
                ackVisibleCreationNudge();
                setNudgeDecisionData(
                  nudgeDecisionFromCalibration(calibrationNudge, "accepted"),
                );
                applyDurationMinutes(newMin);
                clearCreationNudge();
                setNudgeDecisionMade(true);
              }}
              onKeepEstimate={() => {
                ackVisibleCreationNudge();
                setNudgeDecisionData(
                  nudgeDecisionFromCalibration(calibrationNudge, "dismissed"),
                );
                clearCreationNudge();
                setNudgeDecisionMade(true);
              }}
            />
          )}

          {error && (
            <div className="rounded border border-ember/40 bg-ember/5 p-2 text-xs text-ember">
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
              data-testid="new-task-start-as-interruption"
              onClick={submitAsInterruption}
              disabled={submitting || pausedConflict.blockingTitles.length > 0}
            >
              Start as interruption
            </Button>
          ) : softConflict ? (
            <Button
              data-testid="new-task-create-anyway"
              onClick={submitWithForce}
              disabled={submitting}
            >
              Create anyway
            </Button>
          ) : (
            <Button
              data-testid={isEdit ? "new-task-save" : "new-task-create"}
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
