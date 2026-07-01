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
  type BiasLookupResponse,
} from "@/lib/tasks";
import {
  addMinutes,
  defaultStart,
  defaultStartForDate,
  diffMinutes,
  formatLocal,
  roundTo5,
  timeOfDay,
} from "@/lib/task-time";
import { ackExposureRender, ackExposureSuppression } from "@/lib/api";
import {
  previewDeadlineBinding,
  type DeadlinePreviewResponse,
} from "@/lib/deadlines";
import { CategorySelect } from "@/components/category-select";
import { DeadlinePickerSlot } from "@/components/deadline-picker-slot";
import {
  CalibrationNudgeCard,
  type CalibrationNudge,
} from "@/components/calibration-nudge-card";

const BIAS_LOOKUP_DEBOUNCE_MS = 120;
const RESEARCH_PRIOR_DEFAULT = {
  biasFactor: 1.35,
  citation: "Kahneman & Tversky 1979 (planning fallacy mean)",
};
const RESEARCH_PRIORS: Record<string, { biasFactor: number; citation: string }> = {
  development: { biasFactor: 1.5, citation: "Buehler et al. 1994; Connolly & Dean 1997" },
  work: { biasFactor: 1.45, citation: "Buehler et al. 1994" },
  study: { biasFactor: 1.4, citation: "Newby-Clark et al. 2000" },
  academic: { biasFactor: 1.4, citation: "Newby-Clark et al. 2000" },
  exercise: { biasFactor: 1.15, citation: "Roy et al. 2005" },
  fitness: { biasFactor: 1.15, citation: "Roy et al. 2005" },
};
const pendingCreationNudgeRenderAcks = new Set<string>();
const ackedCreationNudgeRenders = new Set<string>();
const pendingCreationNudgeSuppressions = new Set<string>();
const suppressedCreationNudgeExposures = new Set<string>();
const CREATION_NUDGE_RENDER_ACK_RETRY_MS = [250, 750, 1500, 3000, 6000];
const CREATION_NUDGE_SUPPRESSION_RETRY_MS = [500, 1500, 3000];
const CREATION_NUDGE_EXPOSURE_TTL_MS = 30_000;
const creationNudgeExposureIds = new Map<string, { exposureId: string; expiresAt: number }>();

