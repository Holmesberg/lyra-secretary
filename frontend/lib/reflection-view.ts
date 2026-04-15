/**
 * Typed wrappers around /v1/reflection_view/{view_id}/{viewed,dismissed}.
 * Used by the Toast component to stamp impression + dismissal on
 * reflection_view_log rows that fire with every /stopwatch/stop response.
 * Both endpoints are idempotent first-wins on the server.
 */
import { api } from "./api";

export interface ViewedResponse {
  viewed: boolean;
  view_id: string;
  viewed_at: string | null;
}

export interface DismissedResponse {
  dismissed: boolean;
  view_id: string;
  dismissed_at: string | null;
  dwell_seconds: number | null;
}

export function markViewed(viewId: string) {
  return api<ViewedResponse>(
    `/v1/reflection_view/${encodeURIComponent(viewId)}/viewed`,
    { method: "POST" }
  );
}

export function markDismissed(viewId: string) {
  return api<DismissedResponse>(
    `/v1/reflection_view/${encodeURIComponent(viewId)}/dismissed`,
    { method: "POST" }
  );
}
