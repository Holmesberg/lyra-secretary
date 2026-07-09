/**
 * Typed wrappers around the backend task + stopwatch endpoints.
 * All calls go through lib/api.ts which forwards the next-auth Bearer.
 */
import { api } from "./api";
import type { Category } from "./categories";
import { idempotencyHeaders } from "./tasks/idempotency";

export * from "./tasks/notifications";
export * from "./tasks/stopwatch";

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
  is_anchor: boolean;
  rct_arm: string | null;
  initiation_status: string | null;
  session_index_in_day: number;
  pre_task_readiness: number | null;
  post_task_reflection: number | null;
  planned_duration_minutes: number | null;
  executed_duration_minutes: number | null;
  duration_delta_minutes: number | null;
  executed_start: string | null;
  executed_end: string | null;
  effective_executed_duration_minutes: number | null;
  effective_duration_delta_minutes: number | null;
  effective_executed_end: string | null;
  execution_duration_provenance: "observed" | "retroactive";
  execution_correction_id: string | null;
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
  /** Operator-visibility chip 2026-05-01: bound deadline's title so
   *  the /today + /calendar UI can show "↳ Lab 8 due Fri" inline,
   *  letting the user verify explicit/confirmed bindings landed without
   *  cross-referencing the /deadlines page. Null when unbound. */
  deadline_title: string | null;
  // Workstream 1 LLM enrichment (alembic 036, 2026-04-28)
  llm_parse_status: LlmParseStatus | null;
  llm_inferred_deadline_id: string | null;
  llm_deadline_match_confidence: number | null;
  llm_deadline_candidates: LlmDeadlineCandidate[] | null;
  llm_priority: number | null;
  llm_binding_rejected_at: string | null;
  // Trust-not-rewrite contract (alembic 039, 2026-04-28). Populated by
  // the LLM enrichment worker when it disagrees with an existing
  // user/heuristic binding. Chip renders "Possible better match" when
  // present.
  llm_alternative_suggestion: {
    deadline_id: string;
    title: string;
    confidence: number;
    from_source: string;
  } | null;
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
  dateTo: string,
  opts: { includeVoided?: boolean } = {}
): Promise<QueryResponse> {
  const qs = new URLSearchParams({
    date_from: dateFrom,
    date_to: dateTo,
    state: "all",
  });
  if (opts.includeVoided) qs.set("include_voided", "true");
  return api<QueryResponse>(
    `/v1/tasks/query?${qs.toString()}`
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
  // Loop 11 Phase K: optional explicit deadline binding. When absent,
  // deadline suggestions remain suggestion-only; backend does not bind.
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
  idempotencyKey?: string;
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
    headers: idempotencyHeaders("task-create", input.idempotencyKey),
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

export function markAbandoned(task_id: string, reason?: string) {
  return api<unknown>(`/v1/tasks/${task_id}/mark-abandoned`, {
    method: "POST",
    body: JSON.stringify({ reason }),
  });
}

export interface MarkDoneResponse {
  task_id: string;
  done: boolean;
  retrospective: boolean;
  previous_state: TaskState;
  new_state: TaskState;
  initiation_status: string;
}

export function markDone(task_id: string, idempotencyKey?: string) {
  return api<MarkDoneResponse>(`/v1/tasks/${task_id}/mark-done`, {
    method: "POST",
    headers: idempotencyHeaders(`mark-done:${task_id}`, idempotencyKey),
  });
}

export interface ExecutionCorrectionInput {
  corrected_end_time?: string;
  corrected_duration_minutes?: number;
  reason?: "forgot_to_stop_timer" | "accidental_left_running";
  note?: string;
}

export interface ExecutionCorrectionResponse {
  task_id: string;
  correction_id: string;
  corrected: boolean;
  provenance: "retroactive";
  reason: string;
  original_executed_end: string;
  original_executed_duration_minutes: number;
  corrected_executed_end: string;
  corrected_executed_duration_minutes: number;
  effective_duration_delta_minutes: number;
  vt17_eligible: boolean;
}

export function correctExecutionDuration(
  taskId: string,
  input: ExecutionCorrectionInput
) {
  return api<ExecutionCorrectionResponse>(
    `/v1/tasks/${encodeURIComponent(taskId)}/execution-correction`,
    {
      method: "POST",
      body: JSON.stringify({
        reason: "forgot_to_stop_timer",
        ...input,
      }),
    }
  );
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
  /** Explicitly clear the existing deadline binding. Omitted/false = no change. */
  clear_deadline?: boolean;
}

export function rescheduleTask(input: RescheduleInput) {
  return api<{ task_id: string; rescheduled: boolean }>("/v1/reschedule", {
    method: "POST",
    body: JSON.stringify(input),
  });
}

export interface DeadlineBindingInput {
  deadline_id?: string | null;
  clear_deadline?: boolean;
}

export interface DeadlineBindingResult {
  task_id: string;
  deadline_id_after: string | null;
  deadline_title_after: string | null;
  deadline_match_source_after: string | null;
  metadata_correction: boolean;
}

export function updateTaskDeadlineBinding(
  taskId: string,
  input: DeadlineBindingInput
) {
  return api<DeadlineBindingResult>(
    `/v1/tasks/${encodeURIComponent(taskId)}/deadline-binding`,
    {
      method: "POST",
      body: JSON.stringify({
        deadline_id: input.deadline_id ?? undefined,
        clear_deadline: input.clear_deadline ?? false,
      }),
    }
  );
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
  execution_suggested_minutes?: number;
  pause_overhead_minutes?: number;
  pause_overhead_sample_size?: number;
  occupancy_suggested_minutes?: number;
  occupancy_strategy?: string;
  occupancy_factor?: number | null;
  surface_id?: string | null;
  truth_class?: string | null;
  signal_targets?: string[] | null;
  clean_profile?: string | null;
  fallback_mode?: string | null;
  exposure_id?: string | null;
  render_id?: string | null;
  suppressed_reason?: string | null;
}

export interface Insight {
  id: string;
  title?: string;
  body?: string;
  confidence_label?: string;
  authority_label?: string;
  sample_label?: string;
  observation: string;
  data_points: number;
  confidence: "low" | "medium" | "high";
  strength: number;
  seen: boolean;
  evidence?: {
    label: string;
    value: string;
    source_insight_id: string;
  }[];
  evidence_rows?: {
    label: string;
    value: string;
    source_insight_id: string;
  }[];
  surface_id?: string;
  truth_class?: "trace" | "metric" | "interpretation" | "intervention" | "diagnostic_only";
  usage_class?: string;
  clean_profile?: string | null;
  eligible_sample_count?: number;
  min_n_required?: number;
  suppressed_reason?: string | null;
  fallback_mode?: string;
  legacy_adapter?: string | null;
  exposure_id?: string | null;
  render_id?: string | null;
  authority_rung?: string | null;
  mutation_permission?: string | null;
  public_translator?: string | null;
}

export interface SuppressedInsightGenerator {
  id: string;
  surface_id: string;
  truth_class: "trace" | "metric" | "interpretation" | "intervention" | "diagnostic_only";
  usage_class: string;
  clean_profile: string | null;
  eligible_sample_count: number;
  min_n_required: number;
  suppressed_reason: string;
  fallback_mode: string;
  legacy_adapter: string | null;
  owner: string;
  deadline: string;
}

export interface InsightsResponse {
  insights: Insight[];
  sessions_analyzed: number;
  history_events_analyzed?: number;
  min_sessions_required: number;
  unlocked?: boolean;
  ready: boolean;
  surface_id?: string;
  truth_class?: "trace" | "metric" | "interpretation" | "intervention" | "diagnostic_only";
  usage_class?: string;
  clean_profile?: string | null;
  eligible_sample_count?: number;
  min_n_required?: number;
  suppressed_reason?: string | null;
  fallback_mode?: string;
  legacy_adapter?: string | null;
  exposure_id?: string | null;
  render_id?: string | null;
  suppressed_generators?: SuppressedInsightGenerator[];
  message?: string;
  reopen_after_clean_sessions?: number;
  new_clean_sessions_since_hold?: number;
  clean_sessions_until_reopen?: number;
}

export function getInsights() {
  return api<InsightsResponse>("/v1/analytics/insights");
}

const BIAS_LOOKUP_CACHE_TTL_MS = 30_000;
const biasLookupCache = new Map<
  string,
  { storedAt: number; promise: Promise<BiasLookupResponse> }
>();

export function lookupBiasFactor(
  category: string,
  tod: string,
  plannedMinutes: number = 30,
  options?: { fast?: boolean; exposureId?: string | null }
) {
  const fast = Boolean(options?.fast);
  const exposureId = options?.exposureId ?? "";
  const key = `${category}\u0000${tod}\u0000${plannedMinutes}\u0000${fast ? "fast" : "full"}\u0000${exposureId}`;
  const cached = biasLookupCache.get(key);
  if (cached && Date.now() - cached.storedAt < BIAS_LOOKUP_CACHE_TTL_MS) {
    return cached.promise;
  }
  const exposureParam = exposureId
    ? `&exposure_id=${encodeURIComponent(exposureId)}`
    : "";
  const promise = api<BiasLookupResponse>(
    `/v1/analytics/bias_factor/lookup?category=${encodeURIComponent(category)}&tod=${encodeURIComponent(tod)}&planned_minutes=${plannedMinutes}${fast ? "&fast=true" : ""}${exposureParam}`
  );
  biasLookupCache.set(key, { storedAt: Date.now(), promise });
  promise.catch(() => {
    if (biasLookupCache.get(key)?.promise === promise) {
      biasLookupCache.delete(key);
    }
  });
  return promise;
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
 * inferred binding was wrong. For "Possible better match" this keeps the
 * current binding and drops only the alternative; for system-auto bindings
 * with no current alternative, the backend may clear the binding.
 */
export function rejectLlmBinding(
  taskId: string
): Promise<{ task_id: string; rejected_at: string }> {
  return api<{ task_id: string; rejected_at: string }>(
    `/v1/tasks/${taskId}/reject-llm-binding`,
    { method: "POST", body: JSON.stringify({}) }
  );
}
