"use client";

import { useEffect } from "react";
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
import { ackVisiblePressureMap } from "@/lib/pressure-map-exposure";
import { type TaskRow } from "@/lib/tasks";
import {
  PRESSURE_HORIZON_OPTIONS,
  fmtHours,
  fmtHoursText,
  fmtTiming,
  fmtTrust,
  genericPressureCopy,
  pressureClass,
  pressureHorizonClass,
  pressureHorizonLabel,
} from "@/lib/pressure-map-ui";
import {
  durationFromLocal,
  endLocalFromDuration,
  fmtMinutes,
  type PlanRow,
} from "@/lib/pressure-map-planning";
import { selectPressurePlanOption } from "@/lib/pressure-map-options";
import { usePressureMapPlanCommit } from "./use-pressure-map-plan-commit";
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
            This option is diagnostic only right now. The selected pressure points are already planned tasks or need coverage confirmation before LyraOS creates blocks.
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
                    aria-pressed={row.enabled}
                    onClick={() => updateRow(row.id, { enabled: !row.enabled })}
                    className={`inline-flex h-8 items-center gap-1.5 rounded-sm border px-3 font-mono text-[10px] uppercase tracking-widest transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-signal ${
                      row.enabled
                        ? "border-signal/50 bg-signal/10 text-signal hover:bg-signal/15"
                        : "border-hairline bg-void/50 text-dust hover:border-signal/40 hover:text-parchment"
                    }`}
                  >
                    <CheckCircle2 size={12} aria-hidden="true" />
                    {row.enabled ? "Included" : "Excluded"}
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
  useEffect(() => {
    if (pressure) {
      ackVisiblePressureMap(pressure);
    }
  }, [pressure]);

  const {
    previewOpen,
    previewOption,
    rows,
    setRows,
    commitError,
    forceCandidateId,
    committing,
    openPlanPreview,
    closePlanPreview,
    commitPlan,
  } = usePressureMapPlanCommit({ pressure, taskEvidence });
  const items = pressure?.items.slice(0, 4) ?? [];
  const hasItems = items.length > 0;
  const {
    planOption,
    canPreviewPlan,
    primaryIsPlanOption,
  } = selectPressurePlanOption(pressure);
  const projection = pressure?.demand_coverage_projection;
  const calendarSummary = (() => {
    const source = pressure?.source_summary;
    if (!source || source.google_calendar_read_status === "not_connected") {
      return "Google Calendar not connected.";
    }
    if (source.google_calendar_read_status === "unavailable") {
      return "Google Calendar connected; this view could not be read.";
    }
    const knownBusy = fmtMinutes(source.calendar_busy_minutes ?? 0);
    if (source.google_calendar_read_status === "partial") {
      return `Google Calendar partial: ${knownBusy} known busy; more may be missing.`;
    }
    return `Google Calendar available: ${knownBusy} known busy.`;
  })();

  return (
    <div
      id="pressure-map"
      data-testid="pressure-map"
      className="terminal-panel flex h-full scroll-mt-6 flex-col p-5"
    >
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
              aria-label={`Show ${pressureHorizonLabel(days)} pressure horizon`}
              aria-pressed={horizonDays === days}
              data-testid={`pressure-map-horizon-${days}`}
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
                {pressure.source_summary.external_obligation_count} external /{" "}
                {pressure.source_summary.native_obligation_count} native /{" "}
                {pressure.source_summary.academic_task_count} linked tasks /{" "}
                {pressure.source_summary.study_task_count} focus blocks
              </p>
              <p
                data-testid="pressure-map-calendar-coverage"
                data-calendar-read-status={pressure.source_summary.google_calendar_read_status}
                data-calendar-busy-minutes={pressure.source_summary.calendar_busy_minutes ?? ""}
                className="mt-1 text-[11px] leading-snug text-dust"
              >
                {calendarSummary}
              </p>
            </div>
          </div>

          {projection && (
            <div className="mb-3 border-y border-hairline py-3">
              <p
                data-testid="pressure-map-remaining-demand"
                data-low-minutes={projection.remaining_demand.low_minutes}
                data-high-minutes={projection.remaining_demand.high_minutes}
                className="text-[13px] leading-snug text-parchment"
              >
                LyraOS estimates {fmtHoursText(
                  projection.remaining_demand.low_minutes,
                  projection.remaining_demand.high_minutes
                )} of study work remains in this window.
              </p>
              <div className="mt-2 grid grid-cols-2 gap-x-4 gap-y-2 text-[11px] leading-snug">
                <p
                  data-testid="pressure-map-applied-coverage"
                  data-low-minutes={projection.applied_coverage.low_minutes}
                  data-high-minutes={projection.applied_coverage.high_minutes}
                  className="text-dust"
                >
                  <span className="font-medium text-signal">
                    {fmtHoursText(
                      projection.applied_coverage.low_minutes,
                      projection.applied_coverage.high_minutes
                    )}
                  </span>{" "}
                  covered by linked plans
                </p>
                <p
                  data-testid="pressure-map-unscheduled-demand"
                  data-low-minutes={projection.unscheduled_demand.low_minutes}
                  data-high-minutes={projection.unscheduled_demand.high_minutes}
                  className="text-dust"
                >
                  <span className="font-medium text-ember">
                    {fmtHoursText(
                      projection.unscheduled_demand.low_minutes,
                      projection.unscheduled_demand.high_minutes
                    )}
                  </span>{" "}
                  not yet scheduled
                </p>
              </div>
            </div>
          )}

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
                  <Button
                    data-testid="pressure-map-preview"
                    type="button"
                    onClick={() => openPlanPreview(planOption)}
                    size="sm"
                    className="h-8 shrink-0 rounded-sm px-3 font-mono text-[10px] uppercase tracking-widest"
                  >
                    <ListPlus size={13} aria-hidden="true" />
                    Preview plan
                  </Button>
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
                <Button
                  data-testid="pressure-map-preview"
                  type="button"
                  onClick={() => openPlanPreview(planOption)}
                  size="sm"
                  className="h-8 shrink-0 rounded-sm px-3 font-mono text-[10px] uppercase tracking-widest"
                >
                  <ListPlus size={13} aria-hidden="true" />
                  Preview plan
                </Button>
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
            onClose={closePlanPreview}
            onCommit={commitPlan}
          />
        </>
      )}
    </div>
  );
}
