/**
 * Typed wrappers around the backend task + stopwatch endpoints.
 * All calls go through lib/api.ts which forwards the next-auth Bearer.
 */
import { api } from "./api";
import type { Category } from "./categories";

export type TaskState =
  | "PLANNED"
  | "EXECUTING"
  | "PAUSED"
  | "EXECUTED"
  | "SKIPPED"
  | "DELETED";

export interface LlmDeadlineCandidate {
  deadline_id: string;
  title: string;
  confidence: number;
}

export type LlmParseStatus = "pending" | "enriched" | "unavailable" | "failed";

export interface TaskRow {
  task_id: string;
  title: string;
  description: string | null;
  start: string | null;
  end: string | null;
  state: TaskState;
  category: string | null;
  initiation_status: string | null;
  session_index_in_day: number;
  pre_task_readiness: number | null;
  post_task_reflection: number | null;
  planned_duration_minutes: number | null;
  executed_duration_minutes: number | null;
  duration_delta_minutes: number | null;
  executed_start: string | null;
  executed_end: string | null;
  voided_at: string | null;
  // Extended fields (populated by date_from/date_to range queries)
  discrepancy_score: number | null;
  signed_discrepancy: number | null;
  initiation_delay_minutes: number | null;
  total_paused_minutes: number;
  pause_count: number;
  task_completion_percentage: number | null;
  voided_reason: string | null;
  notion_page_id: string | null;
  // Loop 11 deadline binding (alembic 033)
  deadline_id: string | null;
  deadline_match_source: string | null;
  deadline_match_confidence: number | null;
  // Workstream 1 LLM enrichment (alembic 036, 2026-04-28)
  llm_parse_status: LlmParseStatus | null;
  llm_inferred_deadline_id: string | null;
  llm_deadline_match_confidence: number | null;
  llm_deadline_candidates: LlmDeadlineCandidate[] | null;
  llm_priority: number | null;
  llm_binding_rejected_at: string | null;
}

export interface QueryResponse {
  tasks: TaskRow[];
  total: number;
  truncated?: boolean;
}

/**
 * Fetch tasks for a date. Backend filters by single state at a time; passing
 * `state="all"` makes backend's `TaskState()` ValueError branch skip the
 * filter entirely, so every non-`state`-matching row comes back. We then
 * drop DELETED client-side — still visible in audit flows elsewhere.
 *
 * `days` widens the window to `[date, date+days)` — default 1 preserves the
 * single-day Today view; the calendar view passes a larger value to pull a
 * week or month in one round trip.
 */
export async function queryTasks(
  date: string,
  days: number = 1
): Promise<TaskRow[]> {
  const res = await api<QueryResponse>(
    `/v1/tasks/query?date=${encodeURIComponent(date)}&days=${days}&state=all`
  );
  return res.tasks.filter((t) => t.state !== "DELETED");
}

/**
 * Fetch tasks across a date range. Used by the Table view.
 * Returns all states (including DELETED for audit). Caller filters client-side.
 */
export async function queryTasksRange(
  dateFrom: string,
  dateTo: string
): Promise<QueryResponse> {
  return api<QueryResponse>(
    `/v1/tasks/query?date_from=${encodeURIComponent(dateFrom)}&date_to=${encodeURIComponent(dateTo)}&state=all`
  );
}

export interface CreateTaskInput {
  title: string;
  start: string; // ISO with timezone
  end: string;
  // Free-text category — frozen taxonomy (lib/categories.ts) serves as
  // suggestion list, not a closed enum. Backend accepts any string.
  category: string;
  description?: string;
  force?: boolean;
  // Loop 11 Phase K: optional explicit deadline binding. When null/absent
  // the backend's Pass 2 keyword-overlap inference may still bind one
  // automatically. When supplied, it overrides Pass 2.
  deadline_id?: string;
  // Loop 1 calibration_nudge outcome log: when the modal showed a nudge
  // and the user accepted/dismissed it, the four fields below travel with
  // the create payload so the backend can write a calibration_nudge_event
  // row in the same transaction. All-or-none: either all four are set or
  // none are.
  nudge_decision?: "accepted" | "dismissed";
  nudge_suggested_duration_minutes?: number;
  nudge_bias_factor?: number;
  nudge_sample_size?: number;
  // Phase 6 V3 — fire-time of the modal nudge as ISO string. When
  // present, backend computes dwell_seconds = decision_time - viewed_at
  // for the ReflectionViewLog row.
  nudge_viewed_at?: string;
}

