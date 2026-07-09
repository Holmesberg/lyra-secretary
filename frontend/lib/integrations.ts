/**
 * Integrations registry + client.
 *
 * The frontend's source of truth for human-readable integration
 * metadata (name, description, scope disclosure, "coming soon"
 * previews). Per-user connection state lives server-side and is
 * fetched from GET /v1/integrations — the two join at render time
 * in <IntegrationsSection />.
 *
 * Adding a new integration is ~4 edits:
 *   1. Add an entry to INTEGRATIONS below (registry metadata).
 *   2. Add a case to the backend `list_integrations` endpoint.
 *   3. For OAuth-shaped integrations, add connect + callback routes
 *      under frontend/app/api/integrations/<provider>/.
 *   4. For API-key / file-upload shapes, extend IntegrationCard with
 *      the appropriate input UI.
 *
 * See docs/integrations_architecture.md for the full contract.
 */
import { api } from "./api";

export type IntegrationId =
  | "google_calendar"
  | "moodle"
  | "notion"
  | "ics";

export type IntegrationStatus =
  | "connected"
  | "disconnected"
  | "coming_soon";

export type AuthShape = "oauth" | "api_key" | "file" | "url_subscription";

export interface IntegrationDef {
  id: IntegrationId;
  name: string;
  /** Short one-liner under the name. User-facing. */
  description: string;
  /** What the integration enables. Separate from description so copy
   *  stays tight — description sells the "what", capability sells the "why". */
  capabilityLine: string;
  /** Scope strings shown in the disclosure panel. Empty for file-shape
   *  integrations (no scopes; local parse). */
  scopes: string[];
  authShape: AuthShape;
  /** Present when authShape === "oauth" AND the integration is
   *  available. Connect button is `<a href>` for top-level navigation. */
  connectHref?: string;
  /** Preview tile flag — false means "Coming soon". */
  available: boolean;
  /** Optional note shown on the card — "Phase 7 roadmap", etc. */
  comingSoonNote?: string;
  /** Optional research pre-registration hint. Surfaced only for users
   *  who've opted in to research consent. */
  researchNote?: string;
  /** Two-character monogram rendered in a colored badge. Keeps icon
   *  treatment consistent without bringing in brand logos. */
  monogram: string;
  /** Tailwind utility classes for the monogram chip — card-specific
   *  so each integration has a recognizable color identity. */
  monogramClass: string;
}

export const INTEGRATIONS: IntegrationDef[] = [
  {
    id: "google_calendar",
    name: "Google Calendar",
    description:
      "See your external commitments alongside planned LyraOS tasks.",
    capabilityLine:
      "Read-only — your events appear on /today and /calendar as grey background blocks. Past events carry an optional \"Did you attend?\" self-report.",
    scopes: ["https://www.googleapis.com/auth/calendar.readonly"],
    authShape: "oauth",
    connectHref: "/api/integrations/google-calendar/connect",
    available: true,
    researchNote: "Participates in VT-23 (external-source attendance self-report).",
    monogram: "GC",
    monogramClass:
      "bg-signal/15 text-signal border border-signal/30",
  },
  {
    // Moodle LMS — shipped 2026-04-29 (alembic 041) as the LMS-wedge
    // headline integration. Paste a private .ics subscription URL from
    // Moodle's "Export calendar" page; backend syncs every 6h and
    // upserts assignment due dates as LyraOS deadlines flagged with
    // external_source='moodle_ics'. Tested against ASU Engineering
    // Moodle (lms.eng.asu.edu.eg, Moodle 3.7).
    id: "moodle",
    name: "Moodle",
    description:
      "Pull course deadlines straight from your school's Moodle.",
    capabilityLine:
      "Read-only — assignments and quiz due dates appear as LyraOS deadlines. We won't create posts or modify your courses.",
    scopes: [],
    authShape: "url_subscription",
    available: true,
    monogram: "Mo",
    monogramClass:
      "bg-ember/15 text-ember border border-ember/30",
  },
  {
    id: "notion",
    name: "Notion",
    description:
      "Import tasks from a Notion database; outbound sync already runs for operators.",
    capabilityLine:
      "Column-mapping UI lets you pick which properties become LyraOS's title, date, category. Webhooks + bi-directional sync in v2.",
    scopes: ["pages:read", "databases:read"],
    authShape: "oauth",
    available: false,
    comingSoonNote: "Shipping Phase 7 (post-Spring-School).",
    monogram: "N",
    monogramClass:
      "bg-parchment/10 text-parchment border border-parchment/25",
  },
  {
    id: "ics",
    name: "ICS file / URL",
    description:
      "Drop in any .ics file or subscription URL — Apple, Outlook, Fastmail, or Google export.",
    capabilityLine:
      "Local parse, no third-party auth. Universal fallback for calendars LyraOS doesn't natively integrate with yet.",
    scopes: [],
    authShape: "file",
    available: false,
    comingSoonNote: "Shipping first in Phase 7 — zero-auth import pattern.",
    monogram: "iC",
    monogramClass:
      "bg-dust/10 text-dust border border-dust/25",
  },
];

