"use client";

import { ackExposureRender, ackExposureSuppression } from "@/lib/api";
import type { AcademicPressureMapResponse } from "@/lib/academic";

const DISCARD_DELAY_MS = 3_000;
const RENDER_ACK_RETRY_MS = [250, 750, 1500, 3000, 6000];
const SUPPRESSION_RETRY_MS = [500, 1500, 3000];
const discardTimers = new Map<string, ReturnType<typeof setTimeout>>();
const renderAttempted = new Set<string>();
const pendingRenderAcks = new Set<string>();
const ackedRenders = new Set<string>();
const pendingSuppressions = new Set<string>();
const suppressedExposures = new Set<string>();

function clearDiscardTimer(exposureId: string) {
  const timer = discardTimers.get(exposureId);
  if (timer !== undefined) {
    globalThis.clearTimeout(timer);
    discardTimers.delete(exposureId);
  }
}

function suppressDiscardedPressureMap(exposureId: string, attempt = 0) {
  if (
    renderAttempted.has(exposureId) ||
    ackedRenders.has(exposureId) ||
    pendingSuppressions.has(exposureId) ||
    suppressedExposures.has(exposureId)
  ) {
    return;
  }
  pendingSuppressions.add(exposureId);
  void ackExposureSuppression(exposureId, {
    suppressionReason: "client_discarded_before_render",
  })
    .then((ok) => {
      if (ok) {
        suppressedExposures.add(exposureId);
        return;
      }
      const retryDelay = SUPPRESSION_RETRY_MS[attempt];
      if (retryDelay !== undefined) {
        globalThis.setTimeout(() => {
          suppressDiscardedPressureMap(exposureId, attempt + 1);
        }, retryDelay);
      }
    })
    .finally(() => pendingSuppressions.delete(exposureId));
}

export function registerPressureMapCandidate(
  pressure: AcademicPressureMapResponse,
) {
  const exposureId = pressure.exposure_id;
  if (
    !exposureId ||
    renderAttempted.has(exposureId) ||
    ackedRenders.has(exposureId) ||
    suppressedExposures.has(exposureId) ||
    discardTimers.has(exposureId)
  ) {
    return;
  }
  discardTimers.set(
    exposureId,
    globalThis.setTimeout(() => {
      discardTimers.delete(exposureId);
      suppressDiscardedPressureMap(exposureId);
    }, DISCARD_DELAY_MS),
  );
}

export function ackVisiblePressureMap(
  pressure: AcademicPressureMapResponse,
  attempt = 0,
) {
  const exposureId = pressure.exposure_id;
  if (!exposureId) {
    return;
  }
  renderAttempted.add(exposureId);
  clearDiscardTimer(exposureId);
  if (
    !pressure.render_snapshot ||
    pendingRenderAcks.has(exposureId) ||
    ackedRenders.has(exposureId) ||
    pendingSuppressions.has(exposureId) ||
    suppressedExposures.has(exposureId)
  ) {
    return;
  }
  pendingRenderAcks.add(exposureId);
  void ackExposureRender(exposureId, {
    surfaceId: "academic.pressure_map",
    clientEventId: `academic.pressure_map:${exposureId}`,
    contentSnapshot: pressure.render_snapshot,
  })
    .then((ok) => {
      if (ok) {
        ackedRenders.add(exposureId);
        return;
      }
      const retryDelay = RENDER_ACK_RETRY_MS[attempt];
      if (retryDelay !== undefined) {
        globalThis.setTimeout(() => {
          ackVisiblePressureMap(pressure, attempt + 1);
        }, retryDelay);
      }
    })
    .finally(() => pendingRenderAcks.delete(exposureId));
}
