"use client";

import { useCallback, useMemo, useState } from "react";

export interface DescriptionChecklistEstimate {
  itemCount: number;
  perItemMinutes: number;
}

export function useNewTaskDescriptionControls(plannedMinutes: number) {
  const [description, setDescription] = useState("");
  const [showDescription, setShowDescription] = useState(false);

  const resetDescription = useCallback(() => {
    setDescription("");
    setShowDescription(false);
  }, []);

  const loadDescription = useCallback((nextDescription?: string | null) => {
    const value = nextDescription ?? "";
    setDescription(value);
    setShowDescription(value.length > 0);
  }, []);

  const showDescriptionField = useCallback(() => {
    setShowDescription(true);
  }, []);

  const handleDescriptionChange = useCallback((value: string) => {
    setDescription(value);
  }, []);

  const checklistEstimate = useMemo<DescriptionChecklistEstimate | null>(() => {
    const itemCount = description
      .split("\n")
      .filter((line) => /^\s*[-*\u2022]\s|^\s*\d+[.)]\s/.test(line)).length;

    if (itemCount < 2 || plannedMinutes <= 0) {
      return null;
    }

    return {
      itemCount,
      perItemMinutes: Math.round((plannedMinutes / itemCount) * 10) / 10,
    };
  }, [description, plannedMinutes]);

  return useMemo(
    () => ({
      description,
      showDescription,
      checklistEstimate,
      resetDescription,
      loadDescription,
      showDescriptionField,
      handleDescriptionChange,
    }),
    [
      checklistEstimate,
      description,
      handleDescriptionChange,
      loadDescription,
      resetDescription,
      showDescription,
      showDescriptionField,
    ],
  );
}
