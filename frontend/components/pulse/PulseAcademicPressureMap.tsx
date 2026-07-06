"use client";

import { useMemo, useRef, useState } from "react";
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
  AcademicPressureMapResponse,
  AcademicRecoveryOption,
} from "@/lib/academic";
import {
  createTask,
  lookupBiasFactor,
  type TaskRow,
} from "@/lib/tasks";
import {
  PRESSURE_HORIZON_OPTIONS,
  fmtHours,
  fmtTiming,
  fmtTrust,
  genericPressureCopy,
  pressureClass,
  pressureHorizonClass,
  pressureHorizonLabel,
} from "@/lib/pressure-map-ui";
import {
  buildRows,
  calibratedMinutes,
  calibrationSource,
  durationFromLocal,
  endLocalFromDuration,
  fmtMinutes,
  planItemsForOption,
  timeOfDayFromLocalInput,
  type PlanRow,
} from "@/lib/pressure-map-planning";
import { invalidatePressureRecoveryCommitCaches } from "@/lib/query-keys";
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
      <DialogContent
        className="max-h-[88vh] max-w-3xl overflow-y-auto"
        data-testid="pressure-map-plan-preview"
      >
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
                data-testid="pressure-map-plan-row"
                data-obligation-id={row.obligationId}
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
                    data-testid="pressure-map-plan-row-toggle"
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
                      data-testid="pressure-map-plan-row-title"
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
                      data-testid="pressure-map-plan-row-start"
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
                      data-testid="pressure-map-plan-row-end"
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
                    <div data-testid="pressure-map-plan-row-duration" className={`flex min-h-10 items-center rounded-sm border px-3 font-mono text-[12px] ${
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
          <Button
            data-testid="pressure-map-preview-dismiss"
            variant="ghost"
            onClick={onClose}
            disabled={committing}
          >
            Dismiss
          </Button>
          <Button
            data-testid="pressure-map-preview-lock-in"
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
  const commitInFlightRef = useRef(false);
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
    if (commitInFlightRef.current) return;
    const enabledRows = forceRowId
      ? rows.filter((row) => row.id === forceRowId)
      : rows.filter((row) => row.enabled);
    if (!enabledRows.length) return;
    commitInFlightRef.current = true;
    setCommitting(true);
    setCommitError(null);
    if (forceRowId) {
      setForceCandidateId(null);
    }
    let created = 0;
    let firstError: string | null = null;
    const nextRows = [...rows];

    try {
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

      await invalidatePressureRecoveryCommitCaches(qc);
      if (firstError) {
        setCommitError(firstError);
      } else if (created > 0) {
        setPreviewOpen(false);
      }
    } finally {
      commitInFlightRef.current = false;
      setCommitting(false);
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
          {PRESSURE_HORIZON_OPTIONS.map((days) => (
            <button
              key={days}
              type="button"
              onClick={() => onHorizonChange?.(days)}
              className={pressureHorizonClass(days, horizonDays)}
            >
              {pressureHorizonLabel(days)}
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
                    data-testid="pressure-map-preview"
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
                  data-testid="pressure-map-preview"
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
