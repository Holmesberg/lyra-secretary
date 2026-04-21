"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { format, subDays, parseISO } from "date-fns";
import { Download, ChevronUp, ChevronDown } from "lucide-react";
import { queryTasksRange, type TaskRow, type QueryResponse } from "@/lib/tasks";
import {
  CATEGORIES,
  getCategoryColor,
  STATE_STYLES,
  type Category,
} from "@/lib/categories";
import { cn } from "@/lib/utils";

// ─── Types ──────────────────────────────────────────────────────────

type DateRange = "7" | "30" | "all";
type SortColumn =
  | "date"
  | "title"
  | "category"
  | "state"
  | "plan"
  | "exec"
  | "delta"
  | "rf"
  | "init";
type SortDir = "asc" | "desc";

const TASK_STATES = [
  "PLANNED",
  "EXECUTING",
  "PAUSED",
  "EXECUTED",
  "SKIPPED",
] as const;

const INIT_ABBREV: Record<string, string> = {
  initiated: "init",
  not_started: "—",
  abandoned: "aband",
  user_skipped: "skip",
  retroactive: "retro",
  system_error: "err",
};

const STORAGE_KEY = "lyra-table-filters";

interface Filters {
  dateRange: DateRange;
  categories: string[];
  states: string[];
  showVoided: boolean;
  sortColumn: SortColumn;
  sortDir: SortDir;
}

const DEFAULT_FILTERS: Filters = {
  dateRange: "7",
  categories: [],
  states: [],
  showVoided: false,
  sortColumn: "date",
  sortDir: "desc",
};

function loadFilters(): Filters {
  if (typeof window === "undefined") return DEFAULT_FILTERS;
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return DEFAULT_FILTERS;
    return { ...DEFAULT_FILTERS, ...JSON.parse(raw) };
  } catch {
    return DEFAULT_FILTERS;
  }
}

function saveFilters(f: Filters) {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(f));
  } catch {}
}

// ─── Helpers ────────────────────────────────────────────────────────

function dateKey(iso: string | null): string {
  if (!iso) return "unknown";
  return format(parseISO(iso), "yyyy-MM-dd");
}

function displayDate(iso: string | null): string {
  if (!iso) return "—";
  return format(parseISO(iso), "MMM d");
}

function deltaCls(d: number | null): string {
  // Delta polarity still carries meaning: positive = under-estimate (ember
  // warning), negative = over-estimate (signal calm), null = no data.
  if (d == null) return "text-dust-deep";
  if (d > 0) return "text-ember";
  if (d < 0) return "text-signal";
  return "text-dust";
}

function fmtDelta(d: number | null): string {
  if (d == null) return "—";
  if (d === 0) return "±0m";
  return d > 0 ? `−${d}m` : `+${Math.abs(d)}m`;
}

function fmtRF(r: number | null, f: number | null): string {
  if (r == null && f == null) return "—";
  return `${r ?? "?"}→${f ?? "?"}`;
}

// ─── Daily Summary ──────────────────────────────────────────────────

interface DaySummary {
  date: string;
  planned: number;
  executed: number;
  delta: number;
  executedCount: number;
  skippedCount: number;
  avgDiscrepancy: number | null;
}

function computeDaySummaries(tasks: TaskRow[]): Map<string, DaySummary> {
  const map = new Map<string, DaySummary>();
  for (const t of tasks) {
    const dk = dateKey(t.start);
    let s = map.get(dk);
    if (!s) {
      s = {
        date: dk,
        planned: 0,
        executed: 0,
        delta: 0,
        executedCount: 0,
        skippedCount: 0,
        avgDiscrepancy: null,
      };
      map.set(dk, s);
    }
    s.planned += t.planned_duration_minutes ?? 0;
    s.executed += t.executed_duration_minutes ?? 0;
    s.delta += t.duration_delta_minutes ?? 0;
    if (t.state === "EXECUTED") s.executedCount++;
    if (t.state === "SKIPPED") s.skippedCount++;
  }
  // Avg discrepancy per day
  for (const [dk, s] of map) {
    const dayTasks = tasks.filter((t) => dateKey(t.start) === dk);
    const scores = dayTasks
      .map((t) => t.discrepancy_score)
      .filter((v): v is number => v != null);
    s.avgDiscrepancy =
      scores.length > 0
        ? Math.round((scores.reduce((a, b) => a + b, 0) / scores.length) * 10) / 10
        : null;
  }
  return map;
}