export interface ConflictSummary {
  task_id: string;
  title: string;
  start: string;
  end: string;
  state: string;
  // Path A (Apr 16): which gate fired — drives override-rate analytics
  // and the warning copy on the modal. "active_overlap" = HARD,
  // "planned_overlap" / "duplicate_title" = SOFT.
  gate_id?: string | null;
}

export interface CreateTaskResponse {
  task_id: string | null;
  created: boolean;
  notion_synced: boolean;
  // Path A: severity gates whether the modal shows an override button.
  // "hard" → no override (single-mutation authority). "soft" → can force.
  severity?: "hard" | "soft" | null;
  // "overlap" and/or "duplicate_title" — drives the warning copy.
  soft_reasons?: string[];
  conflicts: Array<{
    task_id: string;
    title: string;
    start: string;
    end: string;
    state: TaskState;
    gate_id?: string | null;
  }>;
  can_proceed: boolean;
}

export function createTask(input: CreateTaskInput) {
  return api<CreateTaskResponse>("/v1/create", {
    method: "POST",
    body: JSON.stringify({
      title: input.title,
      start: input.start,
      end: input.end,
      category: input.category,
      description: input.description || undefined,
      source: "web",
      force: input.force ?? false,
      deadline_id: input.deadline_id,
      nudge_decision: input.nudge_decision,
      nudge_suggested_duration_minutes: input.nudge_suggested_duration_minutes,
      nudge_bias_factor: input.nudge_bias_factor,
      nudge_sample_size: input.nudge_sample_size,
      nudge_viewed_at: input.nudge_viewed_at,
    }),
  });
}

// ─── Stopwatch ────────────────────────────────────────────────────────

export interface PausedOther {
  task_id: string;
  title: string;
  session_id: string;
  paused_minutes: number;
  // Apr 25 perf fix: server-computed snapshot of the target's active
  // elapsed time at pause moment. Used for optimistic-anchor on swap
  // so the timer shows correct elapsed instantly rather than 0:00.
  elapsed_minutes: number;
  // LYR-111: second-precision sibling of elapsed_minutes. Banner anchors
  // off this on swap-in so the resumed clock starts at the exact paused
  // second instead of snapping back to the last whole minute.
  elapsed_seconds?: number;
  start_time: string | null;
  total_paused_minutes: number;
}

export interface StopwatchStatus {
  active: boolean;
  task_id?: string;
  task_title?: string;
  session_id?: string;
  start_time?: string;
  elapsed_minutes?: number;
  // LYR-111: second-precision sibling of elapsed_minutes. Same logic
  // (excludes current pause), divided into minutes at display boundary.
  elapsed_seconds?: number;
  planned_duration_minutes?: number;
  paused?: boolean;
  total_paused_minutes?: number;
  // Server-computed seconds since the CURRENT pause started (zero when
  // not paused). Used by the banner's "paused · MM:SS" counter so it
  // doesn't restart from 00:00 on banner remount / multi-task swap.
  // Companion to current_pause_started_at (ISO timestamp). Added 2026-04-26
  // alongside the multi-task-swap pause-counter fix.
  current_pause_seconds?: number;
  current_pause_started_at?: string | null;
  // Multi-tasking swap (Apr 25): paused-with-open-session tasks for this
  // user that aren't currently active. Each is a /switch candidate.
  paused_others?: PausedOther[];
}

export function getStopwatchStatus() {
  return api<StopwatchStatus>("/v1/stopwatch/status");
}

export interface SwitchResponse {
  switched: boolean;
  noop: boolean;
  from_task_id: string | null;
  from_session_id: string | null;
  to_task_id: string;
  to_session_id: string;
  to_title: string;
  to_start_time: string;
  target_pause_duration_minutes: number;
}

export function switchStopwatch(target_task_id: string) {
  return api<SwitchResponse>(
    `/v1/stopwatch/switch/${encodeURIComponent(target_task_id)}`,
    { method: "POST" }
  );
}

export function startStopwatch(task_id: string, pre_task_readiness: number) {
  return api<{ session_id: string; task_id: string; start_time: string }>(
    "/v1/stopwatch/start",
    {
      method: "POST",
      body: JSON.stringify({ task_id, pre_task_readiness }),
    }
  );
}

export interface StopResponse {
  task_id: string;
  session_id: string;
  duration_minutes: number;
  planned_duration_minutes: number;
  delta_minutes: number | null;
  executed_at: string;
  is_early_stop: boolean;
  requires_confirmation?: boolean;
  confirmation_message?: string;
  notion_synced?: boolean;
  discrepancy_score?: number | null;
  micro_mirror?: string | null;
  // LYR-098 Commit 2b: reflection_view_log row id — null when the
  // corresponding signal did not fire. Consumed by Commit 3 toast stack
  // to stamp viewed/dismissed via /v1/reflection_view/{view_id}/*.
  micro_mirror_view_id?: string | null;
  calibration_nudge?: string | null;
  calibration_nudge_view_id?: string | null;
  paused_parent?: {
    task_id: string;
    title: string;
    paused_minutes: number;
  } | null;
}

