"use client";

import { useCallback, useEffect, useRef } from "react";
import type {
  CalibrationNudge,
  CalibrationNudgeSource,
} from "@/components/calibration-nudge-card";
import { ackExposureRender, ackExposureSuppression } from "@/lib/api";

const CREATION_NUDGE_RENDER_ACK_RETRY_MS = [250, 750, 1500, 3000, 6000];
const CREATION_NUDGE_SUPPRESSION_RETRY_MS = [500, 1500, 3000];
const CREATION_NUDGE_EXPOSURE_TTL_MS = 30_000;

const pendingCreationNudgeRenderAcks = new Set<string>();
const ackedCreationNudgeRenders = new Set<string>();
const pendingCreationNudgeSuppressions = new Set<string>();
const suppressedCreationNudgeExposures = new Set<string>();
const creationNudgeExposureIds = new Map<
  string,
  { exposureId: string; expiresAt: number }
>();

function newExposureId(): string {
  return (
    globalThis.crypto?.randomUUID?.() ??
    `client-${Date.now()}-${Math.random().toString(16).slice(2)}`
  );
}

export function exposureIdForCreationNudge(
  category: string,
  tod: string,
  planned: number,
): string {
  const key = `${category}\u0000${tod}\u0000${planned}`;
  const now = Date.now();
  const cached = creationNudgeExposureIds.get(key);
  if (cached && cached.expiresAt > now) {
    return cached.exposureId;
  }
  const exposureId = newExposureId();
  creationNudgeExposureIds.set(key, {
    exposureId,
    expiresAt: now + CREATION_NUDGE_EXPOSURE_TTL_MS,
  });
  return exposureId;
}

function ackCreationNudgeRender(
  exposureId: string,
  contentSnapshot: Record<string, unknown>,
  attempt = 0,
) {
  if (
    pendingCreationNudgeRenderAcks.has(exposureId) ||
    ackedCreationNudgeRenders.has(exposureId)
  ) {
    return;
  }
  pendingCreationNudgeRenderAcks.add(exposureId);
  void ackExposureRender(exposureId, {
    surfaceId: "task.creation_nudge",
    clientEventId: `task.creation_nudge:${exposureId}`,
    contentSnapshot,
  })
    .then((ok) => {
      if (ok) {
        ackedCreationNudgeRenders.add(exposureId);
        return;
      }
      const retryDelay = CREATION_NUDGE_RENDER_ACK_RETRY_MS[attempt];
      if (retryDelay !== undefined) {
        globalThis.setTimeout(() => {
          ackCreationNudgeRender(exposureId, contentSnapshot, attempt + 1);
        }, retryDelay);
      }
    })
    .finally(() => {
      pendingCreationNudgeRenderAcks.delete(exposureId);
    });
}

export function suppressCreationNudgeExposure(exposureId: string, attempt = 0) {
  if (
    pendingCreationNudgeSuppressions.has(exposureId) ||
    suppressedCreationNudgeExposures.has(exposureId) ||
    ackedCreationNudgeRenders.has(exposureId)
  ) {
    return;
  }
  pendingCreationNudgeSuppressions.add(exposureId);
  void ackExposureSuppression(exposureId, {
    suppressionReason: "client_discarded_before_render",
  })
    .then((ok) => {
      if (ok) {
        suppressedCreationNudgeExposures.add(exposureId);
        return;
      }
      const retryDelay = CREATION_NUDGE_SUPPRESSION_RETRY_MS[attempt];
      if (retryDelay !== undefined) {
        globalThis.setTimeout(() => {
          suppressCreationNudgeExposure(exposureId, attempt + 1);
        }, retryDelay);
      }
    })
    .finally(() => {
      pendingCreationNudgeSuppressions.delete(exposureId);
    });
}

function isRenderPendingOrAcked(exposureId: string): boolean {
  return (
    pendingCreationNudgeRenderAcks.has(exposureId) ||
    ackedCreationNudgeRenders.has(exposureId)
  );
}

function creationNudgeRenderSnapshot(
  nudge: CalibrationNudge | null,
  source: CalibrationNudgeSource,
  plannedMinutes: number,
) {
  if (!nudge) {
    return null;
  }
  return {
    template: "task_creation_nudge_lookup",
    category: nudge.cell.category,
    time_of_day: nudge.cell.time_of_day,
    source,
    suggested_minutes: nudge.suggestedMin,
    execution_suggested_minutes: nudge.executionSuggestedMin,
    pause_overhead_minutes: nudge.pauseOverheadMin,
    pause_overhead_sample_size: nudge.pauseOverheadSampleSize,
    occupancy_suggested_minutes: nudge.occupancySuggestedMin,
    occupancy_strategy: nudge.occupancyStrategy,
    planned_minutes: plannedMinutes,
  };
}

export function useCreationNudgeExposure({
  nudge,
  source,
  plannedMinutes,
}: {
  nudge: CalibrationNudge | null;
  source: CalibrationNudgeSource;
  plannedMinutes: number;
}) {
  const exposureRef = useRef<string | null>(null);

  const ackVisibleCreationNudge = useCallback(() => {
    const exposureId = nudge?.exposureId;
    const contentSnapshot = creationNudgeRenderSnapshot(
      nudge,
      source,
      plannedMinutes,
    );
    if (!exposureId || !contentSnapshot) {
      return;
    }
    ackCreationNudgeRender(exposureId, contentSnapshot);
  }, [nudge, plannedMinutes, source]);

  useEffect(() => {
    if (!nudge?.exposureId || !nudge.backendReady) {
      return;
    }
    ackVisibleCreationNudge();
  }, [ackVisibleCreationNudge, nudge?.backendReady, nudge?.exposureId]);

  useEffect(() => {
    const currentExposureId =
      nudge?.backendReady && nudge.exposureId ? nudge.exposureId : null;
    const previousExposureId = exposureRef.current;
    if (
      previousExposureId &&
      previousExposureId !== currentExposureId &&
      !isRenderPendingOrAcked(previousExposureId)
    ) {
      suppressCreationNudgeExposure(previousExposureId);
    }
    exposureRef.current = currentExposureId;
  }, [nudge?.backendReady, nudge?.exposureId]);

  useEffect(() => {
    return () => {
      const previousExposureId = exposureRef.current;
      if (previousExposureId && !isRenderPendingOrAcked(previousExposureId)) {
        suppressCreationNudgeExposure(previousExposureId);
      }
      exposureRef.current = null;
    };
  }, []);

  return { ackVisibleCreationNudge };
}