// ─── CSV Export ─────────────────────────────────────────────────────

const CSV_COLUMNS = [
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
  "notion_page_id",
] as const;

function taskToCsvRow(t: TaskRow): string {
  const vals: string[] = [
    t.task_id,
    t.start ? format(parseISO(t.start), "yyyy-MM-dd") : "",
    t.start ?? "",
    t.end ?? "",
    t.executed_start ?? "",
    t.executed_end ?? "",
    `"${(t.title ?? "").replace(/"/g, '""')}"`,
    t.category ?? "",
    t.state,
    String(t.planned_duration_minutes ?? ""),
    String(t.executed_duration_minutes ?? ""),
    String(t.duration_delta_minutes ?? ""),
    String(t.pre_task_readiness ?? ""),
    String(t.post_task_reflection ?? ""),
    String(t.discrepancy_score ?? ""),
    String(t.signed_discrepancy ?? ""),
    String(t.task_completion_percentage ?? ""),
    String(t.initiation_delay_minutes ?? ""),
    String(t.total_paused_minutes ?? ""),
    String(t.pause_count ?? ""),
    t.initiation_status ?? "",
    t.voided_reason ?? "",
    t.voided_at ?? "",
    t.notion_page_id ?? "",
  ];
  return vals.join(",");
}

function downloadCsv(tasks: TaskRow[]) {
  const header = CSV_COLUMNS.join(",");
  const rows = tasks.map(taskToCsvRow);
  const csv = [header, ...rows].join("\n");
  const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `lyra-export-${format(new Date(), "yyyy-MM-dd")}.csv`;
  a.click();
  URL.revokeObjectURL(url);
}

// ─── Sort ───────────────────────────────────────────────────────────

function sortTasks(
  tasks: TaskRow[],
  col: SortColumn,
  dir: SortDir
): TaskRow[] {
  const sorted = [...tasks];
  const m = dir === "asc" ? 1 : -1;
  sorted.sort((a, b) => {
    switch (col) {
      case "date":
        return m * ((a.start ?? "").localeCompare(b.start ?? ""));
      case "title":
        return m * a.title.localeCompare(b.title);
      case "category":
        return m * ((a.category ?? "").localeCompare(b.category ?? ""));
      case "state":
        return m * a.state.localeCompare(b.state);
      case "plan":
        return m * ((a.planned_duration_minutes ?? 0) - (b.planned_duration_minutes ?? 0));
      case "exec":
        return m * ((a.executed_duration_minutes ?? 0) - (b.executed_duration_minutes ?? 0));
      case "delta":
        return m * ((a.duration_delta_minutes ?? 0) - (b.duration_delta_minutes ?? 0));
      case "rf": {
        const aVal = (a.pre_task_readiness ?? 0) * 10 + (a.post_task_reflection ?? 0);
        const bVal = (b.pre_task_readiness ?? 0) * 10 + (b.post_task_reflection ?? 0);
        return m * (aVal - bVal);
      }
      case "init":
        return m * ((a.initiation_status ?? "").localeCompare(b.initiation_status ?? ""));
      default:
        return 0;
    }
  });
  return sorted;
}

// ─── Multi-select Dropdown ──────────────────────────────────────────

function MultiSelect({
  label,
  options,
  selected,
  onChange,
  renderOption,
}: {
  label: string;
  options: readonly string[];
  selected: string[];
  onChange: (v: string[]) => void;
  renderOption?: (o: string) => React.ReactNode;
}) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function handle(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    }
    document.addEventListener("mousedown", handle);
    return () => document.removeEventListener("mousedown", handle);
  }, []);

  const toggle = (v: string) => {
    onChange(
      selected.includes(v) ? selected.filter((s) => s !== v) : [...selected, v]
    );
  };

  return (
    <div ref={ref} className="relative">
      <button
        type="button"
        onClick={() => setOpen(!open)}
        className={cn(
          "flex items-center gap-1 rounded border px-2.5 py-1.5 text-xs",
          selected.length > 0
            ? "border-signal/40 bg-signal/10 text-signal"
            : "border-hairline bg-void-2/60 text-dust hover:bg-signal/5"
        )}
      >
        {label}
        {selected.length > 0 && (
          <span className="rounded-full bg-signal/20 px-1.5 text-[10px] text-signal">
            {selected.length}
          </span>
        )}
      </button>
      {open && (
        <div className="absolute left-0 top-full z-50 mt-1 max-h-60 w-44 overflow-auto rounded border border-hairline bg-void-2 py-1 shadow-xl">
          {options.map((o) => (
            <label
              key={o}
              className="flex cursor-pointer items-center gap-2 px-3 py-1.5 text-xs text-parchment/80 hover:bg-signal/5"
            >
              <input
                type="checkbox"
                checked={selected.includes(o)}
                onChange={() => toggle(o)}
                className="h-3 w-3 accent-[#4dd4e8]"
              />
              {renderOption ? renderOption(o) : o}
            </label>
          ))}
        </div>
      )}
    </div>
  );
}

