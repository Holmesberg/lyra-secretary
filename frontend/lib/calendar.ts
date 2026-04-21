/**
 * Google Calendar read-only client wrappers.
 *
 * Events are transient context, not persisted tasks. The `/calendar`
 * view merges them into Schedule-X with a distinct calendarId so
 * they render as read-only grey blocks alongside Lyra tasks.
 *
 * See backend/app/services/calendar_sync.py for the server side and
 * docs/strategic_decisions_april_21.md §6 for the research-integrity
 * note (imported events MUST NOT enter the H1 test set).
 */
import { api } from "./api";

export interface ExternalCalendarEvent {
  id: string;
  title: string;
  /** Cairo-local naive ISO "YYYY-MM-DDTHH:MM:SS" — matches project tz contract. */
  start: string;
  end: string;
  calendar_id: string;
  source: "google";
}

export interface CalendarEventsResponse {
  events: ExternalCalendarEvent[];
  source: "google";
  connected: boolean;
  window?: { from: string; to: string };
}

/**
 * Fetch external calendar events for a window.
 *
 * `date_from` / `date_to` accept "YYYY-MM-DD" or full ISO. Backend
 * defaults to now-1d → now+30d when both are omitted.
 *
 * Returns `{ connected: false, events: [] }` gracefully when the
 * user hasn't connected Google Calendar yet — UI should show the
 * "Connect" prompt rather than treating this as an error.
 */
export async function getCalendarEvents(opts: {
  dateFrom?: string;
  dateTo?: string;
} = {}): Promise<CalendarEventsResponse> {
  const params = new URLSearchParams();
  if (opts.dateFrom) params.set("date_from", opts.dateFrom);
  if (opts.dateTo) params.set("date_to", opts.dateTo);
  const qs = params.toString();
  const path = qs ? `/v1/calendar/events?${qs}` : "/v1/calendar/events";
  return api<CalendarEventsResponse>(path);
}

/** Explicit disconnect — clears backend refresh_token storage. */
export async function disconnectCalendar(): Promise<{ ok: boolean }> {
  return api<{ ok: boolean }>("/v1/users/me/google-refresh-token", {
    method: "DELETE",
  });
}
