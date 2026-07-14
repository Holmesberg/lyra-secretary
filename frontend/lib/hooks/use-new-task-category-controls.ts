"use client";

import { useCallback, useMemo, useState } from "react";
import { CATEGORIES } from "@/lib/categories";

export type NewTaskCategoryMode = "picker" | "custom";

export function useNewTaskCategoryControls() {
  const [category, setCategory] = useState<string>("work");
  const [categoryMode, setCategoryMode] =
    useState<NewTaskCategoryMode>("picker");

  const resetCategory = useCallback(() => {
    setCategory("work");
    setCategoryMode("picker");
  }, []);

  const loadCategory = useCallback((nextCategory?: string | null) => {
    const value = nextCategory || "work";
    setCategory(value);
    setCategoryMode(
      (CATEGORIES as readonly string[]).includes(value) ? "picker" : "custom",
    );
  }, []);

  const handleCategorySelect = useCallback((value: string) => {
    if (value === "__CREATE_NEW__") {
      setCategoryMode("custom");
      setCategory("");
      return;
    }
    setCategory(value);
  }, []);

  const handleCustomCategoryChange = useCallback((value: string) => {
    setCategory(value);
  }, []);

  const returnToCategoryPicker = useCallback(() => {
    resetCategory();
  }, [resetCategory]);

  return useMemo(
    () => ({
      category,
      categoryMode,
      resetCategory,
      loadCategory,
      handleCategorySelect,
      handleCustomCategoryChange,
      returnToCategoryPicker,
    }),
    [
      category,
      categoryMode,
      handleCategorySelect,
      handleCustomCategoryChange,
      loadCategory,
      resetCategory,
      returnToCategoryPicker,
    ],
  );
}