export function stopStopwatch(
  post_task_reflection: number,
  opts: { confirmed?: boolean; task_completion_percentage?: number; scope_outcome?: string } = {}
) {
  const qs = opts.confirmed ? "?confirmed=true" : "";
  return api<StopResponse>(`/v1/stopwatch/stop${qs}`, {
    method: "POST",
    body: JSON.stringify({
      post_task_reflection,
      task_completion_percentage: opts.task_completion_percentage,
      scope_outcome: opts.scope_outcome,
    }),
  });
}

export function pauseStopwatch(reason?: string) {
  return api<unknown>("/v1/stopwatch/pause", {
    method: "POST",
    body: JSON.stringify({ pause_reason: reason, pause_initiator: "self" }),
  });
}

export function resumeStopwatch() {
  return api<unknown>("/v1/stopwatch/resume", { method: "POST" });
}

export function markAbandoned(task_id: string, reason?: string) {
  return api<unknown>(`/v1/tasks/${task_id}/mark-abandoned`, {
    method: "POST",
    body: JSON.stringify({ reason }),
  });
}

export interface RescheduleInput {
  task_id: string;
  new_start: string;
  new_end: string;
  title?: string;
  category?: string;
  /** Edit-modal parity (2026-04-28). When changed, backend resets
   * llm_parse_status='pending' so the chip's candidate list refreshes
   * against the new text. */
  description?: string;
  /** Explicit deadline rebind via the edit modal. Sets
   * deadline_match_source='user_explicit' with confidence=1.0. */
  deadline_id?: string | null;
}

export function rescheduleTask(input: RescheduleInput) {
  return api<{ task_id: string; rescheduled: boolean }>("/v1/reschedule", {
    method: "POST",
    body: JSON.stringify(input),
  });
}

export function deleteTask(task_id: string) {
  return api<{ task_id: string; deleted: boolean }>("/v1/delete", {
    method: "POST",
    body: JSON.stringify({ task_id }),
  });
}

export function voidTask(
  task_id: string,
  voided_reason: string,
  void_reason_detail?: string
) {
  return api<unknown>(`/v1/tasks/${task_id}/void`, {
    method: "POST",
    body: JSON.stringify({ voided_reason, void_reason_detail }),
  });
}

// ─── Notifications ────────────────────────────────────────────────────

export interface PausePredictionNotification {
  type: "pause_prediction";
  firing_id: string;
  mechanism: "clock_anchor" | "work_rhythm";
  predicted_at: string;
  lead_minutes: number;
  confidence: number;
  sample_size: number;
  active_task_id?: string;
}

export interface PendingNotificationsResponse {
  notifications: Array<Record<string, unknown>>;
  count: number;
}

export function getPendingNotifications() {
  return api<PendingNotificationsResponse>("/v1/notifications/pending");
}

export function respondToPausePrediction(
  firingId: string,
  response: "pause_now" | "dismiss" | "snooze"
) {
  return api<unknown>(`/v1/pause_predictions/${firingId}/respond`, {
    method: "POST",
    body: JSON.stringify({ user_response: response }),
  });
}

// ─── Analytics ────────────────────────────────────────────────────────

export interface BiasFactorCell {
  bias_factor: number;
  bias_factor_mean: number;
  sessions: number;
  confidence: string;
  interpretation: string;
  category: string;
  time_of_day: string;
  citation?: string;
}

export interface BiasLookupResponse {
  cell: BiasFactorCell | null;
  sessions: number;
  min_sessions: number;
  source?: "personal" | "research";
  signal_level?: string;
  signals?: Array<{ level: string; label: string; bias_factor: number; sessions: number }>;
  // Rule-13 shrinkage-blend fields (MANIFESTO v1.10, 2026-04-22). Present
  // whenever the authenticated scoping hook resolves a user_id (the
  // normal auth path); absent on the legacy unauth fallback that
  // returns the personal-only cascade. UI should prefer these when
  // present — they are the canonical magnitude per the pre-registration.
  bias_factor_final?: number;
  personal_weight?: number;
  prior_weight?: number;
  archetype_id?: string;
  archetype_prior_bias_factor?: number;
  archetype_prior_for_cell?: number;
  archetype_scaling?: number;
  archetype_prior_citation?: string;
}

export interface Insight {
  id: string;
  observation: string;
  data_points: number;
  confidence: "low" | "medium" | "high";
  strength: number;
  seen: boolean;
}