// ─── Sort Header ────────────────────────────────────────────────────

function SortHeader({
  label,
  col,
  current,
  dir,
  onSort,
  className,
}: {
  label: string;
  col: SortColumn;
  current: SortColumn;
  dir: SortDir;
  onSort: (col: SortColumn) => void;
  className?: string;
}) {
  const active = current === col;
  return (
    <th
      onClick={() => onSort(col)}
      className={cn(
        "cursor-pointer select-none px-3 py-2 text-left text-[11px] font-medium uppercase tracking-wider text-dust-deep hover:text-parchment/80",
        active && "text-parchment",
        className
      )}
    >
      <span className="flex items-center gap-1">
        {label}
        {active &&
          (dir === "asc" ? (
            <ChevronUp className="h-3 w-3" />
          ) : (
            <ChevronDown className="h-3 w-3" />
          ))}
      </span>
    </th>
  );
}

// ─── Main Page ──────────────────────────────────────────────────────

export default function TablePage() {
  const [filters, setFilters] = useState<Filters>(DEFAULT_FILTERS);
  const [tasks, setTasks] = useState<TaskRow[]>([]);
  const [totalCount, setTotalCount] = useState(0);
  const [truncated, setTruncated] = useState(false);
  const [loading, setLoading] = useState(true);
  const mounted = useRef(false);

  // Load persisted filters on mount
  useEffect(() => {
    setFilters(loadFilters());
    mounted.current = true;
  }, []);

  // Persist filters on change (skip initial mount)
  useEffect(() => {
    if (mounted.current) saveFilters(filters);
  }, [filters]);

  const updateFilter = useCallback(
    <K extends keyof Filters>(key: K, value: Filters[K]) => {
      setFilters((prev) => ({ ...prev, [key]: value }));
    },
    []
  );

  const toggleSort = useCallback(
    (col: SortColumn) => {
      setFilters((prev) => ({
        ...prev,
        sortColumn: col,
        sortDir: prev.sortColumn === col && prev.sortDir === "desc" ? "asc" : "desc",
      }));
    },
    []
  );

  // Compute date range from filter
  const { dateFrom, dateTo } = useMemo(() => {
    const today = format(new Date(), "yyyy-MM-dd");
    if (filters.dateRange === "7") {
      return { dateFrom: format(subDays(new Date(), 7), "yyyy-MM-dd"), dateTo: today };
    }
    if (filters.dateRange === "30") {
      return { dateFrom: format(subDays(new Date(), 30), "yyyy-MM-dd"), dateTo: today };
    }
    // "all" — 2 years back is plenty at alpha scale
    return { dateFrom: "2024-01-01", dateTo: today };
  }, [filters.dateRange]);

  // Fetch
  useEffect(() => {
    setLoading(true);
    queryTasksRange(dateFrom, dateTo)
      .then((res: QueryResponse) => {
        setTasks(res.tasks);
        setTotalCount(res.total);
        setTruncated(res.truncated ?? false);
      })
      .catch((err) => console.error("Table query failed:", err))
      .finally(() => setLoading(false));
  }, [dateFrom, dateTo]);

  // Client-side filtering
  const filtered = useMemo(() => {
    let result = tasks;
    // Always hide DELETED from table view
    result = result.filter((t) => t.state !== "DELETED");
    if (!filters.showVoided) {
      result = result.filter((t) => !t.voided_at);
    }
    if (filters.categories.length > 0) {
      result = result.filter((t) => t.category && filters.categories.includes(t.category));
    }
    if (filters.states.length > 0) {
      result = result.filter((t) => filters.states.includes(t.state));
    }
    return result;
  }, [tasks, filters.showVoided, filters.categories, filters.states]);

  // Sort
  const sorted = useMemo(
    () => sortTasks(filtered, filters.sortColumn, filters.sortDir),
    [filtered, filters.sortColumn, filters.sortDir]
  );

  // Group by date for summary rows
  const daySummaries = useMemo(() => computeDaySummaries(filtered), [filtered]);

  // Render rows with date group separators
  const rows = useMemo(() => {
    const result: Array<{ type: "summary"; dk: string; summary: DaySummary } | { type: "task"; task: TaskRow }> = [];
    let lastDk = "";
    for (const t of sorted) {
      const dk = dateKey(t.start);
      if (dk !== lastDk) {
        const s = daySummaries.get(dk);
        if (s) result.push({ type: "summary", dk, summary: s });
        lastDk = dk;
      }
      result.push({ type: "task", task: t });
    }
    return result;
  }, [sorted, daySummaries]);

  return (
    <div className="space-y-3">
      {/* Filter bar */}
      <div className="flex flex-wrap items-center gap-2">
        <select
          value={filters.dateRange}
          onChange={(e) => updateFilter("dateRange", e.target.value as DateRange)}
          className="rounded border border-hairline bg-void-2/60 px-2.5 py-1.5 text-xs text-parchment/80 outline-none focus:border-hairline-signal/40"
        >
          <option value="7">Last 7 days</option>
          <option value="30">Last 30 days</option>
          <option value="all">All time</option>
        </select>

        <MultiSelect
          label="Category"
          options={CATEGORIES}
          selected={filters.categories}
          onChange={(v) => updateFilter("categories", v)}
          renderOption={(o) => (
            <span
              className={cn(
                "rounded border px-1.5 py-0.5 text-[10px] uppercase",
                getCategoryColor(o) ?? "text-dust"
              )}
            >
              {o.replace("_", " ")}
            </span>
          )}
        />

        <MultiSelect
          label="State"
          options={TASK_STATES}
          selected={filters.states}
          onChange={(v) => updateFilter("states", v)}
          renderOption={(o) => (
            <span
              className={cn(
                "rounded border px-1.5 py-0.5 text-[10px] uppercase",
                STATE_STYLES[o] ?? ""
              )}
            >
              {o}
            </span>
          )}
        />

        <label className="flex items-center gap-1.5 text-xs text-dust cursor-pointer">
          <input
            type="checkbox"
            checked={filters.showVoided}
            onChange={(e) => updateFilter("showVoided", e.target.checked)}
            className="h-3 w-3 accent-[#4dd4e8]"
          />
          Show voided
        </label>

        <div className="flex-1" />

        <span className="text-[11px] text-dust-deep font-mono">
          {filtered.length} tasks
        </span>

        <button
          type="button"
          onClick={() => downloadCsv(sorted)}
          disabled={sorted.length === 0}
          className="flex items-center gap-1.5 rounded border border-hairline bg-void-2/60 px-2.5 py-1.5 text-xs text-dust hover:bg-signal/10 disabled:opacity-30"
        >
          <Download className="h-3.5 w-3.5" />
          Export CSV
        </button>
      </div>

      {/* Truncation warning */}
      {truncated && (
        <div className="rounded border border-amber-500/20 bg-amber-500/5 px-3 py-2 text-xs text-amber-300">
          Showing 1,000 of {totalCount.toLocaleString()} tasks. Use a narrower date range or export CSV for full data.
        </div>
      )}

      {/* Table */}
      {loading ? (
        <div className="rounded-lg border border-hairline bg-void-2/40 p-10 text-center text-sm text-dust-deep">
          Loading...
        </div>
      ) : sorted.length === 0 ? (
        <div className="rounded-lg border border-hairline bg-void-2/40 p-10 text-center text-sm text-dust-deep">
          No tasks match the current filters.
        </div>
      ) : (
        <div className="overflow-auto rounded-lg border border-hairline bg-void-2/40">
          <table className="w-full text-sm">
            <thead className="sticky top-0 z-10 bg-void/95 border-b border-hairline">
              <tr>
                <SortHeader label="Date" col="date" current={filters.sortColumn} dir={filters.sortDir} onSort={toggleSort} className="w-20" />
                <SortHeader label="Title" col="title" current={filters.sortColumn} dir={filters.sortDir} onSort={toggleSort} />
                <SortHeader label="Category" col="category" current={filters.sortColumn} dir={filters.sortDir} onSort={toggleSort} className="w-24" />
                <SortHeader label="State" col="state" current={filters.sortColumn} dir={filters.sortDir} onSort={toggleSort} className="w-20" />
                <SortHeader label="Plan" col="plan" current={filters.sortColumn} dir={filters.sortDir} onSort={toggleSort} className="w-16 text-right" />
                <SortHeader label="Exec" col="exec" current={filters.sortColumn} dir={filters.sortDir} onSort={toggleSort} className="w-16 text-right" />
                <SortHeader label="Delta" col="delta" current={filters.sortColumn} dir={filters.sortDir} onSort={toggleSort} className="w-16 text-right" />
                <SortHeader label="R→F" col="rf" current={filters.sortColumn} dir={filters.sortDir} onSort={toggleSort} className="w-14 text-center" />
                <SortHeader label="Init" col="init" current={filters.sortColumn} dir={filters.sortDir} onSort={toggleSort} className="w-16" />
              </tr>
            </thead>
            <tbody>
              {rows.map((row, i) => {
                if (row.type === "summary") {
                  const s = row.summary;
                  return (
                    <tr key={`sum-${row.dk}`} className="border-t border-hairline bg-void-2/30">
                      <td className="px-3 py-1.5 text-[11px] font-medium text-dust">
                        {row.dk !== "unknown" ? format(parseISO(row.dk), "MMM d") : "—"}
                      </td>
                      <td colSpan={2} className="px-3 py-1.5 text-[11px] text-dust-deep">
                        {s.executedCount} done, {s.skippedCount} skipped
                        {s.avgDiscrepancy != null && ` · avg disc ${s.avgDiscrepancy}`}
                      </td>
                      <td className="px-3 py-1.5" />
                      <td className="px-3 py-1.5 text-right font-mono text-[11px] text-dust-deep">
                        {s.planned}m
                      </td>
                      <td className="px-3 py-1.5 text-right font-mono text-[11px] text-dust-deep">
                        {s.executed}m
                      </td>
                      <td className={cn("px-3 py-1.5 text-right font-mono text-[11px]", deltaCls(s.delta))}>
                        {fmtDelta(s.delta)}
                      </td>
                      <td className="px-3 py-1.5" />
                      <td className="px-3 py-1.5" />
                    </tr>
                  );
                }

                const t = row.task;
                const cat = t.category as Category | null;
                return (
                  <tr
                    key={t.task_id}
                    className={cn(
                      "border-t border-hairline/50 hover:bg-void-2/60",
                      t.voided_at && "opacity-50"
                    )}
                  >
                    <td className="px-3 py-2 font-mono text-xs text-dust">
                      {displayDate(t.start)}
                    </td>
                    <td className="max-w-[280px] truncate px-3 py-2 text-sm text-parchment" title={t.title}>
                      {t.title}
                    </td>
                    <td className="px-3 py-2">
                      {cat && (() => {
                        const color = getCategoryColor(cat);
                        return color ? (
                          <span
                            className={cn(
                              "rounded border px-1.5 py-0.5 text-[10px] uppercase tracking-wide",
                              color
                            )}
                          >
                            {cat.replace("_", " ")}
                          </span>
                        ) : null;
                      })()}
                    </td>
                    <td className="px-3 py-2">
                      <span
                        className={cn(
                          "rounded border px-1.5 py-0.5 text-[10px] uppercase tracking-wide",
                          STATE_STYLES[t.state] || STATE_STYLES.PLANNED
                        )}
                      >
                        {t.state === "EXECUTED" ? "EXEC" : t.state === "SKIPPED" ? "SKIP" : t.state}
                      </span>
                    </td>
                    <td className="px-3 py-2 text-right font-mono text-xs text-dust">
                      {t.planned_duration_minutes != null ? `${t.planned_duration_minutes}m` : "—"}
                    </td>
                    <td className="px-3 py-2 text-right font-mono text-xs text-dust">
                      {t.executed_duration_minutes != null ? `${t.executed_duration_minutes}m` : "—"}
                    </td>
                    <td className={cn("px-3 py-2 text-right font-mono text-xs", deltaCls(t.duration_delta_minutes))}>
                      {fmtDelta(t.duration_delta_minutes)}
                    </td>
                    <td className="px-3 py-2 text-center font-mono text-xs text-dust">
                      {fmtRF(t.pre_task_readiness, t.post_task_reflection)}
                    </td>
                    <td className="px-3 py-2 font-mono text-[11px] text-dust-deep">
                      {INIT_ABBREV[t.initiation_status ?? ""] ?? t.initiation_status ?? "—"}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
