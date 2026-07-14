import { format, parseISO, subDays } from "date-fns";

import type { TaskRow } from "@/lib/tasks";

export type DateRange = "7" | "30" | "all";
export type SortColumn =
  | "date"
  | "title"
  | "category"
  | "state"
  | "plan"
  | "exec"
  | "delta"
  | "rf"
  | "init";
export type SortDir = "asc" | "desc";

export interface Filters {
  dateRange: DateRange;
  categories: string[];
  states: string[];
  showVoided: boolean;
  sortColumn: SortColumn;
  sortDir: SortDir;
}

export interface DaySummary {
  date: string;
  planned: number;
  executed: number;
  delta: number;
  executedCount: number;
  skippedCount: number;
  avgDiscrepancy: number | null;
}

export type TableRenderRow =
  | { type: "summary"; dk: string; summary: DaySummary }
  | { type: "task"; task: TaskRow };

export const TASK_STATES = [
  "PLANNED",
  "EXECUTING",
  "PAUSED",
  "EXECUTED",
  "SKIPPED",
] as const;

export const INIT_ABBREV: Record<string, string> = {
  initiated: "init",
  not_started: "—",
  abandoned: "aband",
  user_skipped: "skip",
  retroactive: "retro",
  system_error: "err",
};

export const DEFAULT_FILTERS: Filters = {
  dateRange: "7",
  categories: [],
  states: [],
  showVoided: false,
  sortColumn: "date",
  sortDir: "desc",
};

export function dateKey(iso: string | null): string {
  if (!iso) return "unknown";
  return format(parseISO(iso), "yyyy-MM-dd");
}

export function displayDate(iso: string | null): string {
  if (!iso) return "—";
  return format(parseISO(iso), "MMM d");
}

export function deltaCls(d: number | null): string {
  if (d == null) return "text-dust-deep";
  if (d > 0) return "text-ember";
  if (d < 0) return "text-signal";
  return "text-dust";
}

export function fmtDelta(d: number | null): string {
  if (d == null) return "—";
  if (d === 0) return "±0m";
  return d > 0 ? `−${d}m` : `+${Math.abs(d)}m`;
}

export function fmtRF(r: number | null, f: number | null): string {
  if (r == null && f == null) return "—";
  return `${r ?? "?"}→${f ?? "?"}`;
}

export function dateRangeWindow(dateRange: DateRange): {
  dateFrom: string;
  dateTo: string;
} {
  const today = format(new Date(), "yyyy-MM-dd");
  if (dateRange === "7") {
    return { dateFrom: format(subDays(new Date(), 7), "yyyy-MM-dd"), dateTo: today };
  }
  if (dateRange === "30") {
    return { dateFrom: format(subDays(new Date(), 30), "yyyy-MM-dd"), dateTo: today };
  }
  return { dateFrom: "2024-01-01", dateTo: today };
}

export function computeDaySummaries(tasks: TaskRow[]): Map<string, DaySummary> {
  const map = new Map<string, DaySummary>();
  for (const task of tasks) {
    const dk = dateKey(task.start);
    let summary = map.get(dk);
    if (!summary) {
      summary = {
        date: dk,
        planned: 0,
        executed: 0,
        delta: 0,
        executedCount: 0,
        skippedCount: 0,
        avgDiscrepancy: null,
      };
      map.set(dk, summary);
    }
    summary.planned += task.planned_duration_minutes ?? 0;
    summary.executed +=
      task.effective_executed_duration_minutes ?? task.executed_duration_minutes ?? 0;
    summary.delta += task.effective_duration_delta_minutes ?? task.duration_delta_minutes ?? 0;
    if (task.state === "EXECUTED") summary.executedCount++;
    if (task.state === "SKIPPED") summary.skippedCount++;
  }

  for (const [dk, summary] of map) {
    const scores = tasks
      .filter((task) => dateKey(task.start) === dk)
      .map((task) => task.discrepancy_score)
      .filter((value): value is number => value != null);
    summary.avgDiscrepancy =
      scores.length > 0
        ? Math.round((scores.reduce((total, value) => total + value, 0) / scores.length) * 10) /
          10
        : null;
  }
  return map;
}

export const CSV_COLUMNS = [
  "task_id",
  "date",
  "planned_start",
  "planned_end",
  "actual_start",
  "actual_end",
  "title",
  "category",
  "state",
  "planned_duration_minutes",
  "actual_duration_minutes",
  "duration_delta_minutes",
  "pre_task_readiness",
  "post_task_reflection",
  "discrepancy_score",
  "signed_discrepancy",
  "task_completion_percentage",
  "initiation_delay_minutes",
  "total_paused_minutes",
  "pause_count",
  "initiation_status",
  "voided_reason",
  "voided_at",
] as const;

