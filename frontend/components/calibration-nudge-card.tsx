"use client";

import type { BiasFactorCell } from "@/lib/tasks";
import { formatPlanDeltaFromFactor } from "@/lib/task-time";

export type CalibrationNudgeSource = "personal" | "research" | null;

export interface CalibrationNudge {
  cell: BiasFactorCell;
  factor: number;
  personalFactor?: number | null;
  blendFactor?: number | null;
  personalWeight?: number | null;
  priorWeight?: number | null;
  priorFactor?: number | null;
  priorCitation?: string | null;
  suggestedMin: number;
  executionSuggestedMin: number;
  pauseOverheadMin: number;
  pauseOverheadSampleSize: number;
  occupancySuggestedMin: number;
  occupancyStrategy?: string | null;
  firedAt: string;
  exposureId?: string | null;
  backendReady?: boolean;
}

export interface CalibrationNudgeCardProps {
  nudge: CalibrationNudge;
  source: CalibrationNudgeSource;
  plannedMinutes: number;
  onUseSuggested: () => void;
  onKeepEstimate: () => void;
}

export function CalibrationNudgeCard({
  nudge,
  source,
  plannedMinutes,
  onUseSuggested,
  onKeepEstimate,
}: CalibrationNudgeCardProps) {
  return (
    <div className="rounded-sm border border-signal/40 bg-signal/5 p-3 text-xs text-signal">
      <div>
        {source === "research" ? (
          <>
            Research prior for <span className="font-medium text-parchment">{nudge.cell.category}</span> tasks
            sizes this about <span className="font-medium text-parchment">{formatPlanDeltaFromFactor(nudge.factor)}</span>.
            {" "}Your estimate: {plannedMinutes} min.
            {nudge.cell.citation && (
              <span className="block mt-0.5 text-[10px] text-signal/60">{nudge.cell.citation}</span>
            )}
          </>
        ) : nudge.priorWeight !== null &&
          nudge.priorWeight !== undefined &&
          nudge.priorWeight > 0.05 &&
          nudge.personalWeight !== null &&
          nudge.personalWeight !== undefined ? (
          <>
            {nudge.cell.sessions < 10 ? "Low-confidence blend" : "Blended estimate"}
            {" "}({nudge.cell.sessions} sessions + prior): <span className="font-medium text-parchment">{nudge.cell.category}</span> tasks
            {nudge.cell.time_of_day !== "all" && (
              <> in the <span className="font-medium text-parchment">{nudge.cell.time_of_day}</span></>
            )}
            {" "}are sized <span className="font-medium text-parchment">{formatPlanDeltaFromFactor(nudge.factor)}</span>.
            <span className="block mt-0.5 text-[10px] text-signal/70">
              Raw session average: {formatPlanDeltaFromFactor(nudge.personalFactor ?? nudge.factor)};
              {" "}personal weight {Math.round(nudge.personalWeight * 100)}%,
              prior weight {Math.round(nudge.priorWeight * 100)}%.
              {nudge.priorCitation ? ` ${nudge.priorCitation}` : ""}
            </span>
          </>
        ) : (
          <>
            {nudge.cell.sessions < 10 ? "Early data" : "Your data"}
            {" "}({nudge.cell.sessions} sessions): <span className="font-medium text-parchment">{nudge.cell.category}</span> tasks
            {nudge.cell.time_of_day !== "all" && (
              <> in the <span className="font-medium text-parchment">{nudge.cell.time_of_day}</span></>
            )}
            {" "}run <span className="font-medium text-parchment">{formatPlanDeltaFromFactor(nudge.factor)}</span>.
          </>
        )}
      </div>
      <div className="mt-2 grid gap-1 rounded-sm border border-signal/15 bg-void/30 p-2 text-[11px] text-dust">
        <div className="flex items-center justify-between gap-3">
          <span>Execution Time</span>
          <span className="font-medium text-parchment">{nudge.executionSuggestedMin} min</span>
        </div>
        <div className="flex items-center justify-between gap-3">
          <span>Pause Overhead</span>
          <span className="text-right font-medium text-parchment">
            {nudge.pauseOverheadSampleSize >= 3
              ? `+${nudge.pauseOverheadMin} min`
              : nudge.backendReady
                ? "not enough clean pause data"
                : "checking..."}
          </span>
        </div>
        <div className="flex items-center justify-between gap-3 border-t border-signal/10 pt-1 text-signal">
          <span>Occupancy Time</span>
          <span className="font-medium text-parchment">{nudge.occupancySuggestedMin} min</span>
        </div>
      </div>
      <div className="mt-2 flex gap-2">
        <button
          data-testid="new-task-nudge-use"
          type="button"
          disabled={!nudge.exposureId || !nudge.backendReady}
          className="rounded-sm bg-signal/20 px-2 py-1 text-[11px] font-medium text-parchment transition-colors hover:bg-signal/30 disabled:cursor-not-allowed disabled:opacity-50"
          onClick={onUseSuggested}
        >
          Use {nudge.suggestedMin} min
        </button>
        <button
          data-testid="new-task-nudge-keep"
          type="button"
          disabled={!nudge.exposureId || !nudge.backendReady}
          className="rounded-sm bg-void-2 px-2 py-1 text-[11px] text-dust transition-colors hover:bg-void hover:text-parchment disabled:cursor-not-allowed disabled:opacity-50"
          onClick={onKeepEstimate}
        >
          Keep {plannedMinutes} min
        </button>
      </div>
    </div>
  );
}
