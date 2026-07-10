import { api } from "../api";
import type { Category } from "../categories";
import { idempotencyHeaders } from "./idempotency";

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

