"use client";

import { api } from "@/lib/api";

export const UNDO_AVAILABLE_EVENT = "lyra:undo-available";

export interface UndoAvailableDetail {
  message?: string;
}

export interface UndoResponse {
  success: boolean;
  action_undone: string;
  message: string;
}

export function announceUndoAvailable(message = "Action saved.") {
  if (typeof window === "undefined") return;
  window.dispatchEvent(
    new CustomEvent<UndoAvailableDetail>(UNDO_AVAILABLE_EVENT, {
      detail: { message },
    })
  );
}

export function undoLastAction() {
  return api<UndoResponse>("/v1/undo", {
    method: "POST",
    body: JSON.stringify({}),
  });
}
