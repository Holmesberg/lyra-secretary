import { api } from "../api";
import type { PauseReason } from "../stopwatch-pause-reasons";
import { idempotencyHeaders } from "./idempotency";

export interface PausedOther {
  task_id: string;
  title: string;
  session_id: string;
  paused_minutes: number;
  elapsed_minutes: number;
  elapsed_seconds?: number;
  start_time: string | null;
  total_paused_minutes: number;
  planned_duration_minutes?: number | null;
}

export interface StopwatchStatus {
  active: boolean;
  task_id?: string;
  task_title?: string;
  session_id?: string;
  start_time?: string;
  elapsed_minutes?: number;
  elapsed_seconds?: number;
  planned_duration_minutes?: number;
  paused?: boolean;
  total_paused_minutes?: number;
  current_pause_seconds?: number;
  current_pause_started_at?: string | null;
  paused_others?: PausedOther[];
}

export function getStopwatchStatus() {
  return api<StopwatchStatus>("/v1/stopwatch/status");
}

export type ScopeOutcome = "stuck_to_plan" | "expanded" | "reduced";

export interface StalePauseResolutionInput {
  post_task_reflection: number;
  task_completion_percentage: number;
  scope_outcome: ScopeOutcome;
}

export interface StalePauseResolutionResponse {
  resolved: boolean;
  task_id: string;
  session_id: string;
  new_state: string;
  active_minutes: number;
  planned_duration_minutes: number | null;
  paused_minutes: number;
  task_completion_percentage: number;
  post_task_reflection: number;
  scope_outcome: ScopeOutcome;
  data_quality_flag: string;
  closed_at: string;
}

export function resolveStalePause(
  sessionId: string,
  input: StalePauseResolutionInput
) {
  return api<StalePauseResolutionResponse>(
    `/v1/stopwatch/stale-pauses/${encodeURIComponent(sessionId)}/resolve`,
    {
      method: "POST",
      body: JSON.stringify(input),
    }
  );
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

export interface StartStopwatchResponse {
  session_id: string;
  task_id: string;
  start_time: string;
  is_future_task?: boolean;
  planned_start?: string | null;
  pre_task_readiness?: number | null;
  initiation_delay_minutes?: number | null;
  parent_task_id?: string | null;
  interruption_type?: string | null;
}

export function startStopwatch(
  task_id: string,
  pre_task_readiness: number,
  interruption_type?: string | null,
  idempotencyKey?: string
): Promise<StartStopwatchResponse> {
  return api<StartStopwatchResponse>(
    "/v1/stopwatch/start",
    {
      method: "POST",
      headers: idempotencyHeaders(`stopwatch-start:${task_id}`, idempotencyKey),
      body: JSON.stringify({
        task_id,
        pre_task_readiness,
        interruption_type: interruption_type || undefined,
      }),
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
  discrepancy_score?: number | null;
  micro_mirror?: string | null;
  micro_mirror_view_id?: string | null;
  micro_mirror_exposure_id?: string | null;
  calibration_nudge?: string | null;
  calibration_nudge_view_id?: string | null;
  calibration_nudge_exposure_id?: string | null;
  paused_parent?: {
    task_id: string;
    title: string;
    paused_minutes: number;
  } | null;
}

export function stopStopwatch(
  post_task_reflection: number,
  opts: {
    confirmed?: boolean;
    task_completion_percentage?: number;
    scope_outcome?: string;
    idempotencyKey?: string;
  } = {}
) {
  const qs = opts.confirmed ? "?confirmed=true" : "";
  return api<StopResponse>(`/v1/stopwatch/stop${qs}`, {
    method: "POST",
    headers: idempotencyHeaders(
      `stopwatch-stop:${opts.confirmed ? "confirmed" : "initial"}`,
      opts.idempotencyKey
    ),
    body: JSON.stringify({
      post_task_reflection,
      task_completion_percentage: opts.task_completion_percentage,
      scope_outcome: opts.scope_outcome,
    }),
  });
}

export function pauseStopwatch(reason?: PauseReason, idempotencyKey?: string) {
  return api<unknown>("/v1/stopwatch/pause", {
    method: "POST",
    headers: idempotencyHeaders("stopwatch-pause", idempotencyKey),
    body: JSON.stringify({ pause_reason: reason, pause_initiator: "self" }),
  });
}

export function resumeStopwatch(idempotencyKey?: string) {
  return api<unknown>("/v1/stopwatch/resume", {
    method: "POST",
    headers: idempotencyHeaders("stopwatch-resume", idempotencyKey),
  });
}
