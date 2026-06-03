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
import { createTask } from "@/lib/tasks";
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
}

interface PlanRow {
  id: string;
  obligationId: string;
  obligationTitle: string;
  deadlineId: string | null;
  title: string;
  startLocal: string;
  durationMinutes: number;
  category: string;
  estimateSource: string;
  status: "pending" | "created" | "failed";
  error: string | null;
  enabled: boolean;
}

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

function suggestedBlockMinutes(item: AcademicPressureItem): number {
  const midpoint = (item.estimate.low_minutes + item.estimate.high_minutes) / 2;
  const block = Math.round((midpoint / 4) / 30) * 30;
  return Math.min(120, Math.max(30, block || 60));
}

function planItemsForOption(
  pressure: AcademicPressureMapResponse,
  option: AcademicRecoveryOption | null
): AcademicPressureItem[] {
  const ids = new Set(option?.obligation_ids ?? []);
  const selected = ids.size
    ? pressure.items.filter((item) => ids.has(item.obligation_id))
    : [];
  const fallback = pressure.items.filter((item) =>
    item.pressure_level === "high" || item.pressure_level === "overdue"
  );
  return (selected.length ? selected : fallback.length ? fallback : pressure.items.slice(0, 2))
    .filter((item) => item.source_class !== "lyra_task")
    .slice(0, 4);
}

function buildRows(
  pressure: AcademicPressureMapResponse,
  option: AcademicRecoveryOption | null
): PlanRow[] {
  const base = roundUpToNextHalfHour(new Date(Date.now() + 30 * 60_000));
  return planItemsForOption(pressure, option).map((item, index) => {
    const duration = suggestedBlockMinutes(item);
    const start = new Date(base.getTime() + index * (duration + 15) * 60_000);
    return {
      id: `${item.obligation_id}:${index}`,
      obligationId: item.obligation_id,
      obligationTitle: item.title,
      deadlineId: item.source_class === "lyra_task" ? null : item.obligation_id,
      title: `Recovery block: ${item.title}`,
      startLocal: toLocalInput(start),
      durationMinutes: duration,
      category: "study",
      estimateSource: `${item.estimate.confidence} confidence ${item.complexity_source}; ${item.estimate.assumptions[0] ?? "pressure-map prior"}`,
      status: "pending",
      error: null,
      enabled: true,
    };
  });
}

function PlanPreviewDialog({
  open,
  rows,
  committing,
  option,
  onRowsChange,
  onClose,
  onCommit,
}: {
  open: boolean;
  rows: PlanRow[];
  committing: boolean;
  option: AcademicRecoveryOption | null;
  onRowsChange: (rows: PlanRow[]) => void;
  onClose: () => void;
  onCommit: () => void;
}) {
  const enabledCount = rows.filter((row) => row.enabled).length;
  const updateRow = (id: string, patch: Partial<PlanRow>) => {
    onRowsChange(rows.map((row) => row.id === id ? { ...row, ...patch } : row));
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

                <div className="grid gap-3 md:grid-cols-[1.4fr_0.9fr_0.6fr]">
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
                      Start window
                    </span>
                    <Input
                      type="datetime-local"
                      value={row.startLocal}
                      disabled={!row.enabled || committing}
                      onChange={(event) => updateRow(row.id, { startLocal: event.target.value })}
                    />
                  </label>
                  <label className="flex flex-col gap-1">
                    <span className="font-mono text-[9px] uppercase tracking-widest text-dust-deep">
                      Minutes
                    </span>
                    <Input
                      type="number"
                      min={15}
                      max={240}
                      step={15}
                      value={row.durationMinutes}
                      disabled={!row.enabled || committing}
                      onChange={(event) => updateRow(row.id, {
                        durationMinutes: Number(event.target.value || 0),
                      })}
                    />
                  </label>
                </div>

                <div className="mt-3 rounded-sm border border-hairline/70 bg-void/40 px-2 py-2 text-[11px] leading-relaxed text-dust">
                  <span className="font-mono uppercase tracking-widest text-dust-deep">
                    Estimate source:
                  </span>{" "}
                  {row.estimateSource}. This is planning footprint, not execution truth.
                </div>

                {row.status !== "pending" && (
                  <p className={`mt-2 text-[11px] ${row.status === "created" ? "text-signal" : "text-ember"}`}>
                    {row.status === "created" ? "Created." : row.error ?? "Failed to create."}
                  </p>
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
            onClick={onCommit}
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
}: PulseAcademicPressureMapProps) {
  const qc = useQueryClient();
  const [previewOpen, setPreviewOpen] = useState(false);
  const [previewOption, setPreviewOption] = useState<AcademicRecoveryOption | null>(null);
  const [rows, setRows] = useState<PlanRow[]>([]);
  const [commitError, setCommitError] = useState<string | null>(null);
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

  function openPlanPreview(option: AcademicRecoveryOption | null) {
    if (!pressure) return;
    setCommitError(null);
    setPreviewOption(option);
    setRows(buildRows(pressure, option));
    setPreviewOpen(true);
  }

  async function commitPlan() {
    const enabledRows = rows.filter((row) => row.enabled);
    if (!enabledRows.length) return;
    setCommitting(true);
    setCommitError(null);
    let created = 0;
    let firstError: string | null = null;
    const nextRows = [...rows];

    for (const row of enabledRows) {
      const index = nextRows.findIndex((candidate) => candidate.id === row.id);
      try {
        const start = new Date(row.startLocal);
        const end = new Date(start.getTime() + Math.max(15, row.durationMinutes) * 60_000);
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
        });
        if (!response.created) {
          const conflictTitles = response.conflicts.map((conflict) => conflict.title).join(", ");
          const message = conflictTitles
            ? `Conflict with ${conflictTitles}. Edit the window and try again.`
            : "Conflict detected. Edit the window and try again.";
          nextRows[index] = { ...nextRows[index], status: "failed", error: message };
          firstError = firstError ?? message;
          continue;
        }
        created += 1;
        nextRows[index] = { ...nextRows[index], status: "created", error: null, enabled: false };
      } catch (error) {
        const message = error instanceof Error ? error.message : "Failed to create task";
        if (index >= 0) {
          nextRows[index] = { ...nextRows[index], status: "failed", error: message };
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
                {planOption && (
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

          {!pressure.recovery_options.some((option) => option.action === "create_plan" || option.action === "split_into_blocks") && hasItems && (
            <button
              type="button"
              onClick={() => openPlanPreview(null)}
              className="mt-3 inline-flex items-center justify-center gap-2 rounded-sm border border-hairline-signal/40 px-3 py-2 font-mono text-[10px] uppercase tracking-widest text-signal transition-colors hover:bg-signal/5"
            >
              <ListPlus size={13} />
              Preview focus blocks
            </button>
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
