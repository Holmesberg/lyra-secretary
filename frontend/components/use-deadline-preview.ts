"use client";

import { useCallback, useEffect, useRef, useState } from "react";

import { ackExposureRender, ackExposureSuppression } from "@/lib/api";
import {
  previewDeadlineBinding,
  type DeadlinePreviewResponse,
} from "@/lib/deadlines";

interface UseDeadlinePreviewOptions {
  open: boolean;
  isEdit: boolean;
  title: string;
  description: string;
  deadlineId: string | null;
}

const RENDER_ACK_RETRY_MS = [250, 750, 1500, 3000, 6000];
const SUPPRESSION_RETRY_MS = [500, 1500, 3000];
const renderAttempted = new Set<string>();
const pendingRenderAcks = new Set<string>();
const ackedRenders = new Set<string>();
const pendingSuppressions = new Set<string>();
const suppressedExposures = new Set<string>();

function suppressDeadlineSuggestion(exposureId: string, attempt = 0) {
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
          suppressDeadlineSuggestion(exposureId, attempt + 1);
        }, retryDelay);
      }
    })
    .finally(() => pendingSuppressions.delete(exposureId));
}

export function retireDeadlineSuggestion(
  suggestion: DeadlinePreviewResponse | null,
) {
  const exposureId = suggestion?.exposure_id;
  if (exposureId) {
    suppressDeadlineSuggestion(exposureId);
  }
}

export function ackVisibleDeadlineSuggestion(
  suggestion: DeadlinePreviewResponse,
  attempt = 0,
) {
  const exposureId = suggestion.exposure_id;
  const contentSnapshot = suggestion.render_snapshot;
  if (!exposureId) {
    return;
  }
  renderAttempted.add(exposureId);
  if (
    !contentSnapshot ||
    pendingRenderAcks.has(exposureId) ||
    ackedRenders.has(exposureId) ||
    pendingSuppressions.has(exposureId) ||
    suppressedExposures.has(exposureId)
  ) {
    return;
  }
  pendingRenderAcks.add(exposureId);
  void ackExposureRender(exposureId, {
    surfaceId: "task.deadline_binding_suggestion",
    clientEventId: `task.deadline_binding_suggestion:${exposureId}`,
    contentSnapshot,
  })
    .then((ok) => {
      if (ok) {
        ackedRenders.add(exposureId);
        return;
      }
      const retryDelay = RENDER_ACK_RETRY_MS[attempt];
      if (retryDelay !== undefined) {
        globalThis.setTimeout(() => {
          ackVisibleDeadlineSuggestion(suggestion, attempt + 1);
        }, retryDelay);
      }
    })
    .finally(() => pendingRenderAcks.delete(exposureId));
}

export function useDeadlinePreview({
  open,
  isEdit,
  title,
  description,
  deadlineId,
}: UseDeadlinePreviewOptions) {
  const [parserSuggestion, setParserSuggestion] =
    useState<DeadlinePreviewResponse | null>(null);
  const suggestionRef = useRef<DeadlinePreviewResponse | null>(null);
  const replaceParserSuggestion = useCallback(
    (next: DeadlinePreviewResponse | null) => {
      setParserSuggestion((previous) => {
        if (previous?.exposure_id !== next?.exposure_id) {
          retireDeadlineSuggestion(previous);
        }
        suggestionRef.current = next;
        return next;
      });
    },
    [],
  );

  // Loop 11 Phase K - Pass 2 deadline-binding preview.
  //
  // Debounced 500ms (matches the bias_factor lookup cadence) and race-safe:
  // abort any in-flight fetch on every input change so a slower response cannot
  // overwrite a fresher one. The user-selected deadline wins.
  useEffect(() => {
    if (!open || isEdit) {
      replaceParserSuggestion(null);
      return;
    }
    const trimmed = title.trim();
    if (trimmed.length < 3 || deadlineId) {
      replaceParserSuggestion(null);
      return;
    }
    const abortCtl = new AbortController();
    const timer = setTimeout(() => {
      previewDeadlineBinding(trimmed, description.trim() || undefined)
        .then((res) => {
          if (abortCtl.signal.aborted) {
            retireDeadlineSuggestion(res);
            return;
          }
          if (res.deadline_id) replaceParserSuggestion(res);
          else replaceParserSuggestion(null);
        })
        .catch(() => {
          if (!abortCtl.signal.aborted) replaceParserSuggestion(null);
        });
    }, 500);
    return () => {
      clearTimeout(timer);
      abortCtl.abort();
    };
  }, [open, isEdit, title, description, deadlineId, replaceParserSuggestion]);

  useEffect(() => {
    return () => retireDeadlineSuggestion(suggestionRef.current);
  }, []);

  return {
    parserSuggestion,
    setParserSuggestion: replaceParserSuggestion,
  };
}
