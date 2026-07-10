"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { format } from "date-fns";
import { Download, ChevronUp, ChevronDown } from "lucide-react";
import { queryTasksRange, type TaskRow, type QueryResponse } from "@/lib/tasks";
import { ExecutionCorrectionDialog } from "@/components/execution-correction-dialog";
import { queryKeys } from "@/lib/query-keys";
import {
  CATEGORIES,
  getCategoryColor,
  STATE_STYLES,
  type Category,
} from "@/lib/categories";
import { cn } from "@/lib/utils";
import {
  buildTableRows,
  buildTasksCsv,
  computeDaySummaries,
  dateRangeWindow,
  DEFAULT_FILTERS,
  deltaCls,
  displayDate,
  filterTableTasks,
  fmtDelta,
  fmtRF,
  INIT_ABBREV,
  sortTasks,
  TASK_STATES,
  type DateRange,
  type Filters,
  type SortColumn,
  type SortDir,
} from "@/lib/table-view";

// ─── Types ──────────────────────────────────────────────────────────

const STORAGE_KEY = "lyra-table-filters";

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

// ─── Daily Summary ──────────────────────────────────────────────────

// ─── CSV Export ─────────────────────────────────────────────────────

function downloadCsv(tasks: TaskRow[]) {
  const csv = buildTasksCsv(tasks);
  const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `LyraOS-export-${format(new Date(), "yyyy-MM-dd")}.csv`;
  a.click();
  URL.revokeObjectURL(url);
}

// ─── Sort ───────────────────────────────────────────────────────────

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
  const [correctionTask, setCorrectionTask] = useState<TaskRow | null>(null);
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
  const { dateFrom, dateTo } = useMemo(
    () => dateRangeWindow(filters.dateRange),
    [filters.dateRange]
  );

  const {
    data: taskData,
    isLoading: tasksLoading,
    refetch: refetchTasks,
  } = useQuery<QueryResponse>({
    queryKey: queryKeys.tasksRangeWindow(dateFrom, dateTo, true),
    queryFn: () => queryTasksRange(dateFrom, dateTo, { includeVoided: true }),
    staleTime: 60_000,
  });

  const tasks = taskData?.tasks ?? [];
  const totalCount = taskData?.total ?? 0;
  const truncated = taskData?.truncated ?? false;
  const loading = tasksLoading && !taskData;
  const reloadTasks = useCallback(() => {
    void refetchTasks();
  }, [refetchTasks]);

  const filtered = useMemo(() => filterTableTasks(tasks, filters), [tasks, filters]);

  // Sort
  const sorted = useMemo(
    () => sortTasks(filtered, filters.sortColumn, filters.sortDir),
    [filtered, filters.sortColumn, filters.sortDir]
  );

  // Group by date for summary rows
  const daySummaries = useMemo(() => computeDaySummaries(filtered), [filtered]);

  const rows = useMemo(() => buildTableRows(sorted, daySummaries), [sorted, daySummaries]);

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
                        {row.dk !== "unknown" ? displayDate(row.dk) : "—"}
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
                    onClick={() => t.state === "EXECUTED" && setCorrectionTask(t)}
                    className={cn(
                      "border-t border-hairline/50 hover:bg-void-2/60",
                      t.state === "EXECUTED" && "cursor-pointer",
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
                      {(t.effective_executed_duration_minutes ?? t.executed_duration_minutes) != null
                        ? `${t.effective_executed_duration_minutes ?? t.executed_duration_minutes}m`
                        : "—"}
                      {t.execution_duration_provenance === "retroactive" && (
                        <span className="ml-1 text-signal">*</span>
                      )}
                    </td>
                    <td className={cn("px-3 py-2 text-right font-mono text-xs", deltaCls(t.effective_duration_delta_minutes ?? t.duration_delta_minutes))}>
                      {fmtDelta(t.effective_duration_delta_minutes ?? t.duration_delta_minutes)}
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

      <ExecutionCorrectionDialog
        task={correctionTask}
        onClose={() => setCorrectionTask(null)}
        onSaved={reloadTasks}
      />
    </div>
  );
}