function newExposureId(): string {
  return globalThis.crypto?.randomUUID?.() ?? `client-${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

function exposureIdForCreationNudge(category: string, tod: string, planned: number): string {
  const key = `${category}\u0000${tod}\u0000${planned}`;
  const now = Date.now();
  const cached = creationNudgeExposureIds.get(key);
  if (cached && cached.expiresAt > now) {
    return cached.exposureId;
  }
  const exposureId = newExposureId();
  creationNudgeExposureIds.set(key, {
    exposureId,
    expiresAt: now + CREATION_NUDGE_EXPOSURE_TTL_MS,
  });
  return exposureId;
}

function ackCreationNudgeRender(
  exposureId: string,
  contentSnapshot: Record<string, unknown>,
  attempt = 0
) {
  if (
    pendingCreationNudgeRenderAcks.has(exposureId) ||
    ackedCreationNudgeRenders.has(exposureId)
  ) {
    return;
  }
  pendingCreationNudgeRenderAcks.add(exposureId);
  void ackExposureRender(exposureId, {
    surfaceId: "task.creation_nudge",
    clientEventId: `task.creation_nudge:${exposureId}`,
    contentSnapshot,
  })
    .then((ok) => {
      if (ok) {
        ackedCreationNudgeRenders.add(exposureId);
        return;
      }
      const retryDelay = CREATION_NUDGE_RENDER_ACK_RETRY_MS[attempt];
      if (retryDelay !== undefined) {
        globalThis.setTimeout(() => {
          ackCreationNudgeRender(exposureId, contentSnapshot, attempt + 1);
        }, retryDelay);
      }
    })
    .finally(() => {
      pendingCreationNudgeRenderAcks.delete(exposureId);
    });
}

function suppressCreationNudgeExposure(exposureId: string, attempt = 0) {
  if (
    pendingCreationNudgeSuppressions.has(exposureId) ||
    suppressedCreationNudgeExposures.has(exposureId) ||
    ackedCreationNudgeRenders.has(exposureId)
  ) {
    return;
  }
  pendingCreationNudgeSuppressions.add(exposureId);
  void ackExposureSuppression(exposureId, {
    suppressionReason: "client_discarded_before_render",
  })
    .then((ok) => {
      if (ok) {
        suppressedCreationNudgeExposures.add(exposureId);
        return;
      }
      const retryDelay = CREATION_NUDGE_SUPPRESSION_RETRY_MS[attempt];
      if (retryDelay !== undefined) {
        globalThis.setTimeout(() => {
          suppressCreationNudgeExposure(exposureId, attempt + 1);
        }, retryDelay);
      }
    })
    .finally(() => {
      pendingCreationNudgeSuppressions.delete(exposureId);
    });
}

function localResearchNudge(
  category: string,
  tod: string,
  planned: number,
  firedAt: string,
  exposureId: string
) {
  const prior = RESEARCH_PRIORS[category] ?? RESEARCH_PRIOR_DEFAULT;
  const suggestedMin = roundTo5(planned * prior.biasFactor);
  return {
    cell: {
      bias_factor: prior.biasFactor,
      bias_factor_mean: prior.biasFactor,
      sessions: 0,
      confidence: "research",
      interpretation: "underestimates",
      category,
      time_of_day: tod,
      citation: prior.citation,
    } satisfies BiasFactorCell,
    factor: prior.biasFactor,
    personalFactor: null,
    blendFactor: prior.biasFactor,
    personalWeight: 0,
    priorWeight: 1,
    priorFactor: prior.biasFactor,
    priorCitation: prior.citation,
    suggestedMin,
    executionSuggestedMin: suggestedMin,
    pauseOverheadMin: 0,
    pauseOverheadSampleSize: 0,
    occupancySuggestedMin: suggestedMin,
    occupancyStrategy: "execution_only_research_prior",
    firedAt,
    exposureId,
    backendReady: false,
  };
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
  const [calibrationNudge, setCalibrationNudge] =
    useState<CalibrationNudge | null>(null);
  const creationNudgeExposureRef = useRef<string | null>(null);
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
  const [nudgeDecisionData, setNudgeDecisionData] = useState<{
    decision: "accepted" | "dismissed";
    suggested_minutes: number;
    bias_factor: number;
    sample_size: number;
    // Phase 6 V3 — fire-time of the modal nudge. Sent as
    // nudge_viewed_at; backend computes dwell_seconds = decision_time
    // − fire_time for the ReflectionViewLog row.
    viewed_at: string;
  } | null>(null);
  const [editScheduleTouched, setEditScheduleTouched] = useState(false);

  // Loop 11 Phase K — deadline picker. `deadlineId` carries the user's
  // explicit choice (or the confirmed parser suggestion). `parserSuggestion`
  // is the read-only Pass 2 preview surfaced as a soft suggestion above the
  // submit button. They live in separate slices so dismissing the suggestion
  // doesn't clobber an already-confirmed picker choice.
  const [deadlineId, setDeadlineId] = useState<string | null>(null);
  const [parserSuggestion, setParserSuggestion] =
    useState<DeadlinePreviewResponse | null>(null);
  const [showDeadlinePicker, setShowDeadlinePicker] = useState(false);

  // Fetch bias_factor when category, start time, or duration changes
  // (debounced). Create mode remains eligible as soon as the form has a
  // real duration. Edit mode waits until the operator actually touches
  // the schedule/duration; opening an existing task should not nag, but
  // changing the plan should re-run the estimate.
  // Gated on a valid positive planned duration — a 0-min estimate with
  // a `|| 30` fallback (prior behavior) fired the "adjust to X min"
  // popup on an invalid form, visually drowning the end-before-start
  // error banner. Now the nudge only fires when the user has typed a
  // real duration AND the range is valid AND the user hasn't already
  // made a decision on a prior nudge this session.
  useEffect(() => {
    const eligible = open && !nudgeDecisionMade && (!isEdit || editScheduleTouched);
    if (!eligible) {
      setCalibrationNudge(null);
      setNudgeSource(null);
      return;
    }
    const planned = durHours * 60 + durMinutes;
    const rangeValid = diffMinutes(start, end) > 0;
    if (planned <= 0 || !rangeValid) {
      setCalibrationNudge(null);
      setNudgeSource(null);
      return;
    }
    const tod = timeOfDay(start);
    const firedAt = new Date().toISOString();
    const exposureId = exposureIdForCreationNudge(category, tod, planned);
    const provisional = localResearchNudge(category, tod, planned, firedAt, exposureId);
    if (provisional.factor >= 1.2) {
      setCalibrationNudge(provisional);
      setNudgeSource("research");
    } else {
      setCalibrationNudge(null);
      setNudgeSource(null);
    }
    const abortCtl = new AbortController();
    const applyLookupResponse = (res: BiasLookupResponse) => {
      const isResearch = res.source === "research";
      const threshold = isResearch ? 1.20 : 1.25;
      // Rule-13 canonical magnitude (MANIFESTO v1.10): prefer the
      // shrinkage-blended `bias_factor_final` when present. Keep the
      // raw cell.bias_factor separate so the UI does not relabel a
      // prior-blended estimate as pure "early data".
      const magnitude = res.bias_factor_final ?? res.cell?.bias_factor ?? null;
      const executionSuggestedMin =
        res.execution_suggested_minutes ?? (magnitude !== null ? roundTo5(planned * magnitude) : planned);
      const pauseOverheadMin = res.pause_overhead_minutes ?? 0;
      const pauseOverheadSampleSize = res.pause_overhead_sample_size ?? 0;
      const occupancySuggestedMin = res.occupancy_suggested_minutes ?? executionSuggestedMin;
      const occupancyFactor = res.occupancy_factor ?? (planned > 0 ? occupancySuggestedMin / planned : null);
      const executionTriggered = magnitude !== null && magnitude >= threshold;
      const occupancyTriggered =
        occupancyFactor !== null && occupancyFactor >= threshold && pauseOverheadSampleSize >= 3;
      if (!res.cell || magnitude === null || (!executionTriggered && !occupancyTriggered)) {
        if (res.exposure_id && !res.suppressed_reason) {
          suppressCreationNudgeExposure(res.exposure_id);
        }
        if (!abortCtl.signal.aborted) {
          setCalibrationNudge(null);
          setNudgeSource(null);
        }
        return false;
      }

      const backendExposureId = res.exposure_id ?? exposureId;
      const contentSnapshot = {
        template: "task_creation_nudge_lookup",
        category: res.cell.category,
        time_of_day: res.cell.time_of_day,
        source: isResearch ? "research" : "personal",
        suggested_minutes: occupancySuggestedMin,
        execution_suggested_minutes: executionSuggestedMin,
        pause_overhead_minutes: pauseOverheadMin,
        pause_overhead_sample_size: pauseOverheadSampleSize,
        occupancy_suggested_minutes: occupancySuggestedMin,
        occupancy_strategy: res.occupancy_strategy ?? null,
        planned_minutes: planned,
      };
      if (abortCtl.signal.aborted) {
        suppressCreationNudgeExposure(backendExposureId);
        return true;
      }
      setCalibrationNudge({
        cell: res.cell,
        factor: magnitude,
        personalFactor: isResearch ? null : res.cell.bias_factor,
        blendFactor: res.bias_factor_final ?? null,
        personalWeight: res.personal_weight ?? null,
        priorWeight: res.prior_weight ?? null,
        priorFactor: res.archetype_prior_for_cell ?? null,
        priorCitation: res.archetype_prior_citation ?? res.cell.citation ?? null,
        suggestedMin: occupancySuggestedMin,
        executionSuggestedMin,
        pauseOverheadMin,
        pauseOverheadSampleSize,
        occupancySuggestedMin,
        occupancyStrategy: res.occupancy_strategy ?? null,
        firedAt,
        exposureId: backendExposureId,
        backendReady: true,
      });
      setNudgeSource(isResearch ? "research" : "personal");
      return true;
    };
    const timer = setTimeout(() => {
      lookupBiasFactor(category, tod, planned, { fast: true, exposureId })
        .then((res) => {
          const shouldHydrate = applyLookupResponse(res);
          if (!shouldHydrate) return;
          void lookupBiasFactor(category, tod, planned, { exposureId: res.exposure_id ?? exposureId })
            .then(applyLookupResponse)
            .catch(() => {
              // Keep the instant research-backed card if the personal
              // hydration path misses; the fast path already registered
              // the visible surface for exposure accounting.
            });
        })
        .catch(() => { if (!abortCtl.signal.aborted) { setCalibrationNudge(null); setNudgeSource(null); } });
    }, BIAS_LOOKUP_DEBOUNCE_MS);
    return () => { clearTimeout(timer); abortCtl.abort(); };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open, category, start, end, durHours, durMinutes, isEdit, editScheduleTouched, nudgeDecisionMade]);

  const creationNudgeRenderSnapshot = () => {
    if (!calibrationNudge) {
      return null;
    }
    return {
      template: "task_creation_nudge_lookup",
      category: calibrationNudge.cell.category,
      time_of_day: calibrationNudge.cell.time_of_day,
      source: nudgeSource,
      suggested_minutes: calibrationNudge.suggestedMin,
      execution_suggested_minutes: calibrationNudge.executionSuggestedMin,
      pause_overhead_minutes: calibrationNudge.pauseOverheadMin,
      pause_overhead_sample_size: calibrationNudge.pauseOverheadSampleSize,
      occupancy_suggested_minutes: calibrationNudge.occupancySuggestedMin,
      occupancy_strategy: calibrationNudge.occupancyStrategy,
      planned_minutes: durHours * 60 + durMinutes,
    };
  };

  const ackVisibleCreationNudge = () => {
    const exposureId = calibrationNudge?.exposureId;
    const contentSnapshot = creationNudgeRenderSnapshot();
    if (!exposureId || !contentSnapshot) {
      return;
    }
    ackCreationNudgeRender(exposureId, contentSnapshot);
  };

  useEffect(() => {
    if (!calibrationNudge?.exposureId || !calibrationNudge.backendReady) {
      return;
    }
    ackVisibleCreationNudge();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [calibrationNudge, durHours, durMinutes, nudgeSource]);

  useEffect(() => {
    const currentExposureId =
      calibrationNudge?.backendReady && calibrationNudge.exposureId
        ? calibrationNudge.exposureId
        : null;
    const previousExposureId = creationNudgeExposureRef.current;
    if (
      previousExposureId &&
      previousExposureId !== currentExposureId &&
      !pendingCreationNudgeRenderAcks.has(previousExposureId) &&
      !ackedCreationNudgeRenders.has(previousExposureId)
    ) {
      suppressCreationNudgeExposure(previousExposureId);
    }
    creationNudgeExposureRef.current = currentExposureId;
  }, [calibrationNudge?.backendReady, calibrationNudge?.exposureId]);

  useEffect(() => {
    return () => {
      const previousExposureId = creationNudgeExposureRef.current;
      if (
        previousExposureId &&
        !pendingCreationNudgeRenderAcks.has(previousExposureId) &&
        !ackedCreationNudgeRenders.has(previousExposureId)
      ) {
        suppressCreationNudgeExposure(previousExposureId);
      }
      creationNudgeExposureRef.current = null;
    };
  }, []);

  // Loop 11 Phase K — Pass 2 deadline-binding preview.
  //
  // Debounced 500ms (matches the bias_factor lookup cadence) and
  // race-safe: we abort any in-flight fetch on every input change, so
  // a slower late-firing response can't overwrite a fresher one. The
  // effect skips when the user has already explicitly picked a deadline
  // (deadlineId set) — the manual choice wins and we don't second-guess
  // it with a parser suggestion.
  useEffect(() => {
    if (!open || isEdit) {
      setParserSuggestion(null);
      return;
    }
    const trimmed = title.trim();
    if (trimmed.length < 3 || deadlineId) {
      setParserSuggestion(null);
      return;
    }
    const abortCtl = new AbortController();
    const timer = setTimeout(() => {
      previewDeadlineBinding(trimmed, description.trim() || undefined)
        .then((res) => {
          if (abortCtl.signal.aborted) return;
          if (res.deadline_id) setParserSuggestion(res);
          else setParserSuggestion(null);
        })
        .catch(() => {
          if (!abortCtl.signal.aborted) setParserSuggestion(null);
        });
    }, 500);
    return () => { clearTimeout(timer); abortCtl.abort(); };
  }, [open, isEdit, title, description, deadlineId]);

  useEffect(() => {
    void ackExposureRender(parserSuggestion?.exposure_id);
  }, [parserSuggestion?.exposure_id]);

  const totalMinutes = durHours * 60 + durMinutes;
  const endBeforeStart = diffMinutes(start, end) <= 0;
  const canSubmit = !submitting && title.trim().length > 0 && !endBeforeStart && totalMinutes > 0;

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
  const suggestAmPmSwap = (() => {
    if (!endBeforeStart) return null;
    const sDate = new Date(start);
    const eDate = new Date(end);
    if (Number.isNaN(sDate.getTime()) || Number.isNaN(eDate.getTime())) return null;
    if (sDate.toDateString() !== eDate.toDateString()) return null;
    const negDiffMin = diffMinutes(start, end);
    if (negDiffMin >= 0 || negDiffMin <= -12 * 60) return null;
    const shifted = addMinutes(end, 12 * 60);
    const shiftedDate = new Date(shifted);
    if (Number.isNaN(shiftedDate.getTime())) return null;
    // The +12h shift must stay on the start's calendar day. Otherwise
    // the suggestion is nonsense (time-only display formatting hides the
    // date change from the user) and should not render.
    if (shiftedDate.toDateString() !== sDate.toDateString()) return null;
    // Defensive: shifted must now be strictly after start. If the
    // hour math still produces end <= start, something's off — don't
    // suggest.
    if (diffMinutes(start, shifted) <= 0) return null;
    return shifted;
  })();
  function applyAmPmSwap() {
    if (!suggestAmPmSwap) return;
    handleEndChange(suggestAmPmSwap);
  }

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
  const suggestPushStartToFuture = (() => {
    if (!start) return null;
    const sDate = new Date(start);
    if (Number.isNaN(sDate.getTime())) return null;
    if (sDate.getTime() >= now.getTime()) return null;
    const next = new Date(now);
    const mins = next.getMinutes();
    const next5 = Math.ceil(mins / 5) * 5;
    if (next5 >= 60) next.setHours(next.getHours() + 1, 0, 0, 0);
    else next.setMinutes(next5, 0, 0);
    next.setSeconds(0, 0);
    // Ensure strictly after `now` — if current minute is a 5-mark
    // already, Math.ceil returns the same minute. Advance by 5.
    if (next.getTime() <= now.getTime()) {
      next.setMinutes(next.getMinutes() + 5);
    }
    return formatLocal(next);
  })();
  function applyPushStartToFuture() {
    if (!suggestPushStartToFuture) return;
    handleStartChange(suggestPushStartToFuture);
  }

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
      setNudgeDecisionMade(false);
      setNudgeDecisionData(null);
      setEditScheduleTouched(false);
      setDeadlineId(null);
      setParserSuggestion(null);
      setShowDeadlinePicker(false);
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
    // Edit-modal parity (2026-04-28): load description + deadline_id
    // from the task. Without this, opening edit + saving would silently
    // wipe both fields — DATA LOSS bug.
    setDescription(editingTask.description ?? "");
    setShowDescription(!!editingTask.description);
    setDeadlineId(editingTask.deadline_id ?? null);
    setError(null);
    setPausedConflict(null);
    setSoftConflict(null);
    setCalibrationNudge(null);
    setNudgeSource(null);
    setNudgeDecisionMade(false);
    setNudgeDecisionData(null);
    setEditScheduleTouched(false);
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
    setNudgeDecisionMade(false);
    setNudgeDecisionData(null);
    setEditScheduleTouched(false);
    setDeadlineId(null);
    setParserSuggestion(null);
    setShowDeadlinePicker(false);
    setLastEditId(null);
  }

  // --- Bidirectional binding helpers ---

  function markEditScheduleChanged() {
    if (!isEdit) return;
    setEditScheduleTouched(true);
    setNudgeDecisionMade(false);
    setNudgeDecisionData(null);
  }

  function handleStartChange(newStart: string) {
    markEditScheduleChanged();
    // Preserve current duration, shift end
    const dur = durHours * 60 + durMinutes;
    setStart(newStart);
    setEnd(addMinutes(newStart, dur));
  }

  function handleEndChange(newEnd: string) {
    markEditScheduleChanged();
    setEnd(newEnd);
    const mins = diffMinutes(start, newEnd);
    // Always update duration so the UI stays consistent with start/end.
    // For negative ranges we zero the duration state, but the
    // `endBeforeStart` flag drives the error banner + nudge-suppression
    // so the user gets feedback that the range is invalid (previously
    // the duration silently stayed at the last good value, producing
    // "0h 0m / End before start" while the two fields visibly
    // disagreed — see dogfood 2026-04-21 AM/PM bug report).
    if (mins > 0) {
      setDurHours(Math.floor(mins / 60));
      setDurMinutes(mins % 60);
    } else {
      setDurHours(0);
      setDurMinutes(0);
    }
  }

  function handleDurHoursChange(h: number) {
    markEditScheduleChanged();
    const clamped = Math.max(0, h);
    setDurHours(clamped);
    setEnd(addMinutes(start, clamped * 60 + durMinutes));
  }

  function handleDurMinutesChange(m: number) {
    markEditScheduleChanged();
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

      const res = await createTask({
        title: title.trim(),
        start: startDate.toISOString(),
        end: endDate.toISOString(),
        category,
        description: description.trim() || undefined,
        deadline_id: deadlineId ?? undefined,
        ...(nudgeDecisionData
          ? {
              nudge_decision: nudgeDecisionData.decision,
              nudge_suggested_duration_minutes: nudgeDecisionData.suggested_minutes,
              nudge_bias_factor: nudgeDecisionData.bias_factor,
              nudge_sample_size: nudgeDecisionData.sample_size,
              nudge_viewed_at: nudgeDecisionData.viewed_at,
            }
          : {}),
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
        deadline_id: deadlineId ?? undefined,
        ...(nudgeDecisionData
          ? {
              nudge_decision: nudgeDecisionData.decision,
              nudge_suggested_duration_minutes: nudgeDecisionData.suggested_minutes,
              nudge_bias_factor: nudgeDecisionData.bias_factor,
              nudge_sample_size: nudgeDecisionData.sample_size,
              nudge_viewed_at: nudgeDecisionData.viewed_at,
            }
          : {}),
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
        deadline_id: deadlineId ?? undefined,
        ...(nudgeDecisionData
          ? {
              nudge_decision: nudgeDecisionData.decision,
              nudge_suggested_duration_minutes: nudgeDecisionData.suggested_minutes,
              nudge_bias_factor: nudgeDecisionData.bias_factor,
              nudge_sample_size: nudgeDecisionData.sample_size,
              nudge_viewed_at: nudgeDecisionData.viewed_at,
            }
          : {}),
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
                onChange={(val) => {
                  if (val === "__CREATE_NEW__") {
                    setCategoryMode("custom");
                    setCategory("");
                  } else {
                    setCategory(val);
                  }
                }}
              />
            ) : (
              <div className="flex items-center gap-2">
                <Input
                  data-testid="new-task-category-custom"
                  id="category"
                  value={category}
                  onChange={(e) => setCategory(e.target.value)}
                  placeholder="e.g. research, admin, side_project"
                  autoComplete="off"
                  autoFocus
                />
                <button
                  data-testid="new-task-category-back"
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
                onClick={() => setShowDescription(true)}
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
                  onChange={(e) => setDescription(e.target.value)}
                  placeholder="- Step one&#10;- Step two&#10;- Step three"
                  rows={3}
                  className="rounded-sm border border-hairline-signal/30 bg-transparent px-3 py-2 text-sm text-parchment placeholder:text-dust-deep resize-none"
                />
                {(() => {
                  const items = description.split("\n").filter((l) => /^\s*[-*•]\s|^\s*\d+[.)]\s/.test(l));
                  const planned = durHours * 60 + durMinutes;
                  if (items.length >= 2 && planned > 0) {
                    const perItem = Math.round((planned / items.length) * 10) / 10;
                    return (
                      <span className="text-[11px] text-dust-deep">
                        {items.length} items, ~{perItem} min each based on your estimate
                      </span>
                    );
                  }
                  return null;
                })()}
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
              onConfirmSuggestion={() => {
                if (parserSuggestion?.deadline_id) {
                  setDeadlineId(parserSuggestion.deadline_id);
                  setParserSuggestion(null);
                }
              }}
              onDismissSuggestion={() => setParserSuggestion(null)}
              onClearBinding={() => setDeadlineId(null)}
              onTogglePicker={() => setShowDeadlinePicker((s) => !s)}
              onPick={(id) => {
                setDeadlineId(id);
                setShowDeadlinePicker(false);
                setParserSuggestion(null);
              }}
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
                setNudgeDecisionData({
                  decision: "accepted",
                  suggested_minutes: calibrationNudge.suggestedMin,
                  bias_factor: calibrationNudge.factor,
                  sample_size: calibrationNudge.cell.sessions,
                  viewed_at: calibrationNudge.firedAt,
                });
                setDurHours(Math.floor(newMin / 60));
                setDurMinutes(newMin % 60);
                setEnd(addMinutes(start, newMin));
                setCalibrationNudge(null);
                setNudgeDecisionMade(true);
              }}
              onKeepEstimate={() => {
                ackVisibleCreationNudge();
                setNudgeDecisionData({
                  decision: "dismissed",
                  suggested_minutes: calibrationNudge.suggestedMin,
                  bias_factor: calibrationNudge.factor,
                  sample_size: calibrationNudge.cell.sessions,
                  viewed_at: calibrationNudge.firedAt,
                });
                setCalibrationNudge(null);
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
