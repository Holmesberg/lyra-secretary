"use client";

import { useCallback, useEffect, useState } from "react";

import type {
  CalibrationNudge,
  CalibrationNudgeSource,
} from "@/components/calibration-nudge-card";
import {
  exposureIdForCreationNudge,
  suppressCreationNudgeExposure,
} from "@/lib/hooks/use-creation-nudge-exposure";
import {
  lookupBiasFactor,
  type BiasLookupResponse,
} from "@/lib/tasks";
import { diffMinutes, roundTo5, timeOfDay } from "@/lib/task-time";

const BIAS_LOOKUP_DEBOUNCE_MS = 120;

interface UseCreationNudgeLookupOptions {
  open: boolean;
  category: string;
  start: string;
  end: string;
  durHours: number;
  durMinutes: number;
  isEdit: boolean;
  editScheduleTouched: boolean;
  nudgeDecisionMade: boolean;
}

export function useCreationNudgeLookup({
  open,
  category,
  start,
  end,
  durHours,
  durMinutes,
  isEdit,
  editScheduleTouched,
  nudgeDecisionMade,
}: UseCreationNudgeLookupOptions) {
  const [nudgeSource, setNudgeSource] =
    useState<CalibrationNudgeSource>(null);
  const [calibrationNudge, setCalibrationNudge] =
    useState<CalibrationNudge | null>(null);

  const clearCreationNudge = useCallback(() => {
    setCalibrationNudge(null);
    setNudgeSource(null);
  }, []);

  // Fetch bias_factor when category, start time, or duration changes
  // (debounced). Create mode remains eligible as soon as the form has a
  // real duration. Edit mode waits until the operator actually touches
  // the schedule/duration; opening an existing task should not nag, but
  // changing the plan should re-run the estimate.
  useEffect(() => {
    const eligible =
      open && !nudgeDecisionMade && (!isEdit || editScheduleTouched);
    if (!eligible) {
      clearCreationNudge();
      return;
    }
    const planned = durHours * 60 + durMinutes;
    const rangeValid = diffMinutes(start, end) > 0;
    if (planned <= 0 || !rangeValid) {
      clearCreationNudge();
      return;
    }
    const tod = timeOfDay(start);
    const firedAt = new Date().toISOString();
    const exposureId = exposureIdForCreationNudge(category, tod, planned);
    // A prior estimate is not actionable until the backend has confirmed
    // eligibility and created its exposure decision. Clear any estimate for
    // the previous form inputs while the next canonical lookup is pending.
    clearCreationNudge();

    const abortCtl = new AbortController();
    const applyLookupResponse = (
      res: BiasLookupResponse,
      { preserveVisibleOnIneligible = false } = {},
    ) => {
      const isResearch = res.source === "research";
      const threshold = isResearch ? 1.20 : 1.25;
      const magnitude = res.bias_factor_final ?? res.cell?.bias_factor ?? null;
      const executionSuggestedMin =
        res.execution_suggested_minutes ??
        (magnitude !== null ? roundTo5(planned * magnitude) : planned);
      const pauseOverheadMin = res.pause_overhead_minutes ?? 0;
      const pauseOverheadSampleSize = res.pause_overhead_sample_size ?? 0;
      const occupancySuggestedMin =
        res.occupancy_suggested_minutes ?? executionSuggestedMin;
      const occupancyFactor =
        res.occupancy_factor ??
        (planned > 0 ? occupancySuggestedMin / planned : null);
      const executionTriggered = magnitude !== null && magnitude >= threshold;
      const occupancyTriggered =
        occupancyFactor !== null &&
        occupancyFactor >= threshold &&
        pauseOverheadSampleSize >= 3;
      if (
        !res.cell ||
        magnitude === null ||
        (!executionTriggered && !occupancyTriggered)
      ) {
        if (res.exposure_id && !res.suppressed_reason) {
          suppressCreationNudgeExposure(res.exposure_id);
        }
        if (
          !abortCtl.signal.aborted &&
          (!preserveVisibleOnIneligible || Boolean(res.suppressed_reason))
        ) {
          clearCreationNudge();
        }
        return false;
      }

      const backendExposureId = res.exposure_id ?? exposureId;
      if (abortCtl.signal.aborted) {
        suppressCreationNudgeExposure(backendExposureId);
        return true;
      }
      setCalibrationNudge({
        cell: res.cell,
        factor: magnitude,
        personalFactor: isResearch ? null : res.cell.bias_factor,
        blendFactor: res.bias_factor_final ?? null,
        personalWeight: res.personal_weight ?? null,
        priorWeight: res.prior_weight ?? null,
        priorFactor: res.archetype_prior_for_cell ?? null,
        priorCitation:
          res.archetype_prior_citation ?? res.cell.citation ?? null,
        suggestedMin: occupancySuggestedMin,
        executionSuggestedMin,
        pauseOverheadMin,
        pauseOverheadSampleSize,
        occupancySuggestedMin,
        occupancyStrategy: res.occupancy_strategy ?? null,
        firedAt,
        exposureId: backendExposureId,
        backendReady: true,
      });
      setNudgeSource(isResearch ? "research" : "personal");
      return true;
    };

    const timer = setTimeout(() => {
      lookupBiasFactor(category, tod, planned, { fast: true, exposureId })
        .then((res) => {
          const shouldHydrate = applyLookupResponse(res);
          if (!shouldHydrate) return;
          void lookupBiasFactor(category, tod, planned, {
            exposureId: res.exposure_id ?? exposureId,
          })
            .then((hydrated) => {
              // The fast path has already authorized and rendered this
              // estimate. Personal hydration may enrich it, but a stricter
              // personal threshold must not make the actionable card vanish.
              applyLookupResponse(hydrated, {
                preserveVisibleOnIneligible: true,
              });
            })
            .catch(() => {
              // Keep the backend-authorized fast card if personal hydration
              // misses; the visible surface already has exposure authority.
            });
        })
        .catch(() => {
          if (!abortCtl.signal.aborted) {
            clearCreationNudge();
          }
        });
    }, BIAS_LOOKUP_DEBOUNCE_MS);
    return () => {
      clearTimeout(timer);
      abortCtl.abort();
    };
  }, [
    open,
    category,
    start,
    end,
    durHours,
    durMinutes,
    isEdit,
    editScheduleTouched,
    nudgeDecisionMade,
    clearCreationNudge,
  ]);

  return {
    calibrationNudge,
    nudgeSource,
    clearCreationNudge,
  };
}
