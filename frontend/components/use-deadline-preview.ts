"use client";

import { useEffect, useState } from "react";

import { ackExposureRender } from "@/lib/api";
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

export function useDeadlinePreview({
  open,
  isEdit,
  title,
  description,
  deadlineId,
}: UseDeadlinePreviewOptions) {
  const [parserSuggestion, setParserSuggestion] =
    useState<DeadlinePreviewResponse | null>(null);

  // Loop 11 Phase K - Pass 2 deadline-binding preview.
  //
  // Debounced 500ms (matches the bias_factor lookup cadence) and race-safe:
  // abort any in-flight fetch on every input change so a slower response cannot
  // overwrite a fresher one. The user-selected deadline wins.
  useEffect(() => {
    if (!open || isEdit) {
      setParserSuggestion(null);
      return;
    }
    const trimmed = title.trim();
    if (trimmed.length < 3 || deadlineId) {
      setParserSuggestion(null);
      return;
    }
    const abortCtl = new AbortController();
    const timer = setTimeout(() => {
      previewDeadlineBinding(trimmed, description.trim() || undefined)
        .then((res) => {
          if (abortCtl.signal.aborted) return;
          if (res.deadline_id) setParserSuggestion(res);
          else setParserSuggestion(null);
        })
        .catch(() => {
          if (!abortCtl.signal.aborted) setParserSuggestion(null);
        });
    }, 500);
    return () => {
      clearTimeout(timer);
      abortCtl.abort();
    };
  }, [open, isEdit, title, description, deadlineId]);

  useEffect(() => {
    void ackExposureRender(parserSuggestion?.exposure_id);
  }, [parserSuggestion?.exposure_id]);

  return {
    parserSuggestion,
    setParserSuggestion,
  };
}
