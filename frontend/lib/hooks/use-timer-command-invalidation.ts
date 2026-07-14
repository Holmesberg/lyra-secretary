"use client";

import { useCallback } from "react";
import { useQueryClient } from "@tanstack/react-query";

import { invalidateTimerCommandSurfaces } from "@/lib/query-keys";

export function useTimerCommandInvalidation() {
  const queryClient = useQueryClient();

  return useCallback(() => {
    void invalidateTimerCommandSurfaces(queryClient);
  }, [queryClient]);
}