export interface InsightsResponse {
  insights: Insight[];
  sessions_analyzed: number;
  min_sessions_required: number;
  ready: boolean;
}

export function getInsights() {
  return api<InsightsResponse>("/v1/analytics/insights");
}

export function lookupBiasFactor(category: string, tod: string, plannedMinutes: number = 30) {
  return api<BiasLookupResponse>(
    `/v1/analytics/bias_factor/lookup?category=${encodeURIComponent(category)}&tod=${encodeURIComponent(tod)}&planned_minutes=${plannedMinutes}`
  );
}

// ─── User categories ──────────────────────────────────────────────────
// Fixes the 2026-04-21 dogfood report "categories don't persist after
// creating a new category". Modals call this on open to populate the
// dropdown with built-in + any user-custom categories from task
// history — so a custom "BCI" typed two weeks ago stays selectable
// without retyping.

export interface UserCategoriesResponse {
  built_in: string[];
  custom: string[];
}

export function getUserCategories() {
  return api<UserCategoriesResponse>("/v1/users/me/categories");
}

// ─── Retroactive logging ───────────────────────────────────────────────
//
// Posts a completed session after the fact. Backend creates the Task in
// EXECUTED state with initiation_status="retroactive" + a closed
// StopwatchSession with the supplied timestamps. Used by the "Retroactive
// ↓" flow in /today when the operator forgot to log a session live.

export type UnplannedReason =
  | "unexpected_task"
  | "forgot_to_log"
  | "planning_friction"
  | "spontaneous_decision";

export interface RetroactiveInput {
  title: string;
  start_time: string;           // ISO with timezone
  end_time: string;
  post_task_reflection: number; // 1–5, backend-required
  total_paused_minutes: number; // backend-required (0 is fine)
  unplanned_reason: UnplannedReason;
  pre_task_readiness?: number;
  category?: string;
  planned_duration_minutes?: number;
}

export interface RetroactiveResponse {
  task_id: string;
  title: string;
  start_time: string;
  end_time: string;
  duration_minutes: number;
  planned_duration_minutes: number;
  delta_minutes: number;
  initiation_status: "retroactive";
  pre_task_readiness: number | null;
  post_task_reflection: number | null;
  discrepancy_score: number | null;
  notion_synced: boolean;
}

export function createRetroactive(input: RetroactiveInput) {
  return api<RetroactiveResponse>("/v1/stopwatch/retroactive", {
    method: "POST",
    body: JSON.stringify(input),
  });
}

// ─── Workstream 1 LLM enrichment chip clients (2026-04-28) ─────────────

export interface LlmConfirmInput {
  /** Subset of {'deadline', 'priority'}. */
  acceptedFields: ("deadline" | "priority")[];
  /** For Tier 2 MCQ — the deadline_id the user picked from the
   * candidate list. Omit for Tier 1 (auto-uses LLM's top candidate). */
  chosenDeadlineId?: string;
}

export interface LlmConfirmResult {
  task_id: string;
  deadline_id_after: string | null;
  deadline_match_source_after: string | null;
  priority_set: boolean;
}

/**
 * User clicked "keep" (Tier 1) or picked an option (Tier 2) on the
 * LlmEnrichmentChip. Sends an X-Idempotency-Key header to deduplicate
 * double-taps within a 30s window — mirrors the existing /create
 * idempotency pattern.
 */
export function confirmLlmBinding(
  taskId: string,
  input: LlmConfirmInput
): Promise<LlmConfirmResult> {
  const idem =
    typeof crypto !== "undefined" && "randomUUID" in crypto
      ? crypto.randomUUID()
      : `${Date.now()}-${Math.random().toString(36).slice(2)}`;
  return api<LlmConfirmResult>(`/v1/tasks/${taskId}/llm-confirm`, {
    method: "POST",
    headers: { "X-Idempotency-Key": idem },
    body: JSON.stringify({
      accepted_fields: input.acceptedFields,
      chosen_deadline_id: input.chosenDeadlineId,
    }),
  });
}

/**
 * User clicked "Not relevant" on the chip — teaches the model that the
 * inferred binding was wrong. The user's existing deadline_id (if any)
 * stays unchanged; only `llm_binding_rejected_at` is stamped, which
 * tells the chip to stop rendering and feeds future precision/recall
 * analysis.
 */
export function rejectLlmBinding(
  taskId: string
): Promise<{ task_id: string; rejected_at: string }> {
  return api<{ task_id: string; rejected_at: string }>(
    `/v1/tasks/${taskId}/reject-llm-binding`,
    { method: "POST", body: JSON.stringify({}) }
  );
}