export interface IntegrationState {
  id: IntegrationId;
  status: IntegrationStatus;
  available: boolean;
  scopes: string[];
  /** Moodle-specific: last successful iCal sync timestamp (ISO).
   *  Surfaced in the card to reassure the user sync is alive. */
  last_synced_at?: string | null;
  /** Moodle-specific: set when the URL was auto-cleared due to a
   *  permanent failure (4xx). Frontend uses this to render
   *  "Reconnect needed" copy instead of plain "Not connected". */
  disconnect_reason?: string | null;
  /** Moodle Web Services token state (alembic 043, 2026-05-01).
   *  Optional sub-capability: when true, the submission-detection
   *  sync records Moodle submission evidence without silently completing
   *  deadlines.
   *  Boolean (never the token itself) so the API never echoes
   *  the credential. */
  ws_connected?: boolean;
  ws_last_synced_at?: string | null;
  ws_disconnect_reason?: string | null;
}

export interface IntegrationsResponse {
  integrations: IntegrationState[];
}

export async function getIntegrations(): Promise<IntegrationsResponse> {
  return api<IntegrationsResponse>("/v1/integrations");
}

/** Shared disconnect helper — used by the Integrations card. Keeps the
 *  legacy `disconnectCalendar` in lib/calendar.ts as the underlying
 *  implementation so we don't fork the endpoint call. */
export async function disconnectIntegration(id: IntegrationId): Promise<void> {
  if (id === "google_calendar") {
    // Re-export the existing endpoint call. Same endpoint, same effect.
    await api("/v1/users/me/google-refresh-token", { method: "DELETE" });
    return;
  }
  if (id === "moodle") {
    await api("/v1/integrations/moodle/disconnect", {
      method: "DELETE",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ void_imported: false }),
    });
    return;
  }
  throw new Error(`disconnect not implemented for ${id}`);
}

// ─── Moodle connect-flow API surface ───────────────────────────────────

export interface MoodlePreviewEvent {
  external_id: string;
  title: string;
  due_at_utc: string; // naive UTC ISO
  category_hint: string | null;
}

export interface MoodlePreviewResponse {
  ok: boolean;
  error: string | null;
  count: number;
  sample: MoodlePreviewEvent[];
}

export interface MoodleConnectResponse {
  ok: boolean;
  preview_count: number;
  sync: {
    fetched: number;
    created: number;
    updated: number;
    unchanged: number;
    skipped_voided: number;
    skipped_unparseable: number;
    duplicate_existing?: number;
    error: string | null;
  };
}

export async function previewMoodle(
  ics_url: string
): Promise<MoodlePreviewResponse> {
  return api<MoodlePreviewResponse>("/v1/integrations/moodle/preview", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ ics_url }),
  });
}

export async function connectMoodle(
  ics_url: string
): Promise<MoodleConnectResponse> {
  return api<MoodleConnectResponse>("/v1/integrations/moodle/connect", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ ics_url }),
  });
}

export async function syncMoodleNow(): Promise<MoodleConnectResponse["sync"]> {
  const r = await api<MoodleConnectResponse["sync"]>(
    "/v1/integrations/moodle/sync-now",
    { method: "POST" }
  );
  return r;
}


// -----------------------------------------------------------------------
// Moodle Web Services token (Phase B 2026-05-01) — auto-detect submission
// status. Sub-capability of the Moodle integration; iCal can stay
// connected without WS, and vice versa. Backend gates the WS sync to
// users who have set the token.
// -----------------------------------------------------------------------

export interface MoodleWSConnectResponse {
  ok: boolean;
}

export interface MoodleWSSyncResponse {
  ok: boolean;
  matched: number;
  marked_complete: number;
  completion_candidates?: number;
  skipped_no_match: number;
  skipped_not_submitted: number;
  backfilled_completed: number;
  backfilled_completion_candidates?: number;
  backfilled_planned: number;
  backfilled_missed: number;
  marked_titles: string[];
  completion_candidate_titles?: string[];
  backfilled_titles: string[];
  error: string | null;
}

export async function connectMoodleWS(
  ws_token: string,
  base_url?: string,
): Promise<MoodleWSConnectResponse> {
  return api<MoodleWSConnectResponse>("/v1/integrations/moodle/ws-connect", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ ws_token, ...(base_url ? { base_url } : {}) }),
  });
}

export async function syncMoodleWSNow(): Promise<MoodleWSSyncResponse> {
  return api<MoodleWSSyncResponse>("/v1/integrations/moodle/ws-sync-now", {
    method: "POST",
  });
}

export async function disconnectMoodleWS(): Promise<void> {
  await api("/v1/integrations/moodle/ws-disconnect", { method: "DELETE" });
}
