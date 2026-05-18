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
import { api, getApiBase } from "./api";

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
  /** Non-null on deadlines imported from a third-party source (Moodle
   *  iCal, etc.). Frontend renders a "from {source}" badge when set. */
  external_source?: string | null;
  external_id?: string | null;
  imported_at?: string | null;
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
  const headers: Record<string, string> = {};
  if (token) headers["Authorization"] = `Bearer ${token}`;
  const res = await fetch(`${getApiBase()}/v1/deadlines/${deadlineId}`, {
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
  deadline_match_source:
    | "heuristic_exact_title"
    | "heuristic_startswith"
    | "heuristic_substring"
    | "heuristic_alias"
    | null;
  surface_id?: string | null;
  truth_class?: string | null;
  signal_targets?: string[] | null;
  clean_profile?: string | null;
  fallback_mode?: string | null;
  exposure_id?: string | null;
  render_id?: string | null;
}

/**
 * Preview which guarded deadline candidate Lyra would suggest for a
 * given title+description, without creating a task or binding anything.
 * Used by the new-task modal to surface a soft "Lyra thinks this binds
 * to X" affordance the user can confirm or override.
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

/**
 * Pure helper extracted from /today's dueDeadlines filter (2026-04-29
 * /pulse ship). Same overdue semantics: post-sweep state='missed' OR
 * pre-sweep planned/active+past_due. Returns the same shape /today uses
 * so consumers can render the polished OVERDUE pill via DeadlineRow.
 *
 * `pinToToday`: when true, deadlines that aren't on the viewed day but
 * ARE overdue still appear (they pin to today until handled). Mirrors
 * the /today view's "if isViewingToday && isOverdue → include" branch.
 */
export function computeOverdueDeadlines(
  all: DeadlineResponse[],
  opts: { pinToToday?: boolean; nowMs?: number } = {}
): { deadline: DeadlineResponse; overdue: boolean }[] {
  const nowMs = opts.nowMs ?? Date.now();
  return all.flatMap((d) => {
    if (d.voided_at) return [];
    if (d.state === "completed" || d.state === "skipped") return [];
    const isOverdue =
      d.state === "missed" ||
      ((d.state === "planned" || d.state === "active") &&
        new Date(d.due_at_utc).getTime() < nowMs);
    if (isOverdue) return [{ deadline: d, overdue: true }];
    return [];
  });
}