export function taskToCsvRow(task: TaskRow): string {
  const values: string[] = [
    task.task_id,
    task.start ? format(parseISO(task.start), "yyyy-MM-dd") : "",
    task.start ?? "",
    task.end ?? "",
    task.executed_start ?? "",
    task.effective_executed_end ?? task.executed_end ?? "",
    `"${(task.title ?? "").replace(/"/g, '""')}"`,
    task.category ?? "",
    task.state,
    String(task.planned_duration_minutes ?? ""),
    String(task.effective_executed_duration_minutes ?? task.executed_duration_minutes ?? ""),
    String(task.effective_duration_delta_minutes ?? task.duration_delta_minutes ?? ""),
    String(task.pre_task_readiness ?? ""),
    String(task.post_task_reflection ?? ""),
    String(task.discrepancy_score ?? ""),
    String(task.signed_discrepancy ?? ""),
    String(task.task_completion_percentage ?? ""),
    String(task.initiation_delay_minutes ?? ""),
    String(task.total_paused_minutes ?? ""),
    String(task.pause_count ?? ""),
    task.initiation_status ?? "",
    task.voided_reason ?? "",
    task.voided_at ?? "",
  ];
  return values.join(",");
}

export function buildTasksCsv(tasks: TaskRow[]): string {
  const header = CSV_COLUMNS.join(",");
  const rows = tasks.map(taskToCsvRow);
  return [header, ...rows].join("\n");
}

export function sortTasks(
  tasks: TaskRow[],
  column: SortColumn,
  direction: SortDir
): TaskRow[] {
  const sorted = [...tasks];
  const multiplier = direction === "asc" ? 1 : -1;
  sorted.sort((a, b) => {
    switch (column) {
      case "date":
        return multiplier * ((a.start ?? "").localeCompare(b.start ?? ""));
      case "title":
        return multiplier * a.title.localeCompare(b.title);
      case "category":
        return multiplier * ((a.category ?? "").localeCompare(b.category ?? ""));
      case "state":
        return multiplier * a.state.localeCompare(b.state);
      case "plan":
        return multiplier * ((a.planned_duration_minutes ?? 0) - (b.planned_duration_minutes ?? 0));
      case "exec":
        return (
          multiplier *
          (((a.effective_executed_duration_minutes ?? a.executed_duration_minutes) ?? 0) -
            ((b.effective_executed_duration_minutes ?? b.executed_duration_minutes) ?? 0))
        );
      case "delta":
        return (
          multiplier *
          (((a.effective_duration_delta_minutes ?? a.duration_delta_minutes) ?? 0) -
            ((b.effective_duration_delta_minutes ?? b.duration_delta_minutes) ?? 0))
        );
      case "rf": {
        const aVal = (a.pre_task_readiness ?? 0) * 10 + (a.post_task_reflection ?? 0);
        const bVal = (b.pre_task_readiness ?? 0) * 10 + (b.post_task_reflection ?? 0);
        return multiplier * (aVal - bVal);
      }
      case "init":
        return multiplier * ((a.initiation_status ?? "").localeCompare(b.initiation_status ?? ""));
      default:
        return 0;
    }
  });
  return sorted;
}

export function filterTableTasks(tasks: TaskRow[], filters: Filters): TaskRow[] {
  let result = tasks.filter((task) => task.state !== "DELETED");
  if (!filters.showVoided) {
    result = result.filter((task) => !task.voided_at);
  }
  if (filters.categories.length > 0) {
    result = result.filter(
      (task) => task.category && filters.categories.includes(task.category)
    );
  }
  if (filters.states.length > 0) {
    result = result.filter((task) => filters.states.includes(task.state));
  }
  return result;
}

export function buildTableRows(sorted: TaskRow[], summaries: Map<string, DaySummary>): TableRenderRow[] {
  const rows: TableRenderRow[] = [];
  let lastDk = "";
  for (const task of sorted) {
    const dk = dateKey(task.start);
    if (dk !== lastDk) {
      const summary = summaries.get(dk);
      if (summary) rows.push({ type: "summary", dk, summary });
      lastDk = dk;
    }
    rows.push({ type: "task", task });
  }
  return rows;
}
