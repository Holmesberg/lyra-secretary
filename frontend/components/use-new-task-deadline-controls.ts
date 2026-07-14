"use client";

import { useCallback, useMemo, useState } from "react";

import { useDeadlinePreview } from "@/components/use-deadline-preview";

interface UseNewTaskDeadlineControlsOptions {
  open: boolean;
  isEdit: boolean;
  title: string;
  description: string;
}

export function useNewTaskDeadlineControls({
  open,
  isEdit,
  title,
  description,
}: UseNewTaskDeadlineControlsOptions) {
  const [deadlineId, setDeadlineId] = useState<string | null>(null);
  const [showDeadlinePicker, setShowDeadlinePicker] = useState(false);
  const { parserSuggestion, setParserSuggestion } = useDeadlinePreview({
    open,
    isEdit,
    title,
    description,
    deadlineId,
  });

  const resetDeadline = useCallback(() => {
    setDeadlineId(null);
    setParserSuggestion(null);
    setShowDeadlinePicker(false);
  }, [setParserSuggestion]);

  const loadDeadline = useCallback(
    (nextDeadlineId?: string | null) => {
      setDeadlineId(nextDeadlineId ?? null);
      setParserSuggestion(null);
      setShowDeadlinePicker(false);
    },
    [setParserSuggestion],
  );

  const confirmSuggestion = useCallback(() => {
    if (!parserSuggestion?.deadline_id) return;
    setDeadlineId(parserSuggestion.deadline_id);
    setParserSuggestion(null);
  }, [parserSuggestion, setParserSuggestion]);

  const dismissSuggestion = useCallback(() => {
    setParserSuggestion(null);
  }, [setParserSuggestion]);

  const clearBinding = useCallback(() => {
    setDeadlineId(null);
  }, []);

  const togglePicker = useCallback(() => {
    setShowDeadlinePicker((showing) => !showing);
  }, []);

  const pickDeadline = useCallback(
    (nextDeadlineId: string) => {
      setDeadlineId(nextDeadlineId);
      setShowDeadlinePicker(false);
      setParserSuggestion(null);
    },
    [setParserSuggestion],
  );

  return useMemo(
    () => ({
      deadlineId,
      parserSuggestion,
      showDeadlinePicker,
      resetDeadline,
      loadDeadline,
      confirmSuggestion,
      dismissSuggestion,
      clearBinding,
      togglePicker,
      pickDeadline,
    }),
    [
      clearBinding,
      confirmSuggestion,
      deadlineId,
      dismissSuggestion,
      loadDeadline,
      parserSuggestion,
      pickDeadline,
      resetDeadline,
      showDeadlinePicker,
      togglePicker,
    ],
  );
}
