import type {
  AcademicPressureItem,
  AcademicPressureMapResponse,
  AcademicRecoveryOption,
} from "@/lib/academic";
import type { BiasLookupResponse, TaskRow } from "@/lib/tasks";

export interface PlanRow {
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

export function fmtMinutes(minutes: number | null): string {
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

export function durationFromLocal(startLocal: string, endLocal: string): number {
  const start = parseLocalInput(startLocal);
  const end = parseLocalInput(endLocal);
  if (!start || !end) return 0;
  return Math.max(0, Math.round((end.getTime() - start.getTime()) / 60_000));
}

export function endLocalFromDuration(startLocal: string, durationMinutes: number): string {
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

export function timeOfDayFromLocalInput(value: string): string {
  const date = parseLocalInput(value);
  const hour = date?.getHours() ?? new Date().getHours();
  if (hour >= 5 && hour < 12) return "morning";
  if (hour >= 12 && hour < 17) return "afternoon";
  if (hour >= 17 && hour < 21) return "evening";
  return "night";
}

export function calibratedMinutes(row: PlanRow, calibration: BiasLookupResponse): number | null {
  const suggested =
    calibration.occupancy_suggested_minutes ??
    calibration.execution_suggested_minutes ??
    (calibration.bias_factor_final
      ? row.durationMinutes * calibration.bias_factor_final
      : null);
  if (suggested === null || suggested <= 0) return null;
  return floorToMinimumBlock(roundToSlot(suggested));
}

export function calibrationSource(row: PlanRow, calibration: BiasLookupResponse): string {
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

export function planItemsForOption(
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

export function buildRows(
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
