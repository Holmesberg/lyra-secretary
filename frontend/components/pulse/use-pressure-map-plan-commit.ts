"use client";

import { useRef, useState, type Dispatch, type SetStateAction } from "react";
import { useQueryClient } from "@tanstack/react-query";
import type {
  AcademicPressureMapResponse,
  AcademicRecoveryOption,
} from "@/lib/academic";
import {
  buildRows,
  calibratedMinutes,
  calibrationSource,
  durationFromLocal,
  endLocalFromDuration,
  timeOfDayFromLocalInput,
  type PlanRow,
} from "@/lib/pressure-map-planning";
import { invalidatePressureRecoveryCommitCaches } from "@/lib/query-keys";
import { createTask, lookupBiasFactor, type TaskRow } from "@/lib/tasks";

interface UsePressureMapPlanCommitParams {
  pressure: AcademicPressureMapResponse | null;
  taskEvidence: TaskRow[];
}

interface UsePressureMapPlanCommitResult {
  previewOpen: boolean;
  previewOption: AcademicRecoveryOption | null;
  rows: PlanRow[];
  setRows: Dispatch<SetStateAction<PlanRow[]>>;
  commitError: string | null;
  forceCandidateId: string | null;
  committing: boolean;
  openPlanPreview: (option: AcademicRecoveryOption | null) => void;
  closePlanPreview: () => void;
  commitPlan: (forceRowId?: string) => Promise<void>;
}

export function usePressureMapPlanCommit({
  pressure,
  taskEvidence,
}: UsePressureMapPlanCommitParams): UsePressureMapPlanCommitResult {
  const qc = useQueryClient();
  const [previewOpen, setPreviewOpen] = useState(false);
  const [previewOption, setPreviewOption] =
    useState<AcademicRecoveryOption | null>(null);
  const [rows, setRows] = useState<PlanRow[]>([]);
  const [commitError, setCommitError] = useState<string | null>(null);
  const [forceCandidateId, setForceCandidateId] = useState<string | null>(null);
  const [committing, setCommitting] = useState(false);
  const commitInFlightRef = useRef(false);

  async function enrichColdStartRows(baseRows: PlanRow[]) {
    const updatedRows = await Promise.all(
      baseRows.map(async (row) => {
        if (row.estimateBasis !== "cold_start_prior") return row;
        try {
          const calibration = await lookupBiasFactor(
            row.category,
            timeOfDayFromLocalInput(row.startLocal),
            row.durationMinutes,
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
      }),
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
      }),
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

  function closePlanPreview() {
    if (!committing) {
      setPreviewOpen(false);
      setCommitError(null);
    }
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

  return {
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
  };
}
