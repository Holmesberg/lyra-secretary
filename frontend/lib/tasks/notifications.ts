import { api } from "../api";

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

/**
 * Fires when a paused session's paused-for duration approaches the user's
 * historical p75 for the category/time-of-day cell, or the cold-start cap
 * when training data is sparse.
 */
export interface ResumePredictionNotification {
  type: "resume_prediction";
  firing_id: string;
  session_id: string;
  task_id: string;
  task_title: string;
  category: string | null;
  paused_for_minutes: number;
  p75_pause_minutes: number | null;
  mechanism: "category_tod" | "cold_start_synthetic";
  confidence: number;
}

export interface PendingNotificationsResponse {
  notifications: Array<Record<string, unknown>>;
  count: number;
}

export function getPendingNotifications() {
  return api<PendingNotificationsResponse>("/v1/notifications/web/pending");
}

export type NotificationAckEventType =
  | "rendered"
  | "acted"
  | "dismissed"
  | "expired"
  | "lost_unrendered";

export function ackPendingNotifications(
  notificationIds: string[],
  eventType: NotificationAckEventType = "rendered"
) {
  return api<{ acknowledged: number }>("/v1/notifications/web/ack", {
    method: "POST",
    body: JSON.stringify({ notification_ids: notificationIds, event_type: eventType }),
  });
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
