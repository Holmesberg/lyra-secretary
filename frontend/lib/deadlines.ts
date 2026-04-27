/**
 * Deadline client helpers (Loop 11 Phase J + K).
 *
 * Mirrors the backend CRUD at /v1/deadlines + the read-only Pass 2
 * preview at /v1/parse/deadline-preview. The list page consumes the
 * full CRUD; the new-task modal consumes the preview to surface
 * "Lyra thinks this binds to X" before the user submits.
 *
 * voided_at_guard: list/get exclude voided rows by default; the audit
 * paths set include_voided=true. Terminal-state rows (completed,
 * missed, skipped) stay queryable but the preview filters them out
 * so the picker only ever surfaces bindable deadlines.
 */
import { api } from "./api";

export type DeadlineState =
  | "planned"
  | "active"
  | "completed"
  | "missed"
  | "skipped"
  | "voided";

export interface DeadlineResponse {
  deadline_id: string;
  user_id: number;
  title: string;
  description: string | null;
  due_at_utc: string;
  category_hint: string | null;
  state: DeadlineState;
  completed_at: string | null;
  voided_at: string | null;
  created_at: string;
}

export interface DeadlineListResponse {
  deadlines: DeadlineResponse[];
  total: number;
}

export interface DeadlineCreateRequest {
  title: string;
  description?: string;
  due_at_utc: string;
  category_hint?: string;
}

export interface DeadlineUpdateRequest {
  title?: string;
  description?: string;
  due_at_utc?: string;
  category_hint?: string;
  // User-transitionable: planned | active | completed | skipped.
  // Voided uses DELETE; missed is server-stamped.
  state?: "planned" | "active" | "completed" | "skipped";
}

export function listDeadlines(
  state?: DeadlineState,
  includeVoided = false
): Promise<DeadlineListResponse> {
  const qs = new URLSearchParams();
  if (state) qs.set("state", state);
  if (includeVoided) qs.set("include_voided", "true");
  const q = qs.toString();
  return api<DeadlineListResponse>(`/v1/deadlines${q ? `?${q}` : ""}`);
}

export function getDeadline(deadlineId: string): Promise<DeadlineResponse> {
  return api<DeadlineResponse>(`/v1/deadlines/${deadlineId}`);
}

export function createDeadline(
  request: DeadlineCreateRequest
): Promise<DeadlineResponse> {
  return api<DeadlineResponse>("/v1/deadlines", {
    method: "POST",
    body: JSON.stringify(request),
  });
}

export function updateDeadline(
  deadlineId: string,
  request: DeadlineUpdateRequest
): Promise<DeadlineResponse> {
  return api<DeadlineResponse>(`/v1/deadlines/${deadlineId}`, {
    method: "PUT",
    body: JSON.stringify(request),
  });
}

export async function voidDeadline(deadlineId: string): Promise<void> {
  // The DELETE endpoint returns 204 No Content; api() always parses JSON,
  // so we drive fetch directly and tolerate the empty body.
  const { getSession } = await import("next-auth/react");
  const session = await getSession();
  const token = (session as any)?.backendToken as string | undefined;
  const base = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
  const headers: Record<string, string> = {};
  if (token) headers["Authorization"] = `Bearer ${token}`;
  const res = await fetch(`${base}/v1/deadlines/${deadlineId}`, {
    method: "DELETE",
    headers,
  });
  if (!res.ok && res.status !== 204) {
    throw new Error(`void failed: ${res.status}`);
  }
}

// ── Pass 2 preview (Phase K) ──────────────────────────────────────

export interface DeadlinePreviewResponse {
  deadline_id: string | null;
  deadline_title: string | null;
  deadline_match_confidence: number | null;
  deadline_match_source: "parser_auto" | null;
}

/**
 * Preview which deadline the parser would auto-bind for a given
 * title+description, without creating a task. Used by the new-task
 * modal to surface a soft "Lyra thinks this binds to X" affordance
 * the user can confirm or override.
 *
 * Returns all-null fields when no candidate clears the threshold or
 * when the user has no bindable deadlines.
 */
export function previewDeadlineBinding(
  title: string,
  description?: string
): Promise<DeadlinePreviewResponse> {
  return api<DeadlinePreviewResponse>("/v1/parse/deadline-preview", {
    method: "POST",
    body: JSON.stringify({
      title,
      description: description || undefined,
    }),
  });
}
