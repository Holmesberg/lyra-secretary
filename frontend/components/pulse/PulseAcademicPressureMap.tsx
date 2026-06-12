"use client";

import { useMemo, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import {
  AlertTriangle,
  CalendarClock,
  CheckCircle2,
  ClipboardCheck,
  ListPlus,
  ShieldQuestion,
  X,
} from "lucide-react";
import type {
  AcademicPressureItem,
  AcademicPressureMapResponse,
  AcademicRecoveryOption,
} from "@/lib/academic";
import {
  createTask,
  lookupBiasFactor,
  type BiasLookupResponse,
  type TaskRow,
} from "@/lib/tasks";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";

export interface PulseAcademicPressureMapProps {
  pressure: AcademicPressureMapResponse | null;
  loading?: boolean;
  horizonDays?: number;
  onHorizonChange?: (days: number) => void;
  taskEvidence?: TaskRow[];
}

interface PlanRow {
  id: string;
  obligationId: string;
  obligationTitle: string;
  deadlineId: string | null;
  title: string;
  startLocal: string;
  endLocal: string;
  durationMinutes: number;
  category: string;
  estimateSource: string;
  estimateBasis: "linked_deadline_history" | "cold_start_prior";
  status: "pending" | "created" | "failed";
  error: string | null;
  enabled: boolean;
  canForce: boolean;
  conflictTitles: string[];
}

interface EvidenceEstimate {
  minutes: number;
  source: string;
  category: string;
}

const SLOT_GRANULARITY_MINUTES = 15;
const MIN_RECOVERY_BLOCK_MINUTES = SLOT_GRANULARITY_MINUTES;
const DEFAULT_RECOVERY_CATEGORY = "planning";
// Mirrors backend/app/services/interruption_metrics.py clean pause-overhead gate.
const MAX_CLEAN_LEARNING_PAUSE_MINUTES = 240;

function fmtHours(lowMinutes: number, highMinutes: number): string {
  const low = Math.round(lowMinutes / 30) / 2;
  const high = Math.round(highMinutes / 30) / 2;
  if (low === high) return `${low}h`;
  return `${low}-${high}h`;
}

function fmtDue(days: number): string {
  if (days < 0) return "overdue";
  if (days < 1) return "due today";
  if (days < 2) return "due tomorrow";
  return `in ${Math.round(days)}d`;
}

function fmtTiming(item: AcademicPressureItem): string {
  const isTask = item.source_class === "lyra_task";
  const days = item.days_until_due;
  if (!isTask) return fmtDue(days);
  if (days < 0) return "started";
  if (days < 1) return "scheduled today";
  if (days < 2) return "scheduled tomorrow";
  return `scheduled in ${Math.round(days)}d`;
}

function pressureClass(item: AcademicPressureItem): string {
  if (item.pressure_level === "overdue") return "border-ember/50 bg-ember/10";
  if (item.pressure_level === "high") return "border-ember/30 bg-ember/5";
  return "border-hairline bg-void-2/40";
}

function fmtTrust(trust: AcademicPressureItem["trust_state"]): string {
  if (trust === "verified_reachable") return "source reachable";
  if (trust === "requires_user_confirmation") return "needs confirmation";
  if (trust === "verified_exact") return "source verified";
  return trust.replaceAll("_", " ");
}

function genericPressureCopy(copy: string): string {
  return copy
    .replaceAll("visible academic load", "visible load")
    .replaceAll("academic load", "visible load")
    .replaceAll("academic pressure", "visible pressure")
    .replaceAll("academic ranges", "visible ranges")
    .replaceAll("academic obligations", "obligations")
    .replaceAll("academic tasks", "linked tasks")
    .replaceAll("Academic obligations", "Obligations")
    .replaceAll("Academic tasks", "Linked tasks")
    .replaceAll("study blocks", "focus blocks");
}

function toLocalInput(date: Date): string {
  const local = new Date(date.getTime() - date.getTimezoneOffset() * 60_000);
  return local.toISOString().slice(0, 16);
}

function roundUpToNextHalfHour(date: Date): Date {
  const d = new Date(date);
  d.setSeconds(0, 0);
  const minutes = d.getMinutes();
  const add = minutes === 0 || minutes === 30 ? 30 : minutes < 30 ? 30 - minutes : 60 - minutes;
  d.setMinutes(minutes + add);
  return d;
}

function roundToSlot(minutes: number): number {
  return Math.round(minutes / SLOT_GRANULARITY_MINUTES) * SLOT_GRANULARITY_MINUTES;
}

function floorToMinimumBlock(minutes: number): number {
  return Math.max(MIN_RECOVERY_BLOCK_MINUTES, minutes);
}

function mean(values: number[]): number | null {
  if (!values.length) return null;
  return values.reduce((sum, value) => sum + value, 0) / values.length;
}

function fmtMinutes(minutes: number | null): string {
  if (minutes === null || !Number.isFinite(minutes)) return "n/a";
  const rounded = Math.round(minutes);
  if (rounded < 60) return `${rounded}m`;
  const hours = Math.floor(rounded / 60);
  const mins = rounded % 60;
  return mins ? `${hours}h ${mins}m` : `${hours}h`;
}

function parseLocalInput(value: string): Date | null {
  if (!value) return null;
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? null : date;
}

function durationFromLocal(startLocal: string, endLocal: string): number {
  const start = parseLocalInput(startLocal);
  const end = parseLocalInput(endLocal);
  if (!start || !end) return 0;
  return Math.max(0, Math.round((end.getTime() - start.getTime()) / 60_000));
}

function endLocalFromDuration(startLocal: string, durationMinutes: number): string {
  const start = parseLocalInput(startLocal) ?? new Date();
  return toLocalInput(new Date(start.getTime() + floorToMinimumBlock(durationMinutes) * 60_000));
}

function executedMinutes(task: TaskRow): number | null {
  const value = task.effective_executed_duration_minutes ?? task.executed_duration_minutes;
  return value !== null && value > 0 ? value : null;
}

function plannedMinutes(task: TaskRow): number | null {
  return task.planned_duration_minutes !== null && task.planned_duration_minutes > 0
    ? task.planned_duration_minutes
    : null;
}

function normalizeTitle(value: string | null | undefined): string {
  return (value ?? "").trim().toLowerCase().replace(/\s+/g, " ");
}

function completionScaledMinutes(task: TaskRow): number | null {
  const executed = executedMinutes(task);
  const completion = task.task_completion_percentage;
  if (executed === null || completion === null || completion <= 0 || completion >= 100) {
    return executed;
  }
  return executed / (completion / 100);
}

function cleanPauseOverheadMinutes(task: TaskRow): number | null {
  const pause = Math.max(0, task.total_paused_minutes ?? 0);
  if (pause > MAX_CLEAN_LEARNING_PAUSE_MINUTES) return null;
  return pause;
}

function dominantCategory(tasks: TaskRow[]): string {
  const counts = new Map<string, number>();
  for (const task of tasks) {
    if (!task.category) continue;
    counts.set(task.category, (counts.get(task.category) ?? 0) + 1);
  }
  let best = DEFAULT_RECOVERY_CATEGORY;
  let bestCount = 0;
  for (const [category, count] of counts) {
    if (count > bestCount) {
      best = category;
      bestCount = count;
    }
  }
  return best;
}

function timeOfDayFromLocalInput(value: string): string {
  const date = parseLocalInput(value);
  const hour = date?.getHours() ?? new Date().getHours();
  if (hour >= 5 && hour < 12) return "morning";
  if (hour >= 12 && hour < 17) return "afternoon";
  if (hour >= 17 && hour < 21) return "evening";
  return "night";
}

function calibratedMinutes(row: PlanRow, calibration: BiasLookupResponse): number | null {
  const suggested =
    calibration.occupancy_suggested_minutes ??
    calibration.execution_suggested_minutes ??
    (calibration.bias_factor_final
      ? row.durationMinutes * calibration.bias_factor_final
      : null);
  if (suggested === null || suggested <= 0) return null;
  return floorToMinimumBlock(roundToSlot(suggested));
}

function calibrationSource(row: PlanRow, calibration: BiasLookupResponse): string {
  const source = calibration.source === "personal"
    ? `personal ${calibration.signal_level ?? "calibration"}`
    : "research prior";
  const archetype = calibration.archetype_id
    ? `archetype ${calibration.archetype_id}`
    : "archetype fallback";
  const sample = calibration.sessions
    ? `${calibration.sessions} eligible session${calibration.sessions === 1 ? "" : "s"}`
    : "cold start";
  const occupancy = calibration.pause_overhead_sample_size && calibration.pause_overhead_sample_size > 0
    ? `; pause overhead ${fmtMinutes(calibration.pause_overhead_minutes ?? null)} from ${calibration.pause_overhead_sample_size} sample${calibration.pause_overhead_sample_size === 1 ? "" : "s"}`
    : "";
  return `${source} + ${archetype}: ${sample}; base ${fmtMinutes(row.durationMinutes)} -> ${fmtMinutes(calibratedMinutes(row, calibration))}${occupancy}`;
}

function linkedDeadlineTasks(item: AcademicPressureItem, tasks: TaskRow[]): TaskRow[] {
  const itemTitle = normalizeTitle(item.title);
  return tasks.filter((task) =>
    (task.deadline_id === item.obligation_id ||
      normalizeTitle(task.deadline_title) === itemTitle) &&
    task.state !== "DELETED" &&
    task.voided_at === null
  );
}

function estimateFromDeadlineEvidence(
  item: AcademicPressureItem,
  tasks: TaskRow[]
): EvidenceEstimate | null {
  const linked = linkedDeadlineTasks(item, tasks);
  if (!linked.length) return null;

  const plannedValues = linked
    .map(plannedMinutes)
    .filter((value): value is number => value !== null);
  const executedValues = linked
    .map(executedMinutes)
    .filter((value): value is number => value !== null);
  const completionScaledValues = linked
    .map(completionScaledMinutes)
    .filter((value): value is number => value !== null);
  const occupancyValues = linked
    .map((task) => {
      const executed = completionScaledMinutes(task);
      if (executed === null) return null;
      const cleanPause = cleanPauseOverheadMinutes(task);
      if (cleanPause === null) return null;
      return executed + cleanPause;
    })
    .filter((value): value is number => value !== null);
  const pauseValues = linked
    .map(cleanPauseOverheadMinutes)
    .filter((value): value is number => value !== null && value > 0);
  const ignoredPauseAnomalies = linked.filter(
    (task) => cleanPauseOverheadMinutes(task) === null
  ).length;

  const plannedAvg = mean(plannedValues);
  const executedAvg = mean(executedValues);
  const completionScaledAvg = mean(completionScaledValues);
  const occupancyAvg = mean(occupancyValues);
  const pauseAvg = mean(pauseValues) ?? 0;
  const baseline = Math.max(plannedAvg ?? 0, completionScaledAvg ?? executedAvg ?? 0);
  const occupancyMeaningful =
    occupancyAvg !== null &&
    (pauseAvg >= SLOT_GRANULARITY_MINUTES ||
      (baseline > 0 && occupancyAvg >= baseline + SLOT_GRANULARITY_MINUTES));

  const candidates = [
    plannedAvg,
    completionScaledAvg,
    occupancyMeaningful ? occupancyAvg : null,
  ].filter((value): value is number => value !== null && value > 0);

  if (!candidates.length) return null;

  const minutes = floorToMinimumBlock(roundToSlot(Math.max(...candidates)));
  const parts = [];
  if (executedAvg !== null) {
    parts.push(`avg active ${fmtMinutes(executedAvg)} across ${executedValues.length} session${executedValues.length === 1 ? "" : "s"}`);
  }
  if (
    completionScaledAvg !== null &&
    executedAvg !== null &&
    completionScaledAvg >= executedAvg + SLOT_GRANULARITY_MINUTES
  ) {
    parts.push(`completion-adjusted active ${fmtMinutes(completionScaledAvg)}`);
  }
  if (occupancyAvg !== null) {
    parts.push(`avg occupancy ${fmtMinutes(occupancyAvg)}${occupancyMeaningful ? " with pause/recovery overhead" : ""}`);
  }
  if (plannedAvg !== null) {
    parts.push(`avg planned ${fmtMinutes(plannedAvg)} across ${plannedValues.length} task${plannedValues.length === 1 ? "" : "s"}`);
  }
  if (ignoredPauseAnomalies > 0) {
    parts.push(`${ignoredPauseAnomalies} overlong pause sample${ignoredPauseAnomalies === 1 ? "" : "s"} ignored as likely forgotten-timer evidence`);
  }

  return {
    minutes,
    source: `linked-deadline history: ${parts.join("; ")}`,
    category: dominantCategory(linked),
  };
}

function suggestedBlockMinutes(item: AcademicPressureItem): number {
  const midpoint = (item.estimate.low_minutes + item.estimate.high_minutes) / 2;
  return floorToMinimumBlock(roundToSlot(midpoint || item.estimate.high_minutes));
}

function planItemsForOption(
  pressure: AcademicPressureMapResponse,
  option: AcademicRecoveryOption | null
): AcademicPressureItem[] {
  if (
    !option ||
    (option.action !== "create_plan" && option.action !== "split_into_blocks")
  ) {
    return [];
  }
  const ids = new Set(option?.obligation_ids ?? []);
  const eligible = pressure.items.filter((item) => item.source_class !== "lyra_task");
  const selected = ids.size
    ? eligible.filter((item) => ids.has(item.obligation_id))
    : [];
  return selected.slice(0, 4);
}

function buildRows(
  pressure: AcademicPressureMapResponse,
  option: AcademicRecoveryOption | null,
  taskEvidence: TaskRow[]
): PlanRow[] {
  const base = roundUpToNextHalfHour(new Date(Date.now() + 30 * 60_000));
  const fallbackCategory = dominantCategory(taskEvidence);
  return planItemsForOption(pressure, option).map((item, index) => {
    const evidenceEstimate = estimateFromDeadlineEvidence(item, taskEvidence);
    const duration = evidenceEstimate?.minutes ?? suggestedBlockMinutes(item);
    const start = new Date(base.getTime() + index * (duration + 15) * 60_000);
    const startLocal = toLocalInput(start);
    return {
      id: `${item.obligation_id}:${index}`,
      obligationId: item.obligation_id,
      obligationTitle: item.title,
      deadlineId: item.source_class === "lyra_task" ? null : item.obligation_id,
      title: `Recovery block: ${item.title}`,
      startLocal,
      endLocal: endLocalFromDuration(startLocal, duration),
      durationMinutes: duration,
      category: evidenceEstimate?.category ?? fallbackCategory,
      estimateSource: evidenceEstimate?.source ?? `${item.estimate.confidence} confidence ${item.complexity_source}; ${item.estimate.assumptions[0] ?? "pressure-map prior"}`,
      estimateBasis: evidenceEstimate ? "linked_deadline_history" : "cold_start_prior",
      status: "pending",
      error: null,
      enabled: true,
      canForce: false,
      conflictTitles: [],
    };
  });
}

function PlanPreviewDialog({
  open,
  rows,
  committing,
  option,
  forceCandidateId,
  onRowsChange,
  onClose,
  onCommit,
}: {
  open: boolean;
  rows: PlanRow[];
  committing: boolean;
  option: AcademicRecoveryOption | null;
  forceCandidateId: string | null;
  onRowsChange: (rows: PlanRow[]) => void;
  onClose: () => void;
  onCommit: (forceRowId?: string) => void;
}) {
  const enabledCount = rows.filter((row) => row.enabled).length;
  const updateRow = (id: string, patch: Partial<PlanRow>) => {
    onRowsChange(rows.map((row) => row.id === id ? { ...row, ...patch } : row));
  };
  const updateStart = (row: PlanRow, startLocal: string) => {
    updateRow(row.id, {
      startLocal,
      endLocal: endLocalFromDuration(startLocal, row.durationMinutes),
    });
  };
  const updateEnd = (row: PlanRow, endLocal: string) => {
    updateRow(row.id, {
      endLocal,
      durationMinutes: durationFromLocal(row.startLocal, endLocal),
    });
  };

  return (
    <Dialog open={open} onOpenChange={(value) => !value && onClose()}>
      <DialogContent className="max-h-[88vh] max-w-3xl overflow-y-auto">
        <DialogHeader>
          <DialogTitle>Preview recovery plan</DialogTitle>
          <DialogDescription>
            {option?.label ?? "Create editable focus blocks"}. Nothing is created until you lock this in.
          </DialogDescription>
        </DialogHeader>

        {rows.length === 0 ? (
          <div className="rounded-sm border border-hairline bg-void-2/40 px-3 py-4 text-sm text-dust">
            This option is diagnostic only right now. The selected pressure points are already planned tasks or need coverage confirmation before Lyra creates blocks.
          </div>
        ) : (
          <div className="flex flex-col gap-3">
            {rows.map((row) => (
              <div
                key={row.id}
                className="rounded-sm border border-hairline bg-void-2/35 p-3"
              >
                <div className="mb-3 flex items-start justify-between gap-3">
                  <div className="min-w-0">
                    <p className="font-mono text-[9px] uppercase tracking-widest text-signal">
                      Linked obligation
                    </p>
                    <p className="truncate text-sm text-parchment">
                      {row.obligationTitle}
                    </p>
                  </div>
                  <button
                    type="button"
                    onClick={() => updateRow(row.id, { enabled: !row.enabled })}
                    className="rounded-sm border border-hairline px-2 py-1 font-mono text-[10px] uppercase tracking-widest text-dust hover:border-signal/40 hover:text-signal"
                  >
                    {row.enabled ? "Include" : "Discarded"}
                  </button>
                </div>

                <div className="grid gap-3 md:grid-cols-[1.4fr_0.85fr_0.85fr_0.45fr]">
                  <label className="flex flex-col gap-1">
                    <span className="font-mono text-[9px] uppercase tracking-widest text-dust-deep">
                      Title
                    </span>
                    <Input
                      value={row.title}
                      disabled={!row.enabled || committing}
                      onChange={(event) => updateRow(row.id, { title: event.target.value })}
                    />
                  </label>
                  <label className="flex flex-col gap-1">
                    <span className="font-mono text-[9px] uppercase tracking-widest text-dust-deep">
                      Start
                    </span>
                    <Input
                      type="datetime-local"
                      value={row.startLocal}
                      disabled={!row.enabled || committing}
                      onChange={(event) => updateStart(row, event.target.value)}
                    />
                  </label>
                  <label className="flex flex-col gap-1">
                    <span className="font-mono text-[9px] uppercase tracking-widest text-dust-deep">
                      End
                    </span>
                    <Input
                      type="datetime-local"
                      value={row.endLocal}
                      disabled={!row.enabled || committing}
                      onChange={(event) => updateEnd(row, event.target.value)}
                    />
                  </label>
                  <div className="flex flex-col gap-1">
                    <span className="font-mono text-[9px] uppercase tracking-widest text-dust-deep">
                      Duration
                    </span>
                    <div className={`flex min-h-10 items-center rounded-sm border px-3 font-mono text-[12px] ${
                      row.durationMinutes >= 15
                        ? "border-hairline bg-void/40 text-parchment"
                        : "border-ember/40 bg-ember/5 text-ember"
                    }`}>
                      {row.durationMinutes >= 15 ? fmtMinutes(row.durationMinutes) : "invalid"}
                    </div>
                  </div>
                </div>

                <div className="mt-3 rounded-sm border border-hairline/70 bg-void/40 px-2 py-2 text-[11px] leading-relaxed text-dust">
                  <span className="font-mono uppercase tracking-widest text-dust-deep">
                    Estimate source:
                  </span>{" "}
                  {row.estimateSource}. This is planning footprint, not execution truth.
                </div>

                {(row.status !== "pending" || forceCandidateId === row.id) && (
                  <div className="mt-2 flex flex-wrap items-center gap-2">
                    <p className={`text-[11px] ${row.status === "created" ? "text-signal" : "text-ember"}`}>
                      {row.status === "created"
                        ? "Created."
                        : row.error ?? "Conflict detected. Create anyway if this window is intentional."}
                    </p>
                    {(row.canForce || forceCandidateId === row.id) && (
                      <Button
                        type="button"
                        variant="ghost"
                        size="sm"
                        onClick={() => onCommit(row.id)}
                        disabled={committing}
                      >
                        Create anyway
                      </Button>
                    )}
                  </div>
                )}
              </div>
            ))}
          </div>
        )}

        <DialogFooter>
          <Button variant="ghost" onClick={onClose} disabled={committing}>
            Dismiss
          </Button>
          <Button
            onClick={() => onCommit()}
            disabled={committing || enabledCount === 0}
          >
            {committing ? "Creating..." : `Lock in ${enabledCount} block${enabledCount === 1 ? "" : "s"}`}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

export function PulseAcademicPressureMap({
  pressure,
  loading = false,
  horizonDays = 14,
  onHorizonChange,
  taskEvidence = [],
}: PulseAcademicPressureMapProps) {
  const qc = useQueryClient();
  const [previewOpen, setPreviewOpen] = useState(false);
  const [previewOption, setPreviewOption] = useState<AcademicRecoveryOption | null>(null);
  const [rows, setRows] = useState<PlanRow[]>([]);
  const [commitError, setCommitError] = useState<string | null>(null);
  const [forceCandidateId, setForceCandidateId] = useState<string | null>(null);
  const [committing, setCommitting] = useState(false);
  const items = pressure?.items.slice(0, 4) ?? [];
  const hasItems = items.length > 0;
  const planOption = useMemo(() => {
    if (!pressure) return null;
    return (
      pressure.recovery_options.find((option) => option.action === "create_plan") ??
      pressure.recovery_options.find((option) => option.action === "split_into_blocks") ??
      null
    );
  }, [pressure]);
  const canPreviewPlan = useMemo(() => {
    if (!pressure || !planOption) return false;
    return planItemsForOption(pressure, planOption).length > 0;
  }, [pressure, planOption]);
  const primaryRecoveryOption = pressure?.recovery_options[0] ?? null;
  const primaryIsPlanOption =
    primaryRecoveryOption !== null &&
    planOption !== null &&
    primaryRecoveryOption.action === planOption.action;

  async function enrichColdStartRows(baseRows: PlanRow[]) {
    const updatedRows = await Promise.all(
      baseRows.map(async (row) => {
        if (row.estimateBasis !== "cold_start_prior") return row;
        try {
          const calibration = await lookupBiasFactor(
            row.category,
            timeOfDayFromLocalInput(row.startLocal),
            row.durationMinutes
          );
          const minutes = calibratedMinutes(row, calibration);
          if (minutes === null) return row;
          return {
            ...row,
            durationMinutes: minutes,
            endLocal: endLocalFromDuration(row.startLocal, minutes),
            estimateSource: calibrationSource(row, calibration),
          };
        } catch {
          return row;
        }
      })
    );
    setRows((currentRows) =>
      currentRows.map((current) => {
        const updated = updatedRows.find((row) => row.id === current.id);
        if (!updated || current.status !== "pending") return current;
        return {
          ...current,
          durationMinutes: updated.durationMinutes,
          endLocal: endLocalFromDuration(current.startLocal, updated.durationMinutes),
          category: updated.category,
          estimateSource: updated.estimateSource,
        };
      })
    );
  }

  function openPlanPreview(option: AcademicRecoveryOption | null) {
    if (
      !pressure ||
      !option ||
      (option.action !== "create_plan" && option.action !== "split_into_blocks")
    ) {
      return;
    }
    setCommitError(null);
    setForceCandidateId(null);
    setPreviewOption(option);
    const baseRows = buildRows(pressure, option, taskEvidence);
    if (baseRows.length === 0) return;
    setRows(baseRows);
    setPreviewOpen(true);
    void enrichColdStartRows(baseRows);
  }

  async function commitPlan(forceRowId?: string) {
    const enabledRows = forceRowId
      ? rows.filter((row) => row.id === forceRowId)
      : rows.filter((row) => row.enabled);
    if (!enabledRows.length) return;
    setCommitting(true);
    setCommitError(null);
    if (forceRowId) {
      setForceCandidateId(null);
    }
    let created = 0;
    let firstError: string | null = null;
    const nextRows = [...rows];

    for (const row of enabledRows) {
      const index = nextRows.findIndex((candidate) => candidate.id === row.id);
      try {
        const start = new Date(row.startLocal);
        const end = new Date(row.endLocal);
        const duration = durationFromLocal(row.startLocal, row.endLocal);
        if (
          Number.isNaN(start.getTime()) ||
          Number.isNaN(end.getTime()) ||
          duration < 15
        ) {
          const message = "Set an end time at least 15 minutes after the start.";
          nextRows[index] = {
            ...nextRows[index],
            status: "failed",
            error: message,
            canForce: false,
            conflictTitles: [],
          };
          firstError = firstError ?? message;
          continue;
        }
        const response = await createTask({
          title: row.title.trim() || `Recovery block: ${row.obligationTitle}`,
          start: start.toISOString(),
          end: end.toISOString(),
          category: row.category,
          deadline_id: row.deadlineId ?? undefined,
          description: [
            "Created from Pressure Map recovery preview.",
            `Linked obligation: ${row.obligationTitle}`,
            `Estimate source: ${row.estimateSource}`,
            "Planning footprint only; execution truth comes from the timer.",
          ].join("\n"),
          force: forceRowId === row.id,
        });
        if (!response.created) {
          const conflictTitles = response.conflicts.map((conflict) => conflict.title);
          const canForce = response.can_proceed === true && response.severity !== "hard";
          const message = conflictTitles.length
            ? `Conflict with ${conflictTitles.join(", ")}. ${
                canForce
                  ? "Create anyway if this window is intentional."
                  : "Edit the window and try again."
              }`
            : canForce
              ? "Soft conflict detected. Create anyway if this window is intentional."
              : "Conflict detected. Edit the window and try again.";
          nextRows[index] = {
            ...nextRows[index],
            status: "failed",
            error: message,
            canForce,
            conflictTitles,
          };
          if (canForce) {
            setForceCandidateId(row.id);
          }
          firstError = firstError ?? message;
          continue;
        }
        created += 1;
        setForceCandidateId(null);
        nextRows[index] = {
          ...nextRows[index],
          status: "created",
          error: null,
          enabled: false,
          canForce: false,
          conflictTitles: [],
        };
      } catch (error) {
        const message = error instanceof Error ? error.message : "Failed to create task";
        if (index >= 0) {
          nextRows[index] = {
            ...nextRows[index],
            status: "failed",
            error: message,
            canForce: false,
            conflictTitles: [],
          };
        }
        firstError = firstError ?? message;
      }
      setRows([...nextRows]);
    }

    await Promise.all([
      qc.invalidateQueries({ queryKey: ["tasks"] }),
      qc.invalidateQueries({ queryKey: ["pressure-map"] }),
      qc.invalidateQueries({ queryKey: ["deadlines"] }),
    ]);
    setCommitting(false);
    if (firstError) {
      setCommitError(firstError);
    } else if (created > 0) {
      setPreviewOpen(false);
    }
  }

  return (
    <div className="terminal-panel flex h-full flex-col p-5">
      <div className="mb-3 flex items-baseline justify-between gap-3">
        <div className="font-display text-[10px] font-medium uppercase tracking-macro text-dust">
          <span className="opacity-50">[ </span>
          Pressure map
          <span className="opacity-50"> ]</span>
        </div>
        <div className="flex items-center gap-1">
          {[1, 7, 14].map((days) => (
            <button
              key={days}
              type="button"
              onClick={() => onHorizonChange?.(days)}
              className={`rounded-sm border px-2 py-1 font-mono text-[9px] uppercase tracking-widest transition-colors ${
                horizonDays === days
                  ? "border-signal/50 bg-signal/10 text-signal"
                  : "border-hairline text-dust-deep hover:border-signal/30 hover:text-dust"
              }`}
            >
              {days === 1 ? "day" : days === 7 ? "week" : "14d"}
            </button>
          ))}
        </div>
      </div>

      {loading ? (
        <div className="flex flex-1 items-center text-sm text-dust">
          Reading visible load...
        </div>
      ) : !pressure ? (
        <div className="flex flex-1 items-center text-sm text-dust">
          Pressure map unavailable.
        </div>
      ) : (
        <>
          <div className="mb-3 flex items-start gap-3">
            <div className="mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-sm border border-signal/30 bg-signal/10 text-signal">
              <CalendarClock size={16} />
            </div>
            <div className="min-w-0">
              <p className="text-[15px] leading-snug text-parchment">
                {genericPressureCopy(pressure.pressure_summary || pressure.headline)}
              </p>
              <p className="mt-1 font-mono text-[10px] uppercase tracking-widest text-dust-deep">
                {fmtHours(
                  pressure.estimated_low_minutes,
                  pressure.estimated_high_minutes
                )}{" "}
                visible load / {pressure.source_summary.external_obligation_count} external /{" "}
                {pressure.source_summary.native_obligation_count} native /{" "}
                {pressure.source_summary.academic_task_count} linked tasks /{" "}
                {pressure.source_summary.study_task_count} focus blocks
              </p>
            </div>
          </div>

          {pressure.compression_points.length > 0 && (
            <div className="mb-3 rounded-sm border border-hairline bg-void-2/30 px-3 py-2">
              <div className="mb-1 flex items-center gap-2 font-mono text-[9px] uppercase tracking-widest text-dust-deep">
                <ShieldQuestion size={12} className="text-signal" />
                Why the week feels compressed
              </div>
              <p className="text-[12px] leading-snug text-dust">
                {genericPressureCopy(pressure.compression_points[0].detail)}
              </p>
            </div>
          )}

          {hasItems ? (
            <ul className="flex flex-col gap-2">
              {items.map((item) => (
                <li
                  key={item.obligation_id}
                  className={`rounded-sm border px-3 py-2 ${pressureClass(item)}`}
                >
                  <div className="flex items-start justify-between gap-3">
                    <div className="min-w-0">
                      <p className="truncate text-[13px] text-parchment">
                        {item.title}
                      </p>
                      <p className="mt-1 font-mono text-[9px] uppercase tracking-widest text-dust-deep">
                        {item.obligation_type} / {item.complexity_tier} /{" "}
                        {fmtTrust(item.trust_state)}
                      </p>
                    </div>
                    <div className="shrink-0 text-right">
                      <p className="font-display text-[13px] text-signal">
                        {fmtHours(
                          item.estimate.low_minutes,
                          item.estimate.high_minutes
                        )}
                      </p>
                      <p className="font-mono text-[9px] uppercase tracking-widest text-dust-deep">
                        {fmtTiming(item)}
                      </p>
                    </div>
                  </div>
                </li>
              ))}
            </ul>
          ) : (
            <div className="flex flex-1 items-center gap-3 rounded-sm border border-hairline bg-void-2/40 px-3 py-4 text-sm text-dust">
              <CheckCircle2 size={16} className="shrink-0 text-signal" />
              No active obligations in this window.
            </div>
          )}

          {pressure.recovery_options.length > 0 && (
            <div className="mt-3 rounded-sm border border-signal/20 bg-signal/5 px-3 py-2">
              <div className="mb-1 flex items-center justify-between gap-2">
                <div className="flex items-center gap-2 font-mono text-[9px] uppercase tracking-widest text-signal">
                  <ClipboardCheck size={12} />
                  Next recovery option
                </div>
                {primaryIsPlanOption && planOption && canPreviewPlan && (
                  <button
                    type="button"
                    onClick={() => openPlanPreview(planOption)}
                    className="inline-flex items-center gap-1 rounded-sm border border-signal/40 px-2 py-1 font-mono text-[9px] uppercase tracking-widest text-signal transition-colors hover:bg-signal/10"
                  >
                    <ListPlus size={11} />
                    Preview
                  </button>
                )}
              </div>
              <p className="text-[12px] font-medium text-parchment">
                {pressure.recovery_options[0].label}
              </p>
              <p className="mt-1 text-[11px] leading-snug text-dust">
                {genericPressureCopy(pressure.recovery_options[0].detail)}
              </p>
            </div>
          )}

          {!primaryIsPlanOption && planOption && canPreviewPlan && (
            <div className="mt-3 rounded-sm border border-signal/20 bg-signal/5 px-3 py-2">
              <div className="mb-1 flex items-center justify-between gap-2">
                <div className="flex items-center gap-2 font-mono text-[9px] uppercase tracking-widest text-signal">
                  <ListPlus size={12} />
                  Planning option
                </div>
                <button
                  type="button"
                  onClick={() => openPlanPreview(planOption)}
                  className="inline-flex items-center gap-1 rounded-sm border border-signal/40 px-2 py-1 font-mono text-[9px] uppercase tracking-widest text-signal transition-colors hover:bg-signal/10"
                >
                  <ListPlus size={11} />
                  Preview
                </button>
              </div>
              <p className="text-[12px] font-medium text-parchment">
                {planOption.label}
              </p>
              <p className="mt-1 text-[11px] leading-snug text-dust">
                {genericPressureCopy(planOption.detail)}
              </p>
            </div>
          )}

          {commitError && (
            <div className="mt-3 flex items-start gap-2 rounded-sm border border-ember/30 bg-ember/5 px-3 py-2 text-[11px] text-ember">
              <X size={13} className="mt-0.5 shrink-0" />
              {commitError}
            </div>
          )}

          <div className="mt-3 flex items-start gap-2 border-t border-hairline pt-3 text-[11px] leading-relaxed text-dust">
            <AlertTriangle size={14} className="mt-0.5 shrink-0 text-ember" />
            <p>
              Ranges are structure priors, not personal truth.{" "}
              {pressure.coverage_questions.length} coverage question
              {pressure.coverage_questions.length === 1 ? "" : "s"} need
              confirmation before this becomes a plan.
            </p>
          </div>

          <PlanPreviewDialog
            open={previewOpen}
            rows={rows}
            committing={committing}
            option={previewOption}
            forceCandidateId={forceCandidateId}
            onRowsChange={setRows}
            onClose={() => {
              if (!committing) {
                setPreviewOpen(false);
                setCommitError(null);
              }
            }}
            onCommit={commitPlan}
          />
        </>
      )}
    </div>
  );
}
