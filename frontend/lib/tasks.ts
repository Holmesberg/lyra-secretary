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

export interface TaskRow {
  task_id: string;
  title: string;
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
}

export interface QueryResponse {
  tasks: TaskRow[];
  total: number;
}

/**
 * Fetch tasks for a date. Backend filters by single state at a time; passing
 * `state="all"` makes backend's `TaskState()` ValueError branch skip the
 * filter entirely, so every non-`state`-matching row comes back. We then
 * drop DELETED client-side — still visible in audit flows elsewhere.
 */
export async function queryTasks(date: string): Promise<TaskRow[]> {
  const res = await api<QueryResponse>(
    `/v1/tasks/query?date=${encodeURIComponent(date)}&state=all`
  );
  return res.tasks.filter((t) => t.state !== "DELETED");
}

export interface CreateTaskInput {
  title: string;
  start: string; // ISO with timezone
  end: string;
  category: Category;
  force?: boolean;
}

export interface CreateTaskResponse {
  task_id: string | null;
  created: boolean;
  notion_synced: boolean;
  conflicts: Array<{
    task_id: string;
    title: string;
    start: string;
    end: string;
    state: TaskState;
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
      source: "web",
      force: input.force ?? false,
    }),
  });
}

// ─── Stopwatch ────────────────────────────────────────────────────────

export interface StopwatchStatus {
  active: boolean;
  task_id?: string;
  task_title?: string;
  session_id?: string;
  start_time?: string;
  elapsed_minutes?: number;
  planned_duration_minutes?: number;
  paused?: boolean;
  total_paused_minutes?: number;
}

export function getStopwatchStatus() {
  return api<StopwatchStatus>("/v1/stopwatch/status");
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
  calibration_nudge?: string | null;
}

export function stopStopwatch(
  post_task_reflection: number,
  opts: { confirmed?: boolean; task_completion_percentage?: number } = {}
) {
  const qs = opts.confirmed ? "?confirmed=true" : "";
  return api<StopResponse>(`/v1/stopwatch/stop${qs}`, {
    method: "POST",
    body: JSON.stringify({
      post_task_reflection,
      task_completion_percentage: opts.task_completion_percentage,
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
