/**
 * Typed wrappers around the backend task + stopwatch endpoints.
 * All calls go through lib/api.ts which forwards the next-auth Bearer.
 */
import { api } from "./api";

export * from "./tasks/notifications";
export * from "./tasks/stopwatch";

export * from "./tasks/lifecycle";
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
